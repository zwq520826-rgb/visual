#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q5 引力网络图服务
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from database.Q3 import DatabaseManager

logger = logging.getLogger(__name__)


class Q5ForceGraphService:
    """Q5 引力网络图业务服务"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _rank_to_norm(rank_value: float) -> float:
        """将经验/学历 rank 统一为 0~1 刻度。"""
        if rank_value <= 0:
            return 0.0
        if rank_value <= 1:
            return min(1.0, rank_value)
        # 当前项目 rank 多为 10 分制
        return min(1.0, rank_value / 10.0)

    @staticmethod
    def _interpolate_color(t: float) -> str:
        """冷暖薪资色带：低薪冷色(蓝) -> 高薪暖色(橙红)。"""
        t = max(0.0, min(1.0, t))
        c0 = (59, 130, 246)   # cool blue
        c1 = (239, 68, 68)    # warm red
        r = int(c0[0] + (c1[0] - c0[0]) * t)
        g = int(c0[1] + (c1[1] - c0[1]) * t)
        b = int(c0[2] + (c1[2] - c0[2]) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _mix_with_white(hex_color: str, ratio: float = 0.55) -> str:
        """将颜色与白色混合，ratio 越大越浅。"""
        ratio = max(0.0, min(1.0, ratio))
        c = hex_color.lstrip("#")
        if len(c) != 6:
            return hex_color
        r = int(c[0:2], 16)
        g = int(c[2:4], 16)
        b = int(c[4:6], 16)
        r2 = int(r + (255 - r) * ratio)
        g2 = int(g + (255 - g) * ratio)
        b2 = int(b + (255 - b) * ratio)
        return f"#{r2:02x}{g2:02x}{b2:02x}"

    @staticmethod
    def _scale_value(value: float, min_v: float, max_v: float, out_min: float, out_max: float) -> float:
        if max_v <= min_v:
            return (out_min + out_max) / 2.0
        ratio = (value - min_v) / (max_v - min_v)
        ratio = max(0.0, min(1.0, ratio))
        return out_min + (out_max - out_min) * ratio

    def _load_rank_label_mapping(self) -> Tuple[List[Tuple[float, str]], List[Tuple[float, str]]]:
        """读取学历/经验 rank 标签映射。"""
        try:
            edu_query = """
                SELECT education_rank, education_label
                FROM education_mapping
                WHERE education_rank IS NOT NULL AND education_label IS NOT NULL
            """
            exp_query = """
                SELECT experience_rank, experience_label
                FROM experience_mapping
                WHERE experience_rank IS NOT NULL AND experience_label IS NOT NULL
            """

            edu_rows = self.db_manager.execute_query(edu_query)
            exp_rows = self.db_manager.execute_query(exp_query)

            edu_map = [(self._safe_float(r[0]), str(r[1])) for r in edu_rows]
            exp_map = [(self._safe_float(r[0]), str(r[1])) for r in exp_rows]
            return edu_map, exp_map
        except Exception as e:
            logger.warning("读取学历/经验映射表失败，将仅返回 rank 数值: %s", e)
            return [], []

    def _resolve_rank_label(self, rank_value: float, mapping: List[Tuple[float, str]]) -> str:
        if not mapping:
            return "-"
        # rank 可能是 0~1 或 0~10，先做尺度对齐再最近匹配
        max_rank = max(x[0] for x in mapping) if mapping else 10.0
        candidate = rank_value
        if candidate <= 1.0 and max_rank > 1.0:
            candidate = candidate * max_rank
        nearest = min(mapping, key=lambda x: abs(x[0] - candidate))
        return nearest[1]

    def get_emerging_jobs(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        获取新兴职位 TopN：
        - 与现有 Q5 排名口径一致：education_norm * records_count_norm * experience_norm
        - 同时补充卡片展示所需字段（records_count/education_label/experience_label）
        """
        top_n = max(1, min(int(top_n), 50))
        # 只取高代表性候选，避免全表聚合导致接口超时
        query = """
            SELECT
                job_title,
                MAX(records_count) AS records_count,
                MAX(records_count_norm) AS records_count_norm,
                AVG(avg_education_rank) AS avg_education_rank,
                AVG(avg_experience_rank) AS avg_experience_rank
            FROM job_summary
            WHERE job_title IS NOT NULL
              AND records_count_norm IS NOT NULL
              AND avg_education_rank IS NOT NULL
              AND avg_experience_rank IS NOT NULL
            GROUP BY job_title
            ORDER BY MAX(records_count) DESC
            LIMIT 800
        """
        rows = self.db_manager.execute_query(query)

        if not rows:
            return []

        edu_map, exp_map = self._load_rank_label_mapping()
        jobs: List[Dict[str, Any]] = []
        for row in rows:
            job_title = str(row[0])
            records_count = self._safe_int(row[1], 0)
            records_count_norm = self._safe_float(row[2], 0.0)
            avg_education_rank = self._safe_float(row[3], 0.0)
            avg_experience_rank = self._safe_float(row[4], 0.0)
            education_norm = self._rank_to_norm(avg_education_rank)
            experience_norm = self._rank_to_norm(avg_experience_rank)
            composite_score = education_norm * records_count_norm * experience_norm
            jobs.append(
                {
                    "job_title": job_title,
                    "records_count": records_count,
                    "records_count_norm": records_count_norm,
                    "avg_education_rank": avg_education_rank,
                    "avg_experience_rank": avg_experience_rank,
                    "education_label": self._resolve_rank_label(avg_education_rank, edu_map),
                    "experience_label": self._resolve_rank_label(avg_experience_rank, exp_map),
                    "education_norm": education_norm,
                    "experience_norm": experience_norm,
                    "composite_score": composite_score,
                }
            )

        jobs.sort(key=lambda x: x["composite_score"], reverse=True)
        return jobs[:top_n]

    def get_contrast_jobs(self, top_n: int = 6, emerging_top_n: int = 5) -> List[Dict[str, Any]]:
        """
        获取用于与新兴职位对比的岗位（非新兴）：
        - 从 job_summary 全量岗位中计算同口径 composite_score
        - 排除新兴 TopN（emerging_top_n）
        - 优先选择“规模较大且综合分相对温和”的岗位，便于形成对比
        """
        top_n = max(3, min(int(top_n), 10))
        emerging_top_n = max(1, min(int(emerging_top_n), 20))

        query = """
            SELECT
                job_title,
                MAX(records_count) AS records_count,
                MAX(records_count_norm) AS records_count_norm,
                AVG(avg_education_rank) AS avg_education_rank,
                AVG(avg_experience_rank) AS avg_experience_rank
            FROM job_summary
            WHERE job_title IS NOT NULL
              AND records_count_norm IS NOT NULL
              AND avg_education_rank IS NOT NULL
              AND avg_experience_rank IS NOT NULL
            GROUP BY job_title
        """
        rows = self.db_manager.execute_query(query)
        if not rows:
            return []

        edu_map, exp_map = self._load_rank_label_mapping()
        jobs: List[Dict[str, Any]] = []
        for row in rows:
            job_title = str(row[0])
            records_count = self._safe_int(row[1], 0)
            records_count_norm = self._safe_float(row[2], 0.0)
            avg_education_rank = self._safe_float(row[3], 0.0)
            avg_experience_rank = self._safe_float(row[4], 0.0)
            education_norm = self._rank_to_norm(avg_education_rank)
            experience_norm = self._rank_to_norm(avg_experience_rank)
            composite_score = education_norm * records_count_norm * experience_norm
            jobs.append(
                {
                    "job_title": job_title,
                    "records_count": records_count,
                    "records_count_norm": records_count_norm,
                    "avg_education_rank": avg_education_rank,
                    "avg_experience_rank": avg_experience_rank,
                    "education_label": self._resolve_rank_label(avg_education_rank, edu_map),
                    "experience_label": self._resolve_rank_label(avg_experience_rank, exp_map),
                    "education_norm": education_norm,
                    "experience_norm": experience_norm,
                    "composite_score": composite_score,
                }
            )

        jobs.sort(key=lambda x: x["composite_score"], reverse=True)
        emerging_titles = {j["job_title"] for j in jobs[:emerging_top_n]}
        candidates = [j for j in jobs if j["job_title"] not in emerging_titles and j.get("records_count", 0) > 0]
        if not candidates:
            return []

        # 先剔除极小样本噪声，再做“多样性挑选”
        counts_all = sorted([self._safe_int(j.get("records_count"), 0) for j in candidates])
        if counts_all:
            q20_idx = max(0, min(len(counts_all) - 1, int(len(counts_all) * 0.2)))
            count_q20 = counts_all[q20_idx]
            pool = [j for j in candidates if self._safe_int(j.get("records_count"), 0) >= count_q20]
        else:
            pool = candidates
        if len(pool) < top_n:
            pool = candidates

        # 特征归一化（用于多样性距离）
        rc_vals = [math.log1p(max(0, self._safe_int(j.get("records_count"), 0))) for j in pool]
        edu_vals = [self._safe_float(j.get("education_norm"), 0.0) for j in pool]
        exp_vals = [self._safe_float(j.get("experience_norm"), 0.0) for j in pool]
        sc_vals = [self._safe_float(j.get("composite_score"), 0.0) for j in pool]

        def _norm(v: float, arr: List[float]) -> float:
            if not arr:
                return 0.0
            lo = min(arr)
            hi = max(arr)
            if hi <= lo:
                return 0.5
            return (v - lo) / (hi - lo)

        vectors: Dict[str, List[float]] = {}
        for j in pool:
            key = j["job_title"]
            vectors[key] = [
                _norm(math.log1p(max(0, self._safe_int(j.get("records_count"), 0))), rc_vals),
                _norm(self._safe_float(j.get("education_norm"), 0.0), edu_vals),
                _norm(self._safe_float(j.get("experience_norm"), 0.0), exp_vals),
                _norm(self._safe_float(j.get("composite_score"), 0.0), sc_vals),
            ]

        def _dist(a: List[float], b: List[float]) -> float:
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

        # 初始种子：
        # 1) 最大规模岗位
        # 2) 低综合分代表（但规模不太小）
        picked_titles: List[str] = []
        by_count = sorted(pool, key=lambda j: self._safe_int(j.get("records_count"), 0), reverse=True)
        if by_count:
            picked_titles.append(by_count[0]["job_title"])

        half = by_count[: max(1, len(by_count) // 2)]
        if half:
            low_score = min(half, key=lambda j: self._safe_float(j.get("composite_score"), 0.0))
            if low_score["job_title"] not in picked_titles:
                picked_titles.append(low_score["job_title"])

        # 迭代选取：最大化与已选集合的最小距离（max-min diversity）
        while len(picked_titles) < top_n:
            best_title = None
            best_score = -1.0
            for j in pool:
                t = j["job_title"]
                if t in picked_titles:
                    continue
                v = vectors[t]
                if not picked_titles:
                    d_min = 0.0
                else:
                    d_min = min(_dist(v, vectors[s]) for s in picked_titles)
                # 轻微偏向有代表性的规模岗位，避免全是小众样本
                rep_bonus = 0.15 * vectors[t][0]
                score = d_min + rep_bonus
                if score > best_score:
                    best_score = score
                    best_title = t
            if not best_title:
                break
            picked_titles.append(best_title)

        picked_map = {j["job_title"]: j for j in pool}
        picked = [picked_map[t] for t in picked_titles if t in picked_map][:top_n]

        # 简单标签，便于前端展示差异
        for j in picked:
            rc = vectors[j["job_title"]][0]
            edu = vectors[j["job_title"]][1]
            exp = vectors[j["job_title"]][2]
            if rc >= 0.7 and (edu + exp) / 2 <= 0.45:
                tag = "高规模普及型"
            elif rc <= 0.45 and (edu + exp) / 2 >= 0.65:
                tag = "高门槛小众型"
            elif (edu + exp) / 2 >= 0.6:
                tag = "技能门槛型"
            else:
                tag = "常规对比型"
            j["contrast_tag"] = tag

        return picked

    def get_job_industry_force(
        self,
        job_title: str,
        top_k_industry: int = 12,
        city_tier: str = "all",
    ) -> Dict[str, Any]:
        """获取单岗位行业引力网络。"""
        if not job_title:
            raise ValueError("job_title 不能为空")

        top_k_industry = max(3, min(int(top_k_industry), 30))
        tier_filter = (city_tier or "all").strip()

        params: List[Any] = [job_title]
        tier_sql = ""
        if tier_filter and tier_filter.lower() != "all":
            tier_sql = " AND city_tier = %s "
            params.append(tier_filter)

        # 岗位总体规模 / 薪资
        summary_query = f"""
            SELECT
                COUNT(*) AS job_total_count,
                AVG(median_annual_salary) AS job_salary_mean
            FROM data
            WHERE job_title = %s
              AND company_type IS NOT NULL
              AND median_annual_salary IS NOT NULL
              {tier_sql}
        """
        summary_row = self.db_manager.execute_query(summary_query, tuple(params), fetch_one=True)

        job_total_count = self._safe_int(summary_row[0], 0) if summary_row else 0
        job_salary_mean = self._safe_float(summary_row[1], 0.0) if summary_row else 0.0

        # 连边聚合
        edge_params: List[Any] = [job_title]
        edge_tier_sql = ""
        if tier_filter and tier_filter.lower() != "all":
            edge_tier_sql = " AND city_tier = %s "
            edge_params.append(tier_filter)

        edge_query = f"""
            SELECT
                company_type,
                COUNT(*) AS edge_count,
                AVG(median_annual_salary) AS edge_salary
            FROM data
            WHERE job_title = %s
              AND company_type IS NOT NULL
              AND median_annual_salary IS NOT NULL
              {edge_tier_sql}
            GROUP BY company_type
            ORDER BY edge_count DESC
        """
        edge_rows = self.db_manager.execute_query(edge_query, tuple(edge_params))

        if not edge_rows:
            return {
                "job_title": job_title,
                "tier": tier_filter,
                "summary": {
                    "job_total_count": job_total_count,
                    "job_salary_median": round(job_salary_mean, 2),
                    "industry_degree": 0,
                    "industry_entropy": 0.0,
                    "hub_score": 0.0,
                },
                "nodes": [],
                "links": [],
                "legend": {
                    "salary_range": [0.0, 0.0],
                    "count_range": [0, 0],
                },
            }

        edges_all: List[Dict[str, Any]] = []
        for row in edge_rows:
            edges_all.append(
                {
                    "company_type": str(row[0]),
                    "edge_count": self._safe_int(row[1], 0),
                    "edge_salary": self._safe_float(row[2], 0.0),
                }
            )

        # 星与尘分层：
        # - 核心星系：Top core_count
        # - 星尘粒子：其余全部保留（不删）
        core_count = max(10, min(top_k_industry, 15))
        core_edges = edges_all[:core_count]
        dust_edges = edges_all[core_count:]
        edges = edges_all

        counts = [e["edge_count"] for e in edges]
        salaries = [e["edge_salary"] for e in edges]
        count_min, count_max = min(counts), max(counts)
        sal_min, sal_max = min(salaries), max(salaries)
        core_counts = [e["edge_count"] for e in core_edges] if core_edges else counts
        core_min, core_max = min(core_counts), max(core_counts)

        # 破壁性：行业熵
        total_edge_count = sum(counts)
        probs = [(c / total_edge_count) for c in counts if total_edge_count > 0 and c > 0]
        entropy = -sum(p * math.log(p) for p in probs) if probs else 0.0
        k = len(probs)
        entropy_norm = (entropy / math.log(k)) if k > 1 else 0.0

        # 简化 hub_score（当前图内局部打分）
        degree = len(edges_all)
        degree_norm = min(1.0, degree / max(1.0, float(top_k_industry)))
        salary_norm = self._scale_value(job_salary_mean, sal_min, sal_max, 0.0, 1.0)
        hub_score = 0.4 * entropy_norm + 0.3 * degree_norm + 0.3 * salary_norm

        center_size = 58 if job_total_count > 0 else 46
        nodes: List[Dict[str, Any]] = [
            {
                "id": f"job:{job_title}",
                "name": job_title,
                "type": "job",
                "value": job_total_count,
                "symbolSize": center_size,
                "itemStyle": {"color": "#ffd166", "shadowBlur": 24, "shadowColor": "rgba(255,209,102,0.55)"},
            }
        ]

        links: List[Dict[str, Any]] = []
        core_set = {id(x) for x in core_edges}
        for e in edges:
            is_core = id(e) in core_set
            if is_core:
                node_size = self._scale_value(e["edge_count"], core_min, core_max, 20.0, 44.0)
                width = self._scale_value(e["edge_count"], core_min, core_max, 2.6, 10.5)
            else:
                node_size = self._scale_value(e["edge_count"], count_min, count_max, 2.2, 5.0)
                width = self._scale_value(e["edge_count"], count_min, count_max, 0.22, 0.9)

            sal_t = self._scale_value(e["edge_salary"], sal_min, sal_max, 0.0, 1.0)
            warm_color = self._interpolate_color(sal_t)
            color = warm_color if is_core else self._mix_with_white(warm_color, 0.72)
            ind_id = f"ind:{e['company_type']}"
            nodes.append(
                {
                    "id": ind_id,
                    "name": e["company_type"],
                    "type": "industry",
                    "node_class": "core" if is_core else "dust",
                    "value": e["edge_count"],
                    "symbolSize": round(node_size, 2),
                    "label": {"show": is_core},
                    "itemStyle": {
                        "color": "#4ea8de" if is_core else "#9dc6e3",
                        "opacity": 0.96 if is_core else 0.34
                    },
                }
            )
            links.append(
                {
                    "source": f"job:{job_title}",
                    "target": ind_id,
                    "edge_class": "core" if is_core else "dust",
                    "value": e["edge_count"],
                    "salary": round(e["edge_salary"], 2),
                    "lineStyle": {
                        "width": round(width, 2),
                        "color": color,
                        "opacity": 0.92 if is_core else 0.20,
                    },
                }
            )

        return {
            "job_title": job_title,
            "tier": tier_filter,
            "summary": {
                "job_total_count": job_total_count,
                "job_salary_median": round(job_salary_mean, 2),
                "industry_degree": degree,
                "industry_degree_core": len(core_edges),
                "industry_degree_dust": len(dust_edges),
                "industry_entropy": round(entropy_norm, 4),
                "hub_score": round(hub_score, 4),
            },
            "nodes": nodes,
            "links": links,
            "legend": {
                "salary_range": [round(sal_min, 2), round(sal_max, 2)],
                "count_range": [count_min, count_max],
            },
        }

    def get_job_hub_ranking(self, top_n: int = 30, top_k_industry: int = 12) -> List[Dict[str, Any]]:
        """基于当前口径生成 hub 排名。"""
        jobs = self.get_emerging_jobs(top_n=top_n)
        ranking: List[Dict[str, Any]] = []
        for job in jobs:
            try:
                network = self.get_job_industry_force(
                    job_title=job["job_title"],
                    top_k_industry=top_k_industry,
                    city_tier="all",
                )
                summary = network.get("summary", {})
                ranking.append(
                    {
                        "job_title": job["job_title"],
                        "hub_score": summary.get("hub_score", 0.0),
                        "industry_degree": summary.get("industry_degree", 0),
                        "industry_entropy": summary.get("industry_entropy", 0.0),
                        "job_total_count": summary.get("job_total_count", 0),
                        "job_salary_median": summary.get("job_salary_median", 0.0),
                    }
                )
            except Exception as e:
                logger.warning("计算岗位 hub 失败: %s, error=%s", job.get("job_title"), e)

        ranking.sort(key=lambda x: x.get("hub_score", 0.0), reverse=True)
        return ranking[:top_n]
