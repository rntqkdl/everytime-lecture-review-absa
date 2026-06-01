from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.insight_extraction import build_factor_tables
from src.io_utils import empty_csv, ensure_output_dirs, load_config, read_csv_safely, write_csv
from src.sentiment_utils import add_standard_sentiment


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    sentiment_dir = Path(config["output_dirs"]["sentiment"])
    aspects_dir = Path(config["output_dirs"]["aspects"])
    insights_dir = Path(config["output_dirs"]["insights"])

    merged_path = sentiment_dir / "segment_aspect_sentiment_merged.csv"
    if not merged_path.exists():
        print(f"입력 파일이 없습니다: {merged_path}")
        for name in [
            "good_lecture_factors.csv",
            "dissatisfaction_factors.csv",
            "good_lecture_representative_sentences.csv",
            "dissatisfaction_representative_sentences.csv",
            "course_factor_summary.csv",
        ]:
            empty_csv(insights_dir / name, [])
        return

    merged = add_standard_sentiment(read_csv_safely(merged_path))
    keyword_candidates = [
        aspects_dir / "aspect_cluster_keywords.csv",
        aspects_dir / "cpu_baseline_topic_keywords.csv",
    ]
    keywords = None
    for keyword_path in keyword_candidates:
        if keyword_path.exists():
            keywords = read_csv_safely(keyword_path)
            break
    if keywords is None:
        keywords = pd.DataFrame()
    settings = config.get("insight_extraction", {})
    good, bad, good_rep, bad_rep, course_summary = build_factor_tables(
        merged,
        keywords,
        min_cluster_size=int(settings.get("min_cluster_size_for_insight", 10)),
        good_positive_min=float(settings.get("good_factor_positive_ratio_min", 0.6)),
        bad_negative_min=float(settings.get("dissatisfaction_negative_ratio_min", 0.5)),
        representative_top_n=int(settings.get("representative_sentence_top_n", 5)),
    )

    write_csv(good, insights_dir / "good_lecture_factors.csv")
    write_csv(bad, insights_dir / "dissatisfaction_factors.csv")
    write_csv(good_rep, insights_dir / "good_lecture_representative_sentences.csv")
    write_csv(bad_rep, insights_dir / "dissatisfaction_representative_sentences.csv")
    write_csv(course_summary, insights_dir / "course_factor_summary.csv")
    print(f"저장: good_lecture_factors.csv ({len(good)}행)")
    print(f"저장: dissatisfaction_factors.csv ({len(bad)}행)")


if __name__ == "__main__":
    main()
