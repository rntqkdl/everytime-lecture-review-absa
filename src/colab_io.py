from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.sentiment_models import BINARY_BASELINE_MODELS, EMOTION_EXTENSION_MODELS
from src.text_cleaning import clean_review_text


SEGMENT_COLAB_COLUMNS = [
    "segment_id",
    "review_id",
    "lecture_id",
    "course_name",
    "course_group",
    "professor_id",
    "review_rating",
    "rating_satisfaction_signal",
    "rating_group",
    "rating_value",
    "segment_text",
    "segment_text_for_model",
]


def prepare_segment_colab_frames(segments: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = segments.copy()
    for column in SEGMENT_COLAB_COLUMNS:
        if column not in data.columns:
            data[column] = ""
    data["segment_text_for_model"] = data["segment_text"].fillna("").astype(str).apply(clean_review_text)
    embedding = data[SEGMENT_COLAB_COLUMNS].drop_duplicates("segment_id").copy()
    sentiment = data[SEGMENT_COLAB_COLUMNS].drop_duplicates("segment_id").copy()
    return embedding, sentiment


def write_colab_model_config(config: dict[str, Any], output_path: str | Path) -> Path:
    model_config = {
        "colab_t4": config.get("colab_t4", {}),
        "embedding_aspect_discovery": config.get("embedding_aspect_discovery", {}),
        "sentiment_models": {
            "binary_baseline": config.get("sentiment_models", {}).get("binary_baseline", BINARY_BASELINE_MODELS),
            "emotion_extension": config.get("sentiment_models", {}).get("emotion_extension", EMOTION_EXTENSION_MODELS),
        },
        "optional_domain_finetuning": config.get("optional_domain_finetuning", {}),
        "rating_policy": {
            "use_rating_as_sentiment_label": False,
            "use_rating_as_training_label": False,
            "rating_is_review_level_satisfaction_signal_only": True,
            "sentiment_ground_truth_available": False,
        },
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model_config, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
