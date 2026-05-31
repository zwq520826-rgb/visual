# JobWanted 数据集与数据库全表说明

## 1. 文档目的与来源

本文用于统一说明本项目的数据体系，覆盖两部分：

1. `JobWanted_description (1).docx` 中定义的原始数据说明（赛事给定口径）。
2. 项目当前 MySQL（`vision`）中已使用的数据表、用途及字段含义（工程实现口径）。

主要参考文件：

- `docs/data_complain/JobWanted_description (1).docx`
- `docs/数据库表字段总览.md`
- `database/Q3.py`
- `services/*` 与 `routes/*` 中的实际查询逻辑

---

## 2. JobWanted 原始数据说明（来自 docx）

### 2.1 数据集定位

- 该数据集是模拟现实招聘市场的虚拟数据集。
- 用于支持就业趋势、岗位结构、薪资分布、地域差异等分析任务。
- 数据中包含缺失值、异常值、不一致噪声（如无效薪酬、行业缺失等），需要清洗后使用。
- 原始发布格式为 `xlsx`。

### 2.2 原始规模（赛事说明）

`JobWanted_description (1).docx` 描述：

- 招聘通知：430,664
- 职位：169,540
- 企业：267,296
- 行业类别：158
- 行政区划：371

### 2.3 原始字段（赛事定义）

| 字段名 | 含义 | 备注 |
|---|---|---|
| `job_title` | 职位名称（实际为匿名/哈希编码） | 示例：`51b08e...eK` |
| `city` | 行政区划（城市） | 项目中为编码形式（如 `S542`） |
| `salary` | 薪酬字符串 | 示例：`5-10K`、`5-10K·13薪` |
| `experience` | 经验要求（编码） | 示例：`EdD` |
| `education` | 学历要求（编码） | 示例：`GI` |
| `company` | 企业（编码） | 发布招聘通知的企业 |
| `company_type` | 行业类别（编码） | 示例：`type_BLfSmG` |

---

## 3. 项目数据落库与口径说明

### 3.1 当前工程口径与原始口径差异

- 数据库主表 `data` 当前记录数为 **430,394**（见 `docs/数据库表字段总览.md`）。
- 与 docx 中 430,664 存在差异，通常来自清洗、去重、异常剔除或导入口径变化。
- 工程中大量字段为二次加工字段（如薪资分位、经验/学历 rank、熵值、归一化指标）。

### 3.2 数据层次

1. 原始层：`data`
2. 映射层：`experience_mapping`、`education_mapping`
3. 聚合层（按职位/城市/行业）：`job_summary`、`job_summary_by_title`、`cluster_by_city`、`job_city_distribution`
4. 区域层（Q4）：`city_type_statistics`、`city_type_statistics_top20`
5. 行业层（Q5）：`national_industry_stats`

---

## 4. 数据库表总览（当前项目）

> 以下为项目已使用的表（来自 `docs/数据库表字段总览.md` 与代码查询）。

| 表名 | 行数 | 主要用途 |
|---|---:|---|
| `data` | 430394 | 招聘明细主表，所有分析基础 |
| `experience_mapping` | 8 | 经验编码 -> 中文标签/等级映射 |
| `education_mapping` | 9 | 学历编码 -> 中文标签/等级映射 |
| `job_summary_by_title` | 169308 | Q2 职位画像主表（职位聚合） |
| `job_city_distribution` | 268089 | Q2 职位-城市分布 |
| `cluster_by_city` | 268089 | Q1 城市内职位聚类/分层结果 |
| `job_summary` | 242392 | Q5 职位综合统计 |
| `national_industry_stats` | 158 | Q5 行业总体统计 |
| `city_type_statistics` | 7739 | Q4 全量城市-行业统计（气泡） |
| `city_type_statistics_top20` | 7739 | Q4 Top 类别城市-行业统计（热力） |

---

## 5. 各表字段说明（详细）

## 5.1 `data`（招聘明细主表）

**表用途**：全项目基础明细（Q1~Q5 均直接或间接依赖）。

| 字段 | 含义 |
|---|---|
| `job_title` | 职位编码（匿名） |
| `city` | 城市编码（匿名） |
| `salary` | 原始薪资字符串（如 `5-10K·13薪`） |
| `experience` | 经验编码 |
| `education` | 学历编码 |
| `company` | 企业编码 |
| `company_type` | 行业/公司类型编码 |
| `min_annual_salary` | 年薪下界（数值化后） |
| `max_annual_salary` | 年薪上界（数值化后） |
| `median_annual_salary` | 年薪中位估计（数值化后） |
| `city_tier` | 城市等级（如一线/二线/三线/其他） |
| `experience_rank` | 经验等级分值（便于数值计算） |
| `education_rank` | 学历等级分值 |
| `job_level` | 职位层级标签（衍生） |
| `job_in_city_cnt` | 该职位在该城市的岗位量 |
| `is_in_top200` | 是否该城市 Top200 热门职位标记 |
| `city_level` | 城市层级标签（衍生） |
| `city_level_by_salary` | 按薪资口径得到的城市层级标签 |
| `job_in_industry` | 该职位在行业中的规模 |
| `records_count_norm` | 归一化样本量（0~1） |
| `shannon_entropy` | 香农熵（分布离散度/多样性） |

---

## 5.2 `experience_mapping`（经验映射表）

**表用途**：经验编码可读化、排序及评分计算。

| 字段 | 含义 |
|---|---|
| `experience_code` | 经验编码（原始） |
| `experience_rank` | 数值等级（用于均值/排序） |
| `experience_label` | 中文标签（如应届、3-5年等） |
| `avg_annual_salary` | 对应经验层级平均年薪参考值 |

---

## 5.3 `education_mapping`（学历映射表）

**表用途**：学历编码可读化、排序及评分计算。

| 字段 | 含义 |
|---|---|
| `education_code` | 学历编码（原始） |
| `education_rank` | 数值等级（用于均值/排序） |
| `education_label` | 中文标签（如本科、硕士等） |
| `avg_annual_salary` | 对应学历层级平均年薪参考值 |

---

## 5.4 `job_summary_by_title`（职位画像主表，Q2 核心）

**表用途**：按 `job_title` 聚合的画像表，用于 Q2 平行坐标/桑基/嵌套柱图。

| 字段 | 含义 |
|---|---|
| `job_title` | 职位编码 |
| `records_count` | 该职位样本量 |
| `min_salary` | 薪资最小值 |
| `q1_salary` | 薪资 Q1 分位 |
| `median_salary` | 薪资中位数 |
| `q3_salary` | 薪资 Q3 分位 |
| `max_salary` | 薪资最大值 |
| `std_salary` | 薪资标准差（波动） |
| `avg_experience_rank` | 平均经验分值 |
| `avg_education_rank` | 平均学历分值 |
| `total_shannon_entropy` | 分布熵（常用于“行业集中度”的反向指标） |
| `skill_score` | 技能综合分（衍生） |
| `skill_level` | 技能等级标签（初/中/高） |
| `industry_spread` | 行业分散度标签（集中/中等/分散） |
| `market_demand` | 市场需求标签（如冷门/普通/热门） |
| `salary_level` | 薪资层级标签（低/中低/中高/高） |

---

## 5.5 `job_city_distribution`（职位-城市分布表）

**表用途**：Q2 城市偏好与下钻（同职位在不同城市的分布）。

| 字段 | 含义 |
|---|---|
| `job_title` | 职位编码 |
| `city` | 城市编码 |
| `job_count` | 该职位在该城市的岗位数 |
| `avg_salary` | 该职位在该城市平均薪资 |
| `avg_experience` | 该职位在该城市经验均值 |
| `avg_education` | 该职位在该城市学历均值 |

---

## 5.6 `cluster_by_city`（城市内职位聚类结果，Q1 核心）

**表用途**：Q1 散点图、职位层级标签、城市内 Top200 结构分析。

| 字段 | 含义 |
|---|---|
| `job_title` | 职位编码 |
| `city` | 城市编码 |
| `avg_salary` | 城市内该职位平均薪资 |
| `salary_std` | 城市内该职位薪资波动 |
| `avg_education` | 城市内该职位学历均值 |
| `avg_experience` | 城市内该职位经验均值 |
| `min_annual_salary` | 城市内该职位最低年薪 |
| `max_annual_salary` | 城市内该职位最高年薪 |
| `job_in_city_cnt` | 城市内该职位岗位数量 |
| `is_in_top200` | 是否进入该城市 Top200 职位 |
| `job_level_segment` | 职位层级分段标签（如基薪普及/优薪技能/高新管理等） |
| `avg_shannon_entropy` | 该职位分布熵均值 |

---

## 5.7 `job_summary`（职位综合统计表，Q5 排名）

**表用途**：Q5 职位综合排名与多维评分计算。

| 字段 | 含义 |
|---|---|
| `job_title` | 职位编码 |
| `records_count` | 样本量 |
| `min_salary` | 最低薪资 |
| `q1_salary` | Q1 薪资 |
| `median_salary` | 中位薪资 |
| `q3_salary` | Q3 薪资 |
| `max_salary` | 最高薪资 |
| `std_salary` | 薪资标准差 |
| `avg_experience_rank` | 平均经验分值 |
| `avg_education_rank` | 平均学历分值 |
| `records_count_norm` | 归一化样本量（用于综合分） |
| `company_type` | 行业编码 |
| `total_shannon_entropy` | 熵值（多样性/集中度相关） |

---

## 5.8 `national_industry_stats`（行业总览统计表，Q5 行业趋势）

**表用途**：行业玫瑰图、行业散点/趋势分析。

| 字段 | 含义 |
|---|---|
| `company_type` | 行业编码 |
| `job_count` | 全国该行业岗位总数 |
| `avg_median_salary` | 行业平均中位薪资 |
| `avg_experience_rank` | 行业平均经验分值 |
| `avg_education_rank` | 行业平均学历分值 |
| `city_count` | 该行业覆盖城市数量 |
| `job_type_count` | 该行业涉及职位类型数 |

---

## 5.9 `city_type_statistics`（Q4 全量城市-行业统计）

**表用途**：Q4 行业区位气泡图（全量类别，不截断）。

| 字段 | 含义 |
|---|---|
| `city` | 城市编码 |
| `city_tier` | 城市等级 |
| `company_type` | 行业/公司类型编码 |
| `job_count` | 城市-行业组合岗位数 |
| `total_jobs_in_city` | 城市总岗位数 |
| `company_count_in_city` | 城市公司数 |
| `avg_education_rank` | 该组合学历均值 |
| `avg_experience_rank` | 该组合经验均值 |
| `industry_ratio` | 该组合在城市内占比 |
| `is_in_ten` | 是否城市内 Top10 类别 |
| `national_job_count` | 该行业全国岗位总数 |
| `location_quotient` | 区位商（本地占比 / 全国占比） |

---

## 5.10 `city_type_statistics_top20`（Q4 Top 类别城市-行业统计）

**表用途**：Q4 城市等级热力图（Top 类别 + “其他”聚合）。

字段与 `city_type_statistics` 一致，区别在于：

- 该表按城市保留头部行业类别并设置“其他”聚合行；
- 更适合矩形热力图与聚焦对比展示。

---

## 6. 字段编码与可读化说明

- `job_title`、`city`、`company_type` 多为匿名编码，不能直接反解真实名称。
- 可读化依赖映射表或补充字典：
  - 经验：`experience_mapping`
  - 学历：`education_mapping`
- 若需要“城市中文名/经纬度/行政区编码”，当前库未直接提供，需单独映射表。

---

## 7. 质量与使用建议

1. 薪资字段优先使用数值化字段（如 `median_annual_salary`、`median_salary`），少直接用 `salary` 文本。
2. 聚合表中部分数值列为字符串（尤其 `job_summary_by_title`），查询时需 `CAST`。
3. 对于噪声与异常值，建议统一在服务层做过滤（当前项目已有部分处理逻辑）。
4. 对答辩展示建议同时标注两套规模口径：
   - 赛事原始口径（docx）
   - 项目落库口径（当前数据库）

