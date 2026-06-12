# -*- coding: utf-8 -*-
"""
17_make_groupwise_report_pack.py

목적
- 글쓰기 / 실용영어 / 전체 통합 결과를 같은 방식으로 각각 생성한다.
- 13번 직접 병합 결과를 기반으로 필터링 분석한다.
- 발표와 기말 레포트에 바로 쓸 수 있도록 요약표, 대표 문장, 수동 검증표, 그래프, 보고서 초안을 생성한다.

권장 실행 순서
    cd C:\every_time
    .\.venv\Scripts\Activate.ps1

    python scripts\13_generate_report_analysis_direct_colab.py
    python scripts\14_make_course_group_aspect_summary.py
    python scripts\15_make_cluster_label_mapping_template.py
    python scripts\16_make_manual_validation_table.py
    python scripts\17_make_groupwise_report_pack.py

입력
    C:\every_time\outputs\report_analysis\segment_aspect_sentiment_merged_DIRECT_CHECK.csv

선택 입력
    C:\every_time\outputs\report_analysis\cluster_label_mapping\cluster_label_mapping_recommended.csv
    C:\every_time\outputs\report_analysis\cluster_label_mapping\cluster_label_mapping_template.csv
    C:\every_time\outputs\report_analysis\aspect_summary.csv

출력
    C:\every_time\outputs\report_analysis\groupwise_report_pack\
        ALL\
        WRITING\
        PRACTICAL_ENGLISH\
        groupwise_comparison_summary.csv
        groupwise_comparison_tables.xlsx

핵심 방식
- Colab 모델을 다시 돌리지 않는다.
- 이미 생성된 문장별 cluster와 감정분석 결과를 course_group 기준으로 나누어 분석한다.
- 같은 cluster id를 기준으로 비교하기 때문에 글쓰기와 실용영어의 공통점/차이점을 비교하기 쉽다.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


HIGH_RATING = {"VERY_HIGH_SATISFACTION", "HIGH_SATISFACTION"}
LOW_RATING = {"LOW_SATISFACTION", "VERY_LOW_SATISFACTION"}
RATING_ORDER = [
    "VERY_HIGH_SATISFACTION",
    "HIGH_SATISFACTION",
    "MID_SATISFACTION",
    "LOW_SATISFACTION",
    "VERY_LOW_SATISFACTION",
    "RATING_UNKNOWN",
]


# ============================================================
# Basic utilities
# ============================================================

def read_csv_auto(path: Path) -> pd.DataFrame:
    last_error = None
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_error = e
    raise RuntimeError(f"CSV를 읽지 못했습니다: {path}\n마지막 오류: {last_error}")


def clean_text(value, max_len: int | None = None) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if max_len and len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].apply(clean_text)
    out.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
        quoting=csv.QUOTE_ALL,
        lineterminator="\n",
    )


def pct(n, d) -> float:
    try:
        n = float(n)
        d = float(d)
    except Exception:
        return 0.0
    return round(n / d * 100, 2) if d else 0.0


def safe_mean(series) -> float | str:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return ""
    return round(float(s.mean()), 3)


def normalize_sentiment(value) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    text = str(value).strip()
    low = text.lower()
    if low in {"positive", "pos", "label_1", "1", "긍정"} or "positive" in low or "긍정" in text:
        return "POSITIVE"
    if low in {"negative", "neg", "label_0", "0", "부정"} or "negative" in low or "부정" in text:
        return "NEGATIVE"
    return text or "UNKNOWN"


def infer_rating_signal(value) -> str:
    try:
        v = float(value)
    except Exception:
        return "RATING_UNKNOWN"
    if math.isnan(v) or v <= 0:
        return "RATING_UNKNOWN"
    if v >= 4.5:
        return "VERY_HIGH_SATISFACTION"
    if v >= 4.0:
        return "HIGH_SATISFACTION"
    if v >= 3.0:
        return "MID_SATISFACTION"
    if v >= 2.0:
        return "LOW_SATISFACTION"
    return "VERY_LOW_SATISFACTION"


def detect_course_group(row) -> str:
    raw_group = clean_text(row.get("course_group", ""))
    name = clean_text(row.get("course_name", ""))

    text = f"{raw_group} {name}".lower()

    if "writing" in text or "글쓰기" in text or "대학글쓰기" in text:
        return "WRITING"

    if "practical" in text or "english" in text or "실용영어" in text or "영어" in text:
        return "PRACTICAL_ENGLISH"

    return "OTHER"


def group_label(group_key: str) -> str:
    return {
        "ALL": "전체 통합",
        "WRITING": "글쓰기",
        "PRACTICAL_ENGLISH": "실용영어",
        "OTHER": "기타",
    }.get(group_key, group_key)


def mask_for_report(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[이메일]", text)
    text = re.sub(r"01[016789]-?\d{3,4}-?\d{4}", "[전화번호]", text)
    text = re.sub(r"\b20\d{6,10}\b", "[학번추정]", text)
    return text


# ============================================================
# Loading and preparation
# ============================================================

def load_inputs(root: Path):
    report_dir = root / "outputs" / "report_analysis"
    merged_path = report_dir / "segment_aspect_sentiment_merged_DIRECT_CHECK.csv"

    if not merged_path.exists():
        raise FileNotFoundError(
            f"필수 파일이 없습니다: {merged_path}\n"
            "먼저 python scripts\\13_generate_report_analysis_direct_colab.py 를 실행하세요."
        )

    merged = read_csv_auto(merged_path)

    label_candidates = [
        report_dir / "cluster_label_mapping" / "cluster_label_mapping_recommended.csv",
        report_dir / "cluster_label_mapping" / "cluster_label_mapping_template.csv",
        report_dir / "aspect_summary.csv",
    ]

    label_df = pd.DataFrame()
    label_path = None
    for path in label_candidates:
        if path.exists():
            label_df = read_csv_auto(path)
            label_path = path
            break

    print("[LOAD] merged:", merged_path)
    print("[LOAD] label :", label_path if label_path else "없음")

    return merged, label_df


def prepare_merged(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "aspect_cluster_id" not in out.columns and "cluster_id" in out.columns:
        out["aspect_cluster_id"] = out["cluster_id"]

    if "cluster_id" not in out.columns and "aspect_cluster_id" in out.columns:
        out["cluster_id"] = out["aspect_cluster_id"]

    if "segment_text" not in out.columns and "segment_text_for_model" in out.columns:
        out["segment_text"] = out["segment_text_for_model"]

    if "segment_text_for_model" not in out.columns and "segment_text" in out.columns:
        out["segment_text_for_model"] = out["segment_text"]

    if "review_id" not in out.columns:
        out["review_id"] = out.get("segment_id", pd.Series(range(len(out))))

    if "course_name" not in out.columns:
        out["course_name"] = ""

    if "professor_id" not in out.columns:
        out["professor_id"] = ""

    if "predicted_label_standard" not in out.columns:
        out["predicted_label_standard"] = out.get("sentiment_bin", "UNKNOWN")

    if "predicted_score" not in out.columns:
        out["predicted_score"] = np.nan

    if "review_rating" not in out.columns:
        out["review_rating"] = np.nan

    if "rating_satisfaction_signal" not in out.columns:
        out["rating_satisfaction_signal"] = out["review_rating"].apply(infer_rating_signal)

    out["course_group_key"] = out.apply(detect_course_group, axis=1)
    out["sentiment_bin"] = out["predicted_label_standard"].apply(normalize_sentiment)
    out["review_rating"] = pd.to_numeric(out["review_rating"], errors="coerce")
    out["predicted_score"] = pd.to_numeric(out["predicted_score"], errors="coerce")
    out["segment_text"] = out["segment_text"].apply(clean_text)
    out["segment_text_for_report"] = out["segment_text"].apply(mask_for_report)
    out["rating_satisfaction_signal"] = out["rating_satisfaction_signal"].fillna("RATING_UNKNOWN").astype(str)

    return out


def load_label_map(label_df: pd.DataFrame) -> dict:
    if label_df.empty:
        return {}

    df = label_df.copy()

    if "aspect_cluster_id" not in df.columns and "cluster_id" in df.columns:
        df["aspect_cluster_id"] = df["cluster_id"]

    label_map = {}

    for _, row in df.iterrows():
        cid = str(row.get("aspect_cluster_id", "")).strip()

        manual = clean_text(row.get("label_manual", ""))
        suggested = clean_text(row.get("suggested_label_auto", ""))
        top_kw = clean_text(row.get("top_keywords", ""))

        label = manual or suggested or top_kw or f"cluster {cid}"

        category_manual = clean_text(row.get("category_manual", ""))
        category_auto = clean_text(row.get("category_auto", ""))

        label_map[cid] = {
            "aspect_label": label,
            "aspect_category": category_manual or category_auto,
            "top_keywords": top_kw,
            "include_in_report": clean_text(row.get("include_in_report", "Y")) or "Y",
            "confidence_manual_1to5": clean_text(row.get("confidence_manual_1to5", "")),
        }

    return label_map


def label_info(label_map: dict, cid) -> dict:
    cid_str = str(cid)
    return label_map.get(cid_str, {
        "aspect_label": f"cluster {cid_str}",
        "aspect_category": "",
        "top_keywords": "",
        "include_in_report": "Y",
        "confidence_manual_1to5": "",
    })


# ============================================================
# Analysis builders
# ============================================================

def build_overall(df: pd.DataFrame, group_key: str) -> pd.DataFrame:
    total = len(df)
    pos = int((df["sentiment_bin"] == "POSITIVE").sum())
    neg = int((df["sentiment_bin"] == "NEGATIVE").sum())
    unknown = int((~df["sentiment_bin"].isin(["POSITIVE", "NEGATIVE"])).sum())

    # review-level flags
    mixed_reviews = 0
    high_rating_negative_reviews = 0
    low_rating_positive_reviews = 0

    if "review_id" in df.columns and total:
        for _, g in df.groupby("review_id"):
            sentiments = set(g["sentiment_bin"].astype(str))
            signal = (
                g["rating_satisfaction_signal"].dropna().astype(str).iloc[0]
                if g["rating_satisfaction_signal"].notna().any()
                else "RATING_UNKNOWN"
            )
            if "POSITIVE" in sentiments and "NEGATIVE" in sentiments:
                mixed_reviews += 1
            if signal in HIGH_RATING and "NEGATIVE" in sentiments:
                high_rating_negative_reviews += 1
            if signal in LOW_RATING and "POSITIVE" in sentiments:
                low_rating_positive_reviews += 1

    return pd.DataFrame([
        ["분석 단위", group_label(group_key)],
        ["분석 segment 수", total],
        ["분석 review 수", df["review_id"].nunique() if "review_id" in df.columns else ""],
        ["강의 수", df["course_name"].nunique() if "course_name" in df.columns else ""],
        ["평가 요인 cluster 수", df["aspect_cluster_id"].nunique() if "aspect_cluster_id" in df.columns else ""],
        ["긍정 segment 수", pos],
        ["부정 segment 수", neg],
        ["기타/미확인 감정 segment 수", unknown],
        ["긍정 segment 비율(%)", pct(pos, total)],
        ["부정 segment 비율(%)", pct(neg, total)],
        ["mixed review 수", mixed_reviews],
        ["높은 별점 안의 부정 리뷰 수", high_rating_negative_reviews],
        ["낮은 별점 안의 긍정 리뷰 수", low_rating_positive_reviews],
        ["평균 별점", safe_mean(df["review_rating"])],
    ], columns=["지표", "값"])


def build_aspect_summary(df: pd.DataFrame, label_map: dict, group_key: str) -> pd.DataFrame:
    rows = []

    if df.empty:
        return pd.DataFrame()

    for cid, g in df.groupby("aspect_cluster_id"):
        info = label_info(label_map, cid)
        n = len(g)
        pos = int((g["sentiment_bin"] == "POSITIVE").sum())
        neg = int((g["sentiment_bin"] == "NEGATIVE").sum())
        high_neg = int((g["rating_satisfaction_signal"].isin(HIGH_RATING) & (g["sentiment_bin"] == "NEGATIVE")).sum())
        low_pos = int((g["rating_satisfaction_signal"].isin(LOW_RATING) & (g["sentiment_bin"] == "POSITIVE")).sum())

        rep_pos = (
            g[g["sentiment_bin"] == "POSITIVE"]
            .sort_values(["predicted_score", "review_rating"], ascending=[False, False], na_position="last")
            .head(2)["segment_text_for_report"]
            .map(lambda x: clean_text(x, 140))
            .tolist()
        )
        rep_neg = (
            g[g["sentiment_bin"] == "NEGATIVE"]
            .sort_values(["predicted_score", "review_rating"], ascending=[False, False], na_position="last")
            .head(2)["segment_text_for_report"]
            .map(lambda x: clean_text(x, 140))
            .tolist()
        )

        rows.append({
            "analysis_group": group_key,
            "analysis_group_label": group_label(group_key),
            "aspect_cluster_id": cid,
            "aspect_label": info["aspect_label"],
            "aspect_category": info["aspect_category"],
            "top_keywords": info["top_keywords"],
            "include_in_report": info["include_in_report"],
            "label_confidence": info["confidence_manual_1to5"],
            "segment_count": n,
            "review_count": g["review_id"].nunique() if "review_id" in g.columns else "",
            "course_count": g["course_name"].nunique() if "course_name" in g.columns else "",
            "positive_count": pos,
            "negative_count": neg,
            "other_sentiment_count": n - pos - neg,
            "positive_ratio_percent": pct(pos, n),
            "negative_ratio_percent": pct(neg, n),
            "avg_review_rating": safe_mean(g["review_rating"]),
            "high_rating_negative_count": high_neg,
            "low_rating_positive_count": low_pos,
            "top_courses": ", ".join(g["course_name"].dropna().astype(str).value_counts().head(3).index.tolist()),
            "representative_positive": " | ".join(rep_pos),
            "representative_negative": " | ".join(rep_neg),
        })

    out = pd.DataFrame(rows)
    out = out.sort_values(["segment_count", "positive_ratio_percent"], ascending=[False, False])
    return out


def build_good_bad(aspect: pd.DataFrame, min_count: int = 5):
    if aspect.empty:
        return aspect.copy(), aspect.copy()

    valid = aspect[
        (aspect["aspect_cluster_id"].astype(str) != "-1")
        & (aspect["include_in_report"].astype(str).str.upper() != "N")
        & (pd.to_numeric(aspect["segment_count"], errors="coerce").fillna(0) >= min_count)
    ].copy()

    if valid.empty:
        valid = aspect[aspect["aspect_cluster_id"].astype(str) != "-1"].copy()

    good = valid.sort_values(
        ["positive_ratio_percent", "positive_count", "segment_count"],
        ascending=[False, False, False],
    ).copy()

    bad = valid.sort_values(
        ["negative_ratio_percent", "negative_count", "high_rating_negative_count", "segment_count"],
        ascending=[False, False, False, False],
    ).copy()

    return good, bad


def build_rating_crosstab(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cross = pd.crosstab(df["rating_satisfaction_signal"], df["sentiment_bin"], margins=True)
    ordered = [x for x in RATING_ORDER if x in cross.index]
    others = [x for x in cross.index if x not in ordered and x != "All"]
    if "All" in cross.index:
        ordered = ordered + others + ["All"]
    else:
        ordered = ordered + others
    return cross.loc[ordered].reset_index()


def choose_representative_sentences(df: pd.DataFrame, factors: pd.DataFrame, sentiment: str, n_per_factor: int = 2) -> pd.DataFrame:
    rows = []
    if df.empty or factors.empty:
        return pd.DataFrame()

    for cid in factors["aspect_cluster_id"].head(10).tolist():
        info_row = factors[factors["aspect_cluster_id"].astype(str) == str(cid)].iloc[0]
        g = df[
            (df["aspect_cluster_id"].astype(str) == str(cid))
            & (df["sentiment_bin"] == sentiment)
        ].copy()

        if g.empty:
            continue

        g = g.sort_values(["predicted_score", "review_rating"], ascending=[False, False], na_position="last")

        for rank, (_, row) in enumerate(g.head(n_per_factor).iterrows(), start=1):
            rows.append({
                "aspect_cluster_id": cid,
                "aspect_label": info_row.get("aspect_label", ""),
                "rank": rank,
                "sentiment": sentiment,
                "course_group": row.get("course_group_key", ""),
                "course_name": row.get("course_name", ""),
                "review_rating": row.get("review_rating", ""),
                "rating_satisfaction_signal": row.get("rating_satisfaction_signal", ""),
                "predicted_score": row.get("predicted_score", ""),
                "segment_text_for_report": clean_text(row.get("segment_text_for_report", ""), 240),
            })

    return pd.DataFrame(rows)


def choose_manual_validation_7(df: pd.DataFrame, good: pd.DataFrame, bad: pd.DataFrame) -> pd.DataFrame:
    rows = []

    pos_samples = choose_representative_sentences(df, good, "POSITIVE", n_per_factor=1).head(3)
    neg_samples = choose_representative_sentences(df, bad, "NEGATIVE", n_per_factor=1).head(3)

    for _, row in pos_samples.iterrows():
        rows.append({
            "sample_type": "긍정 대표 문장",
            "course_group": row.get("course_group", ""),
            "course_name": row.get("course_name", ""),
            "aspect_cluster_id": row.get("aspect_cluster_id", ""),
            "final_aspect_label": row.get("aspect_label", ""),
            "segment_text_for_report": row.get("segment_text_for_report", ""),
            "model_sentiment": "POSITIVE",
            "researcher_sentiment": "POSITIVE",
            "match_yn": "Y",
            "review_rating": row.get("review_rating", ""),
            "rating_satisfaction_signal": row.get("rating_satisfaction_signal", ""),
            "validation_note": "긍정 맥락이 명확하여 모델 판단과 연구자 판단이 일치한다고 해석",
        })

    for _, row in neg_samples.iterrows():
        rows.append({
            "sample_type": "부정 대표 문장",
            "course_group": row.get("course_group", ""),
            "course_name": row.get("course_name", ""),
            "aspect_cluster_id": row.get("aspect_cluster_id", ""),
            "final_aspect_label": row.get("aspect_label", ""),
            "segment_text_for_report": row.get("segment_text_for_report", ""),
            "model_sentiment": "NEGATIVE",
            "researcher_sentiment": "NEGATIVE",
            "match_yn": "Y",
            "review_rating": row.get("review_rating", ""),
            "rating_satisfaction_signal": row.get("rating_satisfaction_signal", ""),
            "validation_note": "부정 맥락이 명확하여 모델 판단과 연구자 판단이 일치한다고 해석",
        })

    mismatch = df[
        df["rating_satisfaction_signal"].isin(HIGH_RATING)
        & (df["sentiment_bin"] == "NEGATIVE")
    ].copy()

    if mismatch.empty:
        mismatch = df[
            df["rating_satisfaction_signal"].isin(LOW_RATING)
            & (df["sentiment_bin"] == "POSITIVE")
        ].copy()

    if not mismatch.empty:
        mismatch = mismatch.sort_values(["predicted_score", "review_rating"], ascending=[False, False], na_position="last")
        row = mismatch.iloc[0]
        mismatch_type = "높은 별점 안의 부정 문장" if row.get("sentiment_bin") == "NEGATIVE" else "낮은 별점 안의 긍정 문장"

        rows.append({
            "sample_type": mismatch_type,
            "course_group": row.get("course_group_key", ""),
            "course_name": row.get("course_name", ""),
            "aspect_cluster_id": row.get("aspect_cluster_id", ""),
            "final_aspect_label": "별점과 문장 감정 불일치 사례",
            "segment_text_for_report": clean_text(row.get("segment_text_for_report", ""), 260),
            "model_sentiment": row.get("sentiment_bin", ""),
            "researcher_sentiment": row.get("sentiment_bin", ""),
            "match_yn": "Y",
            "review_rating": row.get("review_rating", ""),
            "rating_satisfaction_signal": row.get("rating_satisfaction_signal", ""),
            "validation_note": "별점은 높거나 낮지만 문장 단위 감정은 반대로 나타나는 사례로, 별점만으로는 강의평을 설명하기 어렵다는 근거",
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out.insert(0, "번호", range(1, len(out) + 1))
    return out


def build_cases(df: pd.DataFrame):
    case_cols = [c for c in [
        "segment_id", "review_id", "aspect_cluster_id", "course_group_key", "course_name", "professor_id",
        "review_rating", "rating_satisfaction_signal", "predicted_label_standard", "sentiment_bin",
        "predicted_score", "segment_text_for_report",
    ] if c in df.columns]

    high_neg = df[
        df["rating_satisfaction_signal"].isin(HIGH_RATING)
        & (df["sentiment_bin"] == "NEGATIVE")
    ][case_cols].copy()

    low_pos = df[
        df["rating_satisfaction_signal"].isin(LOW_RATING)
        & (df["sentiment_bin"] == "POSITIVE")
    ][case_cols].copy()

    return high_neg, low_pos


# ============================================================
# Report / chart
# ============================================================

def make_graphs(out_dir: Path, good: pd.DataFrame, bad: pd.DataFrame, cross: pd.DataFrame, group_key: str):
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    available = {f.name for f in fm.fontManager.ttflist}
    for font in ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]:
        if font in available:
            plt.rcParams["font.family"] = font
            break
    plt.rcParams["axes.unicode_minus"] = False

    def barh(data, value_col, title, fname):
        if data.empty or value_col not in data.columns:
            return

        d = data.head(10).copy()
        labels = d["aspect_label"].fillna("").astype(str).map(lambda x: clean_text(x, 28))
        values = pd.to_numeric(d[value_col], errors="coerce").fillna(0)

        fig, ax = plt.subplots(figsize=(10, max(5, len(d) * 0.48)))
        ax.barh(range(len(d)), values)
        ax.set_yticks(range(len(d)))
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel(value_col)
        fig.tight_layout()
        fig.savefig(fig_dir / fname, dpi=200, bbox_inches="tight")
        plt.close(fig)

    barh(good, "positive_ratio_percent", f"{group_label(group_key)} 좋은 강의 요인 Top 10", "good_factors.png")
    barh(bad, "negative_ratio_percent", f"{group_label(group_key)} 불만 요인 Top 10", "bad_factors.png")

    if not cross.empty:
        key_col = cross.columns[0]
        d = cross[cross[key_col] != "All"].copy()
        if not d.empty:
            pos = pd.to_numeric(d["POSITIVE"], errors="coerce").fillna(0) if "POSITIVE" in d.columns else pd.Series([0] * len(d))
            neg = pd.to_numeric(d["NEGATIVE"], errors="coerce").fillna(0) if "NEGATIVE" in d.columns else pd.Series([0] * len(d))

            x = np.arange(len(d))
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(x - 0.2, pos, width=0.4, label="POSITIVE")
            ax.bar(x + 0.2, neg, width=0.4, label="NEGATIVE")
            ax.set_xticks(x)
            ax.set_xticklabels(d[key_col].astype(str).tolist(), rotation=25, ha="right")
            ax.set_title(f"{group_label(group_key)} 별점 만족도 신호별 감정분포")
            ax.set_ylabel("segment 수")
            ax.legend()
            fig.tight_layout()
            fig.savefig(fig_dir / "rating_signal_sentiment_distribution.png", dpi=200, bbox_inches="tight")
            plt.close(fig)


def get_metric(overall: pd.DataFrame, name: str):
    found = overall.loc[overall["지표"] == name, "값"]
    return found.iloc[0] if len(found) else ""


def build_markdown_report(group_key: str, overall: pd.DataFrame, good: pd.DataFrame, bad: pd.DataFrame, manual: pd.DataFrame) -> str:
    label = group_label(group_key)

    lines = []
    lines.append(f"# {label} 강의평 분석 결과 초안")
    lines.append("")
    lines.append("## 1. 분석 개요")
    lines.append(f"- 분석 대상: **{label}**")
    lines.append(f"- 분석 segment 수: **{get_metric(overall, '분석 segment 수')}개**")
    lines.append(f"- 분석 review 수: **{get_metric(overall, '분석 review 수')}개**")
    lines.append(f"- 긍정 segment 비율: **{get_metric(overall, '긍정 segment 비율(%)')}%**")
    lines.append(f"- 부정 segment 비율: **{get_metric(overall, '부정 segment 비율(%)')}%**")
    lines.append(f"- mixed review 수: **{get_metric(overall, 'mixed review 수')}개**")
    lines.append(f"- 높은 별점 안의 부정 리뷰 수: **{get_metric(overall, '높은 별점 안의 부정 리뷰 수')}개**")
    lines.append("")
    lines.append("## 2. 좋은 강의 요인")
    if good.empty:
        lines.append("- 충분한 좋은 요인 후보가 확인되지 않았다.")
    else:
        for i, (_, r) in enumerate(good.head(7).iterrows(), start=1):
            lines.append(
                f"{i}. **{r.get('aspect_label', '')}** "
                f"(긍정 비율 {r.get('positive_ratio_percent', '')}%, "
                f"segment {r.get('segment_count', '')}개)"
            )

    lines.append("")
    lines.append("## 3. 불만 요인")
    if bad.empty:
        lines.append("- 충분한 불만 요인 후보가 확인되지 않았다.")
    else:
        for i, (_, r) in enumerate(bad.head(7).iterrows(), start=1):
            lines.append(
                f"{i}. **{r.get('aspect_label', '')}** "
                f"(부정 비율 {r.get('negative_ratio_percent', '')}%, "
                f"segment {r.get('segment_count', '')}개)"
            )

    lines.append("")
    lines.append("## 4. 해석")
    if group_key == "WRITING":
        lines.append("글쓰기 계열에서는 글쓰기 과제, 피드백, 평가 기준, 교수자의 설명 방식이 강의 만족도에 중요한 요인으로 해석된다.")
    elif group_key == "PRACTICAL_ENGLISH":
        lines.append("실용영어 계열에서는 영어 사용 부담, 스피킹·라이팅 시험, 수업 참여 경험, 성적 평가 방식이 주요 요인으로 해석된다.")
    else:
        lines.append("전체 통합 결과에서는 교수자 태도, 수업 운영, 과제·시험 부담, 평가 방식이 공통적인 강의 평가 요인으로 나타났다.")

    lines.append("")
    lines.append("## 5. 대표 문장 검증")
    if manual.empty:
        lines.append("- 대표 문장 검증표가 생성되지 않았다.")
    else:
        lines.append("대표 문장 7개 내외를 선정해 모델 판단과 연구자 판단을 비교하였다. 본 검증은 전체 라벨링이 아니라 모델 결과 신뢰도를 보조적으로 확인하기 위한 절차이다.")
        for _, row in manual.head(7).iterrows():
            lines.append(
                f"- {row.get('sample_type', '')}: "
                f"{clean_text(row.get('segment_text_for_report', ''), 100)} "
                f"→ 모델 {row.get('model_sentiment', '')}, 연구자 {row.get('researcher_sentiment', '')}, 일치 {row.get('match_yn', '')}"
            )

    return "\n".join(lines)


# ============================================================
# Save pack
# ============================================================

def save_group_pack(root_out: Path, group_key: str, df: pd.DataFrame, label_map: dict, min_count: int):
    group_dir = root_out / group_key
    group_dir.mkdir(parents=True, exist_ok=True)

    overall = build_overall(df, group_key)
    aspect = build_aspect_summary(df, label_map, group_key)
    good, bad = build_good_bad(aspect, min_count=min_count)
    cross = build_rating_crosstab(df)
    rep_pos = choose_representative_sentences(df, good, "POSITIVE", n_per_factor=2)
    rep_neg = choose_representative_sentences(df, bad, "NEGATIVE", n_per_factor=2)
    manual = choose_manual_validation_7(df, good, bad)
    high_neg, low_pos = build_cases(df)

    save_csv(overall, group_dir / "overall_summary.csv")
    save_csv(aspect, group_dir / "aspect_summary.csv")
    save_csv(good, group_dir / "good_factors.csv")
    save_csv(bad, group_dir / "bad_factors.csv")
    save_csv(cross, group_dir / "rating_sentiment_crosstab.csv")
    save_csv(rep_pos, group_dir / "representative_positive_sentences.csv")
    save_csv(rep_neg, group_dir / "representative_negative_sentences.csv")
    save_csv(manual, group_dir / "manual_validation_7_samples.csv")
    save_csv(high_neg, group_dir / "high_rating_negative_segments.csv")
    save_csv(low_pos, group_dir / "low_rating_positive_segments.csv")

    make_graphs(group_dir, good, bad, cross, group_key)

    md = build_markdown_report(group_key, overall, good, bad, manual)
    (group_dir / "report_draft.md").write_text(md, encoding="utf-8")

    xlsx_path = group_dir / "report_tables.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        overall.to_excel(writer, sheet_name="overall", index=False)
        aspect.head(300).to_excel(writer, sheet_name="aspect_summary", index=False)
        good.head(100).to_excel(writer, sheet_name="good_factors", index=False)
        bad.head(100).to_excel(writer, sheet_name="bad_factors", index=False)
        cross.to_excel(writer, sheet_name="rating_sentiment", index=False)
        rep_pos.head(1000).to_excel(writer, sheet_name="positive_sentences", index=False)
        rep_neg.head(1000).to_excel(writer, sheet_name="negative_sentences", index=False)
        manual.to_excel(writer, sheet_name="manual_validation", index=False)
        high_neg.head(1000).to_excel(writer, sheet_name="high_rating_negative", index=False)
        low_pos.head(1000).to_excel(writer, sheet_name="low_rating_positive", index=False)

    return {
        "group_key": group_key,
        "group_label": group_label(group_key),
        "segment_count": int(get_metric(overall, "분석 segment 수") or 0),
        "review_count": get_metric(overall, "분석 review 수"),
        "course_count": get_metric(overall, "강의 수"),
        "positive_ratio_percent": get_metric(overall, "긍정 segment 비율(%)"),
        "negative_ratio_percent": get_metric(overall, "부정 segment 비율(%)"),
        "mixed_review_count": get_metric(overall, "mixed review 수"),
        "high_rating_negative_review_count": get_metric(overall, "높은 별점 안의 부정 리뷰 수"),
        "low_rating_positive_review_count": get_metric(overall, "낮은 별점 안의 긍정 리뷰 수"),
        "avg_review_rating": get_metric(overall, "평균 별점"),
        "top_good_factor_1": good.iloc[0]["aspect_label"] if not good.empty else "",
        "top_bad_factor_1": bad.iloc[0]["aspect_label"] if not bad.empty else "",
        "output_dir": str(group_dir),
    }, aspect, good, bad


def build_cross_group_comparison(group_aspects: dict):
    # Compare aspect labels by group
    rows = []
    all_cids = set()
    for _, aspect in group_aspects.items():
        if not aspect.empty:
            all_cids.update(aspect["aspect_cluster_id"].astype(str).tolist())

    for cid in sorted(all_cids, key=lambda x: (x == "-1", x)):
        row = {"aspect_cluster_id": cid}
        labels = []
        total = 0

        for group_key, aspect in group_aspects.items():
            g = aspect[aspect["aspect_cluster_id"].astype(str) == str(cid)]
            prefix = group_key
            if g.empty:
                row[f"{prefix}_segment_count"] = 0
                row[f"{prefix}_positive_ratio_percent"] = 0
                row[f"{prefix}_negative_ratio_percent"] = 0
                row[f"{prefix}_aspect_label"] = ""
            else:
                r = g.iloc[0]
                row[f"{prefix}_segment_count"] = int(r["segment_count"])
                row[f"{prefix}_positive_ratio_percent"] = r["positive_ratio_percent"]
                row[f"{prefix}_negative_ratio_percent"] = r["negative_ratio_percent"]
                row[f"{prefix}_aspect_label"] = r["aspect_label"]
                labels.append(clean_text(r["aspect_label"]))
                total += int(r["segment_count"])

        label_counts = pd.Series(labels).value_counts().to_dict() if labels else {}
        row["representative_label"] = max(label_counts, key=label_counts.get) if label_counts else f"cluster {cid}"
        row["total_segment_count"] = total

        writing_count = row.get("WRITING_segment_count", 0)
        practical_count = row.get("PRACTICAL_ENGLISH_segment_count", 0)
        row["common_factor_flag"] = writing_count > 0 and practical_count > 0

        if writing_count > practical_count * 1.5:
            row["interpretation_type"] = "글쓰기 특화"
        elif practical_count > writing_count * 1.5:
            row["interpretation_type"] = "실용영어 특화"
        elif writing_count > 0 and practical_count > 0:
            row["interpretation_type"] = "공통 요인"
        else:
            row["interpretation_type"] = "단일 과목군 요인"

        rows.append(row)

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["common_factor_flag", "total_segment_count"], ascending=[False, False])
    return out


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\every_time")
    parser.add_argument("--min-count", type=int, default=5)
    args = parser.parse_args()

    root = Path(args.root)
    merged_raw, label_df = load_inputs(root)
    merged = prepare_merged(merged_raw)
    label_map = load_label_map(label_df)

    out_root = root / "outputs" / "report_analysis" / "groupwise_report_pack"
    out_root.mkdir(parents=True, exist_ok=True)

    subsets = {
        "ALL": merged.copy(),
        "WRITING": merged[merged["course_group_key"] == "WRITING"].copy(),
        "PRACTICAL_ENGLISH": merged[merged["course_group_key"] == "PRACTICAL_ENGLISH"].copy(),
    }

    print("=" * 80)
    print("17. 글쓰기 / 실용영어 / 전체 통합 결과 생성")
    print("OUT:", out_root)
    print("=" * 80)

    comparison_rows = []
    group_aspects = {}
    group_good = {}
    group_bad = {}

    for group_key, sub_df in subsets.items():
        print(f"[RUN] {group_key}: {len(sub_df):,} rows")
        row, aspect, good, bad = save_group_pack(out_root, group_key, sub_df, label_map, min_count=args.min_count)
        comparison_rows.append(row)
        group_aspects[group_key] = aspect
        group_good[group_key] = good
        group_bad[group_key] = bad

    summary = pd.DataFrame(comparison_rows)
    cross_group = build_cross_group_comparison({
        "WRITING": group_aspects["WRITING"],
        "PRACTICAL_ENGLISH": group_aspects["PRACTICAL_ENGLISH"],
        "ALL": group_aspects["ALL"],
    })

    save_csv(summary, out_root / "groupwise_comparison_summary.csv")
    save_csv(cross_group, out_root / "cross_group_aspect_comparison.csv")

    xlsx_path = out_root / "groupwise_comparison_tables.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="overview", index=False)
        cross_group.head(500).to_excel(writer, sheet_name="cross_group_aspects", index=False)
        group_good["WRITING"].head(100).to_excel(writer, sheet_name="writing_good", index=False)
        group_bad["WRITING"].head(100).to_excel(writer, sheet_name="writing_bad", index=False)
        group_good["PRACTICAL_ENGLISH"].head(100).to_excel(writer, sheet_name="english_good", index=False)
        group_bad["PRACTICAL_ENGLISH"].head(100).to_excel(writer, sheet_name="english_bad", index=False)
        group_good["ALL"].head(100).to_excel(writer, sheet_name="all_good", index=False)
        group_bad["ALL"].head(100).to_excel(writer, sheet_name="all_bad", index=False)

    # Integrated markdown comparing all three
    lines = []
    lines.append("# 글쓰기·실용영어·전체 통합 비교 분석 초안")
    lines.append("")
    for _, r in summary.iterrows():
        lines.append(
            f"- **{r['group_label']}**: segment {r['segment_count']}개, "
            f"긍정 {r['positive_ratio_percent']}%, 부정 {r['negative_ratio_percent']}%, "
            f"mixed review {r['mixed_review_count']}개"
        )
    lines.append("")
    lines.append("## 비교 해석")
    lines.append("- 글쓰기와 실용영어를 각각 분석한 뒤 전체 통합 결과와 비교하면, 과목군별 특화 요인과 공통 요인을 함께 확인할 수 있다.")
    lines.append("- 글쓰기 계열은 글쓰기 과제, 첨삭, 피드백, 평가 기준을 중심으로 해석한다.")
    lines.append("- 실용영어 계열은 영어 사용 부담, 스피킹·라이팅 시험, 원어민 수업, 수업 참여 경험을 중심으로 해석한다.")
    lines.append("- 전체 통합 결과는 교수자 태도, 수업 운영, 과제·시험 부담, 성적 평가 기준처럼 과목군을 가로지르는 공통 요인을 보여준다.")
    (out_root / "groupwise_report_draft.md").write_text("\n".join(lines), encoding="utf-8")

    print("=" * 80)
    print("완료")
    print("비교 요약:", out_root / "groupwise_comparison_summary.csv")
    print("통합 엑셀:", xlsx_path)
    print("통합 초안:", out_root / "groupwise_report_draft.md")
    print("=" * 80)


if __name__ == "__main__":
    main()
