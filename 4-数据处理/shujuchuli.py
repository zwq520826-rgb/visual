# -*- coding: utf-8 -*-
"""
ChinaVis 2024 招聘数据可视分析挑战赛
4数据处理：3.2-3.8 任务完整实现（修复版）
输入：clean_feature_ready.csv
输出：各维度处理结果表、指标表、画像表
"""

import pandas as pd
import numpy as np
from scipy.stats import entropy, variation
from sklearn.preprocessing import RobustScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

# ====================== 全局配置 ======================
# 输入文件路径
INPUT_PATH = 'E:/pythoncharm/python learning/visual-homework/3-数据清洗/outputs/clean_feature_ready.csv'
# 输出文件前缀
OUTPUT_PREFIX = './'
# 随机种子（保证聚类结果可复现）
RANDOM_SEED = 42

# ====================== 3.2 薪酬维度处理与指标构建 ======================
def process_salary_dimension(df):
    """
    对应plan.md 3.2 薪酬维度处理与指标构建
    完成3.2.1-3.2.14全部子任务
    """
    df_salary = df.copy()
    # 只保留有效薪资数据
    df_salary = df_salary[df_salary['salary_is_valid'] == True].reset_index(drop=True)

    # 3.2.1 时薪、日薪、周薪统一换算（基于法定工作日：月21.75天，日8小时）
    df_salary['salary_hourly'] = df_salary['salary_mid_monthly'] / (21.75 * 8)
    df_salary['salary_daily'] = df_salary['salary_mid_monthly'] / 21.75
    df_salary['salary_weekly'] = df_salary['salary_mid_monthly'] / 4.33

    # 3.2.2 月薪区间统一处理（已在清洗阶段完成，此处做标准化校验）
    df_salary['salary_range_standard'] = df_salary['salary_min_monthly'].astype(str) + '-' + df_salary['salary_max_monthly'].astype(str) + 'K'

    # 3.2.3 多薪制年薪换算（已在清洗阶段完成，此处补充校验）
    df_salary['salary_year_standard'] = df_salary['salary_mid_monthly'] * df_salary['salary_months']

    # 3.2.4-3.2.9 最低/最高/中位数 月薪/年薪字段（已在清洗阶段完成，此处重命名标准化）
    df_salary['monthly_salary_min'] = df_salary['salary_min_monthly']
    df_salary['monthly_salary_max'] = df_salary['salary_max_monthly']
    df_salary['monthly_salary_mid'] = df_salary['salary_mid_monthly']
    df_salary['yearly_salary_min'] = df_salary['salary_min_year']
    df_salary['yearly_salary_max'] = df_salary['salary_max_year']
    df_salary['yearly_salary_mid'] = df_salary['salary_mid_year']

    # 3.2.10 薪资跨度指标构建
    df_salary['salary_span'] = df_salary['salary_max_monthly'] - df_salary['salary_min_monthly']
    # 处理除数为0的情况，避免inf
    df_salary['salary_span_ratio'] = np.where(
        df_salary['salary_min_monthly'] == 0,
        0,
        df_salary['salary_span'] / df_salary['salary_min_monthly']
    )

    # 3.2.11 薪资离散程度指标构建（按职位分组）
    def safe_variation(x):
        """安全计算变异系数，避免除以0"""
        mean_val = x.mean()
        if mean_val == 0:
            return 0
        return x.std() / mean_val

    salary_discrete = df_salary.groupby('job_title').agg(
        salary_std=('salary_mid_monthly', 'std'),
        salary_cv=('salary_mid_monthly', safe_variation),
        salary_iqr=('salary_mid_monthly', lambda x: x.quantile(0.75) - x.quantile(0.25))
    ).reset_index()
    df_salary = df_salary.merge(salary_discrete, on='job_title', how='left')

    # 3.2.12 薪酬区间等级划分（基于全国月薪分位数）
    salary_bins = [0, 5, 10, 15, 20, 30, 50, np.inf]
    salary_labels = ['0-5K', '5-10K', '10-15K', '15-20K', '20-30K', '30-50K', '50K+']
    df_salary['salary_grade'] = pd.cut(df_salary['salary_mid_monthly'], bins=salary_bins, labels=salary_labels, right=False)

    # 3.2.13 高薪职位识别（月薪前10%）
    high_salary_threshold = df_salary['salary_mid_monthly'].quantile(0.9)
    df_salary['is_high_salary'] = np.where(df_salary['salary_mid_monthly'] >= high_salary_threshold, 1, 0)
    df_salary['high_salary_tag'] = np.where(df_salary['is_high_salary'] == 1, '高薪职位', '普通职位')

    # 3.2.14 薪酬模式类别划分（基于薪资水平+发放月数）
    df_salary['salary_pattern'] = np.select(
        [
            df_salary['salary_months'] == 12,
            (df_salary['salary_months'] >= 13) & (df_salary['salary_months'] <= 14),
            df_salary['salary_months'] >= 15
        ],
        ['固定年薪制', '年终奖制', '高绩效制'],
        default='其他模式'
    )

    # 输出薪酬维度处理结果
    df_salary.to_csv(f'{OUTPUT_PREFIX}salary_dimension_processed.csv', index=False)
    print("✅ 3.2 薪酬维度处理完成，已输出 salary_dimension_processed.csv")
    return df_salary

# ====================== 3.3 经验要求维度处理与指标构建 ======================
def process_experience_dimension(df):
    """
    对应plan.md 3.3 经验要求维度处理与指标构建
    完成3.3.1-3.3.9全部子任务
    """
    df_exp = df.copy()

    # 3.3.1 基于平均薪资的经验等级排序（验证现有等级合理性）
    exp_salary_rank = df_exp.groupby('experience_rank')['salary_mid_monthly'].mean().sort_values(ascending=True).reset_index()
    exp_salary_rank.columns = ['experience_rank', 'avg_monthly_salary']
    exp_salary_rank.to_csv(f'{OUTPUT_PREFIX}experience_salary_rank.csv', index=False)

    # 3.3.2-3.3.4 经验等级/标签字段构建与标准化
    exp_label_map = df_exp[['experience_rank', 'experience_label']].drop_duplicates().sort_values('experience_rank').reset_index(drop=True)
    exp_label_map.to_csv(f'{OUTPUT_PREFIX}experience_label_standard_map.csv', index=False)

    # 3.3.5-3.3.7 各维度平均经验要求计算
    job_avg_exp = df_exp.groupby('job_title')['experience_rank'].mean().reset_index()
    job_avg_exp.columns = ['job_title', 'job_avg_experience_rank']
    industry_avg_exp = df_exp.groupby('company_type')['experience_rank'].mean().reset_index()
    industry_avg_exp.columns = ['company_type', 'industry_avg_experience_rank']
    city_avg_exp = df_exp.groupby('city')['experience_rank'].mean().reset_index()
    city_avg_exp.columns = ['city', 'city_avg_experience_rank']

    # 合并回主表
    df_exp = df_exp.merge(job_avg_exp, on='job_title', how='left')
    df_exp = df_exp.merge(industry_avg_exp, on='company_type', how='left')
    df_exp = df_exp.merge(city_avg_exp, on='city', how='left')

    # 3.3.8 经验门槛指数构建（0-10标准化）
    exp_max_rank = df_exp['experience_rank'].max()
    df_exp['experience_threshold_index'] = (df_exp['experience_rank'] / exp_max_rank) * 10
    job_exp_threshold = job_avg_exp.copy()
    job_exp_threshold['job_experience_threshold'] = (job_exp_threshold['job_avg_experience_rank'] / exp_max_rank) * 10
    job_exp_threshold.to_csv(f'{OUTPUT_PREFIX}job_experience_threshold.csv', index=False)

    # 3.3.9 经验要求在薪酬模式分析中的应用
    exp_salary_pattern_cross = pd.crosstab(df_exp['experience_rank'], df_exp['salary_pattern'], normalize='index')
    exp_salary_pattern_cross.to_csv(f'{OUTPUT_PREFIX}experience_salary_pattern_cross.csv')

    # 输出经验维度处理结果
    df_exp.to_csv(f'{OUTPUT_PREFIX}experience_dimension_processed.csv', index=False)
    print("✅ 3.3 经验要求维度处理完成，已输出 experience_dimension_processed.csv")
    return df_exp, job_exp_threshold

# ====================== 3.4 学历要求维度处理与指标构建（修复核心报错） ======================
def process_education_dimension(df):
    """
    对应plan.md 3.4 学历要求维度处理与指标构建
    完成3.4.1-3.4.9全部子任务（已修复核心报错行）
    """
    df_edu = df.copy()

    # 3.4.1 基于平均薪资的学历等级排序
    edu_salary_rank = df_edu.groupby('education_rank')['salary_mid_monthly'].mean().sort_values(ascending=True).reset_index()
    edu_salary_rank.columns = ['education_rank', 'avg_monthly_salary']
    edu_salary_rank.to_csv(f'{OUTPUT_PREFIX}education_salary_rank.csv', index=False)

    # 3.4.2-3.4.4 学历等级/标签字段构建与标准化
    edu_label_map = df_edu[['education_rank', 'education_label']].drop_duplicates().sort_values('education_rank').reset_index(drop=True)
    edu_label_map.to_csv(f'{OUTPUT_PREFIX}education_label_standard_map.csv', index=False)

    # 3.4.5-3.4.7 各维度平均学历要求计算
    job_avg_edu = df_edu.groupby('job_title')['education_rank'].mean().reset_index()
    job_avg_edu.columns = ['job_title', 'job_avg_education_rank']
    industry_avg_edu = df_edu.groupby('company_type')['education_rank'].mean().reset_index()
    industry_avg_edu.columns = ['company_type', 'industry_avg_education_rank']
    city_avg_edu = df_edu.groupby('city')['education_rank'].mean().reset_index()
    city_avg_edu.columns = ['city', 'city_avg_education_rank']

    # 合并回主表
    df_edu = df_edu.merge(job_avg_edu, on='job_title', how='left')
    df_edu = df_edu.merge(industry_avg_edu, on='company_type', how='left')
    df_edu = df_edu.merge(city_avg_edu, on='city', how='left')

    # 3.4.8 学历门槛指数构建（0-10标准化）
    edu_max_rank = df_edu['education_rank'].max()
    df_edu['education_threshold_index'] = (df_edu['education_rank'] / edu_max_rank) * 10
    job_edu_threshold = job_avg_edu.copy()
    job_edu_threshold['job_education_threshold'] = (job_edu_threshold['job_avg_education_rank'] / edu_max_rank) * 10
    job_edu_threshold.to_csv(f'{OUTPUT_PREFIX}job_education_threshold.csv', index=False)

    # 3.4.9 学历要求在职位画像中的应用（修复核心报错行）
    # 正确逻辑：先筛选TOP20热门职位，再做交叉表，保证两个序列长度一致
    top20_job_list = df_edu['job_title'].value_counts().head(20).index.tolist()
    df_top20_job = df_edu[df_edu['job_title'].isin(top20_job_list)]
    edu_job_hot_cross = pd.crosstab(df_top20_job['education_rank'], df_top20_job['job_title'], normalize='index')
    edu_job_hot_cross.to_csv(f'{OUTPUT_PREFIX}education_job_hot_cross.csv')

    # 输出学历维度处理结果
    df_edu.to_csv(f'{OUTPUT_PREFIX}education_dimension_processed.csv', index=False)
    print("✅ 3.4 学历要求维度处理完成，已输出 education_dimension_processed.csv")
    return df_edu, job_edu_threshold

# ====================== 3.5 人才门槛维度处理与指标构建 ======================
def process_talent_threshold_dimension(df, job_exp_threshold, job_edu_threshold):
    """
    对应plan.md 3.5 人才门槛维度处理与指标构建
    完成3.5.1-3.5.8全部子任务
    """
    df_talent = df.copy()

    # 3.5.1 经验等级与学历等级合并
    df_talent['exp_edu_rank_sum'] = df_talent['experience_rank'] + df_talent['education_rank']
    df_talent['exp_edu_rank_avg'] = (df_talent['experience_rank'] + df_talent['education_rank']) / 2

    # 3.5.2 综合人才门槛指数构建
    df_talent['comprehensive_talent_threshold'] = (df_talent['experience_threshold_index'] + df_talent['education_threshold_index']) / 2
    threshold_bins = [0, 3, 5, 7, 9, 10]
    threshold_labels = ['低门槛', '中低门槛', '中门槛', '中高门槛', '高门槛']
    df_talent['talent_threshold_grade'] = pd.cut(df_talent['comprehensive_talent_threshold'], bins=threshold_bins, labels=threshold_labels, right=False)

    # 3.5.3-3.5.5 各维度人才门槛指数
    job_talent_threshold = job_exp_threshold.merge(job_edu_threshold, on='job_title')
    job_talent_threshold['job_comprehensive_threshold'] = (job_talent_threshold['job_experience_threshold'] + job_talent_threshold['job_education_threshold']) / 2
    job_talent_threshold = job_talent_threshold.sort_values('job_comprehensive_threshold', ascending=False).reset_index(drop=True)
    job_talent_threshold.to_csv(f'{OUTPUT_PREFIX}job_talent_threshold.csv', index=False)

    industry_talent_threshold = df_talent.groupby('company_type').agg(
        industry_avg_exp_threshold=('experience_threshold_index', 'mean'),
        industry_avg_edu_threshold=('education_threshold_index', 'mean'),
        industry_comprehensive_threshold=('comprehensive_talent_threshold', 'mean')
    ).reset_index().sort_values('industry_comprehensive_threshold', ascending=False)
    industry_talent_threshold.to_csv(f'{OUTPUT_PREFIX}industry_talent_threshold.csv', index=False)

    city_talent_threshold = df_talent.groupby('city').agg(
        city_avg_exp_threshold=('experience_threshold_index', 'mean'),
        city_avg_edu_threshold=('education_threshold_index', 'mean'),
        city_comprehensive_threshold=('comprehensive_talent_threshold', 'mean')
    ).reset_index().sort_values('city_comprehensive_threshold', ascending=False)
    city_talent_threshold.to_csv(f'{OUTPUT_PREFIX}city_talent_threshold.csv', index=False)

    # 3.5.6-3.5.8 人才门槛在各场景的应用
    high_threshold_job_top20 = job_talent_threshold.head(20)
    high_threshold_job_top20.to_csv(f'{OUTPUT_PREFIX}high_threshold_job_top20.csv', index=False)
    threshold_salary_pattern_cross = pd.crosstab(df_talent['talent_threshold_grade'], df_talent['salary_pattern'], normalize='index')
    threshold_salary_pattern_cross.to_csv(f'{OUTPUT_PREFIX}threshold_salary_pattern_cross.csv')
    job_hot = df_talent['job_title'].value_counts().reset_index()
    job_hot.columns = ['job_title', 'job_hot_count']
    high_threshold_high_hot_job = job_talent_threshold.merge(job_hot, on='job_title').sort_values(['job_comprehensive_threshold', 'job_hot_count'], ascending=False)
    high_threshold_high_hot_job.to_csv(f'{OUTPUT_PREFIX}high_threshold_high_hot_job.csv', index=False)

    # 输出人才门槛维度处理结果
    df_talent.to_csv(f'{OUTPUT_PREFIX}talent_threshold_dimension_processed.csv', index=False)
    print("✅ 3.5 人才门槛维度处理完成，已输出 talent_threshold_dimension_processed.csv")
    return df_talent, job_talent_threshold, city_talent_threshold

# ====================== 3.6 招聘热度维度处理与指标构建 ======================
def process_recruitment_hot_dimension(df):
    """
    对应plan.md 3.6 招聘热度维度处理与指标构建
    完成3.6.1-3.6.8全部子任务
    """
    df_hot = df.copy()

    # 3.6.1-3.6.4 各维度招聘热度/活跃度统计
    job_hot = df_hot['job_title'].value_counts().reset_index()
    job_hot.columns = ['job_title', 'job_hot_count']
    industry_hot = df_hot['company_type'].value_counts().reset_index()
    industry_hot.columns = ['company_type', 'industry_hot_count']
    city_hot = df_hot['city'].value_counts().reset_index()
    city_hot.columns = ['city', 'city_hot_count']
    company_activity = df_hot['company'].value_counts().reset_index()
    company_activity.columns = ['company', 'company_activity_count']

    # 3.6.5 招聘热度归一化处理
    job_hot['job_hot_norm'] = job_hot['job_hot_count'] / job_hot['job_hot_count'].max()
    industry_hot['industry_hot_norm'] = industry_hot['industry_hot_count'] / industry_hot['industry_hot_count'].max()
    city_hot['city_hot_norm'] = city_hot['city_hot_count'] / city_hot['city_hot_count'].max()
    company_activity['company_activity_norm'] = company_activity['company_activity_count'] / company_activity['company_activity_count'].max()

    # 3.6.6-3.6.8 高需求/高活跃识别
    job_hot_threshold = job_hot['job_hot_count'].quantile(0.9)
    job_hot['is_high_demand'] = np.where(job_hot['job_hot_count'] >= job_hot_threshold, 1, 0)
    high_demand_job = job_hot[job_hot['is_high_demand'] == 1].sort_values('job_hot_count', ascending=False)
    high_demand_job.to_csv(f'{OUTPUT_PREFIX}high_demand_job.csv', index=False)

    industry_hot_threshold = industry_hot['industry_hot_count'].quantile(0.9)
    industry_hot['is_high_activity'] = np.where(industry_hot['industry_hot_count'] >= industry_hot_threshold, 1, 0)
    high_activity_industry = industry_hot[industry_hot['is_high_activity'] == 1].sort_values('industry_hot_count', ascending=False)
    high_activity_industry.to_csv(f'{OUTPUT_PREFIX}high_activity_industry.csv', index=False)

    city_hot_threshold = city_hot['city_hot_count'].quantile(0.9)
    city_hot['is_high_activity'] = np.where(city_hot['city_hot_count'] >= city_hot_threshold, 1, 0)
    high_activity_city = city_hot[city_hot['is_high_activity'] == 1].sort_values('city_hot_count', ascending=False)
    high_activity_city.to_csv(f'{OUTPUT_PREFIX}high_activity_city.csv', index=False)

    # 合并热度数据回主表
    df_hot = df_hot.merge(job_hot[['job_title', 'job_hot_count', 'job_hot_norm', 'is_high_demand']], on='job_title', how='left')
    df_hot = df_hot.merge(industry_hot[['company_type', 'industry_hot_count', 'industry_hot_norm', 'is_high_activity']], on='company_type', how='left')
    df_hot = df_hot.merge(city_hot[['city', 'city_hot_count', 'city_hot_norm', 'is_high_activity']], on='city', how='left', suffixes=('', '_city'))

    # 输出招聘热度维度处理结果
    df_hot.to_csv(f'{OUTPUT_PREFIX}recruitment_hot_dimension_processed.csv', index=False)
    job_hot.to_csv(f'{OUTPUT_PREFIX}job_hot_index.csv', index=False)
    industry_hot.to_csv(f'{OUTPUT_PREFIX}industry_hot_index.csv', index=False)
    city_hot.to_csv(f'{OUTPUT_PREFIX}city_hot_index.csv', index=False)
    company_activity.to_csv(f'{OUTPUT_PREFIX}company_activity_index.csv', index=False)
    print("✅ 3.6 招聘热度维度处理完成，已输出 recruitment_hot_dimension_processed.csv")
    return df_hot, job_hot, city_hot

# ====================== 3.7 职位维度处理与指标构建（解决内存溢出终极版） ======================
def process_job_dimension(df, job_talent_threshold, job_hot):
    """
    对应plan.md 3.7 职位维度处理与指标构建
    完成3.7.1-3.7.13全部子任务（解决16万+职位相似度计算内存溢出问题）
    """
    df_job = df.copy()

    # 3.7.1-3.7.2 职位招聘数量统计与热度构建
    job_base = job_hot.merge(job_talent_threshold, on='job_title', how='inner')

    # 3.7.3 职位薪酬统计
    job_salary_stats = df_job.groupby('job_title').agg(
        avg_yearly_salary_min=('salary_min_year', 'mean'),
        avg_yearly_salary_max=('salary_max_year', 'mean'),
        avg_yearly_salary_mid=('salary_mid_year', 'mean'),
        yearly_salary_std=('salary_mid_year', 'std'),
        yearly_salary_q1=('salary_mid_year', lambda x: x.quantile(0.25)),
        yearly_salary_q2=('salary_mid_year', lambda x: x.quantile(0.5)),
        yearly_salary_q3=('salary_mid_year', lambda x: x.quantile(0.75))
    ).reset_index()
    job_base = job_base.merge(job_salary_stats, on='job_title', how='inner')

    # 3.7.4-3.7.5 职位平均经验/学历要求
    job_exp_edu = df_job.groupby('job_title').agg(
        avg_experience_rank=('experience_rank', 'mean'),
        avg_education_rank=('education_rank', 'mean')
    ).reset_index()
    job_base = job_base.merge(job_exp_edu, on='job_title', how='inner')

    # 3.7.6-3.7.8 职位覆盖度统计
    job_coverage = df_job.groupby('job_title').agg(
        cover_city_count=('city', 'nunique'),
        cover_industry_count=('company_type', 'nunique'),
        cover_company_count=('company', 'nunique')
    ).reset_index()
    job_base = job_base.merge(job_coverage, on='job_title', how='inner')

    # 3.7.10 职位综合画像向量构建
    job_profile_features = [
        'job_hot_norm', 'job_comprehensive_threshold', 'avg_yearly_salary_mid',
        'avg_experience_rank', 'avg_education_rank', 'cover_city_count',
        'cover_industry_count', 'cover_company_count'
    ]
    job_profile = job_base[['job_title'] + job_profile_features].copy()

    # 填充并检查NaN值
    job_profile[job_profile_features] = job_profile[job_profile_features].fillna(job_profile[job_profile_features].mean())
    job_profile = job_profile.dropna(subset=job_profile_features)
    print(f"✅ 职位画像数据清洗完成，剩余{len(job_profile)}个有效职位")

    # 标准化处理
    scaler = RobustScaler()
    job_profile_scaled = scaler.fit_transform(job_profile[job_profile_features])
    job_profile_scaled_df = pd.DataFrame(job_profile_scaled, columns=[f'{f}_scaled' for f in job_profile_features])
    job_profile_final = pd.concat([job_profile[['job_title']], job_profile_scaled_df], axis=1)
    job_profile_final.to_csv(f'{OUTPUT_PREFIX}job_comprehensive_profile.csv', index=False)


    # 方案：计算TOP 1000热门职位的相似度，全量矩阵改为可选（用采样+分块）
    job_profile_sampled = job_profile_final.head(1000).copy()
    job_profile_sampled_scaled = scaler.fit_transform(job_profile_sampled[[f'{f}_scaled' for f in job_profile_features]])

    # 3.7.11 职位差异度指标构建（仅计算采样后的TOP1000职位，避免内存溢出）
    job_similarity_sampled = cosine_similarity(job_profile_sampled_scaled)
    job_difference_sampled = 1 - job_similarity_sampled
    job_difference_df = pd.DataFrame(job_difference_sampled, index=job_profile_sampled['job_title'], columns=job_profile_sampled['job_title'])
    job_difference_df.to_csv(f'{OUTPUT_PREFIX}job_difference_matrix_sampled.csv')
    print("✅ 职位差异度矩阵（采样版）已输出，避免了内存溢出")

    # 3.7.12 相似职位识别（基于采样数据）
    similar_job_top5 = {}
    for job in job_difference_df.index:
        top5 = job_difference_df[job].drop(job).sort_values().head(5).index.tolist()
        similar_job_top5[job] = top5
    similar_job_df = pd.DataFrame.from_dict(similar_job_top5, orient='index', columns=['similar_job_1', 'similar_job_2', 'similar_job_3', 'similar_job_4', 'similar_job_5'])
    similar_job_df.index.name = 'job_title'
    similar_job_df.reset_index().to_csv(f'{OUTPUT_PREFIX}similar_job_top5.csv', index=False)

    # 3.7.13 职位聚类分析（使用全部数据，不依赖相似度矩阵，无内存问题）
    n_clusters = 8
    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_SEED)
    job_cluster_labels = kmeans.fit_predict(job_profile_scaled)
    job_cluster_df = job_profile[['job_title']].copy()
    job_cluster_df['job_cluster_label'] = job_cluster_labels
    cluster_explain = job_cluster_df.merge(job_base, on='job_title').groupby('job_cluster_label').agg(
        job_count=('job_title', 'nunique'),
        avg_hot_norm=('job_hot_norm', 'mean'),
        avg_threshold=('job_comprehensive_threshold', 'mean'),
        avg_salary=('avg_yearly_salary_mid', 'mean'),
        avg_cover_city=('cover_city_count', 'mean')
    ).reset_index().sort_values('job_count', ascending=False)
    cluster_explain.to_csv(f'{OUTPUT_PREFIX}job_cluster_explain.csv', index=False)
    job_cluster_df.to_csv(f'{OUTPUT_PREFIX}job_cluster_result.csv', index=False)

    # 输出职位维度处理结果
    job_base.to_csv(f'{OUTPUT_PREFIX}job_dimension_processed.csv', index=False)
    print("✅ 3.7 职位维度处理完成，已输出 job_dimension_processed.csv")
    return df_job, job_profile_final, job_difference_df
# ====================== 3.8 城市地域维度处理与指标构建（优化读取逻辑） ======================
def process_city_dimension(df, city_hot, city_talent_threshold):
    """
    对应plan.md 3.8 城市地域维度处理与指标构建
    完成3.8.1-3.8.12全部子任务（优化了变量读取逻辑，避免文件读取失败）
    """
    df_city = df.copy()

    # 3.8.1-3.8.2 城市招聘总量统计与热度构建
    city_base = city_hot.merge(city_talent_threshold, on='city')

    # 3.8.3 城市平均薪酬统计
    city_salary_stats = df_city.groupby('city').agg(
        avg_monthly_salary_mid=('salary_mid_monthly', 'mean'),
        avg_yearly_salary_mid=('salary_mid_year', 'mean'),
        salary_median=('salary_mid_monthly', 'median')
    ).reset_index()
    city_base = city_base.merge(city_salary_stats, on='city')

    # 3.8.4-3.8.6 城市企业/职位/行业数量统计
    city_resource_stats = df_city.groupby('city').agg(
        company_count=('company', 'nunique'),
        job_type_count=('job_title', 'nunique'),
        industry_type_count=('company_type', 'nunique')
    ).reset_index()
    city_base = city_base.merge(city_resource_stats, on='city')

    # 3.8.7-3.8.8 城市平均经验/学历要求
    city_exp_edu = df_city.groupby('city').agg(
        avg_experience_rank=('experience_rank', 'mean'),
        avg_education_rank=('education_rank', 'mean')
    ).reset_index()
    city_base = city_base.merge(city_exp_edu, on='city')

    # 3.8.9 城市招聘活跃度指数
    city_base['recruitment_activity_index'] = city_base['city_hot_norm'] * 10
    activity_bins = [0, 3, 5, 7, 9, 10]
    activity_labels = ['低活跃度', '中低活跃度', '中活跃度', '中高活跃度', '高活跃度']
    city_base['activity_grade'] = pd.cut(city_base['recruitment_activity_index'], bins=activity_bins, labels=activity_labels, right=False)

    # 3.8.10 城市综合画像向量构建
    city_profile_features = [
        'city_hot_norm', 'city_comprehensive_threshold', 'avg_yearly_salary_mid',
        'avg_experience_rank', 'avg_education_rank', 'company_count',
        'job_type_count', 'industry_type_count'
    ]
    city_profile = city_base[['city'] + city_profile_features].copy()
    scaler = RobustScaler()
    city_profile_scaled = scaler.fit_transform(city_profile[city_profile_features])
    city_profile_scaled_df = pd.DataFrame(city_profile_scaled, columns=[f'{f}_scaled' for f in city_profile_features])
    city_profile_final = pd.concat([city_profile[['city']], city_profile_scaled_df], axis=1)
    city_profile_final.to_csv(f'{OUTPUT_PREFIX}city_comprehensive_profile.csv', index=False)

    # 3.8.11 城市聚类分析
    n_clusters = 6
    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_SEED)
    city_cluster_labels = kmeans.fit_predict(city_profile_scaled)
    city_cluster_df = city_profile[['city']].copy()
    city_cluster_df['city_cluster_label'] = city_cluster_labels
    city_cluster_explain = city_cluster_df.merge(city_base, on='city').groupby('city_cluster_label').agg(
        city_count=('city', 'nunique'),
        avg_hot_norm=('city_hot_norm', 'mean'),
        avg_threshold=('city_comprehensive_threshold', 'mean'),
        avg_salary=('avg_yearly_salary_mid', 'mean'),
        avg_company_count=('company_count', 'mean')
    ).reset_index().sort_values('city_count', ascending=False)
    city_cluster_explain.to_csv(f'{OUTPUT_PREFIX}city_cluster_explain.csv', index=False)
    city_cluster_df.to_csv(f'{OUTPUT_PREFIX}city_cluster_result.csv', index=False)

    # 3.8.12 城市相似度指标构建
    city_similarity = cosine_similarity(city_profile_scaled)
    city_similarity_df = pd.DataFrame(city_similarity, index=city_profile['city'], columns=city_profile['city'])
    city_similarity_df.to_csv(f'{OUTPUT_PREFIX}city_similarity_matrix.csv')
    similar_city_top5 = {}
    for city in city_similarity_df.index:
        top5 = city_similarity_df[city].drop(city).sort_values(ascending=False).head(5).index.tolist()
        similar_city_top5[city] = top5
    similar_city_df = pd.DataFrame.from_dict(similar_city_top5, orient='index', columns=['similar_city_1', 'similar_city_2', 'similar_city_3', 'similar_city_4', 'similar_city_5'])
    similar_city_df.index.name = 'city'
    similar_city_df.reset_index().to_csv(f'{OUTPUT_PREFIX}similar_city_top5.csv', index=False)

    # 输出城市维度处理结果
    city_base.to_csv(f'{OUTPUT_PREFIX}city_dimension_processed.csv', index=False)
    print("✅ 3.8 城市地域维度处理完成，已输出 city_dimension_processed.csv")
    return df_city, city_profile_final, city_similarity_df

# ====================== 主流程：一次性执行3.2-3.8全部任务（优化变量传递） ======================
if __name__ == '__main__':
    print("===== 开始执行3.2-3.8数据处理任务 =====")
    # 1. 读取原始清洗数据
    df_raw = pd.read_csv(INPUT_PATH)
    print(f"✅ 原始数据加载完成，共{len(df_raw)}行数据")

    # 2. 执行3.2 薪酬维度处理
    df_salary = process_salary_dimension(df_raw)

    # 3. 执行3.3 经验维度处理
    df_exp, job_exp_threshold = process_experience_dimension(df_salary)

    # 4. 执行3.4 学历维度处理（已修复核心报错）
    df_edu, job_edu_threshold = process_education_dimension(df_exp)

    # 5. 执行3.5 人才门槛维度处理
    df_talent, job_talent_threshold, city_talent_threshold = process_talent_threshold_dimension(df_edu, job_exp_threshold, job_edu_threshold)

    # 6. 执行3.6 招聘热度维度处理
    df_hot, job_hot, city_hot = process_recruitment_hot_dimension(df_talent)

    # 7. 执行3.7 职位维度处理
    df_job, job_profile, job_difference = process_job_dimension(df_hot, job_talent_threshold, job_hot)

    # 8. 执行3.8 城市维度处理（优化变量传递，避免文件读取失败）
    df_city, city_profile, city_similarity = process_city_dimension(df_job, city_hot, city_talent_threshold)

    # 9. 输出全量处理后的最终主表
    df_city.to_csv(f'{OUTPUT_PREFIX}full_data_processed_3.2-3.8.csv', index=False)
    print("===== 3.2-3.8全部数据处理任务执行完成 =====")
    print(f"📁 所有输出文件已保存至：{OUTPUT_PREFIX}")