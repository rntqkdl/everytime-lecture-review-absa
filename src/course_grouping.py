from __future__ import annotations

import pandas as pd


PRACTICAL_ENGLISH = "\uc2e4\uc6a9\uc601\uc5b4"
WRITING = "\uae00\uc4f0\uae30"
OTHER = "\uae30\ud0c0"


def normalize_course_group(course_name: str) -> str:
    value = "" if course_name is None else str(course_name).strip()
    lowered = value.lower()
    if PRACTICAL_ENGLISH in value or "practical english" in lowered:
        return PRACTICAL_ENGLISH
    if WRITING in value:
        return WRITING
    return OTHER


def add_course_group(df: pd.DataFrame, source_column: str = "course_name") -> pd.DataFrame:
    result = df.copy()
    if source_column not in result.columns:
        result["course_group"] = OTHER
        return result
    result["course_group"] = result[source_column].apply(normalize_course_group)
    return result
