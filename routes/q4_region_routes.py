#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q4 地域招聘活动画像新接口
"""

import logging
from flask import Blueprint, request

from database.Q3 import DatabaseManager
from services.q4_region_service import Q4RegionService
from utils.response import ResponseBuilder

logger = logging.getLogger(__name__)

q4_region_bp = Blueprint("q4_region", __name__, url_prefix="/api")
service = Q4RegionService(DatabaseManager("default"))


def _cluster_args():
    n_clusters = request.args.get("n_clusters", default=4, type=int)
    algorithm = request.args.get("algorithm", default="kmeans", type=str)
    sample_size = request.args.get("sample_size", default=0, type=int)
    return n_clusters, algorithm, sample_size


@q4_region_bp.route("/regions/summary", methods=["GET"])
def get_regions_summary():
    try:
        n_clusters, algorithm, sample_size = _cluster_args()
        data = service.get_regions_summary(
            n_clusters=n_clusters,
            algorithm=algorithm,
            sample_size=sample_size,
        )
        return ResponseBuilder.success("获取地域拓扑摘要成功", data)
    except Exception as e:
        logger.error(f"获取地域拓扑摘要失败: {e}", exc_info=True)
        return ResponseBuilder.internal_error("服务器内部错误", {"type": "INTERNAL_ERROR", "details": str(e)})


@q4_region_bp.route("/regions/<region_id>", methods=["GET"])
def get_region_detail(region_id: str):
    try:
        n_clusters, algorithm, sample_size = _cluster_args()
        data = service.get_region_detail(
            region_id=region_id,
            n_clusters=n_clusters,
            algorithm=algorithm,
            sample_size=sample_size,
        )
        if not data:
            return ResponseBuilder.not_found(f"未找到地域 {region_id} 画像")
        return ResponseBuilder.success(f"获取地域 {region_id} 画像成功", data)
    except Exception as e:
        logger.error(f"获取地域画像失败: {e}", exc_info=True)
        return ResponseBuilder.internal_error("服务器内部错误", {"type": "INTERNAL_ERROR", "details": str(e)})


@q4_region_bp.route("/regions/cluster_summary", methods=["GET"])
def get_regions_cluster_summary():
    try:
        n_clusters, algorithm, sample_size = _cluster_args()
        data = service.get_cluster_summary(
            n_clusters=n_clusters,
            algorithm=algorithm,
            sample_size=sample_size,
        )
        return ResponseBuilder.success("获取地域聚类摘要成功", data)
    except Exception as e:
        logger.error(f"获取地域聚类摘要失败: {e}", exc_info=True)
        return ResponseBuilder.internal_error("服务器内部错误", {"type": "INTERNAL_ERROR", "details": str(e)})


@q4_region_bp.route("/industry_region_matrix", methods=["GET"])
def get_industry_region_matrix():
    try:
        top_m = request.args.get("top_m", default=20, type=int)
        top_n = request.args.get("top_n", default=15, type=int)
        tier = request.args.get("tier", default="all", type=str)
        data = service.get_industry_region_matrix(top_m=top_m, top_n=top_n, tier=tier)
        if not data:
            return ResponseBuilder.not_found("未找到行业-地域矩阵数据")
        return ResponseBuilder.success("获取行业-地域矩阵成功", data)
    except Exception as e:
        logger.error(f"获取行业-地域矩阵失败: {e}", exc_info=True)
        return ResponseBuilder.internal_error("服务器内部错误", {"type": "INTERNAL_ERROR", "details": str(e)})


@q4_region_bp.route("/regions/position_industry_cooccurrence", methods=["GET"])
def get_position_industry_cooccurrence():
    try:
        region_id = request.args.get("region_id", default=None, type=str)
        top_jobs = request.args.get("top_jobs", default=8, type=int)
        top_industries = request.args.get("top_industries", default=8, type=int)
        data = service.get_position_industry_cooccurrence(
            region_id=region_id,
            top_jobs=top_jobs,
            top_industries=top_industries,
        )
        return ResponseBuilder.success("获取职位-行业共现数据成功", data)
    except Exception as e:
        logger.error(f"获取职位-行业共现数据失败: {e}", exc_info=True)
        return ResponseBuilder.internal_error("服务器内部错误", {"type": "INTERNAL_ERROR", "details": str(e)})


@q4_region_bp.route("/data_quality", methods=["GET"])
def get_q4_data_quality():
    try:
        n_clusters, algorithm, sample_size = _cluster_args()
        data = service.get_data_quality(
            n_clusters=n_clusters,
            algorithm=algorithm,
            sample_size=sample_size,
        )
        return ResponseBuilder.success("获取Q4数据质量指标成功", data)
    except Exception as e:
        logger.error(f"获取Q4数据质量指标失败: {e}", exc_info=True)
        return ResponseBuilder.internal_error("服务器内部错误", {"type": "INTERNAL_ERROR", "details": str(e)})
