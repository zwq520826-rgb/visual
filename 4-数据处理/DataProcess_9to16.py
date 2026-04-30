import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import RobustScaler
from sklearn.cluster import KMeans

# ==================== 1. 配置路径与字段 ====================
SOURCE_DATA_PATH = r"D:\code\pycharm_projects\KeShiHua-course\visual\dataset\3_数据清洗\clean_feature_ready.csv"
BASE_OUTPUT_DIR = r"D:\code\pycharm_projects\KeShiHua-course\visual\4-数据处理\output"

COL_JOB = 'job_title'
COL_COMPANY = 'company'
COL_INDUSTRY = 'company_type'
COL_CITY = 'city'
COL_SALARY = 'salary_mid_monthly'
COL_EXP = 'experience_rank'
COL_EDU = 'education_rank'
COL_TALENT = 'talent_threshold_index'


# ==================== 2. 动态目录与保存逻辑 ====================

def save_result(step_num, df, filename):
    """
    动态创建类似于 'step_9_industry_stats' 这样的文件夹，
    并将文件保存在该文件夹内部。
    """
    # 获取去掉后缀的文件名，比如把 'industry_stats.csv' 变成 'industry_stats'
    base_name = os.path.splitext(filename)[0]

    # 拼接新的文件夹名称，例如：step_9_industry_stats
    folder_name = f"step_{step_num}_{base_name}"
    step_dir = os.path.join(BASE_OUTPUT_DIR, folder_name)

    # 自动创建该特定任务的文件夹
    if not os.path.exists(step_dir):
        os.makedirs(step_dir)

    # 拼接完整的文件保存路径
    out_path = os.path.join(step_dir, filename)

    if filename.endswith('.csv'):
        df.to_csv(out_path, index=False, encoding='utf-8-sig')
    elif filename.endswith('.json'):
        df.to_json(out_path, orient='records', force_ascii=False)

    print(f"  [√] 已创建文件夹并保存: {out_path}")


# ==================== 3. 核心处理逻辑 ====================

def logic_step_9(df):
    print("-> 执行 9. 行业维度分析...")
    industry_stats = df.groupby(COL_INDUSTRY).agg(
        job_count=(COL_JOB, 'count'),
        avg_salary=(COL_SALARY, 'mean'),
        company_count=(COL_COMPANY, 'nunique'),
        city_count=(COL_CITY, 'nunique'),
        avg_exp=(COL_EXP, 'mean'),
        avg_edu=(COL_EDU, 'mean'),
        avg_talent_idx=(COL_TALENT, 'mean')
    ).reset_index()

    industry_stats['hot_index'] = industry_stats['job_count'] / industry_stats['job_count'].max()
    industry_stats['activity_index'] = industry_stats['company_count'] / industry_stats['company_count'].max()

    # 将自动保存在 step_9_industry_stats/industry_stats.csv
    save_result(9, industry_stats, "industry_stats.csv")
    return industry_stats


def logic_step_10(df):
    print("-> 执行 10. 企业维度分析...")
    company_stats = df.groupby(COL_COMPANY).agg(
        job_count=(COL_JOB, 'count'),
        primary_industry=(COL_INDUSTRY, lambda x: x.mode()[0] if not x.mode().empty else np.nan),
        primary_city=(COL_CITY, lambda x: x.mode()[0] if not x.mode().empty else np.nan),
        unique_jobs=(COL_JOB, 'nunique')
    ).reset_index()

    company_stats['activity_score'] = company_stats['job_count']
    save_result(10, company_stats, "company_stats.csv")
    return company_stats


def logic_step_11(df):
    print("-> 执行 11. 城市-行业组合维度分析...")
    city_ind = df.groupby([COL_CITY, COL_INDUSTRY]).agg(
        local_job_count=(COL_JOB, 'count'),
        avg_salary=(COL_SALARY, 'mean'),
        avg_exp=(COL_EXP, 'mean'),
        avg_edu=(COL_EDU, 'mean')
    ).reset_index()

    city_totals = df.groupby(COL_CITY)[COL_JOB].count().reset_index(name='city_total')
    ind_totals = df.groupby(COL_INDUSTRY)[COL_JOB].count().reset_index(name='ind_total')
    national_total = len(df)

    city_ind = city_ind.merge(city_totals, on=COL_CITY).merge(ind_totals, on=COL_INDUSTRY)
    city_ind['local_ratio'] = city_ind['local_job_count'] / city_ind['city_total']
    city_ind['national_ratio'] = city_ind['ind_total'] / national_total
    city_ind['location_quotient'] = city_ind['local_ratio'] / city_ind['national_ratio']
    city_ind['is_specialty'] = city_ind['location_quotient'] > 1.2

    save_result(11, city_ind, "city_industry_stats.csv")
    return city_ind


def logic_step_12(df):
    print("-> 执行 12. 职位-行业分布香农熵分析...")
    job_total = df.groupby(COL_JOB)[COL_COMPANY].count().reset_index(name='total_jobs')
    job_ind = df.groupby([COL_JOB, COL_INDUSTRY])[COL_COMPANY].count().reset_index(name='ind_jobs')

    merged = job_ind.merge(job_total, on=COL_JOB)
    merged['p_x'] = merged['ind_jobs'] / merged['total_jobs']
    merged['entropy_part'] = - merged['p_x'] * np.log2(merged['p_x'])

    job_entropy = merged.groupby(COL_JOB)['entropy_part'].sum().reset_index(name='industry_entropy')

    save_result(12, job_entropy, "job_industry_entropy.csv")
    return job_entropy


def logic_step_13(df):
    print("-> 执行 13. 职位-城市分布分析...")
    job_total = df.groupby(COL_JOB)[COL_COMPANY].count().reset_index(name='total_jobs')
    job_city = df.groupby([COL_JOB, COL_CITY])[COL_COMPANY].count().reset_index(name='city_jobs')

    merged = job_city.merge(job_total, on=COL_JOB)
    merged['p_x'] = merged['city_jobs'] / merged['total_jobs']
    merged['entropy_part'] = - merged['p_x'] * np.log2(merged['p_x'])

    job_city_entropy = merged.groupby(COL_JOB).agg(
        city_entropy=('entropy_part', 'sum'),
        city_coverage=('city_jobs', 'count')
    ).reset_index()

    save_result(13, job_city_entropy, "job_city_entropy.csv")
    return job_city_entropy


def logic_step_14(df):
    print("-> 执行 14. 跨维度建模与薪酬模式识别...")
    job_stats = df.groupby(COL_JOB).agg(
        job_demand=(COL_COMPANY, 'count'),
        avg_salary=(COL_SALARY, 'mean'),
        talent_idx=(COL_TALENT, 'mean')
    ).reset_index()

    med_demand = job_stats['job_demand'].median()
    med_salary = job_stats['avg_salary'].median()

    conditions = [
        (job_stats['avg_salary'] >= med_salary) & (job_stats['job_demand'] >= med_demand),
        (job_stats['avg_salary'] >= med_salary) & (job_stats['job_demand'] < med_demand),
        (job_stats['avg_salary'] < med_salary) & (job_stats['job_demand'] >= med_demand),
        (job_stats['avg_salary'] < med_salary) & (job_stats['job_demand'] < med_demand)
    ]
    choices = ['高薪高需', '高薪低需', '低薪高需', '低薪低需']
    job_stats['salary_pattern'] = np.select(conditions, choices)

    job_stats['demand_norm'] = job_stats['job_demand'] / job_stats['job_demand'].max()
    job_stats['salary_norm'] = job_stats['avg_salary'] / job_stats['avg_salary'].max()
    job_stats['emerging_index'] = (job_stats['demand_norm'] * 0.4) + (job_stats['salary_norm'] * 0.6)

    save_result(14, job_stats, "cross_dim_job_model.csv")
    return job_stats


def logic_step_15(df):
    print("-> 执行 15. K-Means 聚类分析...")
    city_features = df.groupby(COL_CITY).agg(
        job_count=(COL_JOB, 'count'),
        avg_salary=(COL_SALARY, 'mean'),
        avg_exp=(COL_EXP, 'mean'),
        avg_edu=(COL_EDU, 'mean')
    ).reset_index()

    city_features['job_count_log'] = np.log1p(city_features['job_count'])

    features = ['job_count_log', 'avg_salary', 'avg_exp', 'avg_edu']
    X = city_features[features].fillna(0)

    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    city_features['city_cluster'] = kmeans.fit_predict(X_scaled)

    save_result(15, city_features, "city_clustering.csv")
    return city_features


def logic_step_16(df):
    print("-> 执行 16. 生成面向前端的可视化 JSON 数据...")
    city_data = logic_step_15(df)
    viz_city = city_data[[COL_CITY, 'job_count', 'avg_salary', 'city_cluster']]
    # 会自动保存到 step_16_viz_city_clusters/viz_city_clusters.json
    save_result(16, viz_city, "viz_city_clusters.json")
    return viz_city


# ==================== 4. 主控引擎 ====================
def main():
    if not os.path.exists(BASE_OUTPUT_DIR):
        os.makedirs(BASE_OUTPUT_DIR)

    print(f"\n[*] 正在读取源数据: {SOURCE_DATA_PATH}")
    if not os.path.exists(SOURCE_DATA_PATH):
        print(f"[x] 未找到源文件: {SOURCE_DATA_PATH}")
        return

    df_source = pd.read_csv(SOURCE_DATA_PATH, low_memory=False)
    print(f"[*] 数据读取成功，总行数: {len(df_source)}\n")

    logic_step_9(df_source)
    logic_step_10(df_source)
    logic_step_11(df_source)
    logic_step_12(df_source)
    logic_step_13(df_source)
    logic_step_14(df_source)
    logic_step_15(df_source)
    logic_step_16(df_source)

    print("\n[√] 全部完成！各任务文件夹及其包含的结果文件已生成。")


if __name__ == "__main__":
    main()