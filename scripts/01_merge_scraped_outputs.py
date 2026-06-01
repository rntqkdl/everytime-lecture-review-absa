from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import ensure_output_dirs, load_config, read_csv_safely, write_csv


REVIEW_DEDUP_COLUMNS = ["lecture_id", "review_semester", "review_rating", "review_text"]


def merge_pattern(input_dirs: list[str], pattern: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for input_dir in input_dirs:
        directory = Path(input_dir)
        if not directory.exists():
            print(f"입력 폴더 없음: {directory}")
            continue
        for csv_path in sorted(directory.glob(pattern)):
            try:
                df = read_csv_safely(csv_path)
            except Exception as exc:
                print(f"CSV 읽기 실패: {csv_path} - {exc}")
                continue
            df["source_file"] = str(csv_path)
            frames.append(df)
            print(f"읽음: {csv_path} ({len(df)}행)")

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def drop_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> pd.DataFrame:
    if df.empty:
        return df
    if subset:
        existing = [column for column in subset if column in df.columns]
        if existing:
            return df.drop_duplicates(subset=existing).reset_index(drop=True)
    return df.drop_duplicates().reset_index(drop=True)


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    input_dirs = config.get("input_dirs", [])
    processed_dir = Path(config["output_dirs"]["processed"])

    reviews = merge_pattern(input_dirs, "*reviews_raw.csv")
    reviews = drop_duplicates(reviews, REVIEW_DEDUP_COLUMNS)
    if not reviews.empty and "review_id" not in reviews.columns:
        reviews.insert(0, "review_id", [f"R{idx:08d}" for idx in range(1, len(reviews) + 1)])
    write_csv(reviews, processed_dir / "reviews_merged_raw_private.csv")
    print(f"저장: reviews_merged_raw_private.csv ({len(reviews)}행)")

    merge_targets = {
        "lecture_summary_all.csv": "lecture_summary_merged_private.csv",
        "assessment_subjective_all.csv": "assessment_subjective_merged_private.csv",
        "assessment_objective_all.csv": "assessment_objective_merged_private.csv",
        "rating_distribution_all.csv": "rating_distribution_merged_private.csv",
        "review_scroll_logs_all.csv": "review_scroll_logs_merged_private.csv",
    }
    for input_name, output_name in merge_targets.items():
        merged = merge_pattern(input_dirs, input_name)
        merged = drop_duplicates(merged)
        write_csv(merged, processed_dir / output_name)
        print(f"저장: {output_name} ({len(merged)}행)")


if __name__ == "__main__":
    main()
