# readme_数据清洗

本目录用于给下一阶段（`4-数据处理`）提供统一口径的清洗后数据输入。

## 1. 目录位置

- `dataset/3_数据清洗`

## 2. 已提供文件（CSV）

1. `clean_base.csv`
2. `clean_salary.csv`
3. `clean_feature_ready.csv`
4. `experience_mapping.csv`
5. `education_mapping.csv`
6. `salary_type_distribution.csv`
7. `salary_level_distribution.csv`

## 3. 文件用途说明

- `clean_base.csv`
  - 去重后的基础明细；保留原始七字段。

- `clean_salary.csv`
  - 在基础明细上增加薪资解析字段：
  - `salary_type`, `salary_months`, `salary_min_monthly`, `salary_max_monthly`, `salary_mid_monthly`, `salary_min_year`, `salary_max_year`, `salary_mid_year`, `salary_is_valid`, `salary_is_outlier` 等。

- `clean_feature_ready.csv`
  - 在 `clean_salary.csv` 基础上增加门槛量化字段：
  - `experience_rank`, `experience_label`, `education_rank`, `education_label`, `talent_threshold_index`。
  - 推荐作为 `4-数据处理` 的主输入表。

- `experience_mapping.csv`
  - 经验编码到 rank/label 的映射表。

- `education_mapping.csv`
  - 学历编码到 rank/label 的映射表。

- `salary_type_distribution.csv`
  - 薪资解析类型分布统计。

- `salary_level_distribution.csv`
  - 薪资等级分布统计（按月薪分箱）。

## 4. 使用建议

- 第四阶段优先使用 `clean_feature_ready.csv` 进行指标构建和建模。
- 若需要追溯薪资处理细节，使用 `clean_salary.csv`。
- 尽量不要再从 `JobWanted.xlsx` 重新独立解析，避免口径漂移。
