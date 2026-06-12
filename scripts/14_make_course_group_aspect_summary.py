# -*- coding: utf-8 -*-
"""
14_make_course_group_aspect_summary.py

목적
- 13_generate_report_analysis_direct_colab.py 결과를 바탕으로
  글쓰기 / 실용영어 과목군별 평가 요인 비교표를 생성한다.
- 발표와 기말 레포트에서 사용할 과목군 비교 자료를 만든다.

입력 기본값
    C:\every_time\outputs\report_analysis\segment_aspect_sentiment_merged_DIRECT_CHECK.csv
    C:\every_time\outputs\report_analysis\aspect_summary.csv

출력
    C:\every_time\outputs\report_analysis\course_group_analysis\
        course_group_aspect_summary.csv
        writing_aspect_summary.csv
        practical_english_aspect_summary.csv
        course_group_aspect_comparison.csv
        common_aspect_factors.csv
        course_group_analysis_tables.xlsx

실행
    cd C:\every_time
    .\.venv\Scripts\Activate.ps1
    python scripts\14_make_course_group_aspect_summary.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


HIGH_RATING = {"VERY_HIGH_SATISFACTION", "HIGH_SATISFACTION"}
LOW_RATING = {"LOW_SATISFACTION", "VERY_LOW_SATISFACTION"}


def read_csv_auto(path: Path) -> pd.DataFrame:
    last_error = None
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_error = e
    raise RuntimeError(f"CSV를 읽지 못했습니다: {path}\n{last_error}")


def clean_text(value, max_len=None):
    if pd.isna(value):
        return ""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if max_len and len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text


def save_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].apply(clean_text)
    out.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL, lineterminator="\n")


def pct(n, d):
    return round(float(n) / float(d) * 100, 2) if d else 0.0


def normalize_sentiment(value):
    if pd.isna(value):
        return "UNKNOWN"
    text = str(value).strip()
    low = text.lower()
    if low in {"positive", "pos", "label_1", "1", "긍정"} or "positive" in low or "긍정" in text:
        return "POSITIVE"
    if low in {"negative", "neg", "label_0", "0", "부정"} or "negative" in low or "부정" in text:
        return "NEGATIVE"
    return text or "UNKNOWN"


def infer_course_group(row):
    if "course_group" in row and pd.notna(row["course_group"]) and str(row["course_group"]).strip():
        return str(row["course_group"]).strip()
    name = str(row.get("course_name", ""))
    if "글쓰기" in name:
        return "글쓰기"
    if "영어" in name or "English" in name or "Practical" in name:
        return "실용영어"
    return "기타"


def load_inputs(root: Path):
    report_dir = root / "outputs" / "report_analysis"
    merged_path = report_dir / "segment_aspect_sentiment_merged_DIRECT_CHECK.csv"
    aspect_path = report_dir / "aspect_summary.csv"

    if not merged_path.exists():
        raise FileNotFoundError(
            f"필수 입력 파일이 없습니다: {merged_path}\n"
            "먼저 python scripts\\13_generate_report_analysis_direct_colab.py 를 실행하세요."
        )

    merged = read_csv_auto(merged_path)
    aspect = read_csv_auto(aspect_path) if aspect_path.exists() else pd.DataFrame()

    return merged, aspect


def prepare(df: pd.DataFrame):
    df = df.copy()

    if "aspect_cluster_id" not in df.columns and "cluster_id" in df.columns:
        df["aspect_cluster_id"] = df["cluster_id"]

    if "course_group" not in df.columns:
        df["course_group"] = df.apply(infer_course_group, axis=1)
    else:
        df["course_group"] = df.apply(infer_course_group, axis=1)

    if "sentiment_bin" not in df.columns:
        if "predicted_label_standard" in df.columns:
            df["sentiment_bin"] = df["predicted_label_standard"].apply(normalize_sentiment)
        else:
            df["sentiment_bin"] = "UNKNOWN"

    if "review_rating" not in df.columns:
        df["review_rating"] = np.nan

    if "rating_satisfaction_signal" not in df.columns:
        df["rating_satisfaction_signal"] = "RATING_UNKNOWN"

    if "segment_text" not in df.columns and "segment_text_for_model" in df.columns:
        df["segment_text"] = df["segment_text_for_model"]

    if "review_id" not in df.columns:
        df["review_id"] = df.get("segment_id", pd.Series(range(len(df))))

    df["review_rating"] = pd.to_numeric(df["review_rating"], errors="coerce")
    df["predicted_score"] = pd.to_numeric(df.get("predicted_score", np.nan), errors="coerce")
    df["segment_text"] = df.get("segment_text", "").apply(clean_text)
    df["course_name"] = df.get("course_name", "").fillna("").astype(str)

    return df


def make_keyword_map(aspect_summary: pd.DataFrame):
    if aspect_summary.empty:
        return {}
    df = aspect_summary.copy()
    if "aspect_cluster_id" not in df.columns and "cluster_id" in df.columns:
        df["aspect_cluster_id"] = df["cluster_id"]
    if "top_keywords" not in df.columns:
        df["top_keywords"] = ""
    return {
        str(row["aspect_cluster_id"]): clean_text(row["top_keywords"])
        for _, row in df.iterrows()
    }


def summarize_by_course_group_aspect(df: pd.DataFrame, keyword_map: dict):
    rows = []
    for (course_group, cid), g in df.groupby(["course_group", "aspect_cluster_id"]):
        n = len(g)
        pos = int((g["sentiment_bin"] == "POSITIVE").sum())
        neg = int((g["sentiment_bin"] == "NEGATIVE").sum())
        high_neg = int((g["rating_satisfaction_signal"].isin(HIGH_RATING) & (g["sentiment_bin"] == "NEGATIVE")).sum())
        low_pos = int((g["rating_satisfaction_signal"].isin(LOW_RATING) & (g["sentiment_bin"] == "POSITIVE")).sum())

        rows.append({
            "course_group": course_group,
            "aspect_cluster_id": cid,
            "top_keywords": keyword_map.get(str(cid), ""),
            "segment_count": n,
            "review_count": g["review_id"].nunique(),
            "course_count": g["course_name"].nunique(),
            "positive_count": pos,
            "negative_count": neg,
            "positive_ratio_percent": pct(pos, n),
            "negative_ratio_percent": pct(neg, n),
            "high_rating_negative_count": high_neg,
            "low_rating_positive_count": low_pos,
            "avg_review_rating": round(float(g["review_rating"].dropna().mean()), 3) if g["review_rating"].notna().any() else np.nan,
            "top_courses": ", ".join(g["course_name"].dropna().astype(str).value_counts().head(3).index.tolist()),
            "representative_positive": " | ".join(
                g[g["sentiment_bin"] == "POSITIVE"]
                .sort_values("predicted_score", ascending=False, na_position="last")
                .head(2)["segment_text"]
                .map(lambda x: clean_text(x, 120))
                .tolist()
            ),
            "representative_negative": " | ".join(
                g[g["sentiment_bin"] == "NEGATIVE"]
                .sort_values("predicted_score", ascending=False, na_position="last")
                .head(2)["segment_text"]
                .map(lambda x: clean_text(x, 120))
                .tolist()
            ),
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["course_group", "segment_count"], ascending=[True, False])
    return out


def make_comparison(summary: pd.DataFrame):
    if summary.empty:
        return pd.DataFrame(), pd.DataFrame()

    groups = sorted(summary["course_group"].dropna().astype(str).unique().tolist())

    # 글쓰기/실용영어가 있으면 그 순서 우선
    preferred = [g for g in ["글쓰기", "실용영어", "WRITING", "PRACTICAL_ENGLISH"] if g in groups]
    rest = [g for g in groups if g not in preferred]
    groups = preferred + rest

    rows = []
    for cid, g in summary.groupby("aspect_cluster_id"):
        row = {
            "aspect_cluster_id": cid,
            "top_keywords": g["top_keywords"].dropna().astype(str).iloc[0] if len(g) else "",
        }
        for group_name in groups:
            gg = g[g["course_group"] == group_name]
            prefix = str(group_name)
            if gg.empty:
                row[f"{prefix}_segment_count"] = 0
                row[f"{prefix}_positive_ratio_percent"] = 0.0
                row[f"{prefix}_negative_ratio_percent"] = 0.0
                row[f"{prefix}_avg_review_rating"] = np.nan
            else:
                r = gg.iloc[0]
                row[f"{prefix}_segment_count"] = int(r["segment_count"])
                row[f"{prefix}_positive_ratio_percent"] = r["positive_ratio_percent"]
                row[f"{prefix}_negative_ratio_percent"] = r["negative_ratio_percent"]
                row[f"{prefix}_avg_review_rating"] = r["avg_review_rating"]

        counts = {group_name: row.get(f"{group_name}_segment_count", 0) for group_name in groups}
        row["total_segment_count"] = sum(counts.values())
        row["dominant_group"] = max(counts, key=counts.get) if counts else ""
        row["present_group_count"] = sum(1 for v in counts.values() if v > 0)
        row["common_factor_flag"] = row["present_group_count"] >= 2
        rows.append(row)

    comparison = pd.DataFrame(rows)
    if not comparison.empty:
        comparison = comparison.sort_values(["common_factor_flag", "total_segment_count"], ascending=[False, False])

    common = comparison[comparison["common_factor_flag"] == True].copy() if not comparison.empty else comparison

    return comparison, common


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\every_time")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = root / "outputs" / "report_analysis" / "course_group_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("14. 과목군별 평가 요인 비교표 생성")
    print("ROOT:", root)
    print("OUT :", out_dir)
    print("=" * 80)

    merged, aspect = load_inputs(root)
    merged = prepare(merged)
    kmap = make_keyword_map(aspect)

    summary = summarize_by_course_group_aspect(merged, kmap)
    comparison, common = make_comparison(summary)

    writing = summary[summary["course_group"].astype(str).str.contains("글쓰기|WRITING", regex=True, na=False)].copy()
    practical = summary[summary["course_group"].astype(str).str.contains("실용영어|PRACTICAL", regex=True, na=False)].copy()

    save_csv(summary, out_dir / "course_group_aspect_summary.csv")
    save_csv(writing, out_dir / "writing_aspect_summary.csv")
    save_csv(practical, out_dir / "practical_english_aspect_summary.csv")
    save_csv(comparison, out_dir / "course_group_aspect_comparison.csv")
    save_csv(common, out_dir / "common_aspect_factors.csv")

    xlsx_path = out_dir / "course_group_analysis_tables.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="group_aspect_summary", index=False)
        writing.head(200).to_excel(writer, sheet_name="writing", index=False)
        practical.head(200).to_excel(writer, sheet_name="practical_english", index=False)
        comparison.head(300).to_excel(writer, sheet_name="comparison", index=False)
        common.head(200).to_excel(writer, sheet_name="common_factors", index=False)

    print("완료")
    print("통합 엑셀:", xlsx_path)
    print("비교표:", out_dir / "course_group_aspect_comparison.csv")


if __name__ == "__main__":
    main()
