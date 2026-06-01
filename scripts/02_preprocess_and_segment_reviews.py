from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.anonymize import apply_professor_mapping, make_professor_mapping
from src.course_grouping import add_course_group
from src.io_utils import add_stable_id, empty_csv, ensure_output_dirs, load_config, read_csv_safely, write_csv
from src.segmentation import split_review_to_segments
from src.text_cleaning import clean_review_text


def build_segments(reviews: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows: list[dict] = []
    settings = config.get("segmentation", {})
    preprocess = config.get("preprocess", {})
    markers = settings.get("contrast_markers")
    min_len = int(preprocess.get("min_segment_length", 5))

    for _, review in reviews.iterrows():
        review_id = review.get("review_id", "")
        segments = split_review_to_segments(
            review.get("review_text_clean", ""),
            contrast_markers=markers,
            min_segment_length=min_len,
            split_sentence=bool(settings.get("split_sentence", True)),
            split_contrast_markers=bool(settings.get("split_contrast_markers", True)),
        )
        for item in segments:
            sentence_order = int(item.get("sentence_order", 0))
            segment_order = int(item.get("segment_order", 0))
            row = review.to_dict()
            row.update(item)
            row["sentence_id"] = f"{review_id}_S{sentence_order:03d}"
            row["segment_id"] = f"{review_id}_G{segment_order:03d}"
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    processed_dir = Path(config["output_dirs"]["processed"])
    input_path = processed_dir / "reviews_merged_raw_private.csv"

    if not input_path.exists():
        print(f"입력 파일이 없습니다: {input_path}")
        empty_csv(processed_dir / "reviews_preprocessed_private.csv", [])
        empty_csv(processed_dir / "review_segments_private.csv", [])
        empty_csv(processed_dir / "professor_mapping_private.csv", [])
        return

    reviews = read_csv_safely(input_path)
    if reviews.empty:
        empty_csv(processed_dir / "reviews_preprocessed_private.csv", [])
        empty_csv(processed_dir / "review_segments_private.csv", [])
        empty_csv(processed_dir / "professor_mapping_private.csv", [])
        return

    reviews = add_stable_id(reviews, "review_id", "R")
    reviews = add_course_group(reviews, "course_name")
    if "review_text" not in reviews.columns:
        reviews["review_text"] = ""
    reviews["review_text_clean"] = reviews["review_text"].fillna("").astype(str).apply(clean_review_text)
    reviews = reviews[reviews["review_text_clean"].str.len() > 0].drop_duplicates(
        subset=["lecture_id", "review_semester", "review_rating", "review_text_clean"],
        keep="first",
    )

    mapping = make_professor_mapping(reviews)
    reviews = apply_professor_mapping(reviews, mapping)
    segments = build_segments(reviews, config)

    write_csv(reviews, processed_dir / "reviews_preprocessed_private.csv")
    write_csv(segments, processed_dir / "review_segments_private.csv")
    write_csv(mapping, processed_dir / "professor_mapping_private.csv")
    print(f"저장: reviews_preprocessed_private.csv ({len(reviews)}행)")
    print(f"저장: review_segments_private.csv ({len(segments)}행)")
    print(f"저장: professor_mapping_private.csv ({len(mapping)}행)")


if __name__ == "__main__":
    main()
