from __future__ import annotations

import pandas as pd

from src.sentiment_models import standardize_binary_label


def choose_segment_sentiment_label(row: pd.Series) -> str:
    for column in ["model_sentiment_label", "predicted_label_standard"]:
        if column in row and pd.notna(row[column]):
            value = standardize_binary_label(str(row[column]))
            if value in {"POSITIVE", "NEGATIVE", "NEUTRAL"}:
                return value
    return "UNKNOWN"


def add_standard_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if result.empty:
        result["segment_sentiment_label"] = []
        return result
    result["segment_sentiment_label"] = result.apply(choose_segment_sentiment_label, axis=1)
    return result
