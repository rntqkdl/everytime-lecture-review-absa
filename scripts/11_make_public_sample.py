from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import ensure_output_dirs, load_config, read_csv_safely, write_csv


PUBLIC_SEGMENTS = [
    "교수 설명이 이해하기 쉬웠다는 익명 예시 문장입니다.",
    "과제 부담이 있었다는 익명 예시 문장입니다.",
    "시험 방식과 평가 기준에 대한 익명 예시 문장입니다.",
    "수업 운영과 자료 제공에 대한 익명 예시 문장입니다.",
]


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    processed_dir = Path(config["output_dirs"]["processed"])
    sample_path = Path(config.get("project_root", ROOT)) / "sample_data" / "sample_reviews_anonymized.csv"
    input_path = processed_dir / "segments_with_rating_signals_private.csv"
    source = read_csv_safely(input_path).head(20).copy() if input_path.exists() else pd.DataFrame()

    if source.empty:
        source = pd.DataFrame(
            {
                "segment_id": ["PUBLIC_001"],
                "course_name": ["글쓰기 계열 강의"],
                "course_group": ["글쓰기"],
                "professor_id": ["P001"],
                "review_rating": [4.0],
                "rating_satisfaction_signal": ["HIGH_SATISFACTION"],
                "rating_group": ["HIGH_OR_VERY_HIGH"],
            }
        )

    sample = pd.DataFrame()
    sample["sample_id"] = [f"PUBLIC_{idx:03d}" for idx in range(1, len(source) + 1)]
    for column in [
        "segment_id",
        "course_name",
        "course_group",
        "professor_id",
        "review_rating",
        "rating_satisfaction_signal",
        "rating_group",
    ]:
        sample[column] = source[column].values if column in source.columns else ""
    sample["segment_text_public"] = [PUBLIC_SEGMENTS[idx % len(PUBLIC_SEGMENTS)] for idx in range(len(source))]
    sample = sample.head(20)
    write_csv(sample, sample_path)
    print(f"저장: {sample_path} ({len(sample)}행)")


if __name__ == "__main__":
    main()
