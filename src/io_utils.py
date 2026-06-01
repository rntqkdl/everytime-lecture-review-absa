from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_CONFIG: dict[str, Any] = {
    "project_root": str(PROJECT_ROOT),
    "input_dirs": [
        str(PROJECT_ROOT / "data" / "writing_output"),
        str(PROJECT_ROOT / "data" / "practical_english_output"),
        str(PROJECT_ROOT / "data" / "practical_english_variants_output"),
    ],
    "output_dirs": {
        "processed": str(PROJECT_ROOT / "outputs" / "processed"),
        "topics": str(PROJECT_ROOT / "outputs" / "topics"),
        "aspects": str(PROJECT_ROOT / "outputs" / "aspects"),
        "colab_input": str(PROJECT_ROOT / "outputs" / "colab_input"),
        "colab_results": str(PROJECT_ROOT / "outputs" / "colab_results"),
        "sentiment": str(PROJECT_ROOT / "outputs" / "sentiment"),
        "insights": str(PROJECT_ROOT / "outputs" / "insights"),
        "figures": str(PROJECT_ROOT / "outputs" / "figures"),
        "models_cpu": str(PROJECT_ROOT / "outputs" / "models_cpu"),
        "summary": str(PROJECT_ROOT / "outputs" / "summary"),
    },
    "preprocess": {
        "min_segment_length": 5,
        "remove_private_patterns": True,
        "normalize_repeated_chars": True,
    },
    "segmentation": {
        "split_sentence": True,
        "split_contrast_markers": True,
        "contrast_markers": [
            "\uadfc\ub370",
            "\uadf8\ub7f0\ub370",
            "\ud558\uc9c0\ub9cc",
            "\ub2e4\ub9cc",
            "\uadf8\ub798\ub3c4",
            "\ubc18\uba74",
            "\uc544\uc26c\uc6b4 \uc810\uc740",
            "\ub2e8\uc810\uc740",
            "\uc7a5\uc810\uc740",
        ],
    },
    "privacy": {
        "anonymize_professor": True,
        "anonymize_course": False,
        "save_raw_text_public": False,
    },
    "rating_satisfaction_signal": {
        "use_as_sentiment_label": False,
        "use_as_training_label": False,
        "very_high_min": 4.5,
        "high_min": 4.0,
        "mid_min": 3.0,
        "low_min": 2.0,
        "unknown_values": [0, None],
        "labels": {
            "very_high": "VERY_HIGH_SATISFACTION",
            "high": "HIGH_SATISFACTION",
            "mid": "MID_SATISFACTION",
            "low": "LOW_SATISFACTION",
            "very_low": "VERY_LOW_SATISFACTION",
            "unknown": "RATING_UNKNOWN",
        },
    },
    "topic_modeling": {
        "method": "lda",
        "n_topics": 8,
        "max_features": 3000,
        "min_df": 3,
        "max_df": 0.85,
    },
    "inference": {
        "run_transformer_locally": False,
        "local_sample_limit": 20,
        "batch_size": 32,
        "max_length": 128,
        "device": "cuda",
    },
    "cpu_baseline": {
        "enabled": True,
        "use_as_main_method": False,
        "max_features": 5000,
        "n_topics": 10,
        "methods": ["nmf", "lda"],
    },
    "colab_t4": {
        "use_gpu": True,
        "batch_size_embedding": 128,
        "batch_size_sentiment": 32,
        "max_length": 128,
        "save_every_n_batches": 20,
    },
    "embedding_aspect_discovery": {
        "main_method": "sentence_embedding_clustering",
        "default_embedding_model": "jhgan/ko-sroberta-multitask",
        "fallback_embedding_models": [
            "BM-K/KoSimCSE-roberta-multitask",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "intfloat/multilingual-e5-base",
        ],
        "dim_reduction": {
            "method": "umap",
            "n_neighbors": 15,
            "n_components": 5,
            "min_dist": 0.0,
            "metric": "cosine",
        },
        "clustering": {
            "primary_method": "hdbscan",
            "fallback_method": "kmeans",
            "min_cluster_size": 10,
            "n_clusters_fallback": 10,
        },
        "topic_keyword_extraction": {"method": "bertopic_or_ctfidf", "top_n_words": 15},
        "representative_segments": {"top_n": 10},
    },
    "sentiment_models": {
        "binary_baseline": [
            {
                "name": "koelectra_nsmc_monologg",
                "hf_model": "monologg/koelectra-base-finetuned-nsmc",
                "task": "binary_sentiment",
                "priority": 1,
            },
            {
                "name": "koelectra_nsmc_documented",
                "hf_model": "cringepnh/koelectra-korean-sentiment",
                "task": "binary_sentiment",
                "priority": 2,
            },
        ],
        "emotion_extension": [
            {
                "name": "koelectra_kote_44emotion",
                "hf_model": "tobykim/koelectra-44emotions",
                "task": "multi_label_emotion",
                "priority": 1,
            },
            {
                "name": "kluebert_aihub_7emotion",
                "hf_model": "dlckdfuf141/korean-emotion-kluebert-v2",
                "task": "multi_class_emotion",
                "priority": 2,
            },
        ],
    },
    "optional_domain_finetuning": {
        "enabled_by_default": False,
        "run_on_colab_t4": True,
        "caution": "Do not use review_rating as direct segment sentiment label.",
        "training_unit": "review_level_only_if_enabled",
        "base_models": [
            "klue/roberta-base",
            "monologg/koelectra-base-v3-discriminator",
            "beomi/KcELECTRA-base-v2022",
        ],
        "epochs": 2,
        "batch_size": 16,
        "max_length": 128,
    },
    "insight_extraction": {
        "min_cluster_size_for_insight": 10,
        "good_factor_positive_ratio_min": 0.6,
        "dissatisfaction_negative_ratio_min": 0.5,
        "representative_sentence_top_n": 5,
        "use_rating_signal_as_filter_or_grouping_only": True,
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else PROJECT_ROOT / "config" / "project_config.yaml"
    if not path.exists():
        return dict(DEFAULT_CONFIG)

    try:
        import yaml
    except ImportError:
        print("PyYAML is not installed. Using default config.")
        return dict(DEFAULT_CONFIG)

    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    return deep_merge(DEFAULT_CONFIG, loaded)


def resolve_path(path_like: str | Path) -> Path:
    path = Path(path_like)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def ensure_dir(path_like: str | Path) -> Path:
    path = resolve_path(path_like)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_output_dirs(config: dict[str, Any]) -> None:
    for path in config.get("output_dirs", {}).values():
        ensure_dir(path)


def read_csv_safely(path_like: str | Path, **kwargs: Any) -> pd.DataFrame:
    path = resolve_path(path_like)
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
        except UnicodeDecodeError:
            continue
    try:
        return pd.read_csv(path, **kwargs)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def write_csv(df: pd.DataFrame, path_like: str | Path) -> Path:
    path = resolve_path(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def empty_csv(path_like: str | Path, columns: list[str]) -> Path:
    return write_csv(pd.DataFrame(columns=columns), path_like)


def require_columns(df: pd.DataFrame, columns: list[str], fill_value: Any = "") -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = fill_value
    return result


def add_stable_id(df: pd.DataFrame, column: str, prefix: str, width: int = 8) -> pd.DataFrame:
    result = df.copy()
    if column not in result.columns:
        result.insert(0, column, [f"{prefix}{idx:0{width}d}" for idx in range(1, len(result) + 1)])
    else:
        missing = result[column].isna() | (result[column].astype(str).str.strip() == "")
        if missing.any():
            result.loc[missing, column] = [f"{prefix}{idx:0{width}d}" for idx in range(1, missing.sum() + 1)]
    return result
