# Q4 地域招聘活动画像：实现细节与交互规范

说明：基于已读的 `JobWanted_description`（430k+ 条），城市与职位为哈希编码（不可逆）。本文件面向工程落地，包含后端聚合、特征构造、API 输出格式、前端视图实现（ECharts + Vue3）、交互定义与性能注意点。

目录
1. 总体方案概述  
2. 后端：数据预处理与聚合（详细步骤 + 代码片段）  
3. 后端：特征向量、聚类与聚合输出（详细步骤 + 代码片段）  
4. API 设计（接口与返回示例）  
5. 前端视图实现（视图 A/B/C/D 的具体实现、ECharts 配置要点、交互行为）  
6. 性能与采样策略  
7. 输出文件与交付清单

---

## 1. 总体方案概述（快速读）
- 目标：用哈希化地域（city_hash）为单位，生成每个地域的多维画像（行业/职位类别/薪酬/教育/经验/公司类型/技能），并按画像特征聚类，展现在精准的三大视图：  
  A. **地域特征空间拓扑图**（PCA/UMAP 降维）+ 相似地域高亮  
  B. **精简单地域画像**（KPI + 核心图表 + 雷达）  
  C. **行业—地域热力图** + 职位共现摘要（D 内容并入）  
- 设计原则：  
  - 放弃虚假地理映射：city_hash 无实际地理坐标，改用特征空间距离而非地理距离展示相似性；  
  - 相似地域可视化显性表达：不仅通过同色聚类，还通过连线/邻近标记和对比卡片明确 Top-3 相似地域；  
  - 报告友好的信息密度：单张图清晰可读，避免报告截屏时信息过载；  
  - 不可逆哈希原则：展示使用编码或编号（#1/#2），不回溯原名；所依赖字段为 `industryField`、`jobLabel`、`skill_tag` 等可读字段推断职位类别。

---

## 2. 后端：数据预处理与聚合

目标产物：`region_profile.json`（每个 city_hash 一条），`region_cluster_summary.json`（聚类摘要），`industry_region_matrix.csv`（热力图矩阵），`data_quality_report.json`。

2.1 输入（清洗后）
- 文件：`cleaned_jobs.csv`
- 必要字段（已标准化）：  
  `job_id, position_hash, city_hash, salary_min, salary_max, salary_avg, salary_months, education, workYear, city_tier, companyType, industryField, jobLabel, skill_tag, publishTime, financeStage`

2.2 职位类别推断（因 position_hash 不可逆）
- 方法：基于 `industryField`、`jobLabel`、`skill_tag` 做规则+关键词打分；结果字段 `position_category`（技术/产品/运营/销售/HR/市场/设计/其它）
- 实现建议：先做关键词字典（中英），对 `jobLabel`/`skill_tag` 做 tokenize 后计分，取最高得分类别；得分阈值低记为 `其它`。

2.3 聚合维度（按 `city_hash`）
- 基本统计：`job_count`, `job_count_monthly_trend`（最近 N 月同比/环比）
- 薪酬：`salary_mean`, `salary_median`, `salary_q25`, `salary_q75`, `salary_std`, `salary_min`, `salary_max`
- 人才分布：`education_dist`（按标准类别）、`experience_dist`
- 行业/岗位/技能 Top-K：`industry_top`（Top20 可选）、`position_category_top`（Top10）、`skill_tag_top`（Top20）
- 公司与融资：`company_type_dist`, `finance_stage_dist`
- 数据质量：`missing_rate_by_field`, `outlier_salary_ratio`
- 输出示例结构（JSON）见第 4 节 API 示例

2.4 pandas 实现片段（核心聚合）

```python
import pandas as pd
def aggregate_regions(df):
    region_profiles = []
    for city_hash, g in df.groupby('city_hash'):
        profile = {}
        profile['region_id'] = city_hash
        profile['city_tier'] = g['city_tier'].mode().iat[0] if not g['city_tier'].mode().empty else None
        profile['job_count'] = len(g)
        profile['salary_mean'] = g['salary_avg'].mean()
        profile['salary_median'] = g['salary_avg'].median()
        profile['salary_q25'] = g['salary_avg'].quantile(0.25)
        profile['salary_q75'] = g['salary_avg'].quantile(0.75)
        profile['salary_std'] = g['salary_avg'].std()
        profile['education_dist'] = g['education'].value_counts(normalize=True).to_dict()
        profile['experience_dist'] = g['workYear'].value_counts(normalize=True).to_dict()
        profile['industry_top'] = g['industryField'].value_counts().head(20).to_dict()
        profile['position_category_top'] = g['position_category'].value_counts().head(10).to_dict()
        profile['skill_tag_top'] = extract_top_skills(g['skill_tag'], top_n=20)
        profile['company_type_dist'] = g['companyType'].value_counts(normalize=True).to_dict()
        profile['finance_stage_dist'] = g['financeStage'].value_counts(normalize=True).to_dict()
        profile['missing_rate'] = g.isna().mean().to_dict()
        region_profiles.append(profile)
    return pd.DataFrame(region_profiles)
```

说明：`extract_top_skills` 需要解析 `skill_tag` 格式（CSV/JSON等）。

---

## 3. 后端：特征向量、聚类、降维与相似性计算

3.1 特征向量（为聚类构造）
- 组成（样例，总约 45~55 维）：
  1. 行业占比 Top20 → 20维（缺项补0）
  2. 职位类别占比 Top10 → 10维
  3. 教育分布 5维
  4. 经验分布 6维
  5. 薪酬特征 3维（mean_norm, median_norm, iqr_norm）
  6. 公司类型 4维
  7. 融资阶段 4维
  8. city_tier one-hot 4维
- 标准化：`StandardScaler`

3.2 聚类方法
- 首选：KMeans（k 初始 5），验证：`silhouette_score`；保存 `cluster_id`，为前端聚类着色
- 备用：若簇内部异质性大，再用 `GaussianMixture` 验证或分层聚类
- **记录** `silhouette_score` 和 `inertia` 到 `data_quality_report.json`

3.3 降维与拓扑映射（核心改进）
- 方法：用**标准化后的特征向量**做 **PCA + UMAP**
  - PCA 第一步：压缩到 50 维（保留 ≥95% 方差）
  - UMAP 第二步：从 50 维压缩到 2 维（参数建议 `n_neighbors=15, min_dist=0.1`）
- 目的：保留高维特征的全局与局部拓扑结构，使得相似地域在 2D 空间中相近
- 输出：每个 region 新增字段 `pca_x`, `pca_y`（2D 坐标），用于视图 A 的拓扑图

3.4 相似性计算（关键改进）
- 在标准化特征空间中，计算 **pairwise Cosine Similarity**
- 对每个 region，找出 Top-3 Cosine Similarity 最高的其他 region
- 保存到 `region_profile.json` 中，每条记录新增字段：
  ```json
  "top_similar_regions": [
    {"id": "hash_xxx", "similarity": 0.92, "cluster_id": 1},
    {"id": "hash_yyy", "similarity": 0.88, "cluster_id": 1},
    {"id": "hash_zzz", "similarity": 0.85, "cluster_id": 2}
  ]
  ```
- 前端在视图 A 中用**连线**或**邻近圈标记**展示这三个相似地域

3.5 后端输出文件
- `region_profile.json`：按 region 的聚合画像 + PCA/UMAP 坐标 + Top-3 相似地域（用于视图 A/B）
- `region_cluster_summary.json`：每个 cluster 的代表特征、代表 region_id 列表（用于右侧卡片）
- `industry_region_matrix.csv`：Top M 城市 × Top N 行业 的占比矩阵（用于热力图 C）
- `data_quality_report.json`：包含 `silhouette_score`、`umap_variance_retained` 等质量指标

3.6 样例导出（JSON 结构详细示例）

```json
{
  "region_id": "hash_abc123",
  "city_tier": "一线",
  "job_count": 12345,
  "salary_profile": {"mean": 28.5, "median": 25.0, "q25": 18.0, "q75": 35.0},
  "education_dist": {"0":0.08,"1":0.15,"2":0.55,"3":0.18,"4":0.04},
  "experience_dist": {"0":0.10,"1":0.12,"2":0.30,"3":0.25,"4":0.18,"5":0.05},
  "industry_top": [{"industry":"互联网","count":4000,"prop":0.32}, ...],
  "position_category_top": [{"category":"技术","count":5500,"prop":0.45}, ...],
  "skill_tag_top": [{"tag":"Python","count":2400}, ...],
  "company_type_dist": {"上市公司":0.25,"中型":0.30},
  "finance_stage_dist": {"A轮":0.20,"B轮及以后":0.35},
  "cluster_id": 1,
  "pca_x": 2.34,
  "pca_y": -1.56,
  "top_similar_regions": [
    {"id": "hash_xxx", "similarity": 0.92, "cluster_id": 1},
    {"id": "hash_yyy", "similarity": 0.88, "cluster_id": 1},
    {"id": "hash_zzz", "similarity": 0.85, "cluster_id": 2}
  ]
}
```

---

## 4. API 设计（REST）

4.1 /api/regions/summary — 获取所有 region 简要
- 请求：GET
- 返回：JSON 列表每项包含 `region_id, cluster_id, city_tier, job_count, salary_mean, industry_top(简短)`  
- 用途：地图初始化（轻量）

4.2 /api/regions/{region_id} — 获取单 region 画像
- 请求：GET
- 返回：完整 `region_profile.json` 中该 region 条目
- 用途：视图 B 的详细展示

4.3 /api/regions/cluster_summary — 聚类汇总
- 请求：GET
- 返回：`region_cluster_summary.json`（每簇代表特征、代表 region_id 列表）
- 用途：地图右侧卡片面板

4.4 /api/industry_region_matrix?top_m=20&top_n=15 — 热力图矩阵
- 请求：GET
- 返回：CSV 或 JSON 矩阵（Y: region_id, X: industry_code, value: proportion / count）

4.5 /api/data_quality — 数据质量报告
- 请求：GET
- 返回：`data_quality_report.json`

示例：`/api/regions/summary` 返回条目：

```json
{
  "region_id":"hash_abc123",
  "cluster_id":1,
  "city_tier":"一线",
  "job_count":12345,
  "salary_mean":28.5,
  "industry_top":["互联网","金融","大数据"]
}
```

---

## 5. 前端视图实现细节（Vue3 + ECharts）

通用约定：
- 所有 region 在前端显示用短编号（#1/#2）与 `region_id` 段前缀（hover 可显示完整哈希）
- UI 框架：Vue3 + TypeScript + Pinia（状态管理）
- 图表库：ECharts（map、heatmap、bar、boxplot）；对大量点使用 ECharts GL 或 WebGL 图层
- 数据拉取：首次加载 `/api/regions/summary`，懒加载单 region 详情 `/api/regions/{id}`

### 5.1 视图 A（RegionSimilarityTopology：地域特征空间拓扑图 + 相似地域高亮）

#### 核心设计理念
由于 `city_hash` 无真实地理坐标，任何强行映射到中国地图的设计都会造成"视觉误导"。本视图改用**特征空间距离**而非物理距离表示地域相似性，既严谨又直接呼应赛题要求（"识别具有相似招聘特征的地域"）。

#### 数据处理流程（后端）
- 输入：`region_profile.json` 中每个地域的特征向量（45~55 维）
- 处理：
  1. 用 `StandardScaler` 标准化特征向量
  2. 用 PCA 或 UMAP 降维至 2 维（保留全局拓扑结构）
  3. 计算每个 region 与其他所有 region 的 **Cosine Similarity**，记录 Top-3 相似地域
  4. 保留 KMeans `cluster_id` 用于颜色映射
- 输出：扩展 `region_profile.json`，每条记录新增字段：
  ```json
  "pca_x": float,
  "pca_y": float,
  "top_similar_regions": [{"id": "hash_xxx", "similarity": 0.92}, ...]
  ```

#### 前端可视化
- **布局**：左侧拓扑图（70%）+ 右侧聚类/相似卡片（30%）
- **拓扑图实现**：
  - 使用 ECharts `scatter`（或 WebGL 加速的 `scatterGL`）
  - X 轴 / Y 轴：PCA 或 UMAP 降维后的坐标
  - 点颜色：`cluster_id` 映射到预定义色表（5~8 色）
  - 点大小：`symbolSize = sqrt(job_count) * factor`（max 28px）
  - Tooltip：显示 `region_id(哈希前缀) / job_count / salary_mean / city_tier / top industry`

- **交互设计**：
  1. **Hover 点**：高亮该地域，同时用**浅连线**或**邻近圈标记**显示其 Top-3 Cosine Similarity 最相似地域
  2. **Click 点**：
     - 右侧卡片切换为该地域的详情（视图 B）
     - 同时在卡片下方显示"最相似地域对比"，列出 Top-3，并可点击进入它们的详情
  3. **Legend 过滤**：支持按 `cluster_id` 过滤，显示/隐藏特定群组
  4. **Zoom / Pan**：支持平移缩放，方便查看密集区域

- **右侧卡片**：
  - 显示当前选中地域的聚类归属、KPI、代表特征
  - 下方"最相似地域 Top-3"列表（可点击切换）

#### 实现要点
- PCA/UMAP 的超参数建议在后端预处理阶段调优（如保留 95% 方差）
- Cosine Similarity 计算可在后端离线做一次，存储到 JSON 中，前端仅读取展示
- 大量地域点的渲染建议用 WebGL 加速

### 5.2 视图 B（RegionProfileCard：精简单地域画像）

#### 设计原则
避免信息过载。报告中单张图必须清晰可读，过多子组件会导致 A4/PPT 截屏时难以辨认。因此精选最核心的 4 大块：KPI、行业、职位、多维特征。

#### 数据来源
`/api/regions/{region_id}`

#### 组件结构
1. **KPI 卡片区**（顶部）
   - 地域编号、城市等级badge、岗位总量、平均薪资、中位薪资
   - 例："#12 | 二线 | 8,543岗 | 平均23.5K | 中位21K"

2. **行业分布条形图**（左上）
   - Top 5 行业，水平条形，展示绝对数 + 百分比
   - 可点击条形联动热力图过滤

3. **职位类别分布条形图**（右上）
   - Top 5 职位类别，水平条形，同样显示绝对数 + 百分比

4. **多维特征雷达图**（下方）
   - 5 个维度：
     - `education_level`：本科及以上占比（%）
     - `experience_demand`：平均经验要求（年）
     - `company_scale`：大型公司占比（%）
     - `finance_maturity`：融资成熟度指数（0~1，融资阶段越晚越高）
     - `skill_concentration`：技能集中度（0~1，值越高表示技能堆积越集中）
   - 各维度标准化至 0~1，便于对比
   - 颜色可继承该地域的 cluster_id 颜色

5. **最相似地域对比**（下方右侧，可选展开）
   - 三个相似地域的 mini 雷达，并列展示
   - 便于评委快速理解"相似"体现在哪些特征上

#### 交互
- Hover 条形、雷达顶点：显示具体数值
- Click 行业条：全局过滤热力图到该行业
- Tooltip 中显示"该指标在全国排名"
- 导出按钮：生成高分辨率 PNG / PDF

#### 可视规范
- 字体大小选择充分，以 A4 纸打印时仍可辨认
- 条形数据同时展示绝对数与百分比
- 雷达图采用半透明填充，不用过于鲜艳的颜色

### 5.3 视图 C（IndustryRegionHeatmap + 职位共现摘要）

#### 行业—地域热力图
- 数据：`/api/industry_region_matrix?top_m=20&top_n=15`（建议前端默认 top_m=20 regions by job_count）
- ECharts heatmap 配置：
  - xAxis: 行业名（中文）
  - yAxis: region label（显示编号 #n + city_tier 小 badge）
  - visualMap: colorRange white→red
  - Tooltip 显示：industry, region_id, absolute count, proportion, rank_in_region
- 交互：
  - 点击热力格子：打开 RegionProfile（视图 B）并 filter industry
  - 鼠标拖拽选择多行 → 左上显示"比较"按钮（比较所选 regions 的 Top industry/position）

#### 职位—行业共现摘要模块（右侧或下方，可选展开）
- 目的：用小图辅助解释该热力图选中的地域或聚类的内部职位-行业驱动力
- 形式：Top 5 职位类别 × Top 5 行业的共现矩阵（或简化为条形对比）
- 大小：不超过 8cm × 6cm，避免抢占主热力图的视觉权重
- 交互：Hover 显示频次，可链接到完整共现数据（扩展功能）

### 5.4 职位—行业共现（辅助结论，不占独立主图）

#### 定位
视图 D（职位-行业共现）的分析价值是解释"为什么某些地域会聚类到一起"。但如果独立占一张主图，会挤掉地域特征展示空间。建议将其逻辑整合到视图 C 的热力图设计中，或作为报告的"辅助结论"部分。

#### 呈现方式（二选一）

**方案 A：热力图右侧附加共现摘要**
- 在视图 C 的行业—地域热力图旁，增加一个"代表地域职位-行业共现图"
- 展示当前选中地域（或某个聚类）中，职位类别与行业的强关联
- 形式：共现矩阵（Top 5 职位 × Top 5 行业）或 Sankey 简图
- 交互：Hover 单元格显示频次和该组合在地域内的占比

**方案 B：报告文字结论 + Mini 图**
- 在赛题应卷的文字分析部分（不超过 800 字），用小段落解释"某聚类地域的主导职位类别与主导行业的共现规律"
- 附一张 mini 共现矩阵或 Sankey 图（不超 15cm × 8cm），作为论证支撑
- 这样不占用主要图幅，但依然展示了多维分析深度

#### 数据准备
- 后端预计算：`position_category` × `industryField` 频次矩阵（Top N）
- 可按地域或按聚类计算，或同时计算多份以支持联动过滤

---

## 6. 性能、采样、鲁棒性与学术严谨性

6.1 数据规模：430k+ 行，region 数量 ~100~500（取决于哈希分割策略） → 后端聚合合理可行

6.2 前端数据传输
- 拓扑图 initial 请求：`/api/regions/summary`（包含 pca_x/pca_y 坐标，轻量）
- 详情按需：点击 region 拉 `/api/regions/{id}`
- 相似地域自动加载：Top-3 Cosine Similarity 数据已包含在 summary 中
- 热力图请求：按 top_m/top_n 参数分页

6.3 采样策略（可选）
- 若需要展示单 region 内大量职位点（不建议），采用分层抽样（按 position_category 或 salary_bin 分层采样）
- 可视化中显示的 Top-k 值均以全量计算后再传输给前端（前端仅渲染 Top-k）

6.4 聚类与稳定性校验
- 计算并记录 `silhouette_score`，对关键簇做"簇内 variability"报告（std、IQR）
- 做重复抽样（bootstrap）验证聚类稳定性：重复 N 次随机抽样 80% 数据做 KMeans，统计各 region 的簇一致性
- UMAP 超参数验证：不同种子数下的稳定性测试，确保降维结果可复现

6.5 数据质量与学术严谨性
- 生成 `data_quality_report.json`，包含：
  - 字段缺失率
  - salary 解析异常占比
  - 每 region 最低样本阈值（例如 < 50 样本警告）
  - `silhouette_score` 与 `davies_bouldin_index`（簇内聚集度评指标）
  - UMAP 降维后的方差保留率
  - Cosine Similarity 分布（均值、中位数、分位数）
- **说明文案**：在答卷中注明
  - "地域编码为哈希值，不可逆解，故改用特征空间距离表示相似性"
  - "聚类与相似地域计算基于标准化特征向量的 KMeans 与 Cosine Similarity，具体参数详见数据质量报告"
  - "PCA/UMAP 降维用于可视化展示拓扑关系，保留 >95% 信息量"

---

## 7. 输出文件与交付清单（放置于 repo）

- /docs/plan/Q4_region_implementation.md（本文件）
- /backend/region_analysis.py（聚合 + 特征 + 聚类脚本）
- /backend/utils.py（skill_tag 解析、position_category 推断、data quality）
- /data/region_profile.json（后端输出）
- /data/region_cluster_summary.json
- /data/industry_region_matrix.csv
- /frontend/src/components/Q4/Q4_RegionAnalysis.vue
- /frontend/src/components/Q4/RegionClusterMap.vue
- /frontend/src/components/Q4/RegionProfile.vue
- /frontend/src/components/Q4/IndustryHeatmap.vue

---

## 8. 下一步（建议优先顺序）
1. 在后端运行 `aggregate_regions` 生成 `region_profile.json`（先用全部数据做一次批处理）  
2. 计算标准化特征向量，进行 PCA 降维至 50 维（保留 ≥95% 方差）  
3. 使用 UMAP 再降维至 2 维，生成 `pca_x` / `pca_y` 坐标  
4. 计算 pairwise Cosine Similarity，为每个 region 找出 Top-3 最相似 region，记录到 `region_profile.json`  
5. 构造 KMeans 特征矩阵并聚类，保存 `region_cluster_summary.json`，记录 `silhouette_score`  
6. 生成 `industry_region_matrix.csv` 与 `data_quality_report.json`  
7. 在前端实现**拓扑图**（使用 `regions/summary` 的 PCA 坐标），并渲染聚类颜色与相似地域连线  
8. 验证视觉效果与交互（Hover 高亮相似地域、Click 切换到详情、Legend 过滤聚类）  
9. 实现单 region 详情面板（RegionProfileCard），并加入"最相似地域 Top-3"对比卡  
10. 生成行业—地域热力图，并测试与拓扑图、详情面板的联动  
11. 若保留共现分析，则按方案 A 或 B 在热力图旁/报告中补充  
12. 撰写答卷（截取代表 cluster 的拓扑、详情、热力图截屏）+ 数据质量说明文案  

---

## 9. 设计亮点与学术贡献

这个优化方案相比原始方案有三大改进：

1. **严谨性优先**：放弃虚假地理映射，改用"特征空间拓扑"，既尊重数据的哈希性质，又直观呈现相似地域关系。
2. **相似地域强调**：从被动的"同色聚类"升级到主动的"连线+对比"，直接可视化 Cosine Similarity，符合赛题"识别相似地域"的要求。
3. **报告友好**：精简视图 B，优化视图 D 定位，确保 3~4 张主图在报告中清晰可读且层次分明。
