# -*- coding: utf-8 -*-
"""
Everytime lecture review ABSA report analysis script

목적
- Colab GPU 모델 실행 결과와 로컬 후처리 결과를 바탕으로
  보고서 제출용 결론, 표, 그래프, 요약 문장을 자동 생성한다.

실행 위치
    C:\every_time

권장 실행 순서
    1) python scripts\run_segment_absa_pipeline.py --post-colab-only
    2) python scripts\12_generate_report_analysis.py

출력 위치
    C:\every_time\outputs\report_analysis
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ============================================================
# 기본 유틸
# ============================================================

RATING_ORDER = [
    "VERY_HIGH_SATISFACTION",
    "HIGH_SATISFACTION",
    "MID_SATISFACTION",
    "LOW_SATISFACTION",
    "VERY_LOW_SATISFACTION",
    "RATING_UNKNOWN",
]

POSITIVE_LABELS = {"POSITIVE", "긍정", "LABEL_1", "1", "positive", "pos"}
NEGATIVE_LABELS = {"NEGATIVE", "부정", "LABEL_0", "0", "negative", "neg"}
HIGH_RATING = {"VERY_HIGH_SATISFACTION", "HIGH_SATISFACTION"}
LOW_RATING = {"LOW_SATISFACTION", "VERY_LOW_SATISFACTION"}


def safe_read_csv(path: Path) -> pd.DataFrame:
    """CSV 인코딩을 자동으로 시도해서 읽는다."""
    path = Path(path)
    last_error = None

    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_error = e

    raise RuntimeError(f"CSV를 읽지 못했습니다: {path}\n마지막 오류: {last_error}")


def clean_text(value, max_len: Optional[int] = None) -> str:
    """보고서/CSV 저장용 텍스트 정리."""
    if pd.isna(value):
        return ""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if max_len is not None and len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text


def safe_to_csv(df: pd.DataFrame, path: Path) -> None:
    """엑셀에서 한글이 덜 깨지도록 utf-8-sig + 전체 따옴표로 저장."""
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


def find_first_existing(paths: List[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def standardize_cluster_id(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "aspect_cluster_id" not in out.columns and "cluster_id" in out.columns:
        out["aspect_cluster_id"] = out["cluster_id"]
    if "cluster_id" not in out.columns and "aspect_cluster_id" in out.columns:
        out["cluster_id"] = out["aspect_cluster_id"]
    return out


def standardize_sentiment_label(value) -> str:
    if pd.isna(value):
        return "UNKNOWN"

    raw = str(value).strip()
    upper = raw.upper()
    lower = raw.lower()

    if upper in POSITIVE_LABELS or lower in POSITIVE_LABELS:
        return "POSITIVE"
    if upper in NEGATIVE_LABELS or lower in NEGATIVE_LABELS:
        return "NEGATIVE"

    if "positive" in lower or "긍정" in raw:
        return "POSITIVE"
    if "negative" in lower or "부정" in raw:
        return "NEGATIVE"

    # KOTE/KLUE 다중감정은 여기서는 별도 감정으로 보존
    return raw if raw else "UNKNOWN"


def infer_rating_signal_from_value(value) -> str:
    try:
        rating = float(value)
    except Exception:
        return "RATING_UNKNOWN"

    if rating <= 0 or math.isnan(rating):
        return "RATING_UNKNOWN"
    if rating >= 4.5:
        return "VERY_HIGH_SATISFACTION"
    if rating >= 4.0:
        return "HIGH_SATISFACTION"
    if rating >= 3.0:
        return "MID_SATISFACTION"
    if rating >= 2.0:
        return "LOW_SATISFACTION"
    return "VERY_LOW_SATISFACTION"


def rating_rank(signal: str) -> int:
    try:
        return RATING_ORDER.index(signal)
    except ValueError:
        return len(RATING_ORDER)


def top_join(series: pd.Series, n: int = 3) -> str:
    values = (
        series.dropna()
        .astype(str)
        .map(clean_text)
        .loc[lambda s: s.str.len() > 0]
        .value_counts()
        .head(n)
        .index
        .tolist()
    )
    return ", ".join(values)


def pct(num: float, den: float) -> float:
    if den == 0 or pd.isna(den):
        return 0.0
    return round(float(num) / float(den) * 100, 2)


# ============================================================
# 데이터 로드
# ============================================================

def load_analysis_data(root: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """후처리 결과가 있으면 우선 사용하고, 없으면 Colab 결과를 직접 병합한다."""
    outputs = root / "outputs"

    merged_path = find_first_existing([
        outputs / "sentiment" / "segment_aspect_sentiment_merged.csv",
        outputs / "colab_results" / "segment_aspect_sentiment_merged.csv",
    ])

    keyword_path = find_first_existing([
        outputs / "aspects" / "aspect_cluster_keywords.csv",
        outputs / "colab_results" / "aspect_cluster_keywords.csv",
    ])

    rep_path = find_first_existing([
        outputs / "aspects" / "aspect_representative_segments.csv",
        outputs / "colab_results" / "aspect_representative_segments.csv",
    ])

    if merged_path:
        print(f"[LOAD] merged segment result: {merged_path}")
        segments = safe_read_csv(merged_path)
    else:
        aspect_path = find_first_existing([
            outputs / "aspects" / "segment_aspect_clusters.csv",
            outputs / "colab_results" / "segment_embedding_clusters.csv",
        ])
        sentiment_path = find_first_existing([
            outputs / "sentiment" / "segment_sentiment_binary_primary.csv",
            outputs / "colab_results" / "segment_sentiment_binary_primary.csv",
        ])

        if not aspect_path or not sentiment_path:
            raise FileNotFoundError(
                "분석에 필요한 파일을 찾지 못했습니다.\n"
                "먼저 다음 명령을 실행했는지 확인하세요.\n"
                "python scripts\\run_segment_absa_pipeline.py --post-colab-only\n\n"
                "또는 아래 파일들이 있어야 합니다.\n"
                "- outputs/colab_results/segment_embedding_clusters.csv\n"
                "- outputs/colab_results/segment_sentiment_binary_primary.csv"
            )

        print(f"[LOAD] aspect clusters: {aspect_path}")
        print(f"[LOAD] sentiment primary: {sentiment_path}")

        aspect = safe_read_csv(aspect_path)
        sentiment = safe_read_csv(sentiment_path)

        # 중복 컬럼 최소화
        sentiment_keep = [
            c for c in sentiment.columns
            if c in {
                "segment_id",
                "predicted_label_standard",
                "predicted_label_original",
                "predicted_score",
                "model_name",
                "hf_model",
                "task",
                "all_scores_json",
                "run_status",
                "error_message",
            }
        ]

        if "segment_id" not in aspect.columns or "segment_id" not in sentiment.columns:
            raise KeyError("aspect/sentiment 결과에 segment_id 컬럼이 필요합니다.")

        segments = aspect.merge(
            sentiment[sentiment_keep],
            on="segment_id",
            how="left",
        )

    keywords = safe_read_csv(keyword_path) if keyword_path else pd.DataFrame()
    reps = safe_read_csv(rep_path) if rep_path else pd.DataFrame()

    segments = standardize_cluster_id(segments)
    keywords = standardize_cluster_id(keywords)
    reps = standardize_cluster_id(reps)

    return segments, keywords, reps


def prepare_segments(segments: pd.DataFrame) -> pd.DataFrame:
    df = segments.copy()

    # 필수/주요 컬럼 보정
    if "segment_id" not in df.columns:
        df["segment_id"] = [f"S{i:07d}" for i in range(len(df))]

    if "review_id" not in df.columns:
        df["review_id"] = df["segment_id"]

    if "segment_text" not in df.columns and "segment_text_for_model" in df.columns:
        df["segment_text"] = df["segment_text_for_model"]

    if "segment_text_for_model" not in df.columns and "segment_text" in df.columns:
        df["segment_text_for_model"] = df["segment_text"]

    if "predicted_label_standard" not in df.columns:
        df["predicted_label_standard"] = "UNKNOWN"

    if "predicted_score" not in df.columns:
        df["predicted_score"] = np.nan

    if "review_rating" not in df.columns:
        df["review_rating"] = np.nan

    if "rating_satisfaction_signal" not in df.columns:
        df["rating_satisfaction_signal"] = df["review_rating"].apply(infer_rating_signal_from_value)

    if "course_name" not in df.columns:
        df["course_name"] = ""

    if "professor_id" not in df.columns:
        df["professor_id"] = ""

    df["sentiment_bin"] = df["predicted_label_standard"].apply(standardize_sentiment_label)
    df["review_rating"] = pd.to_numeric(df["review_rating"], errors="coerce")
    df["predicted_score"] = pd.to_numeric(df["predicted_score"], errors="coerce")

    df["segment_text"] = df["segment_text"].apply(clean_text)
    df["segment_text_for_model"] = df["segment_text_for_model"].apply(clean_text)
    df["rating_satisfaction_signal"] = df["rating_satisfaction_signal"].fillna("RATING_UNKNOWN").astype(str)

    return df


# ============================================================
# 분석 테이블 생성
# ============================================================

def build_overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    total_segments = len(df)
    total_reviews = df["review_id"].nunique()
    total_courses = df["course_name"].nunique() if "course_name" in df.columns else 0
    total_clusters = df["aspect_cluster_id"].nunique() if "aspect_cluster_id" in df.columns else 0

    positive = int((df["sentiment_bin"] == "POSITIVE").sum())
    negative = int((df["sentiment_bin"] == "NEGATIVE").sum())
    unknown = int((~df["sentiment_bin"].isin(["POSITIVE", "NEGATIVE"])).sum())

    high_rating_segments = int(df["rating_satisfaction_signal"].isin(HIGH_RATING).sum())
    low_rating_segments = int(df["rating_satisfaction_signal"].isin(LOW_RATING).sum())

    rows = [
        ("분석 segment 수", total_segments),
        ("분석 review 수", total_reviews),
        ("강의 수", total_courses),
        ("평가 요인 cluster 수", total_clusters),
        ("긍정 segment 수", positive),
        ("부정 segment 수", negative),
        ("기타/미확인 감정 segment 수", unknown),
        ("긍정 segment 비율(%)", pct(positive, total_segments)),
        ("부정 segment 비율(%)", pct(negative, total_segments)),
        ("높은 만족도 segment 수", high_rating_segments),
        ("낮은 만족도 segment 수", low_rating_segments),
        ("평균 별점", round(float(df["review_rating"].dropna().mean()), 3) if df["review_rating"].notna().any() else ""),
    ]

    return pd.DataFrame(rows, columns=["지표", "값"])


def build_review_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for review_id, group in df.groupby("review_id"):
        sentiments = set(group["sentiment_bin"].astype(str))
        rating_signal = (
            group["rating_satisfaction_signal"]
            .dropna()
            .astype(str)
            .sort_values(key=lambda s: s.map(rating_rank))
            .iloc[0]
            if group["rating_satisfaction_signal"].notna().any()
            else "RATING_UNKNOWN"
        )

        pos_segments = group.loc[group["sentiment_bin"] == "POSITIVE", "segment_text"].map(lambda x: clean_text(x, 140)).tolist()
        neg_segments = group.loc[group["sentiment_bin"] == "NEGATIVE", "segment_text"].map(lambda x: clean_text(x, 140)).tolist()

        rows.append({
            "review_id": review_id,
            "course_name": top_join(group["course_name"], 1),
            "professor_id": top_join(group["professor_id"], 1),
            "review_rating": group["review_rating"].dropna().mean() if group["review_rating"].notna().any() else np.nan,
            "rating_satisfaction_signal": rating_signal,
            "segment_count": len(group),
            "positive_segment_count": int((group["sentiment_bin"] == "POSITIVE").sum()),
            "negative_segment_count": int((group["sentiment_bin"] == "NEGATIVE").sum()),
            "mixed_review_flag": ("POSITIVE" in sentiments and "NEGATIVE" in sentiments),
            "high_rating_negative_segment_flag": rating_signal in HIGH_RATING and "NEGATIVE" in sentiments,
            "low_rating_positive_segment_flag": rating_signal in LOW_RATING and "POSITIVE" in sentiments,
            "positive_segments_preview": " | ".join(pos_segments[:3]),
            "negative_segments_preview": " | ".join(neg_segments[:3]),
        })

    return pd.DataFrame(rows)


def build_aspect_summary(df: pd.DataFrame, keywords: pd.DataFrame) -> pd.DataFrame:
    keyword_map: Dict[str, str] = {}

    if not keywords.empty:
        for _, row in keywords.iterrows():
            cid = str(row.get("aspect_cluster_id", row.get("cluster_id", "")))
            keyword_map[cid] = clean_text(row.get("top_keywords", ""))

    rows = []

    for cid, group in df.groupby("aspect_cluster_id"):
        cid_str = str(cid)
        n = len(group)
        pos = int((group["sentiment_bin"] == "POSITIVE").sum())
        neg = int((group["sentiment_bin"] == "NEGATIVE").sum())
        other = n - pos - neg

        high_neg = int(
            (
                group["rating_satisfaction_signal"].isin(HIGH_RATING)
                & (group["sentiment_bin"] == "NEGATIVE")
            ).sum()
        )
        low_pos = int(
            (
                group["rating_satisfaction_signal"].isin(LOW_RATING)
                & (group["sentiment_bin"] == "POSITIVE")
            ).sum()
        )

        rating_dist = (
            group["rating_satisfaction_signal"]
            .fillna("RATING_UNKNOWN")
            .astype(str)
            .value_counts()
            .to_dict()
        )

        rows.append({
            "aspect_cluster_id": cid,
            "top_keywords": keyword_map.get(cid_str, ""),
            "segment_count": n,
            "review_count": group["review_id"].nunique(),
            "course_count": group["course_name"].nunique() if "course_name" in group.columns else 0,
            "positive_count": pos,
            "negative_count": neg,
            "other_sentiment_count": other,
            "positive_ratio": round(pos / n, 4) if n else 0,
            "negative_ratio": round(neg / n, 4) if n else 0,
            "other_ratio": round(other / n, 4) if n else 0,
            "positive_ratio_percent": pct(pos, n),
            "negative_ratio_percent": pct(neg, n),
            "high_rating_negative_count": high_neg,
            "high_rating_negative_ratio_percent": pct(high_neg, n),
            "low_rating_positive_count": low_pos,
            "low_rating_positive_ratio_percent": pct(low_pos, n),
            "avg_review_rating": round(float(group["review_rating"].dropna().mean()), 3) if group["review_rating"].notna().any() else np.nan,
            "avg_predicted_score": round(float(group["predicted_score"].dropna().mean()), 4) if group["predicted_score"].notna().any() else np.nan,
            "rating_group_distribution_json": json.dumps(rating_dist, ensure_ascii=False),
            "top_courses": top_join(group["course_name"], 3),
            "top_professor_ids": top_join(group["professor_id"], 3),
        })

    summary = pd.DataFrame(rows)

    if summary.empty:
        return summary

    summary = summary.sort_values(
        by=["segment_count", "positive_ratio", "negative_ratio"],
        ascending=[False, False, False],
    )

    return summary


def build_factor_tables(aspect_summary: pd.DataFrame, min_count: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if aspect_summary.empty:
        return aspect_summary.copy(), aspect_summary.copy()

    valid = aspect_summary[
        (aspect_summary["segment_count"] >= min_count)
        & (aspect_summary["aspect_cluster_id"].astype(str) != "-1")
    ].copy()

    if valid.empty:
        valid = aspect_summary[aspect_summary["segment_count"] >= max(1, min_count // 2)].copy()

    good = valid[
        (valid["positive_ratio"] >= 0.50)
        | (valid["positive_count"] >= valid["negative_count"])
    ].copy()

    good = good.sort_values(
        by=["positive_ratio", "positive_count", "segment_count", "avg_review_rating"],
        ascending=[False, False, False, False],
    )

    dissatisfaction = valid[
        (valid["negative_ratio"] >= 0.35)
        | (valid["high_rating_negative_count"] > 0)
    ].copy()

    dissatisfaction = dissatisfaction.sort_values(
        by=["negative_ratio", "negative_count", "high_rating_negative_count", "segment_count"],
        ascending=[False, False, False, False],
    )

    return good, dissatisfaction


def build_representative_sentences(df: pd.DataFrame, top_aspects: pd.DataFrame, sentiment: str, top_n_per_aspect: int = 3) -> pd.DataFrame:
    rows = []

    if top_aspects.empty:
        return pd.DataFrame()

    target_cids = top_aspects["aspect_cluster_id"].head(10).tolist()

    for cid in target_cids:
        group = df[
            (df["aspect_cluster_id"].astype(str) == str(cid))
            & (df["sentiment_bin"] == sentiment)
        ].copy()

        if group.empty:
            continue

        group = group.sort_values(
            by=["predicted_score", "review_rating"],
            ascending=[False, False],
            na_position="last",
        )

        for rank, (_, row) in enumerate(group.head(top_n_per_aspect).iterrows(), start=1):
            rows.append({
                "aspect_cluster_id": cid,
                "rank": rank,
                "sentiment": sentiment,
                "course_name": row.get("course_name", ""),
                "professor_id": row.get("professor_id", ""),
                "review_rating": row.get("review_rating", ""),
                "rating_satisfaction_signal": row.get("rating_satisfaction_signal", ""),
                "predicted_score": row.get("predicted_score", ""),
                "segment_text": clean_text(row.get("segment_text", ""), 220),
            })

    return pd.DataFrame(rows)


def build_rating_sentiment_crosstab(df: pd.DataFrame) -> pd.DataFrame:
    cross = pd.crosstab(
        df["rating_satisfaction_signal"],
        df["sentiment_bin"],
        margins=True,
    )

    # 보기 좋은 순서
    ordered_index = [x for x in RATING_ORDER if x in cross.index] + [
        x for x in cross.index if x not in RATING_ORDER and x != "All"
    ]
    if "All" in cross.index:
        ordered_index.append("All")

    cross = cross.loc[ordered_index]
    return cross.reset_index()


# ============================================================
# 그래프 생성
# ============================================================

def setup_matplotlib():
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # Windows 로컬 기준: 맑은 고딕 우선
    candidates = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
    available = {f.name for f in fm.fontManager.ttflist}

    for font in candidates:
        if font in available:
            plt.rcParams["font.family"] = font
            break

    plt.rcParams["axes.unicode_minus"] = False
    return plt


def make_bar_chart(df: pd.DataFrame, label_col: str, value_col: str, title: str, output_path: Path, top_n: int = 10) -> None:
    if df.empty or label_col not in df.columns or value_col not in df.columns:
        return

    plt = setup_matplotlib()

    plot_df = df.copy().head(top_n)
    if plot_df.empty:
        return

    labels = plot_df[label_col].fillna("").astype(str).map(lambda x: clean_text(x, 28))
    values = pd.to_numeric(plot_df[value_col], errors="coerce").fillna(0)

    fig = plt.figure(figsize=(10, max(5, len(plot_df) * 0.45)))
    ax = fig.gca()
    ax.barh(range(len(plot_df)), values)
    ax.set_yticks(range(len(plot_df)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel(value_col)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def make_sentiment_distribution_chart(df: pd.DataFrame, output_path: Path) -> None:
    if df.empty:
        return

    plt = setup_matplotlib()

    counts = df["sentiment_bin"].fillna("UNKNOWN").astype(str).value_counts()

    fig = plt.figure(figsize=(8, 5))
    ax = fig.gca()
    ax.bar(counts.index.tolist(), counts.values.tolist())
    ax.set_title("문장/절 단위 감정분포")
    ax.set_xlabel("감정")
    ax.set_ylabel("segment 수")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def make_rating_sentiment_chart(crosstab: pd.DataFrame, output_path: Path) -> None:
    if crosstab.empty:
        return

    plt = setup_matplotlib()

    df = crosstab.copy()
    key_col = df.columns[0]
    df = df[df[key_col] != "All"].copy()

    if df.empty:
        return

    # crosstab 결과에 POSITIVE/NEGATIVE 컬럼이 없을 수도 있다.
    # df.get("POSITIVE", 0)을 쓰면 컬럼이 없을 때 int 0이 반환되어
    # fillna() 호출에서 AttributeError가 발생한다.
    if "POSITIVE" in df.columns:
        positive = pd.to_numeric(df["POSITIVE"], errors="coerce").fillna(0)
    else:
        positive = pd.Series([0] * len(df), index=df.index, dtype="float64")

    if "NEGATIVE" in df.columns:
        negative = pd.to_numeric(df["NEGATIVE"], errors="coerce").fillna(0)
    else:
        negative = pd.Series([0] * len(df), index=df.index, dtype="float64")

    x = np.arange(len(df))

    fig = plt.figure(figsize=(10, 5))
    ax = fig.gca()
    ax.bar(x - 0.2, positive, width=0.4, label="POSITIVE")
    ax.bar(x + 0.2, negative, width=0.4, label="NEGATIVE")
    ax.set_xticks(x)
    ax.set_xticklabels(df[key_col].astype(str).tolist(), rotation=25, ha="right")
    ax.set_title("별점 만족도 신호별 감정분포")
    ax.set_xlabel("rating_satisfaction_signal")
    ax.set_ylabel("segment 수")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 보고서 문장 생성
# ============================================================

def keywords_or_cluster(row: pd.Series) -> str:
    kw = clean_text(row.get("top_keywords", ""))
    if kw:
        return kw
    return f"cluster {row.get('aspect_cluster_id', '')}"


def build_report_markdown(
    overall: pd.DataFrame,
    aspect_summary: pd.DataFrame,
    good: pd.DataFrame,
    dissatisfaction: pd.DataFrame,
    review_summary: pd.DataFrame,
    rating_cross: pd.DataFrame,
    out_dir: Path,
    top_n: int,
) -> str:
    def get_metric(name: str, default=""):
        found = overall.loc[overall["지표"] == name, "값"]
        return found.iloc[0] if len(found) else default

    total_segments = get_metric("분석 segment 수")
    total_reviews = get_metric("분석 review 수")
    total_clusters = get_metric("평가 요인 cluster 수")
    pos_ratio = get_metric("긍정 segment 비율(%)")
    neg_ratio = get_metric("부정 segment 비율(%)")
    avg_rating = get_metric("평균 별점")

    mixed_count = int(review_summary["mixed_review_flag"].sum()) if not review_summary.empty else 0
    high_neg_count = int(review_summary["high_rating_negative_segment_flag"].sum()) if not review_summary.empty else 0
    low_pos_count = int(review_summary["low_rating_positive_segment_flag"].sum()) if not review_summary.empty else 0

    review_count = len(review_summary)
    mixed_ratio = pct(mixed_count, review_count)
    high_neg_ratio = pct(high_neg_count, review_count)
    low_pos_ratio = pct(low_pos_count, review_count)

    top_good = good.head(top_n)
    top_bad = dissatisfaction.head(top_n)

    lines: List[str] = []

    lines.append("# 에브리타임 강의평 분석 결과 보고서 초안")
    lines.append("")
    lines.append("## 1. 분석 목적")
    lines.append("")
    lines.append(
        "본 분석은 에브리타임 강의평을 문장 및 절 단위로 나누고, "
        "각 문장이 어떤 평가 요인을 말하는지와 해당 요인에 대한 감정이 긍정인지 부정인지 파악하기 위해 수행하였다. "
        "별점은 문장 감정의 정답 라벨로 사용하지 않고, 리뷰 전체의 만족도를 나타내는 보조 신호로만 활용하였다."
    )
    lines.append("")
    lines.append("## 2. 분석 데이터 개요")
    lines.append("")
    lines.append(f"- 분석 문장/절 segment 수: **{total_segments}개**")
    lines.append(f"- 분석 review 수: **{total_reviews}개**")
    lines.append(f"- 평가 요인 cluster 수: **{total_clusters}개**")
    lines.append(f"- 평균 별점: **{avg_rating}**")
    lines.append(f"- 긍정 segment 비율: **{pos_ratio}%**")
    lines.append(f"- 부정 segment 비율: **{neg_ratio}%**")
    lines.append("")
    lines.append("## 3. 핵심 분석 결과")
    lines.append("")
    lines.append("### 3-1. 좋은 강의 요인")
    lines.append("")

    if top_good.empty:
        lines.append("- 충분한 segment 수를 가진 긍정 평가 요인이 확인되지 않았다.")
    else:
        for i, (_, row) in enumerate(top_good.iterrows(), start=1):
            lines.append(
                f"{i}. **{keywords_or_cluster(row)}** "
                f"(긍정 비율 {row.get('positive_ratio_percent', '')}%, "
                f"segment {row.get('segment_count', '')}개, "
                f"평균 별점 {row.get('avg_review_rating', '')})"
            )

    lines.append("")
    lines.append("### 3-2. 불만 요인")
    lines.append("")

    if top_bad.empty:
        lines.append("- 충분한 segment 수를 가진 부정 평가 요인이 확인되지 않았다.")
    else:
        for i, (_, row) in enumerate(top_bad.iterrows(), start=1):
            lines.append(
                f"{i}. **{keywords_or_cluster(row)}** "
                f"(부정 비율 {row.get('negative_ratio_percent', '')}%, "
                f"segment {row.get('segment_count', '')}개, "
                f"높은 별점 내 부정 segment {row.get('high_rating_negative_count', '')}개)"
            )

    lines.append("")
    lines.append("### 3-3. 복합 감정 리뷰")
    lines.append("")
    lines.append(
        f"- 하나의 리뷰 안에 긍정 segment와 부정 segment가 함께 나타난 mixed review는 "
        f"**{mixed_count}개**로 확인되었다. 전체 리뷰 기준 비율은 **{mixed_ratio}%**이다."
    )
    lines.append(
        f"- 높은 별점 리뷰 안에서도 부정 segment가 포함된 사례는 **{high_neg_count}개**로 확인되었다."
    )
    lines.append(
        f"- 낮은 별점 리뷰 안에서도 긍정 segment가 포함된 사례는 **{low_pos_count}개**로 확인되었다."
    )
    lines.append("")
    lines.append("이 결과는 별점을 곧바로 긍정/부정 라벨로 사용하는 방식이 부정확할 수 있음을 보여준다. "
                 "따라서 본 연구처럼 리뷰를 문장/절 단위로 분리하여 측면별 감정을 분석하는 방식이 더 적절하다.")
    lines.append("")
    lines.append("## 4. 결론")
    lines.append("")
    lines.append(
        "분석 결과, 학생들의 강의 평가는 단순히 좋다 또는 나쁘다로만 나뉘지 않았다. "
        "하나의 리뷰 안에서도 교수 설명, 수업 운영, 과제 부담, 시험 난이도, 평가 방식 등 여러 요인에 대한 감정이 동시에 나타났다. "
        "따라서 강의평 분석에서는 리뷰 전체 별점보다 문장/절 단위의 세부 평가 요인을 분리해 해석하는 것이 중요하다."
    )
    lines.append("")

    if not top_good.empty:
        good_keywords = [keywords_or_cluster(row) for _, row in top_good.head(3).iterrows()]
        lines.append(
            "좋은 강의 요인은 주로 "
            f"**{', '.join(good_keywords)}** 계열의 표현에서 확인되었다. "
            "이는 학생들이 강의를 긍정적으로 평가할 때 단순한 성적 결과뿐만 아니라 "
            "수업을 이해하기 쉬웠는지, 교수자와의 상호작용이 좋았는지, 수업 운영이 명확했는지를 중요하게 본다는 점을 시사한다."
        )
        lines.append("")

    if not top_bad.empty:
        bad_keywords = [keywords_or_cluster(row) for _, row in top_bad.head(3).iterrows()]
        lines.append(
            "반면 불만 요인은 "
            f"**{', '.join(bad_keywords)}** 계열에서 많이 확인되었다. "
            "특히 높은 별점 리뷰 안에서도 부정 segment가 발견된다는 점은, "
            "전체 만족도는 높더라도 특정 요소에 대한 부담이나 불편이 함께 존재할 수 있음을 의미한다."
        )
        lines.append("")

    lines.append("## 5. 보고서 작성 시 주의점")
    lines.append("")
    lines.append("- 본 결과는 자동 감정분석 모델과 임베딩 클러스터링 결과이므로, 최종 평가 요인명은 연구자가 대표 키워드와 대표 문장을 확인한 뒤 명명해야 한다.")
    lines.append("- 별점은 문장 감정의 정답 라벨이 아니라 전체 만족도 신호로만 해석해야 한다.")
    lines.append("- 에브리타임 강의평 원문은 민감할 수 있으므로, 보고서 제출 시 교수명과 원문 노출 범위를 조절해야 한다.")
    lines.append("- 본 분석은 상관적 패턴을 보여주는 것이며, 특정 요인이 강의 만족도를 직접적으로 유발한다고 단정해서는 안 된다.")
    lines.append("")
    lines.append("## 6. 생성된 결과 파일")
    lines.append("")
    lines.append(f"- 보고서 표 모음: `{out_dir / 'report_tables.xlsx'}`")
    lines.append(f"- 전체 요약: `{out_dir / 'overall_summary.csv'}`")
    lines.append(f"- 평가 요인 요약: `{out_dir / 'aspect_summary.csv'}`")
    lines.append(f"- 좋은 강의 요인: `{out_dir / 'good_lecture_factors_report.csv'}`")
    lines.append(f"- 불만 요인: `{out_dir / 'dissatisfaction_factors_report.csv'}`")
    lines.append(f"- 대표 긍정 문장: `{out_dir / 'representative_positive_sentences.csv'}`")
    lines.append(f"- 대표 부정 문장: `{out_dir / 'representative_negative_sentences.csv'}`")
    lines.append(f"- 그래프 폴더: `{out_dir / 'figures'}`")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\every_time", help="프로젝트 루트 경로")
    parser.add_argument("--min-count", type=int, default=5, help="요인 분석에 포함할 최소 segment 수")
    parser.add_argument("--top-n", type=int, default=10, help="보고서에 표시할 상위 요인 수")
    parser.add_argument("--sentence-top-n", type=int, default=3, help="요인별 대표 문장 수")
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = root / "outputs" / "report_analysis"
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Everytime ABSA 보고서 분석 코드")
    print("ROOT:", root)
    print("OUT :", out_dir)
    print("=" * 80)

    segments_raw, keywords, reps = load_analysis_data(root)
    segments = prepare_segments(segments_raw)

    overall = build_overall_summary(segments)
    review_summary = build_review_summary(segments)
    aspect_summary = build_aspect_summary(segments, keywords)
    good, dissatisfaction = build_factor_tables(aspect_summary, min_count=args.min_count)
    rating_cross = build_rating_sentiment_crosstab(segments)

    rep_pos = build_representative_sentences(
        segments,
        good,
        sentiment="POSITIVE",
        top_n_per_aspect=args.sentence_top_n,
    )
    rep_neg = build_representative_sentences(
        segments,
        dissatisfaction,
        sentiment="NEGATIVE",
        top_n_per_aspect=args.sentence_top_n,
    )

    # 추가 사례 테이블
    high_rating_negative_segments = segments[
        segments["rating_satisfaction_signal"].isin(HIGH_RATING)
        & (segments["sentiment_bin"] == "NEGATIVE")
    ].copy()

    low_rating_positive_segments = segments[
        segments["rating_satisfaction_signal"].isin(LOW_RATING)
        & (segments["sentiment_bin"] == "POSITIVE")
    ].copy()

    # 보기용 컬럼 제한
    case_cols = [
        "segment_id",
        "review_id",
        "aspect_cluster_id",
        "course_name",
        "professor_id",
        "review_rating",
        "rating_satisfaction_signal",
        "predicted_label_standard",
        "predicted_score",
        "segment_text",
    ]
    case_cols = [c for c in case_cols if c in segments.columns]

    # 저장
    safe_to_csv(overall, out_dir / "overall_summary.csv")
    safe_to_csv(review_summary, out_dir / "review_level_summary.csv")
    safe_to_csv(aspect_summary, out_dir / "aspect_summary.csv")
    safe_to_csv(good, out_dir / "good_lecture_factors_report.csv")
    safe_to_csv(dissatisfaction, out_dir / "dissatisfaction_factors_report.csv")
    safe_to_csv(rating_cross, out_dir / "rating_signal_sentiment_crosstab_report.csv")
    safe_to_csv(rep_pos, out_dir / "representative_positive_sentences.csv")
    safe_to_csv(rep_neg, out_dir / "representative_negative_sentences.csv")
    safe_to_csv(high_rating_negative_segments[case_cols], out_dir / "high_rating_negative_segments_for_report.csv")
    safe_to_csv(low_rating_positive_segments[case_cols], out_dir / "low_rating_positive_segments_for_report.csv")

    # 그래프
    make_sentiment_distribution_chart(segments, fig_dir / "sentiment_distribution.png")
    make_rating_sentiment_chart(rating_cross, fig_dir / "rating_signal_sentiment_distribution.png")

    good_chart_df = good.copy()
    good_chart_df["chart_label"] = good_chart_df["top_keywords"].fillna("").astype(str)
    make_bar_chart(
        good_chart_df,
        label_col="chart_label",
        value_col="positive_ratio_percent",
        title="좋은 강의 요인 상위 항목",
        output_path=fig_dir / "good_lecture_factors.png",
        top_n=args.top_n,
    )

    bad_chart_df = dissatisfaction.copy()
    bad_chart_df["chart_label"] = bad_chart_df["top_keywords"].fillna("").astype(str)
    make_bar_chart(
        bad_chart_df,
        label_col="chart_label",
        value_col="negative_ratio_percent",
        title="불만 요인 상위 항목",
        output_path=fig_dir / "dissatisfaction_factors.png",
        top_n=args.top_n,
    )

    # Excel 통합 저장
    excel_path = out_dir / "report_tables.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        overall.to_excel(writer, sheet_name="overall_summary", index=False)
        aspect_summary.head(200).to_excel(writer, sheet_name="aspect_summary", index=False)
        good.head(100).to_excel(writer, sheet_name="good_factors", index=False)
        dissatisfaction.head(100).to_excel(writer, sheet_name="bad_factors", index=False)
        rating_cross.to_excel(writer, sheet_name="rating_sentiment", index=False)
        review_summary.head(5000).to_excel(writer, sheet_name="review_summary", index=False)
        rep_pos.head(1000).to_excel(writer, sheet_name="positive_sentences", index=False)
        rep_neg.head(1000).to_excel(writer, sheet_name="negative_sentences", index=False)
        high_rating_negative_segments[case_cols].head(1000).to_excel(writer, sheet_name="high_rating_negative", index=False)
        low_rating_positive_segments[case_cols].head(1000).to_excel(writer, sheet_name="low_rating_positive", index=False)

    # Markdown 보고서 초안
    md = build_report_markdown(
        overall=overall,
        aspect_summary=aspect_summary,
        good=good,
        dissatisfaction=dissatisfaction,
        review_summary=review_summary,
        rating_cross=rating_cross,
        out_dir=out_dir,
        top_n=args.top_n,
    )

    md_path = out_dir / "report_conclusion_draft.md"
    md_path.write_text(md, encoding="utf-8")

    # 콘솔 요약
    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)
    print("보고서 초안:", md_path)
    print("통합 Excel:", excel_path)
    print("그래프 폴더:", fig_dir)
    print("\n상위 좋은 강의 요인")
    if not good.empty:
        print(good[["aspect_cluster_id", "top_keywords", "segment_count", "positive_ratio_percent"]].head(args.top_n).to_string(index=False))
    else:
        print("없음")

    print("\n상위 불만 요인")
    if not dissatisfaction.empty:
        print(dissatisfaction[["aspect_cluster_id", "top_keywords", "segment_count", "negative_ratio_percent", "high_rating_negative_count"]].head(args.top_n).to_string(index=False))
    else:
        print("없음")

    print("\n다음 파일을 먼저 열어보세요:")
    print(f"1) {excel_path}")
    print(f"2) {md_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
