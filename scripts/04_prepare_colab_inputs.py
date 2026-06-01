from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.colab_io import prepare_segment_colab_frames, write_colab_model_config
from src.io_utils import empty_csv, ensure_output_dirs, load_config, read_csv_safely, write_csv


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    processed_dir = Path(config["output_dirs"]["processed"])
    colab_dir = Path(config["output_dirs"]["colab_input"])
    input_path = processed_dir / "segments_with_rating_signals_private.csv"

    if not input_path.exists():
        print(f"입력 파일이 없습니다: {input_path}")
        empty_csv(colab_dir / "segments_for_embedding_colab.csv", [])
        empty_csv(colab_dir / "segments_for_sentiment_colab.csv", [])
        write_colab_model_config(config, colab_dir / "colab_model_config.json")
        return

    segments = read_csv_safely(input_path)
    embedding, sentiment = prepare_segment_colab_frames(segments)
    write_csv(embedding, colab_dir / "segments_for_embedding_colab.csv")
    write_csv(sentiment, colab_dir / "segments_for_sentiment_colab.csv")
    write_colab_model_config(config, colab_dir / "colab_model_config.json")
    print(f"저장: segments_for_embedding_colab.csv ({len(embedding)}행)")
    print(f"저장: segments_for_sentiment_colab.csv ({len(sentiment)}행)")
    print("저장: colab_model_config.json")
    print("주의: Colab 입력에는 rating_satisfaction_signal이 포함되지만 감정 정답 라벨은 포함하지 않습니다.")


if __name__ == "__main__":
    main()
