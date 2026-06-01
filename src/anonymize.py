from __future__ import annotations

import pandas as pd


PROFESSOR_COLUMNS = ["professor_raw", "professors_raw", "target_professor_raw"]


def make_professor_mapping(df: pd.DataFrame) -> pd.DataFrame:
    source_columns = [column for column in PROFESSOR_COLUMNS if column in df.columns]
    if not source_columns:
        return pd.DataFrame(columns=["professor_raw", "professor_id"])

    values: set[str] = set()
    for column in source_columns:
        series = df[column].fillna("").astype(str).str.strip()
        for value in series:
            if value:
                values.add(value)

    if not values:
        values.add("미상")

    rows = [
        {"professor_raw": professor, "professor_id": f"P{idx:04d}"}
        for idx, professor in enumerate(sorted(values), start=1)
    ]
    return pd.DataFrame(rows)


def apply_professor_mapping(df: pd.DataFrame, mapping_df: pd.DataFrame, keep_original: bool = False) -> pd.DataFrame:
    result = df.copy()
    if "professor_raw" not in result.columns:
        result["professor_raw"] = "미상"
    result["professor_raw"] = result["professor_raw"].fillna("").astype(str).str.strip().replace({"": "미상"})

    if mapping_df.empty:
        result["professor_id"] = "P0000"
    else:
        result = result.merge(mapping_df, on="professor_raw", how="left")
        result["professor_id"] = result["professor_id"].fillna("P0000")

    if not keep_original:
        drop_columns = [column for column in PROFESSOR_COLUMNS if column in result.columns]
        result = result.drop(columns=drop_columns)
    return result
