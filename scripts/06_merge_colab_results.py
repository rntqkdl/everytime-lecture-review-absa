from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import empty_csv, ensure_output_dirs, load_config, read_csv_safely, write_csv
from src.sentiment_models import standardize_binary_label
from src.sentiment_utils import add_standard_sentiment


def read_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"Colab 결과 없음: {path.name}")
        return pd.DataFrame()
    return read_csv_safely(path)


def copy_or_empty(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    if df.empty:
        empty_csv(path, columns)
    else:
        write_csv(df, path)


def normalize_binary(binary: pd.DataFrame) -> pd.DataFrame:
    if binary.empty:
        return binary
    result = binary.copy()
    if "model_sentiment_label" not in result.columns:
        source_col = "predicted_label_standard" if "predicted_label_standard" in result.columns else "predicted_label_original"
        if source_col in result.columns:
            result["model_sentiment_label"] = result[source_col].apply(standardize_binary_label)
    if "model_sentiment_score" not in result.columns and "predicted_score" in result.columns:
        result["model_sentiment_score"] = pd.to_numeric(result["predicted_score"], errors="coerce").fillna(0)
    return result


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    processed_dir = Path(config["output_dirs"]["processed"])
    colab_results_dir = Path(config["output_dirs"]["colab_results"])
    aspects_dir = Path(config["output_dirs"]["aspects"])
    sentiment_dir = Path(config["output_dirs"]["sentiment"])

    segment_path = processed_dir / "segments_with_rating_signals_private.csv"
    segments = read_csv_safely(segment_path) if segment_path.exists() else pd.DataFrame()

    clusters = read_optional(colab_results_dir / "segment_embedding_clusters.csv")
    cluster_keywords = read_optional(colab_results_dir / "aspect_cluster_keywords.csv")
    representatives = read_optional(colab_results_dir / "aspect_representative_segments.csv")
    all_models = read_optional(colab_results_dir / "segment_sentiment_predictions_all_models.csv")
    binary = normalize_binary(read_optional(colab_results_dir / "segment_sentiment_binary_primary.csv"))
    emotion = read_optional(colab_results_dir / "segment_emotion_extension.csv")

    if clusters.empty:
        cpu_clusters = read_optional(aspects_dir / "cpu_baseline_segment_topic_assignments.csv")
        if not cpu_clusters.empty:
            clusters = cpu_clusters.rename(
                columns={"cpu_baseline_topic_id": "cluster_id", "cpu_baseline_topic_score": "cluster_probability"}
            )
            clusters["cluster_source"] = "cpu_tfidf_nmf_baseline"
    else:
        clusters["cluster_source"] = "colab_embedding"

    if cluster_keywords.empty:
        cpu_keywords = read_optional(aspects_dir / "cpu_baseline_topic_keywords.csv")
        if not cpu_keywords.empty:
            cluster_keywords = cpu_keywords.rename(columns={"topic_id": "cluster_id"})
            cluster_keywords["cluster_source"] = "cpu_tfidf_nmf_baseline"
    else:
        cluster_keywords["cluster_source"] = "colab_embedding"

    if not binary.empty:
        binary["sentiment_source"] = "colab_model"
    else:
        print("Colab 감정 결과가 없어 segment sentiment는 UNKNOWN으로 남깁니다. 별점으로 감정을 대체하지 않습니다.")

    copy_or_empty(clusters, aspects_dir / "segment_aspect_clusters.csv", ["segment_id", "cluster_id", "cluster_probability"])
    copy_or_empty(cluster_keywords, aspects_dir / "aspect_cluster_keywords.csv", ["cluster_id", "keyword", "weight"])
    copy_or_empty(representatives, aspects_dir / "aspect_representative_segments.csv", ["cluster_id", "segment_id", "segment_text"])
    copy_or_empty(all_models, sentiment_dir / "segment_sentiment_predictions_all_models.csv", [])
    copy_or_empty(binary, sentiment_dir / "segment_sentiment_binary_primary.csv", ["segment_id", "model_sentiment_label"])
    copy_or_empty(emotion, sentiment_dir / "segment_emotion_extension.csv", [])

    if segments.empty:
        empty_csv(sentiment_dir / "segment_aspect_sentiment_merged.csv", [])
        print("segment 데이터가 없어 병합 산출물을 만들지 못했습니다.")
        return

    merged = segments.copy()
    if not clusters.empty and "segment_id" in clusters.columns:
        cluster_cols = [col for col in ["segment_id", "cluster_id", "cluster_probability", "cluster_source"] if col in clusters.columns]
        merged = merged.merge(clusters[cluster_cols].drop_duplicates("segment_id"), on="segment_id", how="left")
    if not binary.empty and "segment_id" in binary.columns:
        sent_cols = [
            col
            for col in [
                "segment_id",
                "model_name",
                "hf_model",
                "model_sentiment_label",
                "model_sentiment_score",
                "sentiment_source",
                "predicted_label_original",
            ]
            if col in binary.columns
        ]
        merged = merged.merge(binary[sent_cols].drop_duplicates("segment_id"), on="segment_id", how="left")
    merged = add_standard_sentiment(merged)
    write_csv(merged, sentiment_dir / "segment_aspect_sentiment_merged.csv")
    print(f"저장: segment_aspect_sentiment_merged.csv ({len(merged)}행)")


if __name__ == "__main__":
    main()
