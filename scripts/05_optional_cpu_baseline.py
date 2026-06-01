from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cpu_baseline import run_topic_baseline
from src.io_utils import empty_csv, ensure_output_dirs, load_config, read_csv_safely


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    if not config.get("cpu_baseline", {}).get("enabled", True):
        print("CPU baseline이 비활성화되어 있습니다.")
        return

    processed_dir = Path(config["output_dirs"]["processed"])
    aspects_dir = Path(config["output_dirs"]["aspects"])
    input_path = processed_dir / "segments_with_rating_signals_private.csv"

    if not input_path.exists():
        print(f"입력 파일이 없습니다: {input_path}")
        empty_csv(aspects_dir / "cpu_baseline_topic_keywords.csv", [])
        empty_csv(aspects_dir / "cpu_baseline_segment_topic_assignments.csv", [])
        return

    segments = read_csv_safely(input_path)
    settings = config.get("cpu_baseline", {})
    max_features = int(settings.get("max_features", 5000))
    n_topics = int(settings.get("n_topics", 10))
    topic_keywords, topic_assignments = run_topic_baseline(
        segments,
        aspects_dir,
        max_features=max_features,
        n_topics=n_topics,
    )
    print(f"저장: cpu_baseline_topic_keywords.csv ({len(topic_keywords)}행)")
    print(f"저장: cpu_baseline_segment_topic_assignments.csv ({len(topic_assignments)}행)")
    print("주의: CPU baseline은 TF-IDF/NMF topic 비교용이며, 별점으로 sentiment 모델을 학습하지 않습니다.")


if __name__ == "__main__":
    main()
