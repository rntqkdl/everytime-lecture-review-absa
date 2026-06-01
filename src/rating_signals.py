from __future__ import annotations

import pandas as pd


VERY_HIGH = "VERY_HIGH_SATISFACTION"
HIGH = "HIGH_SATISFACTION"
MID = "MID_SATISFACTION"
LOW = "LOW_SATISFACTION"
VERY_LOW = "VERY_LOW_SATISFACTION"
UNKNOWN = "RATING_UNKNOWN"


def rating_to_satisfaction_signal(rating: float | int | str | None) -> str:
    value = pd.to_numeric(pd.Series([rating]), errors="coerce").iloc[0]
    if pd.isna(value) or float(value) == 0.0:
        return UNKNOWN
    value = float(value)
    if value >= 4.5:
        return VERY_HIGH
    if value >= 4.0:
        return HIGH
    if value >= 3.0:
        return MID
    if value >= 2.0:
        return LOW
    if value > 0:
        return VERY_LOW
    return UNKNOWN


def rating_to_group(signal: str) -> str:
    if signal in {VERY_HIGH, HIGH}:
        return "HIGH_OR_VERY_HIGH"
    if signal == MID:
        return "MID"
    if signal in {LOW, VERY_LOW}:
        return "LOW_OR_VERY_LOW"
    return UNKNOWN


def add_rating_satisfaction_signals(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "review_rating" not in result.columns:
        result["review_rating"] = pd.NA
    result["rating_value"] = pd.to_numeric(result["review_rating"], errors="coerce")
    result["rating_satisfaction_signal"] = result["rating_value"].apply(rating_to_satisfaction_signal)
    result["rating_group"] = result["rating_satisfaction_signal"].apply(rating_to_group)
    result["rating_signal_source"] = "review_rating"
    return result


def build_rating_signal_distribution(reviews: pd.DataFrame, segments: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for unit, df in {"review": reviews, "segment": segments}.items():
        if df.empty or "rating_satisfaction_signal" not in df.columns:
            continue
        counts = df["rating_satisfaction_signal"].value_counts(dropna=False)
        total = int(counts.sum())
        for signal, count in counts.items():
            rows.append(
                {
                    "unit": unit,
                    "rating_satisfaction_signal": signal,
                    "count": int(count),
                    "ratio": float(count / total) if total else 0.0,
                }
            )
    return pd.DataFrame(rows)
