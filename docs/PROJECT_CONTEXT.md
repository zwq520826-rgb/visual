# 职数洞见 - 项目上下文

## 项目概览
- 名称：职数洞见（Job Market Visual Analytics）
- 目标：基于 40 万条招聘数据，进行薪酬模式分析和可视化
- 赛事：ChinaVis 2024 数据可视化挑战赛

## 数据源
- 数据集：40 万条招聘通知
- 主要字段：
  * positionName（职位）
  * salary_min / salary_max / salary_avg / salary_months（已标准化）
  * education（学历：0-4 映射）
  * workYear（经验：0-5 映射）
  * city / city_tier（地域）
  * companyType / industryField（行业）
  * jobLabel / skill_tag（岗位标签）
  * publishTime, financeStage 等

## 项目结构
```
/Users/zwq/six_smester/visual_all/git_vis/visual/
├── backend/
│   ├── data_processing.py          # 数据清洗
│   ├── clustering_pipeline.py      # 聚类与 UMAP（待编写）
│   └── output_formatter.py         # 格式化输出
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ScatterPlot.vue     # 散点图（待编写）
│   │   │   ├── ParallelCoords.vue  # 平行坐标（待编写）
│   │   │   └── Legend.vue
│   │   ├── stores/
│   │   │   └── visualStore.ts      # Pinia 状态管理（待编写）
│   │   └── views/
│   │       └── Dashboard.vue       # 主面板
├── docs/
│   └── plan/
│       └── Q3_new_plan.md          # 详细设计方案
└── README.md
```

## 核心技术栈
- **后端**：Python 3.8+，pandas, scikit-learn, umap-learn
- **前端**：Vue 3, TypeScript, ECharts, Pinia

## 核心视图设计

### 视图一：UMAP 散点图
- X/Y：UMAP 降维坐标
- 颜色：聚类 ID
- 大小：默认 1.5px
- 交互：brush / lasso 选区
- 技术：ECharts scatterGL（WebGL）

### 视图二：平行坐标系
- 轴顺序：education → workYear → city_tier → companyType → salary_avg
- 数据降噪：聚类质心聚合（20-30 条线）
- 颜色：与视图一同步
- 透明度：0.08 默认，1.0 选中

## 双向联动
- 空间→多维：散点选区 → 平行坐标高亮
- 多维→空间：平行坐标筛选 → 散点图放大/高亮

## 输出格式
后端生成 JSON：
```json
{
  "id": 1,
  "positionName": "Python 开发工程师",
  "umap_x": 2.34,
  "umap_y": -1.56,
  "cluster_id": 2,
  "salary_avg": 15.5,
  "education": 2,
  "workYear": 2,
  "city_tier": "一线",
  "companyType": "互联网",
  "industryField": "人工智能"
}
```