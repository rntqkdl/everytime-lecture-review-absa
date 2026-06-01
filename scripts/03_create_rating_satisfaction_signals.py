from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import empty_csv, ensure_output_dirs, load_config, read_csv_safely, write_csv
from src.rating_signals import add_rating_satisfaction_signals, build_rating_signal_distribution


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    processed_dir = Path(config["output_dirs"]["processed"])

    review_path = processed_dir / "reviews_preprocessed_private.csv"
    segment_path = processed_dir / "review_segments_private.csv"

    reviews = read_csv_safely(review_path) if review_path.exists() else pd.DataFrame()
    segments = read_csv_safely(segment_path) if segment_path.exists() else pd.DataFrame()

    reviews_with_signals = add_rating_satisfaction_signals(reviews) if not reviews.empty else reviews
    segments_with_signals = add_rating_satisfaction_signals(segments) if not segments.empty else segments

    if reviews_with_signals.empty:
        empty_csv(
            processed_dir / "reviews_with_rating_signals_private.csv",
            ["review_id", "review_rating", "rating_satisfaction_signal", "rating_group", "rating_value"],
        )
    else:
        write_csv(reviews_with_signals, processed_dir / "reviews_with_rating_signals_private.csv")

    if segments_with_signals.empty:
        empty_csv(
            processed_dir / "segments_with_rating_signals_private.csv",
            ["review_id", "segment_id", "review_rating", "rating_satisfaction_signal", "rating_group", "rating_value"],
        )
    else:
        write_csv(segments_with_signals, processed_dir / "segments_with_rating_signals_private.csv")

    distribution = build_rating_signal_distribution(reviews_with_signals, segments_with_signals)
    write_csv(distribution, processed_dir / "rating_signal_distribution.csv")

    print(f"저장: reviews_with_rating_signals_private.csv ({len(reviews_with_signals)}행)")
    print(f"저장: segments_with_rating_signals_private.csv ({len(segments_with_signals)}행)")
    print(f"저장: rating_signal_distribution.csv ({len(distribution)}행)")
    print("주의: 별점은 segment 감정 라벨로 사용하지 않았고, 전체 만족도 신호로만 저장했습니다.")


if __name__ == "__main__":
    main()
