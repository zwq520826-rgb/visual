from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class CleanConfig:
    work_hours_per_day: float = 8.0
    work_days_per_month: float = 21.75
    work_weeks_per_month: float = 4.33
    default_salary_months: int = 12
    iqr_k: float = 1.5


ROOT = Path(__file__).resolve().parents[1]
INPUT_XLSX = ROOT / "dataset" / "JobWanted.xlsx"
OUT_DIR = ROOT / "3-数据清洗" / "outputs"


def parse_salary(raw: object, cfg: CleanConfig) -> dict[str, object]:
    s = "" if pd.isna(raw) else str(raw).strip()
    if not s:
        return {
            "salary_raw": s,
            "salary_type": "missing",
            "salary_months": None,
            "salary_min_monthly": np.nan,
            "salary_max_monthly": np.nan,
            "salary_mid_monthly": np.nan,
            "salary_min_year": np.nan,
            "salary_max_year": np.nan,
            "salary_mid_year": np.nan,
            "salary_is_valid": False,
            "salary_invalid_reason": "missing",
        }

    month_match = re.search(r"[·.]\s*(\d{1,2})\s*薪", s)
    months = int(month_match.group(1)) if month_match else cfg.default_salary_months

    if "面议" in s:
        return {
            "salary_raw": s,
            "salary_type": "negotiable",
            "salary_months": months,
            "salary_min_monthly": np.nan,
            "salary_max_monthly": np.nan,
            "salary_mid_monthly": np.nan,
            "salary_min_year": np.nan,
            "salary_max_year": np.nan,
            "salary_mid_year": np.nan,
            "salary_is_valid": False,
            "salary_invalid_reason": "negotiable",
        }

    # hourly / daily / weekly
    hr = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*元\s*/\s*(?:时|小时)", s)
    if hr:
        lo, hi = float(hr.group(1)), float(hr.group(2))
        lo_m = lo * cfg.work_hours_per_day * cfg.work_days_per_month
        hi_m = hi * cfg.work_hours_per_day * cfg.work_days_per_month
        return _finalize(s, "hourly", months, lo_m, hi_m)

    dy = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*元\s*/\s*(?:天|日)", s)
    if dy:
        lo, hi = float(dy.group(1)), float(dy.group(2))
        lo_m = lo * cfg.work_days_per_month
        hi_m = hi * cfg.work_days_per_month
        return _finalize(s, "daily", months, lo_m, hi_m)

    wk = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*元\s*/\s*周", s)
    if wk:
        lo, hi = float(wk.group(1)), float(wk.group(2))
        lo_m = lo * cfg.work_weeks_per_month
        hi_m = hi * cfg.work_weeks_per_month
        return _finalize(s, "weekly", months, lo_m, hi_m)

    # monthly range with unit
    mrg = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*([Kk万千元])", s)
    if mrg:
        lo, hi, unit = mrg.groups()
        factor = 1000.0 if unit in ("K", "k", "千") else 10000.0 if unit == "万" else 1.0
        lo_m, hi_m = float(lo) * factor, float(hi) * factor
        return _finalize(s, "monthly_range", months, lo_m, hi_m)

    # single value
    sv = re.search(r"(\d+(?:\.\d+)?)\s*([Kk万千元])(?:\s*以上)?", s)
    if sv:
        val, unit = sv.groups()
        factor = 1000.0 if unit in ("K", "k", "千") else 10000.0 if unit == "万" else 1.0
        v = float(val) * factor
        return _finalize(s, "single_value", months, v, v)

    return {
        "salary_raw": s,
        "salary_type": "unparsed",
        "salary_months": months if month_match else None,
        "salary_min_monthly": np.nan,
        "salary_max_monthly": np.nan,
        "salary_mid_monthly": np.nan,
        "salary_min_year": np.nan,
        "salary_max_year": np.nan,
        "salary_mid_year": np.nan,
        "salary_is_valid": False,
        "salary_invalid_reason": "unparsed",
    }


def _finalize(s: str, t: str, months: int, lo_m: float, hi_m: float) -> dict[str, object]:
    if hi_m < lo_m or lo_m < 0:
        return {
            "salary_raw": s,
            "salary_type": t,
            "salary_months": months,
            "salary_min_monthly": np.nan,
            "salary_max_monthly": np.nan,
            "salary_mid_monthly": np.nan,
            "salary_min_year": np.nan,
            "salary_max_year": np.nan,
            "salary_mid_year": np.nan,
            "salary_is_valid": False,
            "salary_invalid_reason": "invalid_range",
        }
    mid_m = (lo_m + hi_m) / 2.0
    return {
        "salary_raw": s,
        "salary_type": t,
        "salary_months": months,
        "salary_min_monthly": lo_m,
        "salary_max_monthly": hi_m,
        "salary_mid_monthly": mid_m,
        "salary_min_year": lo_m * months,
        "salary_max_year": hi_m * months,
        "salary_mid_year": mid_m * months,
        "salary_is_valid": True,
        "salary_invalid_reason": "",
    }


def salary_level(mid_monthly: float) -> str:
    if pd.isna(mid_monthly):
        return "未解析"
    k = mid_monthly / 1000.0
    if k < 5:
        return "0-5K"
    if k >= 40:
        return "40K+"
    lo = int(k // 5) * 5
    return f"{lo}-{lo+5}K"


def build_rank_maps(df_valid: pd.DataFrame) -> tuple[dict[str, int], dict[str, str], dict[str, int], dict[str, str]]:
    exp_order = (
        df_valid.groupby("experience", as_index=False)["salary_mid_year"]
        .median()
        .sort_values("salary_mid_year")
    )
    edu_order = (
        df_valid.groupby("education", as_index=False)["salary_mid_year"]
        .median()
        .sort_values("salary_mid_year")
    )

    exp_rank = {v: i + 1 for i, v in enumerate(exp_order["experience"].tolist())}
    edu_rank = {v: i + 1 for i, v in enumerate(edu_order["education"].tolist())}
    exp_label = {k: f"E{i}" for k, i in exp_rank.items()}
    edu_label = {k: f"D{i}" for k, i in edu_rank.items()}
    return exp_rank, exp_label, edu_rank, edu_label


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = CleanConfig()

    raw = pd.read_excel(INPUT_XLSX)
    base_cols = ["job_title", "city", "salary", "experience", "education", "company", "company_type"]
    missing_cols = [c for c in base_cols if c not in raw.columns]
    if missing_cols:
        raise ValueError(f"missing required columns: {missing_cols}")

    raw = raw[base_cols].copy()
    raw_rows = len(raw)
    dup_rows = int(raw.duplicated().sum())
    clean_base = raw.drop_duplicates().copy()

    parsed = pd.DataFrame([parse_salary(v, cfg) for v in clean_base["salary"]])
    clean_salary = pd.concat([clean_base.reset_index(drop=True), parsed], axis=1)

    # salary outlier flag on valid mid_year
    valid_mid = clean_salary.loc[clean_salary["salary_is_valid"], "salary_mid_year"]
    q1 = valid_mid.quantile(0.25) if not valid_mid.empty else np.nan
    q3 = valid_mid.quantile(0.75) if not valid_mid.empty else np.nan
    iqr = q3 - q1 if pd.notna(q1) and pd.notna(q3) else np.nan
    low = q1 - cfg.iqr_k * iqr if pd.notna(iqr) else np.nan
    high = q3 + cfg.iqr_k * iqr if pd.notna(iqr) else np.nan

    clean_salary["salary_is_outlier"] = False
    if pd.notna(low) and pd.notna(high):
        m = clean_salary["salary_is_valid"] & ((clean_salary["salary_mid_year"] < low) | (clean_salary["salary_mid_year"] > high))
        clean_salary.loc[m, "salary_is_outlier"] = True

    clean_salary["salary_level"] = clean_salary["salary_mid_monthly"].map(salary_level)

    # rank fields from valid data
    df_valid = clean_salary[clean_salary["salary_is_valid"]].copy()
    exp_rank, exp_label, edu_rank, edu_label = build_rank_maps(df_valid)

    clean_feature = clean_salary.copy()
    clean_feature["experience_rank"] = clean_feature["experience"].map(exp_rank)
    clean_feature["experience_label"] = clean_feature["experience"].map(exp_label)
    clean_feature["education_rank"] = clean_feature["education"].map(edu_rank)
    clean_feature["education_label"] = clean_feature["education"].map(edu_label)
    clean_feature["talent_threshold_index"] = (
        clean_feature["experience_rank"].fillna(0) * 0.5 + clean_feature["education_rank"].fillna(0) * 0.5
    )

    # outputs
    clean_base.to_csv(OUT_DIR / "clean_base.csv", index=False)
    clean_salary.to_csv(OUT_DIR / "clean_salary.csv", index=False)
    clean_feature.to_csv(OUT_DIR / "clean_feature_ready.csv", index=False)

    # mapping tables
    pd.DataFrame(
        [{"experience": k, "experience_rank": v, "experience_label": exp_label[k]} for k, v in sorted(exp_rank.items(), key=lambda x: x[1])]
    ).to_csv(OUT_DIR / "experience_mapping.csv", index=False)
    pd.DataFrame(
        [{"education": k, "education_rank": v, "education_label": edu_label[k]} for k, v in sorted(edu_rank.items(), key=lambda x: x[1])]
    ).to_csv(OUT_DIR / "education_mapping.csv", index=False)

    salary_type_dist = clean_salary["salary_type"].value_counts(dropna=False).rename_axis("salary_type").reset_index(name="count")
    salary_level_dist = clean_salary["salary_level"].value_counts(dropna=False).rename_axis("salary_level").reset_index(name="count")
    salary_type_dist.to_csv(OUT_DIR / "salary_type_distribution.csv", index=False)
    salary_level_dist.to_csv(OUT_DIR / "salary_level_distribution.csv", index=False)

    log = {
        "input_file": str(INPUT_XLSX),
        "raw_rows": int(raw_rows),
        "duplicate_rows_removed": int(dup_rows),
        "clean_base_rows": int(len(clean_base)),
        "salary_valid_rows": int(clean_salary["salary_is_valid"].sum()),
        "salary_invalid_rows": int((~clean_salary["salary_is_valid"]).sum()),
        "salary_outlier_rows": int(clean_salary["salary_is_outlier"].sum()),
        "salary_outlier_bounds_year": {"low": None if pd.isna(low) else float(low), "high": None if pd.isna(high) else float(high)},
        "config": {
            "work_hours_per_day": cfg.work_hours_per_day,
            "work_days_per_month": cfg.work_days_per_month,
            "work_weeks_per_month": cfg.work_weeks_per_month,
            "default_salary_months": cfg.default_salary_months,
            "iqr_k": cfg.iqr_k,
        },
    }
    (OUT_DIR / "clean_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        "# 数据清洗日志",
        "",
        f"- 原始记录数: {raw_rows:,}",
        f"- 去重删除数: {dup_rows:,}",
        f"- 清洗后基础记录数: {len(clean_base):,}",
        f"- 薪资可用记录数: {int(clean_salary['salary_is_valid'].sum()):,}",
        f"- 薪资不可用记录数: {int((~clean_salary['salary_is_valid']).sum()):,}",
        f"- 薪资异常值记录数(IQR): {int(clean_salary['salary_is_outlier'].sum()):,}",
        "",
        "输出文件:",
        "- clean_base.csv",
        "- clean_salary.csv",
        "- clean_feature_ready.csv",
        "- experience_mapping.csv",
        "- education_mapping.csv",
        "- salary_type_distribution.csv",
        "- salary_level_distribution.csv",
        "- clean_log.json",
    ]
    (OUT_DIR / "clean_log.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"[OK] cleaned outputs written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
