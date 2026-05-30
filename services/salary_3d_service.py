#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三维薪资分析业务逻辑服务
用于处理三维柱状图和箱线图相关的业务逻辑
"""
import logging
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple
import statistics
import hashlib
import json
import os
from datetime import datetime

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from database.Q3 import DatabaseManager

logger = logging.getLogger(__name__)


class Salary3DService:
    """三维薪资分析业务逻辑服务"""
    CLUSTER_CACHE_VERSION = "q3_cluster_v13_fixed_k5_pca_projection_unique_jobtitle"
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.cluster_cache_dir = os.path.join(project_root, "dataset", "cache", "q3_salary_clusters")
        try:
            os.makedirs(self.cluster_cache_dir, exist_ok=True)
        except Exception:
            logger.warning("创建Q3聚类缓存目录失败，将退化为无文件缓存", exc_info=True)
    
    def get_boxplot_statistics(self, experience: str = None, education: str = None,
                               city: str = None, company_type: str = None) -> Dict[str, Any]:
        """
        获取箱线图统计数据
        返回按城市和公司类型分组的薪资分布统计量
        
        Args:
            experience: 工作经验筛选条件
            education: 学历筛选条件
            city: 城市筛选条件
            company_type: 公司类型筛选条件
        
        Returns:
            包含城市和公司类型分组统计数据的字典
        """
        try:
            # 获取原始数据
            raw_data = self.db_manager.get_boxplot_data(
                experience=experience,
                education=education,
                city=city,
                company_type=company_type
            )
            
            if not raw_data:
                return {
                    'city_data': [],
                    'company_type_data': [],
                    'cities': [],
                    'company_types': []
                }
            
            # 按城市分组
            city_salaries = {}
            company_type_salaries = {}
            cities_set = set()
            company_types_set = set()
            
            for row in raw_data:
                city_val, company_type_val, salary = row
                if city_val and company_type_val and salary:
                    # 按城市分组
                    if city_val not in city_salaries:
                        city_salaries[city_val] = []
                    city_salaries[city_val].append(float(salary))
                    cities_set.add(city_val)
                    
                    # 按公司类型分组
                    if company_type_val not in company_type_salaries:
                        company_type_salaries[company_type_val] = []
                    company_type_salaries[company_type_val].append(float(salary))
                    company_types_set.add(company_type_val)
            
            # 计算统计量：按城市
            city_data = []
            for city_name, salaries in sorted(city_salaries.items()):
                if len(salaries) > 0:
                    stats = self._calculate_statistics(salaries)
                    city_data.append({
                        'name': city_name,
                        'stats': stats,
                        'count': len(salaries)
                    })
            
            # 计算统计量：按公司类型
            company_type_data = []
            for company_type_name, salaries in sorted(company_type_salaries.items()):
                if len(salaries) > 0:
                    stats = self._calculate_statistics(salaries)
                    company_type_data.append({
                        'name': company_type_name,
                        'stats': stats,
                        'count': len(salaries)
                    })
            
            return {
                'city_data': city_data,
                'company_type_data': company_type_data,
                'cities': sorted(list(cities_set)),
                'company_types': sorted(list(company_types_set))
            }
            
        except Exception as e:
            logger.error(f"获取箱线图统计数据失败: {e}", exc_info=True)
            raise
    
    def _calculate_statistics(self, salaries: List[float]) -> Dict[str, float]:
        """
        计算箱线图统计量
        包括：最小值、下四分位数(Q1)、中位数(median)、上四分位数(Q3)、最大值
        
        Args:
            salaries: 薪资列表
        
        Returns:
            包含统计量的字典
        """
        if not salaries or len(salaries) == 0:
            return {
                'min': 0,
                'q1': 0,
                'median': 0,
                'q3': 0,
                'max': 0,
                'count': 0
            }
        
        # 排序
        sorted_salaries = sorted(salaries)
        n = len(sorted_salaries)
        
        # 最小值
        min_val = sorted_salaries[0]
        
        # 最大值
        max_val = sorted_salaries[-1]
        
        # 中位数
        if n % 2 == 0:
            median = (sorted_salaries[n // 2 - 1] + sorted_salaries[n // 2]) / 2
        else:
            median = sorted_salaries[n // 2]
        
        # 下四分位数 (Q1) - 使用标准方法
        # Q1位置 = (n + 1) * 0.25
        q1_pos = (n + 1) * 0.25
        if q1_pos == int(q1_pos):
            # 整数位置
            q1 = sorted_salaries[int(q1_pos) - 1]
        else:
            # 非整数位置，使用线性插值
            lower_idx = int(q1_pos) - 1
            upper_idx = int(q1_pos)
            if upper_idx >= n:
                q1 = sorted_salaries[lower_idx]
            else:
                weight = q1_pos - int(q1_pos)
                q1 = sorted_salaries[lower_idx] * (1 - weight) + sorted_salaries[upper_idx] * weight
        
        # 上四分位数 (Q3) - 使用标准方法
        # Q3位置 = (n + 1) * 0.75
        q3_pos = (n + 1) * 0.75
        if q3_pos == int(q3_pos):
            # 整数位置
            q3 = sorted_salaries[int(q3_pos) - 1]
        else:
            # 非整数位置，使用线性插值
            lower_idx = int(q3_pos) - 1
            upper_idx = int(q3_pos)
            if upper_idx >= n:
                q3 = sorted_salaries[lower_idx]
            else:
                weight = q3_pos - int(q3_pos)
                q3 = sorted_salaries[lower_idx] * (1 - weight) + sorted_salaries[upper_idx] * weight
        
        # 尝试使用statistics模块的更精确方法（Python 3.8+）
        try:
            quantiles = statistics.quantiles(sorted_salaries, n=4, method='inclusive')
            if len(quantiles) >= 3:
                q1 = quantiles[0]
                q3 = quantiles[2]
        except:
            # 如果statistics.quantiles不可用或失败，使用上面的计算方法
            pass
        
        return {
            'min': round(float(min_val), 2),
            'q1': round(float(q1), 2),
            'median': round(float(median), 2),
            'q3': round(float(q3), 2),
            'max': round(float(max_val), 2),
            'count': n
        }

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _encode_demand_spread(market_demand: Any, industry_spread: Any) -> float:
        demand_map = {"冷门": 0.0, "普通": 1.0, "热门": 2.0}
        spread_map = {"集中": 0.0, "中等": 1.0, "分散": 2.0}
        d_raw = str(market_demand or "").strip()
        s_raw = str(industry_spread or "").strip()
        d = demand_map.get(d_raw, None)
        s = spread_map.get(s_raw, None)
        if d is not None and s is not None:
            return 0.6 * d + 0.4 * s
        if d is not None:
            return d
        if s is not None:
            return s
        return 1.0

    def get_salary_cluster_data(
        self,
        n_clusters: int = 5,
        algorithm: str = "kmeans",
        sample_size: int = 12000
    ) -> Dict[str, Any]:
        """获取职位薪资模式聚类数据（Q3 聚类视图）"""
        # 当前阶段按 Q3_new_plan 先做固定 5 簇的输入特征聚类。
        fixed_n_clusters = 5
        fixed_algorithm = "kmeans"

        cache_key = self._build_cluster_cache_key(
            n_clusters=fixed_n_clusters,
            algorithm=fixed_algorithm,
            sample_size=sample_size
        )
        cached = self._load_cluster_cache(cache_key)
        if cached:
            cached.setdefault("metadata", {})
            cached["metadata"]["cache_hit"] = True
            cached["metadata"]["cache_key"] = cache_key
            cached["metadata"]["cache_file"] = self._cluster_cache_path(cache_key)
            city_payload, city_file = self._build_city_cluster_assignment_payload(
                points=cached.get("points", []),
                cache_key=cache_key,
                n_clusters=int(cached.get("metadata", {}).get("n_clusters", fixed_n_clusters)),
                algorithm=str(cached.get("metadata", {}).get("cluster_algorithm", fixed_algorithm)),
                sample_size=int(cached.get("metadata", {}).get("sample_size", sample_size)),
            )
            cached["city_cluster_assignments"] = city_payload.get("cities", [])
            cached["metadata"]["city_cluster_json_file"] = city_file
            cached["metadata"]["city_cluster_count"] = len(city_payload.get("cities", []))
            return cached

        rows = self._query_cluster_rows(sample_size=sample_size)
        if not rows:
            return {
                "points": [],
                "cluster_summary": [],
                "metadata": {"n_clusters": 0, "total_jobs": 0, "cluster_algorithm": fixed_algorithm}
            }

        points = []
        for idx, r in enumerate(rows):
            points.append({
                "point_id": int(idx),
                "job_title": r[0],
                "company_type": r[1] or "未知",
                "city_tier": (r[2] if len(r) > 2 else "未知") or "未知",
                "features": {
                    "median_salary": self._safe_float(r[3]),
                    "q1_salary": self._safe_float(r[4]),
                    "q3_salary": self._safe_float(r[5]),
                    "std_salary": self._safe_float(r[6]),
                    "avg_experience_rank": self._safe_float(r[7]),
                    "avg_education_rank": self._safe_float(r[8]),
                    "records_count": self._safe_float(r[9]),
                    "total_shannon_entropy": self._safe_float(r[10]),
                }
            })

        def _z(arr: np.ndarray) -> np.ndarray:
            if arr.size == 0:
                return arr
            # 对极端值做轻度截尾，避免少量异常值主导投影方向
            lo = float(np.quantile(arr, 0.02))
            hi = float(np.quantile(arr, 0.98))
            clipped = np.clip(arr, lo, hi)
            mu = float(np.mean(clipped))
            sigma = float(np.std(clipped))
            if sigma <= 1e-9:
                return np.zeros_like(arr, dtype=float)
            return (clipped - mu) / sigma

        medians = np.array([p["features"]["median_salary"] for p in points], dtype=float)
        q1_m = float(np.quantile(medians, 0.33)) if len(medians) else 0.0
        q2_m = float(np.quantile(medians, 0.66)) if len(medians) else 0.0
        for p in points:
            m = p["features"]["median_salary"]
            if m <= q1_m:
                p["salary_level"] = "低薪"
            elif m <= q2_m:
                p["salary_level"] = "中薪"
            else:
                p["salary_level"] = "高薪"

        median_salary_raw = np.array([p["features"]["median_salary"] for p in points], dtype=float)
        std_salary_raw = np.array([p["features"]["std_salary"] for p in points], dtype=float)
        exp_raw = np.array([p["features"]["avg_experience_rank"] for p in points], dtype=float)
        edu_raw = np.array([p["features"]["avg_education_rank"] for p in points], dtype=float)
        records_raw = np.array([max(0.0, p["features"]["records_count"]) for p in points], dtype=float)
        entropy_raw = np.array([p["features"]["total_shannon_entropy"] for p in points], dtype=float)

        salary_index = _z(median_salary_raw)
        exp_index = _z(exp_raw)
        edu_index = _z(edu_raw)
        barrier_index = 0.55 * exp_index + 0.45 * edu_index
        volatility_index = _z(std_salary_raw)
        scale_index = _z(np.log1p(records_raw))
        entropy_index = _z(entropy_raw)

        X = np.column_stack([
            salary_index,
            barrier_index,
            volatility_index,
            scale_index,
            entropy_index,
        ])

        for i, p in enumerate(points):
            p["cluster_inputs"] = {
                "salary_index": round(float(salary_index[i]), 4),
                "barrier_index": round(float(barrier_index[i]), 4),
                "volatility_index": round(float(volatility_index[i]), 4),
                "scale_index": round(float(scale_index[i]), 4),
                "entropy_index": round(float(entropy_index[i]), 4),
            }

        n = len(points)
        k = max(1, min(int(fixed_n_clusters), n))
        if n <= 2:
            labels = np.zeros(n, dtype=int)
            proj2d = np.zeros((n, 2), dtype=float)
            proj_method = "pca_degenerate"
        else:
            try:
                labels = KMeans(n_clusters=k, random_state=42, n_init=20).fit_predict(X)
            except Exception:
                labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)

            # 聚簇图坐标改为“聚类输入特征”的PCA投影，视觉上更接近典型簇团分布。
            try:
                pca = PCA(n_components=2, random_state=42)
                proj2d = np.asarray(pca.fit_transform(X), dtype=float)
                proj_method = "pca_cluster_features"
            except Exception:
                # 极端情况下兜底到(薪资,门槛)坐标，保证接口稳定返回
                proj2d = np.column_stack([median_salary_raw, barrier_index])
                proj_method = "salary_barrier_fallback"

        raw_cluster_groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for i, p in enumerate(points):
            cid = int(labels[i]) if len(labels) else 0
            raw_cluster_groups[cid].append(p)

        mapping = self._build_cluster_labels(raw_cluster_groups)

        cluster_groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for i, p in enumerate(points):
            raw_cid = int(labels[i]) if len(labels) else 0
            mapped = mapping.get(raw_cid, {"cluster_id": raw_cid, "cluster_label": f"簇{raw_cid}"})
            cid = int(mapped["cluster_id"])
            p["cluster_id"] = cid
            p["cluster_label"] = str(mapped["cluster_label"])
            p["umap_x"] = float(proj2d[i][0]) if len(proj2d) > i else 0.0
            p["umap_y"] = float(proj2d[i][1]) if len(proj2d) > i else 0.0
            cluster_groups[cid].append(p)

        cluster_summary = []
        for cid, plist in sorted(cluster_groups.items(), key=lambda it: it[0]):
            sorted_jobs = sorted(
                plist,
                key=lambda p: float(p["features"].get("records_count", 0)),
                reverse=True
            )
            cluster_summary.append({
                "cluster_id": cid,
                "cluster_label": str(plist[0].get("cluster_label", f"簇{cid}")),
                "count": len(plist),
                "top_jobs": [p["job_title"] for p in sorted_jobs[:8]],
                "representative_jobs": [
                    {
                        "job_title": p["job_title"],
                        "company_type": p["company_type"],
                        "city_tier": p["city_tier"],
                        "median_salary": round(float(p["features"].get("median_salary", 0)), 2),
                        "records_count": int(round(float(p["features"].get("records_count", 0))))
                    }
                    for p in sorted_jobs[:12]
                ],
                "profile_scores": self._cluster_profile(plist),
                "pattern_description": self._build_pattern_description(
                    plist,
                    str(plist[0].get("cluster_label", f"簇{cid}"))
                )
            })

        result = {
            "points": points,
            "cluster_summary": cluster_summary,
            "parallel_payload": self._build_parallel_payload(
                points=points,
                cluster_groups=cluster_groups,
                sample_size=sample_size
            ),
            "metadata": {
                "n_clusters": len(cluster_summary),
                "total_jobs": len(points),
                "cluster_algorithm": fixed_algorithm,
                "requested_n_clusters": int(n_clusters or fixed_n_clusters),
                "requested_algorithm": str(algorithm or fixed_algorithm),
                "fixed_n_clusters": fixed_n_clusters,
                "sample_size": int(sample_size or 0),
                "projection_method": proj_method,
                "feature_set": [
                    "salary_index",
                    "barrier_index",
                    "volatility_index",
                    "scale_index",
                    "entropy_index",
                ],
                "color_encoding_options": [
                    "cluster",
                    "industry",
                    "city_tier",
                    "salary_level"
                ],
                "cache_hit": False,
                "cache_key": cache_key,
                "cache_file": self._cluster_cache_path(cache_key)
            }
        }
        city_payload, city_file = self._build_city_cluster_assignment_payload(
            points=points,
            cache_key=cache_key,
            n_clusters=len(cluster_summary),
            algorithm=str(fixed_algorithm),
            sample_size=int(sample_size or 0),
        )
        result["city_cluster_assignments"] = city_payload.get("cities", [])
        result["metadata"]["city_cluster_json_file"] = city_file
        result["metadata"]["city_cluster_count"] = len(city_payload.get("cities", []))
        self._save_cluster_cache(cache_key, result)
        return result

    def _build_cluster_cache_key(self, n_clusters: int, algorithm: str, sample_size: int) -> str:
        algo = str(algorithm or "gmm").strip().lower()
        size = int(sample_size or 12000)
        payload = f"{self.CLUSTER_CACHE_VERSION}|k={int(n_clusters or 5)}|alg={algo}|size={size}"
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    def _cluster_cache_path(self, cache_key: str) -> str:
        return os.path.join(self.cluster_cache_dir, f"{cache_key}.json")

    def _cluster_city_json_path(self, cache_key: str) -> str:
        return os.path.join(self.cluster_cache_dir, f"{cache_key}_city_clusters.json")

    def _load_cluster_cache(self, cache_key: str) -> Dict[str, Any]:
        path = self._cluster_cache_path(cache_key)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("读取Q3聚类缓存失败，改为重新计算: %s", path, exc_info=True)
            return {}

    def _save_cluster_cache(self, cache_key: str, payload: Dict[str, Any]) -> None:
        path = self._cluster_cache_path(cache_key)
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            os.replace(tmp_path, path)
        except Exception:
            logger.warning("写入Q3聚类缓存失败: %s", path, exc_info=True)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def _project_2d(self, Xs: np.ndarray, labels: np.ndarray = None) -> Tuple[np.ndarray, str]:
        """将标准化特征投影到二维。固定使用PCA主成分坐标。"""
        n = int(Xs.shape[0]) if Xs is not None else 0
        if n <= 0:
            return np.zeros((0, 2), dtype=float), "empty"
        if n == 1:
            return np.array([[0.0, 0.0]], dtype=float), "single"
        try:
            pca = PCA(n_components=2, random_state=42)
            emb = np.asarray(pca.fit_transform(Xs), dtype=float)
            if emb is not None and len(emb) == n:
                return emb, "pca"
        except Exception:
            pass
        # 兜底：取前两列（理论上不会走到这里）
        x = np.asarray(Xs, dtype=float)
        if x.shape[1] >= 2:
            return x[:, :2], "fallback_raw2d"
        if x.shape[1] == 1:
            return np.hstack([x, np.zeros((n, 1), dtype=float)]), "fallback_raw1d"
        return np.zeros((n, 2), dtype=float), "fallback_zero"

    def _separate_clusters_layout(self, proj2d: np.ndarray, labels: np.ndarray) -> np.ndarray:
        """基于簇标签对2D投影做布局拉开，保留簇内相对形状，增强“一簇一团”可读性。"""
        if proj2d is None:
            return proj2d
        arr = np.asarray(proj2d, dtype=float)
        if arr.ndim != 2 or arr.shape[1] < 2:
            return arr
        if labels is None or len(labels) != len(arr):
            return arr

        label_arr = np.asarray(labels, dtype=int)
        uniq = sorted(set(label_arr.tolist()))
        if len(uniq) <= 1:
            return arr

        # 估计全局簇内离散度，决定簇中心锚点半径
        spread_vals = []
        centroids = {}
        for cid in uniq:
            idx = np.where(label_arr == cid)[0]
            if len(idx) == 0:
                continue
            sub = arr[idx, :2]
            c = np.mean(sub, axis=0)
            centroids[cid] = c
            d = np.linalg.norm(sub - c, axis=1)
            spread_vals.append(float(np.percentile(d, 75)))

        if not spread_vals:
            return arr
        base_spread = max(0.8, float(np.median(spread_vals)))
        # 更强的簇间拉开：半径与簇数、离散度共同放大
        radius = base_spread * (7.5 + 0.55 * len(uniq))

        out = np.zeros_like(arr[:, :2], dtype=float)
        for i, cid in enumerate(uniq):
            idx = np.where(label_arr == cid)[0]
            if len(idx) == 0:
                continue
            angle = 2.0 * np.pi * i / len(uniq)
            anchor = np.array([np.cos(angle), np.sin(angle)], dtype=float) * radius
            c = centroids.get(cid, np.zeros(2, dtype=float))
            # 保留簇内形状并明显压缩，再平移到锚点
            out[idx] = (arr[idx, :2] - c) * 0.44 + anchor

        return out

    def _query_city_job_distribution_rows(self) -> List[Tuple]:
        query_cluster_by_city = """
            SELECT
                city,
                job_title,
                SUM(COALESCE(job_in_city_cnt, 1)) AS job_count
            FROM cluster_by_city
            WHERE city IS NOT NULL
              AND city <> ''
              AND job_title IS NOT NULL
              AND job_title <> ''
            GROUP BY city, job_title
        """
        query_data_fallback = """
            SELECT
                city,
                job_title,
                COUNT(*) AS job_count
            FROM data
            WHERE city IS NOT NULL
              AND city <> ''
              AND job_title IS NOT NULL
              AND job_title <> ''
            GROUP BY city, job_title
        """
        try:
            return self.db_manager.execute_query(query_cluster_by_city)
        except Exception:
            return self.db_manager.execute_query(query_data_fallback)

    def _build_city_cluster_assignment_payload(
        self,
        points: List[Dict[str, Any]],
        cache_key: str,
        n_clusters: int,
        algorithm: str,
        sample_size: int
    ) -> Tuple[Dict[str, Any], str]:
        city_file = self._cluster_city_json_path(cache_key)

        # 先尝试复用已落盘文件
        if os.path.exists(city_file):
            try:
                with open(city_file, "r", encoding="utf-8") as f:
                    return json.load(f), city_file
            except Exception:
                logger.warning("读取城市簇归属JSON失败，改为重算: %s", city_file, exc_info=True)

        # 1) 职位 -> 簇（同名职位可能出现多条，按 records_count 加权投票）
        title_cluster_weight: Dict[str, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        cluster_labels: Dict[int, str] = {}
        for p in points or []:
            title = str(p.get("job_title") or "").strip()
            if not title:
                continue
            cid = int(p.get("cluster_id", 0))
            w = max(1.0, float(p.get("features", {}).get("records_count", 1.0)))
            title_cluster_weight[title][cid] += w
            cluster_labels[cid] = str(p.get("cluster_label") or f"簇{cid}")

        title_to_cluster: Dict[str, int] = {}
        for title, counter in title_cluster_weight.items():
            if not counter:
                continue
            title_to_cluster[title] = max(counter.items(), key=lambda kv: kv[1])[0]

        # 2) 城市-职位 -> 招聘权重，汇总成 城市-簇
        rows = self._query_city_job_distribution_rows()
        city_cluster_weight: Dict[str, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        city_total: Dict[str, float] = defaultdict(float)
        for row in rows or []:
            city = str(row[0] or "").strip()
            title = str(row[1] or "").strip()
            if not city or not title:
                continue
            cnt = max(0.0, self._safe_float(row[2], 0.0))
            if cnt <= 0:
                continue
            cid = title_to_cluster.get(title, None)
            if cid is None:
                continue
            city_cluster_weight[city][int(cid)] += cnt
            city_total[city] += cnt

        cities = []
        for city, cc in city_cluster_weight.items():
            total = float(city_total.get(city, 0.0))
            if total <= 0:
                continue
            assigned_cid = int(max(cc.items(), key=lambda kv: kv[1])[0])
            distribution = [
                {
                    "cluster_id": int(cid),
                    "cluster_label": cluster_labels.get(int(cid), f"簇{int(cid)}"),
                    "weight": round(float(w), 2),
                    "share": round(float(w) / total, 4),
                }
                for cid, w in sorted(cc.items(), key=lambda kv: kv[1], reverse=True)
            ]
            cities.append({
                "city": city,
                "assigned_cluster_id": assigned_cid,
                "assigned_cluster_label": cluster_labels.get(assigned_cid, f"簇{assigned_cid}"),
                "confidence": round(float(cc.get(assigned_cid, 0.0)) / total, 4),
                "total_weight": round(total, 2),
                "distribution": distribution
            })

        cities.sort(key=lambda x: (-float(x.get("total_weight", 0)), str(x.get("city", ""))))
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "cache_key": cache_key,
            "n_clusters": int(n_clusters or 0),
            "algorithm": str(algorithm or "gmm"),
            "sample_size": int(sample_size or 0),
            "city_count": len(cities),
            "cluster_labels": {str(k): v for k, v in sorted(cluster_labels.items(), key=lambda it: int(it[0]))},
            "cities": cities
        }

        tmp_path = f"{city_file}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            os.replace(tmp_path, city_file)
        except Exception:
            logger.warning("写入城市簇归属JSON失败: %s", city_file, exc_info=True)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
        return payload, city_file

    def _query_cluster_rows(self, sample_size: int = 12000) -> List[Tuple]:
        size = max(3000, min(int(sample_size or 12000), 60000))
        query_join_with_tier = """
            SELECT
                js.job_title,
                MIN(js.company_type) AS company_type,
                MIN(js.city_tier) AS city_tier,
                AVG(js.median_salary) AS median_salary,
                AVG(js.q1_salary) AS q1_salary,
                AVG(js.q3_salary) AS q3_salary,
                AVG(js.std_salary) AS std_salary,
                AVG(js.avg_experience_rank) AS avg_experience_rank,
                AVG(js.avg_education_rank) AS avg_education_rank,
                SUM(js.records_count) AS records_count,
                AVG(js.total_shannon_entropy) AS total_shannon_entropy
            FROM job_summary js
            WHERE js.job_title IS NOT NULL
              AND js.job_title <> ''
              AND js.median_salary IS NOT NULL
              AND js.q1_salary IS NOT NULL
              AND js.q3_salary IS NOT NULL
              AND js.std_salary IS NOT NULL
              AND js.records_count IS NOT NULL
              AND js.avg_experience_rank IS NOT NULL
              AND js.avg_education_rank IS NOT NULL
              AND js.total_shannon_entropy IS NOT NULL
            GROUP BY js.job_title
            ORDER BY COALESCE(SUM(js.records_count), 0) DESC
            LIMIT %s
        """
        query_join_without_tier = """
            SELECT
                js.job_title,
                MIN(js.company_type) AS company_type,
                NULL AS city_tier,
                AVG(js.median_salary) AS median_salary,
                AVG(js.q1_salary) AS q1_salary,
                AVG(js.q3_salary) AS q3_salary,
                AVG(js.std_salary) AS std_salary,
                AVG(js.avg_experience_rank) AS avg_experience_rank,
                AVG(js.avg_education_rank) AS avg_education_rank,
                SUM(js.records_count) AS records_count,
                AVG(js.total_shannon_entropy) AS total_shannon_entropy
            FROM job_summary js
            WHERE js.job_title IS NOT NULL
              AND js.job_title <> ''
              AND js.median_salary IS NOT NULL
              AND js.q1_salary IS NOT NULL
              AND js.q3_salary IS NOT NULL
              AND js.std_salary IS NOT NULL
              AND js.records_count IS NOT NULL
              AND js.avg_experience_rank IS NOT NULL
              AND js.avg_education_rank IS NOT NULL
              AND js.total_shannon_entropy IS NOT NULL
            GROUP BY js.job_title
            ORDER BY COALESCE(SUM(js.records_count), 0) DESC
            LIMIT %s
        """
        query_core_only = """
            SELECT
                js.job_title,
                MIN(js.company_type) AS company_type,
                NULL AS city_tier,
                AVG(js.median_salary) AS median_salary,
                AVG(js.q1_salary) AS q1_salary,
                AVG(js.q3_salary) AS q3_salary,
                AVG(js.std_salary) AS std_salary,
                AVG(js.avg_experience_rank) AS avg_experience_rank,
                AVG(js.avg_education_rank) AS avg_education_rank,
                SUM(js.records_count) AS records_count,
                AVG(js.total_shannon_entropy) AS total_shannon_entropy
            FROM job_summary js
            WHERE js.job_title IS NOT NULL
              AND js.job_title <> ''
              AND js.median_salary IS NOT NULL
              AND js.q1_salary IS NOT NULL
              AND js.q3_salary IS NOT NULL
              AND js.std_salary IS NOT NULL
              AND js.records_count IS NOT NULL
              AND js.avg_experience_rank IS NOT NULL
              AND js.avg_education_rank IS NOT NULL
              AND js.total_shannon_entropy IS NOT NULL
            GROUP BY js.job_title
            ORDER BY COALESCE(SUM(js.records_count), 0) DESC
            LIMIT %s
        """
        try:
            return self.db_manager.execute_query(query_join_with_tier, (size,))
        except Exception:
            try:
                return self.db_manager.execute_query(query_join_without_tier, (size,))
            except Exception:
                return self.db_manager.execute_query(query_core_only, (size,))

    def _build_cluster_labels(self, groups: Dict[int, List[Dict[str, Any]]]) -> Dict[int, Dict[str, Any]]:
        if not groups:
            return {}
        metrics = {}
        for cid, plist in groups.items():
            if not plist:
                continue
            salary = float(np.mean([float(p.get("cluster_inputs", {}).get("salary_index", 0)) for p in plist]))
            barrier = float(np.mean([float(p.get("cluster_inputs", {}).get("barrier_index", 0)) for p in plist]))
            volatility = float(np.mean([float(p.get("cluster_inputs", {}).get("volatility_index", 0)) for p in plist]))
            scale = float(np.mean([float(p.get("cluster_inputs", {}).get("scale_index", 0)) for p in plist]))
            entropy = float(np.mean([float(p.get("cluster_inputs", {}).get("entropy_index", 0)) for p in plist]))
            metrics[int(cid)] = {
                "salary": salary,
                "barrier": barrier,
                "volatility": volatility,
                "scale": scale,
                "entropy": entropy,
            }

        if not metrics:
            return {}

        cluster_ids = sorted(metrics.keys())
        targets = [
            (0, "高薪高门槛型"),
            (1, "低薪低门槛型"),
            (2, "高薪波动型"),
            (3, "稀缺潜力型"),
            (4, "大众稳定型"),
        ]

        def score(target_id: int, m: Dict[str, float]) -> float:
            s = float(m["salary"])
            b = float(m["barrier"])
            v = float(m["volatility"])
            sc = float(m["scale"])
            e = float(m["entropy"])
            if target_id == 0:  # C0 高薪高门槛型
                return 1.2 * s + 1.2 * b - 0.3 * v + 0.1 * sc
            if target_id == 1:  # C1 低薪低门槛型
                return -1.2 * s - 1.2 * b + 0.2 * sc - 0.1 * v
            if target_id == 2:  # C2 高薪波动型
                return 1.1 * s + 1.4 * v + 0.3 * e - 0.15 * sc
            if target_id == 3:  # C3 稀缺潜力型
                return -1.3 * sc + 0.85 * s + 0.85 * b + 0.5 * e + 0.2 * v
            # C4 大众稳定型
            return 1.4 * sc - 1.2 * v - 0.6 * abs(s) - 0.2 * b

        assigned_cids = set()
        assigned_targets = set()
        mapping = {}

        # 按业务簇顺序贪心分配，确保 C0~C4 语义尽可能稳定。
        for tid, tlabel in targets:
            candidates = [cid for cid in cluster_ids if cid not in assigned_cids]
            if not candidates:
                break
            best_cid = max(candidates, key=lambda cid: score(tid, metrics[cid]))
            assigned_cids.add(best_cid)
            assigned_targets.add(tid)
            mapping[best_cid] = {"cluster_id": tid, "cluster_label": tlabel}

        # 兜底：如果簇数不是 5，给剩余簇分配未使用业务ID；再不足则顺延编号。
        free_target_ids = [tid for tid, _ in targets if tid not in assigned_targets]
        free_idx = 0
        for cid in cluster_ids:
            if cid in mapping:
                continue
            if free_idx < len(free_target_ids):
                tid = free_target_ids[free_idx]
                label = dict(targets).get(tid, f"簇{tid}")
                free_idx += 1
            else:
                tid = max([m["cluster_id"] for m in mapping.values()], default=-1) + 1
                label = f"扩展簇{tid}"
            mapping[cid] = {"cluster_id": tid, "cluster_label": label}

        return mapping

    def _cluster_profile(self, plist: List[Dict[str, Any]]) -> Dict[str, float]:
        if not plist:
            return {}
        fvals = lambda key: [float(p["features"].get(key, 0)) for p in plist]
        return {
            "median_salary": round(float(np.mean(fvals("median_salary"))), 2),
            "q1_salary": round(float(np.mean(fvals("q1_salary"))), 2),
            "q3_salary": round(float(np.mean(fvals("q3_salary"))), 2),
            "std_salary": round(float(np.mean(fvals("std_salary"))), 2),
            "avg_experience_rank": round(float(np.mean(fvals("avg_experience_rank"))), 2),
            "avg_education_rank": round(float(np.mean(fvals("avg_education_rank"))), 2),
            "records_count": round(float(np.mean(fvals("records_count"))), 2),
            "total_shannon_entropy": round(float(np.mean(fvals("total_shannon_entropy"))), 2),
            "barrier_index": round(float(np.mean([float(p.get("cluster_inputs", {}).get("barrier_index", 0)) for p in plist])), 3),
            "volatility_index": round(float(np.mean([float(p.get("cluster_inputs", {}).get("volatility_index", 0)) for p in plist])), 3),
            "scale_index": round(float(np.mean([float(p.get("cluster_inputs", {}).get("scale_index", 0)) for p in plist])), 3),
            "entropy_index": round(float(np.mean([float(p.get("cluster_inputs", {}).get("entropy_index", 0)) for p in plist])), 3),
        }

    @staticmethod
    def _rank_to_education_label(rank: float) -> str:
        v = float(rank or 0)
        if v < 2.5:
            return "大专及以下"
        if v < 4.5:
            return "本科"
        if v < 5.5:
            return "硕士"
        return "博士及以上"

    @staticmethod
    def _rank_to_experience_label(rank: float) -> str:
        v = float(rank or 0)
        if v < 0.5:
            return "无经验"
        if v < 1.5:
            return "1年以下"
        if v < 2.5:
            return "1-3年"
        if v < 3.5:
            return "3-5年"
        if v < 4.5:
            return "5-7年"
        if v < 5.5:
            return "7-10年"
        return "10年以上"

    @staticmethod
    def _city_tier_bucket(city_tier: Any) -> str:
        s = str(city_tier or "").strip()
        if not s:
            return "其他"
        if "新一线" in s:
            return "新一线"
        if "一线" in s:
            return "一线"
        if "二线" in s:
            return "二线"
        return "其他"

    def _build_parallel_payload(
        self,
        points: List[Dict[str, Any]],
        cluster_groups: Dict[int, List[Dict[str, Any]]],
        sample_size: int
    ) -> Dict[str, Any]:
        if not points:
            return {
                "axis_meta": {},
                "centroid_lines": [],
                "sampled_lines": []
            }

        education_labels = ["大专及以下", "本科", "硕士", "博士及以上"]
        experience_labels = ["无经验", "1年以下", "1-3年", "3-5年", "5-7年", "7-10年", "10年以上"]
        city_labels = ["一线", "新一线", "二线", "其他"]

        company_counter = Counter([str(p.get("company_type") or "未知").strip() or "未知" for p in points])
        company_labels = [name for name, _ in company_counter.most_common(10)] + ["Other"]

        edu_idx = {name: i for i, name in enumerate(education_labels)}
        exp_idx = {name: i for i, name in enumerate(experience_labels)}
        city_idx = {name: i for i, name in enumerate(city_labels)}
        company_idx = {name: i for i, name in enumerate(company_labels)}

        def encode_point_row(point: Dict[str, Any], pid: int) -> Dict[str, Any]:
            f = point.get("features", {})
            e_label = self._rank_to_education_label(f.get("avg_education_rank"))
            x_label = self._rank_to_experience_label(f.get("avg_experience_rank"))
            c_label = self._city_tier_bucket(point.get("city_tier"))
            comp_name = str(point.get("company_type") or "未知").strip() or "未知"
            comp_label = comp_name if comp_name in company_idx else "Other"
            salary = float(f.get("median_salary", 0))
            return {
                "id": int(pid),
                "cluster_id": int(point.get("cluster_id", 0)),
                "education_label": e_label,
                "experience_label": x_label,
                "city_label": c_label,
                "company_label": comp_label,
                "salary_mean": round(salary, 2),
                "values": [
                    int(edu_idx.get(e_label, 0)),
                    int(exp_idx.get(x_label, 0)),
                    int(city_idx.get(c_label, 0)),
                    int(company_idx.get(comp_label, len(company_labels) - 1)),
                    round(salary, 2),
                ]
            }

        sampled_target = max(2000, min(5000, int(max(1, int(sample_size or 12000)) * 0.35)))
        sampled_target = min(sampled_target, len(points))
        total = max(1, len(points))
        rng = np.random.default_rng(42)
        sampled_rows: List[Dict[str, Any]] = []
        for cid, plist in sorted(cluster_groups.items(), key=lambda it: it[0]):
            idxs = [int(p.get("point_id", i)) for i, p in enumerate(plist)]
            quota = max(1, int(round(len(idxs) / total * sampled_target)))
            if quota >= len(idxs):
                chosen = idxs
            else:
                chosen = rng.choice(np.asarray(idxs, dtype=int), size=quota, replace=False).tolist()
            for pid in chosen:
                sampled_rows.append(encode_point_row(points[pid], pid))

        if len(sampled_rows) > sampled_target:
            sampled_rows = sampled_rows[:sampled_target]

        centroid_rows: List[Dict[str, Any]] = []
        for cid, plist in sorted(cluster_groups.items(), key=lambda it: it[0]):
            if not plist:
                continue
            avg_edu = float(np.mean([float(p["features"].get("avg_education_rank", 0)) for p in plist]))
            avg_exp = float(np.mean([float(p["features"].get("avg_experience_rank", 0)) for p in plist]))
            avg_salary = float(np.mean([float(p["features"].get("median_salary", 0)) for p in plist]))
            city_mode = Counter([self._city_tier_bucket(p.get("city_tier")) for p in plist]).most_common(1)[0][0]
            comp_raw_mode = Counter([str(p.get("company_type") or "未知").strip() or "未知" for p in plist]).most_common(1)[0][0]
            comp_mode = comp_raw_mode if comp_raw_mode in company_idx else "Other"

            e_label = self._rank_to_education_label(avg_edu)
            x_label = self._rank_to_experience_label(avg_exp)
            centroid_rows.append({
                "id": f"cluster-{cid}",
                "cluster_id": int(cid),
                "count": int(len(plist)),
                "education_label": e_label,
                "experience_label": x_label,
                "city_label": city_mode,
                "company_label": comp_mode,
                "salary_mean": round(avg_salary, 2),
                "values": [
                    int(edu_idx.get(e_label, 0)),
                    int(exp_idx.get(x_label, 0)),
                    int(city_idx.get(city_mode, 0)),
                    int(company_idx.get(comp_mode, len(company_labels) - 1)),
                    round(avg_salary, 2),
                ]
            })

        salaries = [float(p["features"].get("median_salary", 0)) for p in points]
        salary_min = round(float(np.min(salaries)), 2) if salaries else 0.0
        salary_max = round(float(np.max(salaries)), 2) if salaries else 100.0

        return {
            "axis_meta": {
                "education_labels": education_labels,
                "experience_labels": experience_labels,
                "city_labels": city_labels,
                "company_labels": company_labels,
                "salary_range": [salary_min, salary_max]
            },
            "centroid_lines": centroid_rows,
            "sampled_lines": sampled_rows,
            "default_mode": "centroid",
            "sampled_count": len(sampled_rows),
            "centroid_count": len(centroid_rows)
        }

    def _build_pattern_description(self, plist: List[Dict[str, Any]], cluster_label: str) -> str:
        if not plist:
            return "样本不足，暂无法生成模式描述。"
        profile = self._cluster_profile(plist)
        salary = profile.get("median_salary", 0.0)
        volatility = profile.get("std_salary", 0.0)
        exp = profile.get("avg_experience_rank", 0.0)
        edu = profile.get("avg_education_rank", 0.0)
        demand = profile.get("records_count", 0.0)
        barrier_idx = profile.get("barrier_index", 0.0)
        return (
            f"{cluster_label}：中位薪资约 {salary:.1f}K，波动 {volatility:.1f}K，"
            f"经验/学历门槛均值约 {exp:.2f}/{edu:.2f}，"
            f"招聘规模均值约 {demand:.0f}，门槛指数均值 {barrier_idx:.2f}。"
        )
