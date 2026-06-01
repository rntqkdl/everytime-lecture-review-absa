from __future__ import annotations

import pandas as pd

from src.sentiment_models import safe_json_dumps


HIGH_SIGNALS = {"VERY_HIGH_SATISFACTION", "HIGH_SATISFACTION"}


def _cluster_label_column(df: pd.DataFrame) -> str:
    for column in ["cluster_id", "aspect_cluster_id", "cpu_baseline_topic_id"]:
        if column in df.columns:
            return column
    return ""


def _keyword_lookup(keywords: pd.DataFrame) -> dict:
    if keywords.empty:
        return {}
    cluster_col = _cluster_label_column(keywords) or ("topic_id" if "topic_id" in keywords.columns else "")
    if not cluster_col:
        return {}
    keyword_col = "keyword" if "keyword" in keywords.columns else "top_keywords"
    if keyword_col not in keywords.columns:
        return {}
    lookup: dict = {}
    for cluster_id, group in keywords.groupby(cluster_col, dropna=False):
        if "rank" in group.columns:
            group = group.sort_values("rank")
        lookup[cluster_id] = ", ".join(group[keyword_col].dropna().astype(str).head(15).tolist())
    return lookup


def _ratio(series: pd.Series, value: str) -> float:
    if series.empty:
        return 0.0
    return float((series == value).mean())


def build_factor_tables(
    merged: pd.DataFrame,
    keywords: pd.DataFrame,
    min_cluster_size: int = 10,
    good_positive_min: float = 0.6,
    bad_negative_min: float = 0.5,
    representative_top_n: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cluster_col = _cluster_label_column(merged)
    if merged.empty or not cluster_col or "segment_sentiment_label" not in merged.columns:
        empty = pd.DataFrame()
        return empty, empty, empty, empty, empty

    keyword_map = _keyword_lookup(keywords)
    rows: list[dict] = []
    good_rep_rows: list[dict] = []
    bad_rep_rows: list[dict] = []

    for cluster_id, group in merged.groupby(cluster_col, dropna=False):
        segment_count = len(group)
        if segment_count < min_cluster_size:
            continue
        sentiment_counts = group["segment_sentiment_label"].value_counts(normalize=True)
        positive_ratio = float(sentiment_counts.get("POSITIVE", 0.0))
        negative_ratio = float(sentiment_counts.get("NEGATIVE", 0.0))
        neutral_ratio = float(sentiment_counts.get("NEUTRAL", 0.0))
        unknown_ratio = float(sentiment_counts.get("UNKNOWN", 0.0))
        avg_rating = pd.to_numeric(group.get("review_rating"), errors="coerce").mean()
        representative = group.drop_duplicates("segment_text").head(representative_top_n)
        related_courses = group["course_name"].dropna().astype(str).value_counts().head(5).index.tolist() if "course_name" in group.columns else []
        rating_distribution = (
            group["rating_satisfaction_signal"].dropna().astype(str).value_counts(normalize=True).round(4).to_dict()
            if "rating_satisfaction_signal" in group.columns
            else {}
        )
        high_rating_share = (
            group["rating_satisfaction_signal"].dropna().astype(str).isin(HIGH_SIGNALS).mean()
            if "rating_satisfaction_signal" in group.columns
            else 0.0
        )
        high_rating_negative_count = int(
            (
                group.get("rating_satisfaction_signal", pd.Series(index=group.index, dtype=str)).isin(HIGH_SIGNALS)
                & (group["segment_sentiment_label"] == "NEGATIVE")
            ).sum()
        )
        keywords_text = keyword_map.get(cluster_id, "")
        hint = keywords_text or "대표 segment를 보고 cluster 이름을 해석하세요."

        base = {
            "aspect_cluster_id": cluster_id,
            "aspect_cluster_keywords": keywords_text,
            "positive_ratio": positive_ratio,
            "negative_ratio": negative_ratio,
            "neutral_ratio": neutral_ratio,
            "unknown_ratio": unknown_ratio,
            "avg_review_rating": float(avg_rating) if pd.notna(avg_rating) else 0.0,
            "rating_group_distribution": safe_json_dumps(rating_distribution),
            "high_rating_share": float(high_rating_share) if pd.notna(high_rating_share) else 0.0,
            "high_rating_negative_segment_count": high_rating_negative_count,
            "segment_count": int(segment_count),
            "representative_segments": safe_json_dumps(representative["segment_text"].dropna().astype(str).tolist()),
            "related_courses": safe_json_dumps(related_courses),
            "interpretation_hint": hint,
        }
        rows.append(base)

        if positive_ratio >= good_positive_min:
            for _, rep in representative.iterrows():
                good_rep_rows.append({**base, "segment_id": rep.get("segment_id", ""), "segment_text": rep.get("segment_text", "")})
        if negative_ratio >= bad_negative_min or high_rating_negative_count > 0:
            for _, rep in representative.iterrows():
                bad_rep_rows.append({**base, "segment_id": rep.get("segment_id", ""), "segment_text": rep.get("segment_text", "")})

    factors = pd.DataFrame(rows)
    if factors.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty, empty
    good = factors[
        (factors["positive_ratio"] >= good_positive_min)
        & (factors["segment_count"] >= min_cluster_size)
    ].sort_values(["positive_ratio", "high_rating_share", "segment_count"], ascending=False)
    bad = factors[
        (factors["negative_ratio"] >= bad_negative_min)
        | (factors["high_rating_negative_segment_count"] > 0)
    ].sort_values(["negative_ratio", "high_rating_negative_segment_count", "segment_count"], ascending=False)

    course_summary = pd.DataFrame()
    if "course_group" in merged.columns:
        group_cols = ["course_group", cluster_col, "segment_sentiment_label"]
        if "rating_satisfaction_signal" in merged.columns:
            group_cols.append("rating_satisfaction_signal")
        course_summary = (
            merged.groupby(group_cols, dropna=False)
            .size()
            .reset_index(name="segment_count")
            .rename(columns={cluster_col: "aspect_cluster_id"})
        )

    return good, bad, pd.DataFrame(good_rep_rows), pd.DataFrame(bad_rep_rows), course_summary
