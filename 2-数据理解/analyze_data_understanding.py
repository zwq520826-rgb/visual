from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "dataset" / "JobWanted.xlsx"
OUT_DIR = ROOT / "2_data_understand" / "output"


def parse_salary_text(text: object) -> dict[str, object]:
    s = "" if pd.isna(text) else str(text).strip()
    if not s:
        return {"salary_type": "missing", "salary_avg_monthly": None, "salary_months": None, "is_valid": False}

    m = re.search(r"[·.]\s*(\d{1,2})\s*薪", s)
    months = int(m.group(1)) if m else 12

    if "面议" in s:
        return {"salary_type": "negotiable", "salary_avg_monthly": None, "salary_months": months, "is_valid": False}
    if re.search(r"元\s*/\s*(时|小时)", s):
        return {"salary_type": "hourly", "salary_avg_monthly": None, "salary_months": months, "is_valid": False}
    if re.search(r"元\s*/\s*(天|日)", s):
        return {"salary_type": "daily", "salary_avg_monthly": None, "salary_months": months, "is_valid": False}
    if re.search(r"元\s*/\s*周", s):
        return {"salary_type": "weekly", "salary_avg_monthly": None, "salary_months": months, "is_valid": False}

    rg = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*([Kk万千元])", s)
    if rg:
        lo, hi, unit = rg.groups()
        factor = 1000.0 if unit in ("K", "k", "千") else 10000.0 if unit == "万" else 1.0
        lo_v = float(lo) * factor
        hi_v = float(hi) * factor
        if hi_v < lo_v:
            return {"salary_type": "invalid_range", "salary_avg_monthly": None, "salary_months": months, "is_valid": False}
        return {
            "salary_type": "monthly_range",
            "salary_avg_monthly": (lo_v + hi_v) / 2.0,
            "salary_months": months,
            "is_valid": True,
        }

    sv = re.search(r"(\d+(?:\.\d+)?)\s*([Kk万千元])(?:\s*以上)?", s)
    if sv:
        val, unit = sv.groups()
        factor = 1000.0 if unit in ("K", "k", "千") else 10000.0 if unit == "万" else 1.0
        return {
            "salary_type": "single_value",
            "salary_avg_monthly": float(val) * factor,
            "salary_months": months,
            "is_valid": True,
        }

    return {"salary_type": "unparsed", "salary_avg_monthly": None, "salary_months": months if m else None, "is_valid": False}


def salary_bin(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "未解析"
    if v < 0:
        return "异常值"
    if v >= 40000:
        return "40K+"
    idx = int(v // 5000)
    lo = idx * 5
    hi = lo + 5
    return f"{lo}-{hi}K"


def build_field_dictionary() -> pd.DataFrame:
    rows = [
        ["job_title", "职位名称（编码）", "bfbc45b...GC", "类别型（高基数）", "匿名编码，需通过统计关联解释语义", "职位需求、职位画像、职位差异度分析"],
        ["city", "行政区划（编码）", "F047", "类别型", "匿名编码，可做地域聚合", "城市规模、城市薪资、城市画像与相似度"],
        ["salary", "薪酬文本", "15-30K·15薪", "文本型", "格式混杂，需解析为可比较月薪", "薪资分布、薪酬模式、高薪识别"],
        ["experience", "经验要求（编码）", "EdD", "类别型（可转有序）", "匿名编码，可用薪资关系推断门槛梯度", "经验门槛、门槛-薪资关系"],
        ["education", "学历要求（编码）", "GI", "类别型（可转有序）", "匿名编码，可用薪资关系推断门槛梯度", "学历门槛、门槛-薪资关系"],
        ["company", "企业标识", "company_623498", "类别型（高基数）", "企业唯一标识，适合活跃度统计", "企业数量、企业招聘活跃度"],
        ["company_type", "行业类别（编码）", "type_BLfSmG", "类别型", "匿名编码，适合行业聚合", "行业规模、行业薪资、行业结构"],
    ]
    return pd.DataFrame(rows, columns=["字段名", "字段含义", "示例", "数据类型", "说明", "分析用途"])


def write_markdown(df: pd.DataFrame, salary_df: pd.DataFrame) -> None:
    def md_table(dfx: pd.DataFrame, cols: list[str], n: int | None = None) -> list[str]:
        t = dfx[cols].copy()
        if n is not None:
            t = t.head(n)
        header = "| " + " | ".join(cols) + " |"
        sep = "|" + "|".join(["---" for _ in cols]) + "|"
        rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in t.values.tolist()]
        return [header, sep] + rows

    valid = salary_df[salary_df["is_valid"]]["salary_avg_monthly"]
    uq = {c: int(df[c].nunique(dropna=True)) for c in ["job_title", "city", "salary", "experience", "education", "company", "company_type"]}

    city_full = pd.read_csv(OUT_DIR / "表2_9_城市维度_全量.csv")
    ind_full = pd.read_csv(OUT_DIR / "表2_10_行业维度_全量.csv")
    job_full = pd.read_csv(OUT_DIR / "表2_8_职位维度_全量.csv")
    exp_full = pd.read_csv(OUT_DIR / "表2_7_经验维度_全量.csv")
    edu_full = pd.read_csv(OUT_DIR / "表2_7_学历维度_全量.csv")
    salary_bins = pd.read_csv(OUT_DIR / "表2_6_薪资区间分布_5K分箱.csv")

    lines = [
        "# 第二章 数据说明与数据理解（正式稿）",
        "",
        "## 2.1 数据来源",
        "- 数据集来源：ChinaVis 2024 赛道1官方指定数据集 `JobWanted.xlsx`。",
        "- 数据主题：多变量招聘市场分析，包含职位、城市、薪资、经验、学历、企业、行业。",
        "- 数据格式：xlsx 单表；记录粒度为单条招聘通知。",
        "- 编码特点：多数字段为匿名编码，语义通过统计模式解释。",
        "",
        "小结：数据结构完整，适配本赛题的多维可视分析任务。",
        "",
        "## 2.2 数据概览",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 原始记录数 | {len(df):,} |",
        f"| 字段数 | {df.shape[1]} |",
        f"| 职位数 | {uq['job_title']:,} |",
        f"| 企业数 | {uq['company']:,} |",
        f"| 行业数 | {uq['company_type']:,} |",
        f"| 城市数 | {uq['city']:,} |",
        f"| 经验类别数 | {uq['experience']:,} |",
        f"| 学历类别数 | {uq['education']:,} |",
        f"| 完全重复记录 | {int(df.duplicated().sum()):,} |",
        "",
        "小结：样本体量大、覆盖维度广、重复占比低。",
        "",
        "## 2.3 数据字段说明",
        "字段明细见：`2_data_understand/output/表2_3_字段说明_完整版.csv`（含字段含义、示例、数据类型、说明、分析用途）。",
        "",
        "小结：字段角色清晰，支持后续维度分析与指标构建。",
        "",
        "## 2.4 薪资分布",
        "- 有效月薪样本数：{:,.0f}".format(float(valid.shape[0])),
        "- 月薪统计：min={:.2f}, p25={:.2f}, median={:.2f}, p75={:.2f}, mean={:.2f}, max={:.2f}".format(
            float(valid.min()), float(valid.quantile(0.25)), float(valid.median()), float(valid.quantile(0.75)), float(valid.mean()), float(valid.max())
        ),
        "",
        "### 2.4.1 薪资区间分布（0~5K为一步，40K以上合并）",
        "分箱明细如下：",
    ]
    lines.extend(md_table(salary_bins, ["薪资区间", "记录数", "占比"]))
    lines.extend([
        "",
        "（完整分箱文件：`2_data_understand/output/表2_6_薪资区间分布_5K分箱.csv`）",
        "",
        "小结：薪资呈右偏分布，高薪尾部明显，40K+为高溢价岗位聚集区。",
        "",
        "## 2.5 职位维度分析",
        "- 全量职位表：`2_data_understand/output/表2_8_职位维度_全量.csv`。",
        "- 字段包含：职位名称、职位数（招聘量）、平均薪资、中位薪资、企业数、城市数、行业数、薪资离散度。",
        f"- 职位总数：{len(job_full):,}；Top1职位招聘量：{int(job_full['职位数'].max()):,}。",
        "- 职位维度Top10示例：",
    ])
    lines.extend(md_table(job_full, ["职业名称", "职位数", "平均薪资", "企业数", "城市数", "行业数"], 10))
    lines.extend([
        "",
        "小结：职位需求呈头部集中与长尾并存，职位间薪资与覆盖范围差异显著。",
        "",
        "## 2.6 城市维度分析",
        "- 全量城市规模表：`2_data_understand/output/表2_9_城市维度_全量.csv`。",
        "- 字段包含：招聘规模、平均薪资、中位薪资、职位数、行业数、企业数、薪资离散度。",
        f"- 城市总数：{len(city_full):,}；招聘规模Top1城市：{city_full.iloc[0]['城市编码']}（{int(city_full.iloc[0]['招聘规模']):,}）。",
        "- 城市维度Top10示例：",
    ])
    lines.extend(md_table(city_full, ["城市编码", "招聘规模", "平均薪资", "职位数", "行业数", "企业数"], 10))
    lines.extend([
        "",
        "小结：城市间存在显著的规模与薪资梯度差异，可作为地域画像基础单元。",
        "",
        "## 2.7 行业维度分析",
        "- 全量行业规模表：`2_data_understand/output/表2_10_行业维度_全量.csv`。",
        "- 字段包含：招聘规模、平均薪资、中位薪资、企业数、城市覆盖、职位数、薪资离散度。",
        f"- 行业总数：{len(ind_full):,}；招聘规模Top1行业：{ind_full.iloc[0]['行业编码']}（{int(ind_full.iloc[0]['招聘规模']):,}）。",
        "- 行业维度Top10示例：",
    ])
    lines.extend(md_table(ind_full, ["行业编码", "招聘规模", "平均薪资", "企业数", "城市覆盖", "职位数"], 10))
    lines.extend([
        "",
        "小结：行业侧同时存在高需高薪与高需普薪类型，结构分层明显。",
        "",
        "## 2.8 经验与学历维度分析",
        "- 经验全量表：`2_data_understand/output/表2_7_经验维度_全量.csv`。",
        "- 学历全量表：`2_data_understand/output/表2_7_学历维度_全量.csv`。",
        f"- 经验类别数：{len(exp_full):,}；学历类别数：{len(edu_full):,}。",
        "- 经验维度列表：",
    ])
    lines.extend(md_table(exp_full, ["经验编码", "样本量", "平均薪资", "中位薪资", "城市覆盖", "行业覆盖"], None))
    lines.extend([
        "",
        "- 学历维度列表：",
    ])
    lines.extend(md_table(edu_full, ["学历编码", "样本量", "平均薪资", "中位薪资", "城市覆盖", "行业覆盖"], None))
    lines.extend([
        "",
        "小结：经验/学历维度与薪资有稳定统计关联，可作为门槛指标的核心输入。",
        "",
        "## 2.9 深度洞察与发现",
        "1. 薪资水平发现：薪资分布右偏，均值高于中位数，高薪尾部（尤其40K+）体现市场溢价岗位存在。",
        f"2. 市场需求发现：城市Top1为 {city_full.iloc[0]['城市编码']}，行业Top1为 {ind_full.iloc[0]['行业编码']}，需求集中趋势明显。",
        "3. 主要结论：",
        "   - 市场集中度：招聘市场呈明显头部集中，少数城市与行业承载主要需求。",
        "   - 结构异质性：职位、城市、行业在规模、薪资、覆盖度上均有显著差异。",
        "   - 门槛关联性：经验与学历可稳定解释薪资分层。",
        "   - 分析可行性：数据可直接支撑赛题五项任务并为后续建模提供可靠基础。",
        "",
        "## 2.10 本章总结",
        "- 本章完成了数据概览、字段理解、薪资分布、职位/城市/行业/经验/学历全维度分析。",
        "- 已输出全量明细表和可复用统计结果，为第三章清洗与第四章指标构建打下基础。",
    ])

    (ROOT / "2_data_understand" / "第二章_数据说明与数据理解_正式稿.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(DATA_PATH)

    salary_info = pd.DataFrame([parse_salary_text(x) for x in df["salary"]])
    data = pd.concat([df, salary_info], axis=1)

    field_df = build_field_dictionary()
    field_df.to_csv(OUT_DIR / "表2_3_字段说明_完整版.csv", index=False)

    # 薪资格式分布
    salary_type = data["salary_type"].value_counts().rename_axis("薪资类型").reset_index(name="记录数")
    salary_type["占比"] = salary_type["记录数"] / len(data)
    salary_type.to_csv(OUT_DIR / "表2_6_薪资格式分布.csv", index=False)

    # 薪资5K分箱（0~5K一步，40K+合并）
    valid = data.loc[data["is_valid"], "salary_avg_monthly"].copy()
    bins_df = pd.DataFrame({"salary_avg_monthly": valid})
    bins_df["薪资区间"] = bins_df["salary_avg_monthly"].map(salary_bin)
    order = [f"{i}-{i+5}K" for i in range(0, 40, 5)] + ["40K+"]
    dist = bins_df["薪资区间"].value_counts().reindex(order, fill_value=0).rename_axis("薪资区间").reset_index(name="记录数")
    dist["占比"] = dist["记录数"] / max(len(valid), 1)
    dist.to_csv(OUT_DIR / "表2_6_薪资区间分布_5K分箱.csv", index=False)

    # 职位维度全量
    job = (
        data.groupby("job_title", as_index=False)
        .agg(
            职位数=("job_title", "size"),
            平均薪资=("salary_avg_monthly", "mean"),
            中位薪资=("salary_avg_monthly", "median"),
            企业数=("company", "nunique"),
            城市数=("city", "nunique"),
            行业数=("company_type", "nunique"),
            薪资标准差=("salary_avg_monthly", "std"),
        )
        .rename(columns={"job_title": "职业名称"})
        .sort_values("职位数", ascending=False)
    )
    job.to_csv(OUT_DIR / "表2_8_职位维度_全量.csv", index=False)

    # 城市维度全量
    city = (
        data.groupby("city", as_index=False)
        .agg(
            招聘规模=("city", "size"),
            平均薪资=("salary_avg_monthly", "mean"),
            中位薪资=("salary_avg_monthly", "median"),
            职位数=("job_title", "nunique"),
            行业数=("company_type", "nunique"),
            企业数=("company", "nunique"),
            薪资标准差=("salary_avg_monthly", "std"),
        )
        .rename(columns={"city": "城市编码"})
        .sort_values("招聘规模", ascending=False)
    )
    city.to_csv(OUT_DIR / "表2_9_城市维度_全量.csv", index=False)

    # 行业维度全量
    ind = (
        data.groupby("company_type", as_index=False)
        .agg(
            招聘规模=("company_type", "size"),
            平均薪资=("salary_avg_monthly", "mean"),
            中位薪资=("salary_avg_monthly", "median"),
            企业数=("company", "nunique"),
            城市覆盖=("city", "nunique"),
            职位数=("job_title", "nunique"),
            薪资标准差=("salary_avg_monthly", "std"),
        )
        .rename(columns={"company_type": "行业编码"})
        .sort_values("招聘规模", ascending=False)
    )
    ind.to_csv(OUT_DIR / "表2_10_行业维度_全量.csv", index=False)

    # 经验维度全量
    exp = (
        data.groupby("experience", as_index=False)
        .agg(
            样本量=("experience", "size"),
            平均薪资=("salary_avg_monthly", "mean"),
            中位薪资=("salary_avg_monthly", "median"),
            城市覆盖=("city", "nunique"),
            行业覆盖=("company_type", "nunique"),
            企业数=("company", "nunique"),
        )
        .rename(columns={"experience": "经验编码"})
        .sort_values("样本量", ascending=False)
    )
    exp.to_csv(OUT_DIR / "表2_7_经验维度_全量.csv", index=False)

    # 学历维度全量
    edu = (
        data.groupby("education", as_index=False)
        .agg(
            样本量=("education", "size"),
            平均薪资=("salary_avg_monthly", "mean"),
            中位薪资=("salary_avg_monthly", "median"),
            城市覆盖=("city", "nunique"),
            行业覆盖=("company_type", "nunique"),
            企业数=("company", "nunique"),
        )
        .rename(columns={"education": "学历编码"})
        .sort_values("样本量", ascending=False)
    )
    edu.to_csv(OUT_DIR / "表2_7_学历维度_全量.csv", index=False)

    profile = {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "unique_counts": {k: int(v) for k, v in df.nunique(dropna=True).to_dict().items()},
        "salary_valid_count": int(data["is_valid"].sum()),
        "salary_type_distribution": salary_type.to_dict(orient="records"),
    }
    (OUT_DIR / "数据画像.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    write_markdown(df, data)
    print(f"[OK] outputs generated in: {OUT_DIR}")


if __name__ == "__main__":
    main()
