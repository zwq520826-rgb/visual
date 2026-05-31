一、聚类图定位
图名

职位薪酬模式聚类图

核心问题

这张图要回答：

○ 哪些职位是 高薪高门槛型？
○ 哪些职位是 低薪低门槛型？
○ 哪些职位虽然高薪，但薪酬差异很大？
○ 哪些职位招聘量不大，但具备潜力？
○ 哪些职位需求大、薪资稳定，是成熟岗位？

二、推荐使用的数据表
主表：job_summary

我建议优先使用 job_summary，因为它已经包含 Q3 聚类最需要的数值字段：

字段	含义	在聚类图中的作用
job_title	职位编码	每个气泡代表一个职位
records_count	样本量	表示岗位规模，映射气泡大小
median_salary	中位薪资	表示职位典型薪资水平
q1_salary	Q1 薪资	用于计算薪资分布
q3_salary	Q3 薪资	用于计算薪资分布
std_salary	薪资标准差	表示薪资波动程度
avg_experience_rank	平均经验分值	表示经验门槛
avg_education_rank	平均学历分值	表示学历门槛
company_type	行业编码	用于行业筛选或 tooltip 展示
total_shannon_entropy	熵值	表示分布离散度 / 扩散程度

job_summary 中这些字段正好可以支撑“薪资水平、薪资波动、经验学历门槛、岗位规模、行业属性、离散程度”等分析。

三、聚类图视觉设计
主图形式

使用 气泡散点聚类图。

Y 轴：门槛指数
↑
│          C0 高薪高门槛型        C2 高薪波动型
│               ● ●                 ◎ ◎
│
│          C3 稀缺潜力型
│               ○ ○
│
│          C1 低薪低门槛型        C4 大众稳定型
│               ● ●                 ●●●
└────────────────────────────────────→
             X 轴：中位薪资 / 薪资指数
四、字段映射设计
1. X 轴：薪资水平
使用字段
median_salary
含义

表示该职位的典型薪资水平。

解释

X 轴越靠右，说明该职位薪资越高。

2. Y 轴：门槛指数
使用字段
avg_experience_rank
avg_education_rank
建议计算
门槛指数 = 0.55 × 标准化(avg_experience_rank)
        + 0.45 × 标准化(avg_education_rank)
含义

综合表示该职位对工作经验和学历的要求。

解释

Y 轴越高，说明该职位越偏高门槛。
经验和学历映射表中已经有 experience_rank、education_rank，可以支持这种数值化计算。

3. 气泡大小：岗位规模
使用字段
records_count
建议处理
气泡大小 = log(records_count + 1)
含义

表示该职位的招聘样本量。

解释

气泡越大，说明市场需求越大。
这样可以突出 C4 大众稳定型，也能避免极大值把图压扁。

4. 气泡颜色：薪酬模式簇

固定为你们当前设定的 5 类：

簇	名称	建议颜色	含义
C0	高薪高门槛型	蓝色	薪资高、学历经验要求高
C1	低薪低门槛型	黄色 / 橙黄	薪资低、门槛低
C2	高薪波动型	红色	薪资高，但内部差异大
C3	稀缺潜力型	绿色	岗位量不大，但薪资和门槛不低
C4	大众稳定型	青色	岗位量大，薪资稳定
5. 气泡描边：薪资波动
使用字段
std_salary
视觉映射
std_salary	显示方式
低	细描边
中	中等描边
高	粗描边 / 发光外圈
作用

突出 C2 高薪波动型。

这类职位不是简单“高薪”，而是同一职位内部薪资差异大，说明它可能受到城市、行业、企业层级影响。

6. Tooltip：职位详情

鼠标悬浮某个气泡时显示：

内容	字段
职位编码	job_title
薪资区间	q1_salary ~ q3_salary
中位薪资	median_salary
薪资波动	std_salary
岗位数量	records_count
平均经验要求	avg_experience_rank
平均学历要求	avg_education_rank
所属行业	company_type
分布熵	total_shannon_entropy
五、五类簇如何根据字段定义
C0：高薪高门槛型
字段特征
指标	表现
median_salary	高
avg_experience_rank	高
avg_education_rank	高
std_salary	中等或偏低
records_count	中等或偏高
解释

这类职位薪资高，同时对经验和学历要求高。
它们通常是核心技术、管理、专业能力要求较高的职位。

图上位置

右上区域。

C1：低薪低门槛型
字段特征
指标	表现
median_salary	低
avg_experience_rank	低
avg_education_rank	低
std_salary	低
records_count	中等或偏高
解释

这类职位门槛低、薪资低，更多属于基础型、入门型岗位。

图上位置

左下区域。

C2：高薪波动型
字段特征
指标	表现
median_salary	高
std_salary	很高
q3_salary - q1_salary	大
company_type	可能分布在多个行业
total_shannon_entropy	中高
解释

这类职位虽然薪资高，但不同样本之间差距大。
原因可能是同一职位在不同行业、城市、公司层级中的薪酬差异明显。

图上位置

右侧区域，并通过粗描边或发光外圈突出。

C3：稀缺潜力型
字段特征
指标	表现
records_count	偏低
median_salary	中高
avg_experience_rank	中高
avg_education_rank	中高
total_shannon_entropy	较高
解释

这类职位数量不一定多，但薪资和门槛都不低，并且分布有扩散趋势。
它适合解释“潜在高价值职位”。

图上位置

中高薪、小气泡、绿色标记。

C4：大众稳定型
字段特征
指标	表现
records_count	高
median_salary	中等
std_salary	低
avg_experience_rank	中低
avg_education_rank	中低
解释

这类职位招聘量大，薪资水平相对稳定，是市场中比较成熟、常规的岗位类型。

图上位置

中间偏左，大气泡，青色。

六、聚类输入字段设计
推荐聚类特征
聚类特征	来源字段	作用
salary_index	median_salary	判断高薪 / 低薪
barrier_index	avg_experience_rank + avg_education_rank	判断高门槛 / 低门槛
volatility_index	std_salary 或 q3_salary - q1_salary	判断薪资波动
scale_index	records_count	判断大众 / 稀缺
entropy_index	total_shannon_entropy	判断分布扩散程度
推荐计算方式
salary_index = 标准化(median_salary)

barrier_index =
0.55 × 标准化(avg_experience_rank)
+ 0.45 × 标准化(avg_education_rank)

volatility_index =
标准化(std_salary)

scale_index =
标准化(log(records_count + 1))

entropy_index =
标准化(total_shannon_entropy)
七、聚类算法建议
推荐方法
K-Means，k = 5

因为你们已经固定了 5 个业务簇：

C0 高薪高门槛型
C1 低薪低门槛型
C2 高薪波动型
C3 稀缺潜力型
C4 大众稳定型

K-Means 聚完后，不要直接使用模型输出的 0、1、2、3、4，而是根据每个簇的均值画像重新命名。

聚类后命名规则
判断条件	命名
薪资高、门槛高	C0 高薪高门槛型
薪资低、门槛低	C1 低薪低门槛型
薪资高、波动高	C2 高薪波动型
规模低、薪资中高、门槛中高	C3 稀缺潜力型
规模高、波动低、薪资中等	C4 大众稳定型
八、页面布局设计
页面结构
┌──────────────────────────────────────────────┐
│ 图2 职位薪酬模式聚类图                         │
│ C0 高薪高门槛型  C1 低薪低门槛型  C2 高薪波动型 │
│ C3 稀缺潜力型    C4 大众稳定型                  │
├──────────────────────────┬───────────────────┤
│                          │ 簇画像说明卡        │
│     职位气泡聚类图        │                   │
│                          │ 平均薪资            │
│ X=中位薪资                │ 平均门槛            │
│ Y=门槛指数                │ 平均波动            │
│ Size=岗位数量             │ 职位数量            │
│ Color=薪酬模式簇          │ 典型解释            │
├──────────────────────────┴───────────────────┤
│ 底部：五类簇均值对比条：薪资 / 门槛 / 波动 / 规模 / 熵 │
└──────────────────────────────────────────────┘
九、和第一个三维柱状图如何联动

你说第一个视图是：

X 轴：工作经验等级
Y 轴：学历等级
Z 轴：平均薪资
点击柱子联动箱线图

那么聚类图可以这样联动：

1. 点击三维柱状图某根柱子

例如点击：

经验 = 3-5年
学历 = 本科

聚类图只高亮：

avg_experience_rank 接近 3-5年
avg_education_rank 接近 本科

对应的职位点。

2. 点击聚类图某个气泡

联动下面箱线图，展示该职位的薪资分布：

min_salary / q1_salary / median_salary / q3_salary / max_salary

也可以联动城市薪资差异：

job_city_distribution.avg_salary

因为 job_city_distribution 中有同一职位在不同城市的岗位数量、平均薪资、平均经验、平均学历，适合用于下钻分析。

十、最终视图说明文案

你可以在图旁边放这段：

本视图基于职位的中位薪资、薪资标准差、平均经验要求、平均学历要求、岗位数量和分布熵构建薪酬模式聚类。每个气泡代表一个职位，横轴表示薪资水平，纵轴表示学历经验综合门槛，气泡大小表示招聘规模，颜色表示薪酬模式类别。通过该图可以识别高薪高门槛型、低薪低门槛型、高薪波动型、稀缺潜力型和大众稳定型五类职位薪酬模式，并进一步解释不同职位在薪酬待遇上的结构性差异。

十一、最终推荐设计
视图名称

职位薪酬模式聚类图

数据表

优先使用：

job_summary

补充使用：

job_city_distribution
cluster_by_city
主图字段
视觉元素	字段 / 指标
点	job_title
X 轴	median_salary
Y 轴	barrier_index
气泡大小	records_count
气泡颜色	C0-C4 聚类类别
气泡描边	std_salary
Tooltip	q1_salary、median_salary、q3_salary、avg_experience_rank、avg_education_rank、company_type、total_shannon_entropy
五类模式
类别	名称	解释
C0	高薪高门槛型	高薪资、高经验学历要求
C1	低薪低门槛型	低薪资、低经验学历要求
C2	高薪波动型	高薪资、高标准差，受城市/行业影响大
C3	稀缺潜力型	数量少但薪资和门槛不低，有成长空间
C4	大众稳定型	岗位多、薪资稳定、市场成熟