from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import empty_csv, ensure_output_dirs, load_config, read_csv_safely, write_csv
from src.sentiment_utils import add_standard_sentiment


HIGH_SIGNALS = {"VERY_HIGH_SATISFACTION", "HIGH_SATISFACTION"}
LOW_SIGNALS = {"LOW_SATISFACTION", "VERY_LOW_SATISFACTION"}


def summarize_factor(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "cluster_id" not in df.columns:
        return pd.DataFrame()
    summary = (
        df.groupby(["cluster_id", "segment_sentiment_label"], dropna=False)
        .size()
        .reset_index(name="segment_count")
    )
    return summary.sort_values("segment_count", ascending=False)


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    sentiment_dir = Path(config["output_dirs"]["sentiment"])
    insights_dir = Path(config["output_dirs"]["insights"])
    merged_path = sentiment_dir / "segment_aspect_sentiment_merged.csv"

    outputs = [
        "rating_signal_sentiment_crosstab.csv",
        "high_rating_negative_factor_summary.csv",
        "low_rating_positive_factor_summary.csv",
        "rating_group_mixed_review_summary.csv",
        "aspect_cluster_avg_rating.csv",
    ]
    if not merged_path.exists():
        for name in outputs:
            empty_csv(insights_dir / name, [])
        return

    merged = add_standard_sentiment(read_csv_safely(merged_path))
    if merged.empty:
        for name in outputs:
            empty_csv(insights_dir / name, [])
        return

    if {"rating_satisfaction_signal", "segment_sentiment_label"}.issubset(merged.columns):
        crosstab = (
            pd.crosstab(
                merged["rating_satisfaction_signal"],
                merged["segment_sentiment_label"],
                normalize="index",
            )
            .reset_index()
        )
    else:
        crosstab = pd.DataFrame()

    high_negative = merged[
        merged.get("rating_satisfaction_signal", pd.Series(index=merged.index, dtype=str)).isin(HIGH_SIGNALS)
        & (merged["segment_sentiment_label"] == "NEGATIVE")
    ].copy()
    low_positive = merged[
        merged.get("rating_satisfaction_signal", pd.Series(index=merged.index, dtype=str)).isin(LOW_SIGNALS)
        & (merged["segment_sentiment_label"] == "POSITIVE")
    ].copy()
    high_summary = summarize_factor(high_negative)
    low_summary = summarize_factor(low_positive)

    mixed_path = sentiment_dir / "mixed_sentiment_reviews.csv"
    mixed = read_csv_safely(mixed_path) if mixed_path.exists() else pd.DataFrame()
    if not mixed.empty and "rating_satisfaction_signal" in mixed.columns:
        mixed_summary = (
            mixed.groupby("rating_satisfaction_signal", dropna=False)
            .agg(
                mixed_review_count=("review_id", "nunique"),
                high_rating_negative_review_count=("high_rating_negative_segment_flag", lambda s: int(pd.Series(s).astype(str).str.lower().eq("true").sum())),
                low_rating_positive_review_count=("low_rating_positive_segment_flag", lambda s: int(pd.Series(s).astype(str).str.lower().eq("true").sum())),
            )
            .reset_index()
        )
    else:
        mixed_summary = pd.DataFrame()

    if "cluster_id" in merged.columns:
        avg_rating = (
            merged.groupby("cluster_id", dropna=False)
            .agg(
                avg_review_rating=("review_rating", lambda s: pd.to_numeric(s, errors="coerce").mean()),
                segment_count=("segment_id", "count"),
            )
            .reset_index()
            .sort_values("segment_count", ascending=False)
        )
    else:
        avg_rating = pd.DataFrame()

    write_csv(crosstab, insights_dir / "rating_signal_sentiment_crosstab.csv")
    write_csv(high_summary, insights_dir / "high_rating_negative_factor_summary.csv")
    write_csv(low_summary, insights_dir / "low_rating_positive_factor_summary.csv")
    write_csv(mixed_summary, insights_dir / "rating_group_mixed_review_summary.csv")
    write_csv(avg_rating, insights_dir / "aspect_cluster_avg_rating.csv")
    print(f"저장: rating_signal_sentiment_crosstab.csv ({len(crosstab)}행)")
    print(f"저장: high_rating_negative_factor_summary.csv ({len(high_summary)}행)")
    print(f"저장: low_rating_positive_factor_summary.csv ({len(low_summary)}행)")


if __name__ == "__main__":
    main()
