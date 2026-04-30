一、核心主表（8 个）
每个维度的完整处理后主表，包含该维度所有衍生字段和指标。
表格
文件名	对应任务	核心用途
full_data_processed_3.2-3.8.csv	全量整合	最终交付的核心文件，包含所有维度的全部处理字段，可直接用于后续所有分析和可视化
salary_dimension_processed.csv	3.2 薪酬维度	包含薪资换算、跨度、离散度、等级、模式等全量薪酬衍生字段
experience_dimension_processed.csv	3.3 经验维度	包含经验等级、平均经验要求、门槛指数等全量经验衍生字段
education_dimension_processed.csv	3.4 学历维度	包含学历等级、平均学历要求、门槛指数等全量学历衍生字段
talent_threshold_dimension_processed.csv	3.5 人才门槛维度	包含综合人才门槛指数、等级划分、各维度门槛汇总字段
recruitment_hot_dimension_processed.csv	3.6 招聘热度维度	包含职位 / 行业 / 城市热度、活跃度、高需求识别等热度字段
job_dimension_processed.csv	3.7 职位维度	包含职位全维度统计、覆盖度、画像特征等职位核心字段
city_dimension_processed.csv	3.8 城市维度	包含城市全维度统计、资源量、活跃度、画像特征等城市核心字段

二、维度基础映射与排名表（7 个）
用于字段标准化、等级合理性验证、基础排名统计，是指标构建的基础支撑
experience_salary_rank.csv（经验等级 - 平均薪资对应排名表，验证经验等级合理性）
experience_label_standard_map.csv（经验等级 - 标签标准化映射表，统一字段规范）
education_salary_rank.csv（学历等级 - 平均薪资对应排名表，验证学历等级合理性）
education_label_standard_map.csv（学历等级 - 标签标准化映射表，统一字段规范）
job_experience_threshold.csv（各职位经验门槛指数表，0-10 标准化）
job_education_threshold.csv（各职位学历门槛指数表，0-10 标准化）
job_talent_threshold.csv（各职位综合人才门槛指数表，0-10 标准化）
三、行业 / 城市 / 企业维度指标表（10 个）
针对行业、城市、企业三个维度的专项统计指标，直接对应赛题的地域分析、行业分析、企业招聘行为分析场景
industry_talent_threshold.csv（各行业综合人才门槛指数表）
city_talent_threshold.csv（各城市综合人才门槛指数表）
job_hot_index.csv（各职位招聘热度指数表，含归一化值）
industry_hot_index.csv（各行业招聘热度指数表，含归一化值）
city_hot_index.csv（各城市招聘热度指数表，含归一化值）
company_activity_index.csv（各企业招聘活跃度指数表，含归一化值）
high_demand_job.csv（高需求职位清单，热度前 10%）
high_activity_industry.csv（高活跃行业清单，热度前 10%）
high_activity_city.csv（高活跃城市清单，热度前 10%）
high_threshold_job_top20.csv（高门槛职位 TOP20 清单）
四、深度分析与模型结果表（14 个）
用于赛题作答、可视化展示的核心分析结果，包含聚类、相似度、差异度、交叉分析等，直接对应赛题的职位画像、城市对比、新兴职位识别等核心任务
experience_salary_pattern_cross.csv（经验等级 - 薪酬模式交叉分析表）
education_job_hot_cross.csv（学历等级 - 职位热度交叉分析表）
threshold_salary_pattern_cross.csv（人才门槛等级 - 薪酬模式交叉分析表）
high_threshold_high_hot_job.csv（高门槛 + 高热度新兴职位清单）
job_comprehensive_profile.csv（职位标准化综合画像向量表，用于相似度计算）
job_difference_matrix.csv（职位差异度矩阵表，全量职位两两差异度）
similar_job_top5.csv（每个职位的 TOP5 最相似职位清单）
job_cluster_explain.csv（职位聚类结果解释表，每个聚类的核心特征）
job_cluster_result.csv（职位聚类结果表，每个职位对应的聚类标签）
city_comprehensive_profile.csv（城市标准化综合画像向量表）
city_similarity_matrix.csv（城市相似度矩阵表，全量城市两两相似度）
similar_city_top5.csv（每个城市的 TOP5 最相似城市清单）
city_cluster_explain.csv（城市聚类结果解释表，每个聚类的核心特征）
city_cluster_result.csv（城市聚类结果表，每个城市对应的聚类标签）