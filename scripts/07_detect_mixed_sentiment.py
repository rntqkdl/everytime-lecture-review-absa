from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import empty_csv, ensure_output_dirs, load_config, read_csv_safely, write_csv
from src.sentiment_models import safe_json_dumps
from src.sentiment_utils import add_standard_sentiment


HIGH_SIGNALS = {"VERY_HIGH_SATISFACTION", "HIGH_SATISFACTION"}
LOW_SIGNALS = {"LOW_SATISFACTION", "VERY_LOW_SATISFACTION"}


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    sentiment_dir = Path(config["output_dirs"]["sentiment"])
    input_path = sentiment_dir / "segment_aspect_sentiment_merged.csv"

    output_names = [
        "mixed_sentiment_reviews.csv",
        "mixed_aspect_sentiment_cases.csv",
        "high_rating_negative_segments.csv",
        "low_rating_positive_segments.csv",
    ]
    if not input_path.exists():
        print(f"입력 파일이 없습니다: {input_path}")
        for name in output_names:
            empty_csv(sentiment_dir / name, [])
        return

    data = add_standard_sentiment(read_csv_safely(input_path))
    if data.empty or "review_id" not in data.columns:
        for name in output_names:
            empty_csv(sentiment_dir / name, [])
        return

    review_rows: list[dict] = []
    aspect_rows: list[dict] = []
    high_negative = data[
        data.get("rating_satisfaction_signal", pd.Series(index=data.index, dtype=str)).isin(HIGH_SIGNALS)
        & (data["segment_sentiment_label"] == "NEGATIVE")
    ].copy()
    low_positive = data[
        data.get("rating_satisfaction_signal", pd.Series(index=data.index, dtype=str)).isin(LOW_SIGNALS)
        & (data["segment_sentiment_label"] == "POSITIVE")
    ].copy()

    for review_id, group in data.groupby("review_id", dropna=False):
        positives = group[group["segment_sentiment_label"] == "POSITIVE"]
        negatives = group[group["segment_sentiment_label"] == "NEGATIVE"]
        mixed_review = not positives.empty and not negatives.empty
        positive_clusters = positives["cluster_id"].dropna().astype(str).unique().tolist() if "cluster_id" in positives.columns else []
        negative_clusters = negatives["cluster_id"].dropna().astype(str).unique().tolist() if "cluster_id" in negatives.columns else []
        mixed_aspect = mixed_review and bool(set(positive_clusters) ^ set(negative_clusters))
        first = group.iloc[0]
        rating_signal = first.get("rating_satisfaction_signal", "")
        high_rating_negative = rating_signal in HIGH_SIGNALS and not negatives.empty
        low_rating_positive = rating_signal in LOW_SIGNALS and not positives.empty
        if mixed_review or high_rating_negative or low_rating_positive:
            review_rows.append(
                {
                    "review_id": review_id,
                    "review_text_clean": first.get("review_text_clean", ""),
                    "course_name": first.get("course_name", ""),
                    "course_group": first.get("course_group", ""),
                    "professor_id": first.get("professor_id", ""),
                    "review_rating": first.get("review_rating", ""),
                    "rating_satisfaction_signal": rating_signal,
                    "rating_group": first.get("rating_group", ""),
                    "positive_segments": safe_json_dumps(positives["segment_text"].dropna().astype(str).head(10).tolist()),
                    "negative_segments": safe_json_dumps(negatives["segment_text"].dropna().astype(str).head(10).tolist()),
                    "positive_clusters": safe_json_dumps(positive_clusters),
                    "negative_clusters": safe_json_dumps(negative_clusters),
                    "mixed_review_flag": mixed_review,
                    "mixed_aspect_sentiment_flag": mixed_aspect,
                    "high_rating_negative_segment_flag": high_rating_negative,
                    "low_rating_positive_segment_flag": low_rating_positive,
                }
            )
        if mixed_aspect:
            for _, row in group.iterrows():
                aspect_rows.append(row.to_dict())

    write_csv(pd.DataFrame(review_rows), sentiment_dir / "mixed_sentiment_reviews.csv")
    write_csv(pd.DataFrame(aspect_rows), sentiment_dir / "mixed_aspect_sentiment_cases.csv")
    write_csv(high_negative, sentiment_dir / "high_rating_negative_segments.csv")
    write_csv(low_positive, sentiment_dir / "low_rating_positive_segments.csv")
    print(f"저장: mixed_sentiment_reviews.csv ({len(review_rows)}행)")
    print(f"저장: mixed_aspect_sentiment_cases.csv ({len(aspect_rows)}행)")
    print(f"저장: high_rating_negative_segments.csv ({len(high_negative)}행)")
    print(f"저장: low_rating_positive_segments.csv ({len(low_positive)}행)")


if __name__ == "__main__":
    main()
