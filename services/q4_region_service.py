#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q4 地域招聘活动画像服务
基于现有数据库在线构建：
1) 地域画像 summary/detail
2) 聚类摘要
3) 行业-地域热力矩阵
4) 职位-行业共现摘要
5) 数据质量指标
"""

from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from database.Q3 import DatabaseManager
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

try:
    import umap  # type: ignore
except Exception:  # pragma: no cover
    umap = None

logger = logging.getLogger(__name__)


@dataclass
class RegionBuildConfig:
    n_clusters: int = 4
    algorithm: str = "kmeans"
    sample_size: int = 0


class Q4RegionService:
    """Q4 地域画像核心服务"""

    TIER_ORDER = ["一线", "二线", "三线", "其他"]

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager("default")
        self._cache: Dict[Tuple[int, str, int], Dict[str, Any]] = {}

    def get_regions_summary(self, n_clusters: int = 4, algorithm: str = "kmeans", sample_size: int = 0) -> Dict[str, Any]:
        artifacts = self._build_artifacts(RegionBuildConfig(n_clusters=n_clusters, algorithm=algorithm, sample_size=sample_size))
        return {
            "regions": artifacts["summary"],
            "metadata": artifacts["metadata"],
        }

    def get_region_detail(self, region_id: str, n_clusters: int = 4, algorithm: str = "kmeans", sample_size: int = 0) -> Dict[str, Any]:
        artifacts = self._build_artifacts(RegionBuildConfig(n_clusters=n_clusters, algorithm=algorithm, sample_size=sample_size))
        return artifacts["detail_map"].get(region_id, {})

    def get_cluster_summary(self, n_clusters: int = 4, algorithm: str = "kmeans", sample_size: int = 0) -> Dict[str, Any]:
        artifacts = self._build_artifacts(RegionBuildConfig(n_clusters=n_clusters, algorithm=algorithm, sample_size=sample_size))
        return {
            "clusters": artifacts["cluster_summary"],
            "metadata": artifacts["metadata"],
        }

    def get_data_quality(self, n_clusters: int = 4, algorithm: str = "kmeans", sample_size: int = 0) -> Dict[str, Any]:
        artifacts = self._build_artifacts(RegionBuildConfig(n_clusters=n_clusters, algorithm=algorithm, sample_size=sample_size))
        return artifacts["data_quality"]

    def get_industry_region_matrix(self, top_m: int = 20, top_n: int = 15, tier: str = "all") -> Dict[str, Any]:
        top_m = max(5, min(int(top_m), 60))
        top_n = max(5, min(int(top_n), 40))

        all_rows = self.db_manager.get_city_type_statistics_by_tiers(self.TIER_ORDER)
        if not all_rows:
            return {}

        rows = [r for r in all_rows if self._tier_match(r.get("city_tier"), tier)]
        if not rows:
            return {}

        city_total = {}
        city_tier = {}
        city_industry = defaultdict(dict)
        industry_total = Counter()

        for r in rows:
            city = str(r.get("city") or "")
            ind = str(r.get("company_type") or "未知")
            if not city:
                continue
            jc = int(self._to_float(r.get("job_count")))
            total = int(self._to_float(r.get("total_jobs_in_city")))
            ratio = self._to_float(r.get("industry_ratio"))
            city_total[city] = max(city_total.get(city, 0), total)
            city_tier[city] = str(r.get("city_tier") or "其他")
            city_industry[city][ind] = {
                "count": jc,
                "ratio": ratio,
            }

        top_cities = [k for k, _ in sorted(city_total.items(), key=lambda x: x[1], reverse=True)[:top_m]]
        top_city_set = set(top_cities)
        for city in top_cities:
            for ind, info in city_industry.get(city, {}).items():
                industry_total[ind] += int(info["count"])

        top_inds = [k for k, _ in industry_total.most_common(top_n)]
        heatmap_data = []
        for c in top_cities:
            ranked = sorted(city_industry.get(c, {}).items(), key=lambda x: x[1]["count"], reverse=True)
            rank_map = {name: idx + 1 for idx, (name, _) in enumerate(ranked)}
            for ind in top_inds:
                info = city_industry.get(c, {}).get(ind, {"count": 0, "ratio": 0.0})
                heatmap_data.append(
                    {
                        "x": ind,
                        "y": c,
                        "value": float(info["ratio"]),
                        "count": int(info["count"]),
                        "city_tier": city_tier.get(c, "其他"),
                        "rank_in_region": rank_map.get(ind),
                    }
                )

        city_meta = [{"city": c, "city_tier": city_tier.get(c, "其他"), "total_jobs": city_total.get(c, 0)} for c in top_cities]
        ind_meta = [{"industry": ind, "total_jobs": int(industry_total.get(ind, 0))} for ind in top_inds]
        return {
            "tier": tier,
            "top_m": top_m,
            "top_n": top_n,
            "dimensions": {"x_axis": top_inds, "y_axis": top_cities},
            "city_meta": city_meta,
            "industry_meta": ind_meta,
            "heatmap_data": heatmap_data,
            "title": "行业-地域热力图",
        }

    def get_position_industry_cooccurrence(
        self,
        region_id: Optional[str] = None,
        top_jobs: int = 8,
        top_industries: int = 8,
    ) -> Dict[str, Any]:
        top_jobs = max(3, min(int(top_jobs), 20))
        top_industries = max(3, min(int(top_industries), 20))

        where_sql = ""
        params: Tuple[Any, ...] = tuple()
        if region_id:
            where_sql = " AND city = %s "
            params = (region_id,)

        query = f"""
            SELECT job_title, company_type, COUNT(*) AS cnt
            FROM data
            WHERE job_title IS NOT NULL
              AND company_type IS NOT NULL
              AND city IS NOT NULL
              {where_sql}
            GROUP BY job_title, company_type
        """
        rows = self._query_dict(query, params)
        if not rows:
            return {"region_id": region_id, "jobs": [], "industries": [], "matrix": [], "top_pairs": []}

        job_total = Counter()
        ind_total = Counter()
        for r in rows:
            job = str(r.get("job_title") or "")
            ind = str(r.get("company_type") or "未知")
            cnt = int(self._to_float(r.get("cnt")))
            if not job:
                continue
            job_total[job] += cnt
            ind_total[ind] += cnt

        top_job_list = [k for k, _ in job_total.most_common(top_jobs)]
        top_ind_list = [k for k, _ in ind_total.most_common(top_industries)]
        top_job_set = set(top_job_list)
        top_ind_set = set(top_ind_list)

        matrix = []
        pair_list = []
        pair_map = defaultdict(int)
        for r in rows:
            job = str(r.get("job_title") or "")
            ind = str(r.get("company_type") or "未知")
            cnt = int(self._to_float(r.get("cnt")))
            pair_map[(job, ind)] += cnt

        for j in top_job_list:
            for ind in top_ind_list:
                cnt = int(pair_map.get((j, ind), 0))
                matrix.append({"job_title": j, "industry": ind, "count": cnt})
                if cnt > 0:
                    pair_list.append({"job_title": j, "industry": ind, "count": cnt})

        pair_list.sort(key=lambda x: x["count"], reverse=True)
        return {
            "region_id": region_id,
            "jobs": top_job_list,
            "industries": top_ind_list,
            "matrix": matrix,
            "top_pairs": pair_list[:12],
        }

    def _build_artifacts(self, cfg: RegionBuildConfig) -> Dict[str, Any]:
        key = (int(cfg.n_clusters), str(cfg.algorithm).lower(), int(cfg.sample_size or 0))
        if key in self._cache:
            return self._cache[key]

        rows = self.db_manager.get_city_type_statistics_by_tiers(self.TIER_ORDER)
        if not rows:
            artifacts = {
                "summary": [],
                "detail_map": {},
                "cluster_summary": [],
                "metadata": {"n_regions": 0, "n_clusters": 0, "cluster_algorithm": cfg.algorithm},
                "data_quality": {},
            }
            self._cache[key] = artifacts
            return artifacts

        city_rows = defaultdict(list)
        for r in rows:
            city = str(r.get("city") or "")
            if city:
                city_rows[city].append(r)

        salary_map = self._fetch_salary_stats()
        edu_dist_map = self._fetch_dist("education", "education_mapping", "education_code", "education_label")
        exp_dist_map = self._fetch_dist("experience", "experience_mapping", "experience_code", "experience_label")
        top_job_map = self._fetch_top_jobs_per_city()
        position_struct_map = self._fetch_position_structure_stats()
        high_salary_share_map = self._fetch_high_salary_share_map()

        city_list = sorted(city_rows.keys())
        idx_map = {c: i for i, c in enumerate(city_list)}

        city_metric_rows: List[Dict[str, Any]] = []
        detail_map: Dict[str, Dict[str, Any]] = {}
        for city in city_list:
            rs = city_rows[city]
            tier = self._mode([str(x.get("city_tier") or "其他") for x in rs]) or "其他"
            total_jobs = int(max(self._to_float(x.get("total_jobs_in_city")) for x in rs))
            salary = salary_map.get(city, self._empty_salary())
            industry_info = sorted(
                [
                    (
                        str(x.get("company_type") or "未知"),
                        int(self._to_float(x.get("job_count"))),
                        self._to_float(x.get("industry_ratio")),
                    )
                    for x in rs
                ],
                key=lambda t: t[1],
                reverse=True,
            )
            industry_top = [
                {
                    "industry": n,
                    "count": c,
                    "prop": float(p if p > 0 else (c / max(total_jobs, 1))),
                }
                for n, c, p in industry_info[:20]
            ]

            edu_dist = edu_dist_map.get(city, {})
            exp_dist = exp_dist_map.get(city, {})
            # 优先使用 dataset 预聚合字段（city_type_statistics.*_rank），避免回到 data 明细重算
            avg_edu_rank = self._weighted_avg(rs, "avg_education_rank", "job_count")
            avg_exp_rank = self._weighted_avg(rs, "avg_experience_rank", "job_count")
            education_level = float(round(min(1.0, max(0.0, avg_edu_rank / 8.0)), 4))
            experience_demand = float(round(min(1.0, max(0.0, avg_exp_rank / 7.0)), 4))
            industry_counts = [int(it["count"]) for it in industry_top if int(it["count"]) > 0]
            industry_count = int(
                len(
                    {
                        str(n).strip()
                        for n, c, _p in industry_info
                        if int(c) > 0 and str(n).strip()
                    }
                )
            )
            industry_entropy = float(self._normalized_entropy(industry_counts))
            top_industry_share = float(max(industry_counts) / max(total_jobs, 1)) if industry_counts else 0.0
            # 兼容旧视图字段：集中度（越高越集中）
            skill_raw = float(self._skill_concentration(industry_counts))
            pos_struct = position_struct_map.get(city, {"position_entropy": 0.0, "top_position_share": 0.0})
            position_entropy = float(pos_struct.get("position_entropy", 0.0))
            top_position_share = float(pos_struct.get("top_position_share", 0.0))
            high_salary_share = float(high_salary_share_map.get(city, 0.0))
            barrier_index = float(round((education_level + experience_demand) * 0.5, 4))
            structure_index = float(round((industry_entropy + position_entropy) * 0.5, 4))
            finance_maturity = float(
                round(
                    {
                        "一线": 1.0,
                        "二线": 0.75,
                        "三线": 0.55,
                        "其他": 0.4,
                    }.get(tier, 0.4),
                    4,
                )
            )
            scale_raw = float(math.log1p(max(0, total_jobs)))

            detail_map[city] = {
                "region_id": city,
                "region_label": f"#{idx_map[city] + 1}",
                "city_tier": tier,
                "job_count": total_jobs,
                "industry_count": industry_count,
                "salary_profile": {
                    "mean": salary["salary_mean"],
                    "median": salary["salary_median"],
                    "q25": salary["salary_q25"],
                    "q75": salary["salary_q75"],
                    "std": salary["salary_std"],
                    "min": salary["salary_min"],
                    "max": salary["salary_max"],
                },
                "industry_top": industry_top,
                "position_category_top": top_job_map.get(city, [])[:10],
                "education_dist": edu_dist,
                "experience_dist": exp_dist,
                "top_similar_regions": [],
                "cluster_id": 0,
                "pca_x": 0.0,
                "pca_y": 0.0,
                "radar_metrics": {
                    "education_level": education_level,
                    "experience_demand": experience_demand,
                    "edu_threshold": education_level,
                    "exp_threshold": experience_demand,
                    "skill_concentration": 0.0,
                    "finance_maturity": finance_maturity,
                    "scale_intensity": 0.0,
                    "barrier_index": barrier_index,
                    "industry_entropy": round(industry_entropy, 4),
                    "position_entropy": round(position_entropy, 4),
                    "structure_index": structure_index,
                    "top_industry_share": round(top_industry_share, 4),
                    "top_position_share": round(top_position_share, 4),
                    "high_salary_share": round(high_salary_share, 4),
                    "log_job_count": round(scale_raw, 4),
                },
            }
            city_metric_rows.append(
                {
                    "city": city,
                    "education_level": education_level,
                    "experience_demand": experience_demand,
                    "skill_raw": skill_raw,
                    "finance_maturity": finance_maturity,
                    "scale_raw": scale_raw,
                    "log_job_count": scale_raw,
                    "industry_entropy": industry_entropy,
                    "position_entropy": position_entropy,
                    "top_industry_share": top_industry_share,
                    "top_position_share": top_position_share,
                    "barrier_index": barrier_index,
                    "high_salary_share": high_salary_share,
                }
            )

        scale_vals = [float(r["scale_raw"]) for r in city_metric_rows]
        skill_vals = [float(r["skill_raw"]) for r in city_metric_rows]
        scale_min = min(scale_vals) if scale_vals else 0.0
        scale_max = max(scale_vals) if scale_vals else 1.0
        skill_min = min(skill_vals) if skill_vals else 0.0
        skill_max = max(skill_vals) if skill_vals else 1.0
        feature_rows = []
        for row in city_metric_rows:
            scale_intensity = float(round(self._norm(float(row["scale_raw"]), scale_min, scale_max), 4))
            skill_concentration = float(round(self._norm(float(row["skill_raw"]), skill_min, skill_max), 4))
            city = str(row["city"])
            detail_map[city]["radar_metrics"]["scale_intensity"] = scale_intensity
            detail_map[city]["radar_metrics"]["skill_concentration"] = skill_concentration
            detail_map[city]["radar_metrics"]["structure_index"] = float(
                round((float(row["industry_entropy"]) + float(row["position_entropy"])) * 0.5, 4)
            )
            feature_rows.append(
                [
                    float(row["log_job_count"]),
                    float(row["industry_entropy"]),
                    float(row["position_entropy"]),
                    float(row["top_industry_share"]),
                    float(row["top_position_share"]),
                    float(row["barrier_index"]),
                    float(row["high_salary_share"]),
                ]
            )

        X = np.array(feature_rows, dtype=float)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        X = self._winsorize_matrix(X, lower=0.01, upper=0.99)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)

        n_regions = len(city_list)
        k = min(max(2, int(cfg.n_clusters)), max(2, n_regions))
        # Q4 当前实验固定使用 KMeans（前置 StandardScaler 标准化）
        algo = "kmeans"
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(Xs)
        coords, embedding_algorithm, embedding_warning = self._reduce_to_2d(Xs)
        sim = cosine_similarity(Xs)

        for i, city in enumerate(city_list):
            detail_map[city]["cluster_id"] = int(labels[i])
            detail_map[city]["pca_x"] = float(coords[i, 0])
            detail_map[city]["pca_y"] = float(coords[i, 1])

        for i, city in enumerate(city_list):
            order = np.argsort(sim[i])[::-1]
            top3 = []
            for j in order:
                if j == i:
                    continue
                other = city_list[int(j)]
                top3.append(
                    {
                        "id": other,
                        "similarity": float(round(sim[i, int(j)], 4)),
                        "cluster_id": int(labels[int(j)]),
                    }
                )
                if len(top3) >= 3:
                    break
            detail_map[city]["top_similar_regions"] = top3

        summary = []
        for city in city_list:
            d = detail_map[city]
            radar = d.get("radar_metrics", {}) or {}
            summary.append(
                {
                    "region_id": city,
                    "region_label": d["region_label"],
                    "cluster_id": d["cluster_id"],
                    "city_tier": d["city_tier"],
                    "job_count": d["job_count"],
                    "industry_count": int(d.get("industry_count", 0)),
                    "salary_mean": d["salary_profile"]["mean"],
                    "salary_median": d["salary_profile"]["median"],
                    "education_level": float(radar.get("education_level", 0.0)),
                    "experience_demand": float(radar.get("experience_demand", 0.0)),
                    "skill_concentration": float(radar.get("skill_concentration", 0.0)),
                    "finance_maturity": float(radar.get("finance_maturity", 0.0)),
                    "scale_intensity": float(radar.get("scale_intensity", 0.0)),
                    "barrier_index": float(radar.get("barrier_index", 0.0)),
                    "industry_entropy": float(radar.get("industry_entropy", 0.0)),
                    "position_entropy": float(radar.get("position_entropy", 0.0)),
                    "structure_index": float(radar.get("structure_index", 0.0)),
                    "top_industry_share": float(radar.get("top_industry_share", 0.0)),
                    "top_position_share": float(radar.get("top_position_share", 0.0)),
                    "high_salary_share": float(radar.get("high_salary_share", 0.0)),
                    "log_job_count": float(radar.get("log_job_count", 0.0)),
                    "pca_x": d["pca_x"],
                    "pca_y": d["pca_y"],
                    "industry_top": [x["industry"] for x in d["industry_top"][:3]],
                    "top_similar_regions": d["top_similar_regions"],
                }
            )

        cluster_summary = self._build_cluster_summary(summary, detail_map, label_override=None)
        data_quality = self._build_data_quality(Xs, labels, summary)
        axis_x = "PCA-1" if embedding_algorithm != "umap" else "UMAP-1"
        axis_y = "PCA-2" if embedding_algorithm != "umap" else "UMAP-2"

        metadata = {
            "n_regions": n_regions,
            "n_clusters": k,
            "cluster_algorithm": algo,
            "sample_size": int(cfg.sample_size or 0),
            "coordinate_basis": "umap_2d_projection" if embedding_algorithm == "umap" else "pca_2d_projection",
            "coordinate_axes": {
                "x": axis_x,
                "y": axis_y,
            },
            "embedding_algorithm": embedding_algorithm,
            "embedding_warning": embedding_warning,
            "clustering_features": [
                "log_job_count",
                "industry_entropy",
                "position_entropy",
                "top_industry_share",
                "top_position_share",
                "barrier_index",
                "high_salary_share",
            ],
        }

        artifacts = {
            "summary": summary,
            "detail_map": detail_map,
            "cluster_summary": cluster_summary,
            "metadata": metadata,
            "data_quality": data_quality,
        }
        self._cache[key] = artifacts
        return artifacts

    def _build_cluster_summary(
        self,
        summary: List[Dict[str, Any]],
        detail_map: Dict[str, Dict[str, Any]],
        label_override: Optional[Dict[int, str]] = None,
    ) -> List[Dict[str, Any]]:
        groups = defaultdict(list)
        for r in summary:
            groups[int(r["cluster_id"])].append(r)

        cluster_metrics = []
        result = []
        for cid, rows in sorted(groups.items(), key=lambda x: x[0]):
            region_ids = [r["region_id"] for r in rows]
            avg_job = float(np.mean([r["job_count"] for r in rows])) if rows else 0.0
            avg_salary = float(np.mean([r["salary_mean"] for r in rows])) if rows else 0.0

            edu_vals = []
            exp_vals = []
            skill_vals = []
            maturity_vals = []
            scale_vals = []
            barrier_vals = []
            ind_entropy_vals = []
            pos_entropy_vals = []
            struct_vals = []
            top_ind_share_vals = []
            top_pos_share_vals = []
            high_salary_share_vals = []
            log_job_vals = []
            for rid in region_ids:
                radar = detail_map.get(rid, {}).get("radar_metrics", {}) or {}
                edu_vals.append(float(radar.get("education_level", 0.0)))
                exp_vals.append(float(radar.get("experience_demand", 0.0)))
                skill_vals.append(float(radar.get("skill_concentration", 0.0)))
                maturity_vals.append(float(radar.get("finance_maturity", 0.0)))
                scale_vals.append(float(radar.get("scale_intensity", 0.0)))
                barrier_vals.append(float(radar.get("barrier_index", 0.0)))
                ind_entropy_vals.append(float(radar.get("industry_entropy", 0.0)))
                pos_entropy_vals.append(float(radar.get("position_entropy", 0.0)))
                struct_vals.append(float(radar.get("structure_index", 0.0)))
                top_ind_share_vals.append(float(radar.get("top_industry_share", 0.0)))
                top_pos_share_vals.append(float(radar.get("top_position_share", 0.0)))
                high_salary_share_vals.append(float(radar.get("high_salary_share", 0.0)))
                log_job_vals.append(float(radar.get("log_job_count", 0.0)))

            ind_counter = Counter()
            for rid in region_ids:
                for it in detail_map.get(rid, {}).get("industry_top", [])[:5]:
                    ind_counter[it["industry"]] += int(it.get("count", 0))
            top_ind = [k for k, _ in ind_counter.most_common(3)]

            cluster_metrics.append(
                {
                    "cluster_id": cid,
                    "avg_job_count": avg_job,
                    "education_level": float(np.mean(edu_vals) if edu_vals else 0.0),
                    "experience_demand": float(np.mean(exp_vals) if exp_vals else 0.0),
                    "skill_concentration": float(np.mean(skill_vals) if skill_vals else 0.0),
                    "finance_maturity": float(np.mean(maturity_vals) if maturity_vals else 0.0),
                    "scale_intensity": float(np.mean(scale_vals) if scale_vals else 0.0),
                    "barrier_index": float(np.mean(barrier_vals) if barrier_vals else 0.0),
                    "industry_entropy": float(np.mean(ind_entropy_vals) if ind_entropy_vals else 0.0),
                    "position_entropy": float(np.mean(pos_entropy_vals) if pos_entropy_vals else 0.0),
                    "structure_index": float(np.mean(struct_vals) if struct_vals else 0.0),
                    "top_industry_share": float(np.mean(top_ind_share_vals) if top_ind_share_vals else 0.0),
                    "top_position_share": float(np.mean(top_pos_share_vals) if top_pos_share_vals else 0.0),
                    "high_salary_share": float(np.mean(high_salary_share_vals) if high_salary_share_vals else 0.0),
                    "log_job_count": float(np.mean(log_job_vals) if log_job_vals else 0.0),
                }
            )

            result.append(
                {
                    "cluster_id": cid,
                    "cluster_label": "",
                    "region_count": len(rows),
                    "avg_salary": round(avg_salary, 2),
                    "avg_job_count": int(round(avg_job)),
                    "top_industries": top_ind,
                    "representative_regions": region_ids[:5],
                }
            )

        if label_override is None:
            # 不再使用语义化簇名，统一改为中性簇标签
            labels_by_cluster = {int(c["cluster_id"]): f"簇{int(c['cluster_id'])}" for c in cluster_metrics}
            metrics_by_cluster = {}
            for c in cluster_metrics:
                cid = int(c["cluster_id"])
                metrics_by_cluster[cid] = {
                    "education_level": round(float(c["education_level"]), 4),
                    "experience_demand": round(float(c["experience_demand"]), 4),
                    "skill_concentration": round(float(c["skill_concentration"]), 4),
                    "finance_maturity": round(float(c["finance_maturity"]), 4),
                    "scale_intensity": round(float(c.get("scale_intensity", 0.0)), 4),
                    "barrier_index": round(float(c.get("barrier_index", 0.0)), 4),
                    "industry_entropy": round(float(c.get("industry_entropy", 0.0)), 4),
                    "position_entropy": round(float(c.get("position_entropy", 0.0)), 4),
                    "structure_index": round(float(c.get("structure_index", 0.0)), 4),
                    "top_industry_share": round(float(c.get("top_industry_share", 0.0)), 4),
                    "top_position_share": round(float(c.get("top_position_share", 0.0)), 4),
                    "high_salary_share": round(float(c.get("high_salary_share", 0.0)), 4),
                    "log_job_count": round(float(c.get("log_job_count", 0.0)), 4),
                    # 语义别名，便于后续分析导出
                    "edu_threshold": round(float(c["education_level"]), 4),
                    "exp_threshold": round(float(c["experience_demand"]), 4),
                }
        else:
            labels_by_cluster = {int(k): str(v) for k, v in label_override.items()}
            metrics_by_cluster = {}
            for c in cluster_metrics:
                cid = int(c["cluster_id"])
                metrics_by_cluster[cid] = {
                    "education_level": round(float(c["education_level"]), 4),
                    "experience_demand": round(float(c["experience_demand"]), 4),
                    "skill_concentration": round(float(c["skill_concentration"]), 4),
                    "finance_maturity": round(float(c["finance_maturity"]), 4),
                    "scale_intensity": round(float(c.get("scale_intensity", 0.0)), 4),
                    "barrier_index": round(float(c.get("barrier_index", 0.0)), 4),
                    "industry_entropy": round(float(c.get("industry_entropy", 0.0)), 4),
                    "position_entropy": round(float(c.get("position_entropy", 0.0)), 4),
                    "structure_index": round(float(c.get("structure_index", 0.0)), 4),
                    "top_industry_share": round(float(c.get("top_industry_share", 0.0)), 4),
                    "top_position_share": round(float(c.get("top_position_share", 0.0)), 4),
                    "high_salary_share": round(float(c.get("high_salary_share", 0.0)), 4),
                    "log_job_count": round(float(c.get("log_job_count", 0.0)), 4),
                    "edu_threshold": round(float(c["education_level"]), 4),
                    "exp_threshold": round(float(c["experience_demand"]), 4),
                }
        for item in result:
            cid = int(item["cluster_id"])
            item["cluster_label"] = labels_by_cluster.get(cid, f"簇{cid}")
            item["profile_scores"] = metrics_by_cluster.get(cid, {})
        return result

    def _get_q4_archetypes(self) -> Dict[str, Dict[str, float]]:
        return {
            "高端人才型": {
                "education_level": 0.90,
                "experience_demand": 0.90,
                "skill_concentration": 0.85,
                "finance_maturity": 0.85,
                "scale_intensity": 0.55,
            },
            "技能驱动型": {
                "education_level": 0.72,
                "experience_demand": 0.68,
                "skill_concentration": 0.95,
                "finance_maturity": 0.60,
                "scale_intensity": 0.52,
            },
            "均衡发展型": {
                "education_level": 0.60,
                "experience_demand": 0.60,
                "skill_concentration": 0.60,
                "finance_maturity": 0.60,
                "scale_intensity": 0.60,
            },
            "需求规模集聚型": {
                "education_level": 0.48,
                "experience_demand": 0.55,
                "skill_concentration": 0.45,
                "finance_maturity": 0.58,
                "scale_intensity": 0.95,
            },
            "基础岗位普及型": {
                "education_level": 0.22,
                "experience_demand": 0.22,
                "skill_concentration": 0.20,
                "finance_maturity": 0.25,
                "scale_intensity": 0.45,
            },
        }

    def _assign_city_archetype_labels(
        self,
        city_list: List[str],
        detail_map: Dict[str, Dict[str, Any]],
    ) -> Tuple[np.ndarray, Dict[int, str]]:
        archetypes = self._get_q4_archetypes()
        label_order = list(archetypes.keys())
        keys = ["education_level", "experience_demand", "skill_concentration", "finance_maturity", "scale_intensity"]

        cluster_ids = []
        used_ids = set()
        for city in city_list:
            radar = detail_map.get(city, {}).get("radar_metrics", {}) or {}
            vec = {k: float(radar.get(k, 0.0)) for k in keys}
            best_idx = 0
            best_dist = None
            for i, label in enumerate(label_order):
                target = archetypes[label]
                dist = 0.0
                for k in keys:
                    dist += (vec[k] - float(target[k])) ** 2
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_idx = i
            cluster_ids.append(best_idx)
            used_ids.add(best_idx)

        id_to_label = {i: label_order[i] for i in sorted(used_ids)}
        return np.array(cluster_ids, dtype=int), id_to_label

    def _build_grouped_layout_projection(
        self,
        Xs: np.ndarray,
        labels: np.ndarray,
    ) -> Tuple[np.ndarray, str, Optional[str]]:
        base, _, _ = self._reduce_to_2d(Xs)
        n = len(base)
        if n == 0:
            return base, "prototype_grouped", "原型分型布局（无样本）"

        coords = np.zeros_like(base)
        unique_labels = sorted(set(int(x) for x in labels.tolist()))
        m = max(1, len(unique_labels))
        radius = 8.0
        for idx, cid in enumerate(unique_labels):
            angle = 2.0 * math.pi * idx / m
            center = np.array([radius * math.cos(angle), radius * math.sin(angle)], dtype=float)
            mask = labels == cid
            sub = base[mask]
            if len(sub) == 0:
                continue
            sub_center = np.mean(sub, axis=0, keepdims=True)
            sub_shift = sub - sub_center
            std = float(np.std(sub_shift))
            scale = std if std > 1e-6 else 1.0
            coords[mask] = center + (sub_shift / scale) * 1.15

        return coords, "prototype_grouped", "按原型分型分组布局（同类型自动聚拢）"

    def _assign_q4_cluster_labels(self, cluster_metrics: List[Dict[str, float]]) -> Tuple[Dict[int, str], Dict[int, Dict[str, float]]]:
        if not cluster_metrics:
            return {}, {}

        metrics_by_cluster: Dict[int, Dict[str, float]] = {}
        for c in cluster_metrics:
            cid = int(c["cluster_id"])
            metrics_by_cluster[cid] = {
                "education_level": round(float(c["education_level"]), 4),
                "experience_demand": round(float(c["experience_demand"]), 4),
                "skill_concentration": round(float(c["skill_concentration"]), 4),
                "finance_maturity": round(float(c["finance_maturity"]), 4),
                "scale_intensity": round(float(c.get("scale_intensity", 0.0)), 4),
            }

        archetypes = self._get_q4_archetypes()

        keys = ["education_level", "experience_demand", "skill_concentration", "finance_maturity", "scale_intensity"]

        dist_map: Dict[int, Dict[str, float]] = {}
        for cid, vec in metrics_by_cluster.items():
            dist_map[cid] = {}
            for label, target in archetypes.items():
                dist = 0.0
                for k in keys:
                    dist += (float(vec.get(k, 0.0)) - float(target.get(k, 0.0))) ** 2
                dist_map[cid][label] = dist

        assignments: Dict[int, str] = {}
        used_clusters = set()
        used_labels = set()

        all_pairs = []
        for cid, label_dist in dist_map.items():
            for label, dist in label_dist.items():
                all_pairs.append((dist, cid, label))
        all_pairs.sort(key=lambda x: x[0])

        for _, cid, label in all_pairs:
            if cid in used_clusters or label in used_labels:
                continue
            assignments[cid] = label
            used_clusters.add(cid)
            used_labels.add(label)
            if len(used_clusters) == len(cluster_metrics) or len(used_labels) == len(archetypes):
                break

        for cid in metrics_by_cluster.keys():
            if cid in assignments:
                continue
            best = min(dist_map[cid].items(), key=lambda x: x[1])[0]
            assignments[cid] = best

        return assignments, metrics_by_cluster

    def _build_data_quality(self, Xs: np.ndarray, labels: np.ndarray, summary: List[Dict[str, Any]]) -> Dict[str, Any]:
        score_sil = None
        score_db = None
        if len(summary) > 2 and len(set(labels.tolist())) > 1:
            try:
                score_sil = float(silhouette_score(Xs, labels))
            except Exception:
                score_sil = None
            try:
                score_db = float(davies_bouldin_score(Xs, labels))
            except Exception:
                score_db = None

        missing_rates = self._fetch_missing_rates()
        sim_mean = float(np.mean(cosine_similarity(Xs))) if len(summary) else 0.0
        return {
            "missing_rate_by_field": missing_rates,
            "silhouette_score": score_sil,
            "davies_bouldin_index": score_db,
            "similarity_matrix_mean": round(sim_mean, 4),
            "region_count": len(summary),
        }

    def _fetch_missing_rates(self) -> Dict[str, float]:
        cols = ["job_title", "city", "salary", "experience", "education", "company", "company_type"]
        ratios = {}
        for c in cols:
            q = f"SELECT AVG(CASE WHEN {c} IS NULL OR {c}='' THEN 1 ELSE 0 END) AS miss_rate FROM data"
            rows = self._query_dict(q)
            ratios[c] = round(self._to_float(rows[0].get("miss_rate")) if rows else 0.0, 4)
        return ratios

    def _fetch_salary_stats(self) -> Dict[str, Dict[str, float]]:
        # 优先使用 dataset 预处理产物（cluster_by_city），其中薪资已区间数值化
        query_pre_agg = """
            SELECT
                city,
                avg_salary,
                min_annual_salary,
                max_annual_salary,
                job_in_city_cnt
            FROM cluster_by_city
            WHERE city IS NOT NULL
              AND avg_salary IS NOT NULL
        """
        try:
            rows = self._query_dict(query_pre_agg)
            if rows:
                city_vals: Dict[str, List[Tuple[float, float, float, float]]] = defaultdict(list)
                for r in rows:
                    city = str(r.get("city") or "")
                    if not city:
                        continue
                    avg_salary = self._to_float(r.get("avg_salary"))
                    smin = self._to_float(r.get("min_annual_salary"))
                    smax = self._to_float(r.get("max_annual_salary"))
                    w = max(1.0, self._to_float(r.get("job_in_city_cnt")))
                    city_vals[city].append((avg_salary, smin, smax, w))

                out = {}
                for city, items in city_vals.items():
                    weights = np.array([it[3] for it in items], dtype=float)
                    vals = np.array([it[0] for it in items], dtype=float)
                    total_w = float(weights.sum()) if len(weights) else 0.0
                    if total_w <= 0:
                        continue
                    mean = float(np.average(vals, weights=weights))
                    var = float(np.average((vals - mean) ** 2, weights=weights))
                    std = math.sqrt(max(var, 0.0))

                    order = np.argsort(vals)
                    sorted_vals = vals[order]
                    sorted_w = weights[order]
                    cum_w = np.cumsum(sorted_w)

                    def weighted_q(q: float) -> float:
                        if len(sorted_vals) == 0:
                            return 0.0
                        target = q * total_w
                        idx = int(np.searchsorted(cum_w, target, side="left"))
                        idx = max(0, min(idx, len(sorted_vals) - 1))
                        return float(sorted_vals[idx])

                    city_min = float(min(it[1] for it in items))
                    city_max = float(max(it[2] for it in items))
                    q25 = weighted_q(0.25)
                    q50 = weighted_q(0.50)
                    q75 = weighted_q(0.75)
                    out[city] = {
                        "salary_mean": round(mean, 2),
                        "salary_median": round(q50, 2),
                        "salary_q25": round(q25, 2),
                        "salary_q75": round(q75, 2),
                        "salary_std": round(std, 2),
                        "salary_min": round(city_min, 2),
                        "salary_max": round(city_max, 2),
                    }
                if out:
                    return out
        except Exception as e:
            logger.warning(f"读取 cluster_by_city 薪资失败，回退 data 明细薪资解析: {e}")

        # 回退逻辑：从 data 解析薪资
        expr = """COALESCE(
                median_annual_salary,
                (CAST(SUBSTRING_INDEX(salary, '-', 1) AS UNSIGNED) +
                 CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(salary, '-', 2), '-', -1) AS UNSIGNED)) / 2
            )"""
        query = f"""
            SELECT
                city,
                COUNT(*) AS cnt,
                AVG({expr}) AS salary_mean,
                MIN({expr}) AS salary_min,
                MAX({expr}) AS salary_max,
                STDDEV_POP({expr}) AS salary_std
            FROM data
            WHERE city IS NOT NULL
              AND ({expr}) IS NOT NULL
            GROUP BY city
        """
        rows = self._query_dict(query)
        out = {}
        for r in rows:
            city = str(r.get("city") or "")
            if not city:
                continue
            mean = self._to_float(r.get("salary_mean"))
            smin = self._to_float(r.get("salary_min"))
            smax = self._to_float(r.get("salary_max"))
            sstd = self._to_float(r.get("salary_std"))
            q25 = max(smin, mean - 0.674 * sstd)
            q75 = min(smax, mean + 0.674 * sstd)
            out[city] = {
                "salary_mean": round(mean, 2),
                "salary_median": round(mean, 2),
                "salary_q25": round(q25, 2),
                "salary_q75": round(q75, 2),
                "salary_std": round(sstd, 2),
                "salary_min": round(smin, 2),
                "salary_max": round(smax, 2),
            }
        return out

    def _fetch_dist(self, field: str, map_table: str, code_col: str, label_col: str) -> Dict[str, Dict[str, float]]:
        query = f"""
            SELECT d.city, COALESCE(m.{label_col}, d.{field}, '未知') AS label, COUNT(*) AS cnt
            FROM data d
            LEFT JOIN {map_table} m ON d.{field} = m.{code_col}
            WHERE d.city IS NOT NULL
            GROUP BY d.city, COALESCE(m.{label_col}, d.{field}, '未知')
        """
        rows = self._query_dict(query)
        city_counter = defaultdict(Counter)
        for r in rows:
            city = str(r.get("city") or "")
            label = str(r.get("label") or "未知")
            cnt = int(self._to_float(r.get("cnt")))
            if city:
                city_counter[city][label] += cnt
        out = {}
        for city, counter in city_counter.items():
            total = sum(counter.values()) or 1
            out[city] = {k: round(v / total, 4) for k, v in counter.items()}
        return out

    def _fetch_top_jobs_per_city(self) -> Dict[str, List[Dict[str, Any]]]:
        query = """
            SELECT city, job_title, COUNT(*) AS cnt
            FROM data
            WHERE city IS NOT NULL AND job_title IS NOT NULL
            GROUP BY city, job_title
        """
        rows = self._query_dict(query)
        city_counter = defaultdict(Counter)
        for r in rows:
            city = str(r.get("city") or "")
            job = str(r.get("job_title") or "")
            cnt = int(self._to_float(r.get("cnt")))
            if city and job:
                city_counter[city][job] += cnt
        out = {}
        for city, counter in city_counter.items():
            total = sum(counter.values()) or 1
            out[city] = [
                {"category": job, "count": cnt, "prop": round(cnt / total, 4)}
                for job, cnt in counter.most_common(10)
            ]
        return out

    def _fetch_position_structure_stats(self) -> Dict[str, Dict[str, float]]:
        query = """
            SELECT city, job_title, COUNT(*) AS cnt
            FROM data
            WHERE city IS NOT NULL AND job_title IS NOT NULL
            GROUP BY city, job_title
        """
        rows = self._query_dict(query)
        city_counter = defaultdict(Counter)
        for r in rows:
            city = str(r.get("city") or "")
            job = str(r.get("job_title") or "")
            cnt = int(self._to_float(r.get("cnt")))
            if city and job and cnt > 0:
                city_counter[city][job] += cnt

        out: Dict[str, Dict[str, float]] = {}
        for city, counter in city_counter.items():
            counts = [int(v) for v in counter.values() if int(v) > 0]
            total = float(sum(counts))
            top_share = (max(counts) / total) if total > 0 and counts else 0.0
            out[city] = {
                "position_entropy": round(self._normalized_entropy(counts), 4),
                "top_position_share": round(float(top_share), 4),
            }
        return out

    def _fetch_high_salary_share_map(self) -> Dict[str, float]:
        # 以全体岗位薪资的 P75 作为高薪阈值，统计各城市高薪岗位占比
        query_pre_agg = """
            SELECT city, avg_salary, job_in_city_cnt
            FROM cluster_by_city
            WHERE city IS NOT NULL AND avg_salary IS NOT NULL
        """
        try:
            rows = self._query_dict(query_pre_agg)
            if rows:
                city_pairs = defaultdict(list)
                all_pairs = []
                for r in rows:
                    city = str(r.get("city") or "")
                    if not city:
                        continue
                    s = self._to_float(r.get("avg_salary"))
                    w = max(1.0, self._to_float(r.get("job_in_city_cnt")))
                    city_pairs[city].append((s, w))
                    all_pairs.append((s, w))
                p75 = self._weighted_quantile(all_pairs, q=0.75)
                out: Dict[str, float] = {}
                for city, pairs in city_pairs.items():
                    total_w = float(sum(w for _, w in pairs))
                    high_w = float(sum(w for s, w in pairs if s >= p75))
                    out[city] = round((high_w / total_w) if total_w > 0 else 0.0, 4)
                if out:
                    return out
        except Exception as e:
            logger.warning(f"读取 cluster_by_city 高薪占比失败，回退 data 明细薪资解析: {e}")

        expr = """COALESCE(
                median_annual_salary,
                (CAST(SUBSTRING_INDEX(salary, '-', 1) AS UNSIGNED) +
                 CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(salary, '-', 2), '-', -1) AS UNSIGNED)) / 2
            )"""
        query = f"""
            SELECT city, {expr} AS salary_value
            FROM data
            WHERE city IS NOT NULL
              AND ({expr}) IS NOT NULL
        """
        rows = self._query_dict(query)
        if not rows:
            return {}
        city_vals = defaultdict(list)
        all_vals = []
        for r in rows:
            city = str(r.get("city") or "")
            val = self._to_float(r.get("salary_value"))
            if city and val > 0:
                city_vals[city].append(val)
                all_vals.append(val)
        if not all_vals:
            return {}
        p75 = float(np.quantile(np.array(all_vals, dtype=float), 0.75))
        out = {}
        for city, vals in city_vals.items():
            n = len(vals)
            if n <= 0:
                out[city] = 0.0
                continue
            high = sum(1 for v in vals if v >= p75)
            out[city] = round(high / n, 4)
        return out

    def _reduce_to_2d(self, Xs: np.ndarray) -> Tuple[np.ndarray, str, Optional[str]]:
        n, d = Xs.shape
        if n <= 2:
            pad = np.zeros((n, 2), dtype=float)
            if n == 1:
                return pad, "pca_fallback", None
            pad[:, : min(2, d)] = Xs[:, : min(2, d)]
            return pad, "pca_fallback", None
        pca_dim = min(20, d, n - 1)
        pca = PCA(n_components=pca_dim, random_state=42)
        Xp = pca.fit_transform(Xs)
        # 按当前实验要求：固定使用 PCA 便于与 UMAP 做可控对比
        p2 = PCA(n_components=2, random_state=42)
        return p2.fit_transform(Xp), "pca_forced", "按实验设置固定使用 PCA（未启用 UMAP）"

    def _query_dict(self, query: str, params: Tuple[Any, ...] = tuple()) -> List[Dict[str, Any]]:
        with self.db_manager.get_connection() as conn:
            import pymysql

            cur = conn.cursor(pymysql.cursors.DictCursor)
            try:
                cur.execute(query, params)
                return cur.fetchall() or []
            finally:
                cur.close()

    def _tier_match(self, city_tier: Any, tier: str) -> bool:
        if tier == "all":
            return True
        t = str(city_tier or "其他").strip()
        mapper = {
            "first_tier": "一线",
            "second_tier": "二线",
            "third_tier": "三线",
            "other": "其他",
        }
        return t == mapper.get(tier, tier)

    def _mode(self, arr: List[str]) -> str:
        if not arr:
            return ""
        return Counter(arr).most_common(1)[0][0]

    def _weighted_avg(self, rows: List[Dict[str, Any]], vkey: str, wkey: str) -> float:
        num = 0.0
        den = 0.0
        for r in rows:
            v = self._to_float(r.get(vkey))
            w = self._to_float(r.get(wkey))
            num += v * w
            den += w
        return round(num / den, 4) if den else 0.0

    def _entropy(self, counts: List[int]) -> float:
        total = float(sum(max(0, int(c)) for c in counts))
        if total <= 0:
            return 0.0
        ent = 0.0
        for c in counts:
            if c <= 0:
                continue
            p = c / total
            ent -= p * math.log(p + 1e-12)
        return round(ent, 4)

    def _normalized_entropy(self, counts: List[int]) -> float:
        positive = [max(0, int(c)) for c in counts if int(c) > 0]
        if not positive:
            return 0.0
        n = len(positive)
        if n <= 1:
            return 0.0
        ent = self._entropy(positive)
        max_ent = math.log(float(n))
        if max_ent <= 0:
            return 0.0
        return max(0.0, min(1.0, float(ent / max_ent)))

    def _skill_concentration(self, counts: List[int]) -> float:
        """
        用行业占比集中度近似“技能集中度”：
        - 先计算 HHI = sum(p^2)
        - 再归一化到 [0, 1]，值越高表示越集中
        """
        positive = [max(0, int(c)) for c in counts if int(c) > 0]
        if not positive:
            return 0.0
        total = float(sum(positive))
        if total <= 0:
            return 0.0
        n = len(positive)
        probs = [c / total for c in positive]
        hhi = float(sum(p * p for p in probs))
        if n <= 1:
            return 1.0
        baseline = 1.0 / float(n)
        return max(0.0, min(1.0, (hhi - baseline) / (1.0 - baseline)))

    def _weighted_quantile(self, pairs: List[Tuple[float, float]], q: float) -> float:
        if not pairs:
            return 0.0
        q = max(0.0, min(1.0, float(q)))
        clean = [(float(v), max(0.0, float(w))) for v, w in pairs if float(w) > 0]
        if not clean:
            return 0.0
        clean.sort(key=lambda x: x[0])
        vals = np.array([v for v, _ in clean], dtype=float)
        ws = np.array([w for _, w in clean], dtype=float)
        cum = np.cumsum(ws)
        total = float(cum[-1])
        if total <= 0:
            return float(vals[-1])
        target = q * total
        idx = int(np.searchsorted(cum, target, side="left"))
        idx = max(0, min(idx, len(vals) - 1))
        return float(vals[idx])

    def _winsorize_matrix(self, X: np.ndarray, lower: float = 0.01, upper: float = 0.99) -> np.ndarray:
        if X.size == 0:
            return X
        lo = max(0.0, min(1.0, float(lower)))
        hi = max(0.0, min(1.0, float(upper)))
        if hi < lo:
            lo, hi = hi, lo
        Xw = X.copy()
        for j in range(Xw.shape[1]):
            col = Xw[:, j]
            if col.size == 0:
                continue
            ql = float(np.quantile(col, lo))
            qh = float(np.quantile(col, hi))
            if qh < ql:
                ql, qh = qh, ql
            Xw[:, j] = np.clip(col, ql, qh)
        return Xw

    @staticmethod
    def _norm(v: float, vmin: float, vmax: float) -> float:
        if vmax <= vmin:
            return 0.5
        x = (v - vmin) / (vmax - vmin)
        return max(0.0, min(1.0, float(x)))

    def _avg_dist_rank(self, dist: Dict[str, float]) -> float:
        if not dist:
            return 0.0
        mapper = {
            "小学": 1,
            "初中": 2,
            "高中": 3,
            "大专": 4,
            "本科": 5,
            "硕士": 6,
            "博士": 7,
            "博士以上": 8,
            "无经验": 1,
            "应届生": 2,
            "1-3年": 3,
            "3-5年": 4,
            "5-7年": 5,
            "7年以上": 6,
            "7-10年": 6,
            "10年以上": 7,
        }
        num = 0.0
        den = 0.0
        for k, v in dist.items():
            r = mapper.get(k, 4)
            num += r * float(v)
            den += float(v)
        return num / den if den else 0.0

    def _to_float(self, value: Any) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except Exception:
            return 0.0

    def _empty_salary(self) -> Dict[str, float]:
        return {
            "salary_mean": 0.0,
            "salary_median": 0.0,
            "salary_q25": 0.0,
            "salary_q75": 0.0,
            "salary_std": 0.0,
            "salary_min": 0.0,
            "salary_max": 0.0,
        }
