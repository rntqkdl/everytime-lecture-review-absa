from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from src.io_utils import write_csv
from src.text_cleaning import clean_review_text


def _vectorizer(max_features: int) -> TfidfVectorizer:
    return TfidfVectorizer(
        max_features=max_features,
        min_df=2,
        max_df=0.9,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[0-9A-Za-z\uAC00-\uD7A3]{2,}\b",
    )


def run_topic_baseline(
    segments: pd.DataFrame,
    output_dir: Path,
    max_features: int = 5000,
    n_topics: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if segments.empty or "segment_text" not in segments.columns:
        return pd.DataFrame(), pd.DataFrame()

    texts = segments["segment_text"].fillna("").astype(str).apply(clean_review_text)
    vectorizer = _vectorizer(max_features)
    matrix = vectorizer.fit_transform(texts)
    n_components = max(1, min(n_topics, matrix.shape[0], matrix.shape[1]))
    model = NMF(n_components=n_components, random_state=42, init="nndsvda", max_iter=300)
    topic_matrix = model.fit_transform(matrix)
    terms = vectorizer.get_feature_names_out()

    keyword_rows: list[dict] = []
    for topic_id, weights in enumerate(model.components_):
        for rank, index in enumerate(weights.argsort()[::-1][:15], start=1):
            keyword_rows.append(
                {
                    "method": "tfidf_nmf_cpu_baseline",
                    "topic_id": topic_id,
                    "rank": rank,
                    "keyword": terms[index],
                    "weight": float(weights[index]),
                }
            )

    base_cols = [
        "segment_id",
        "review_id",
        "lecture_id",
        "course_name",
        "course_group",
        "rating_satisfaction_signal",
        "rating_group",
        "segment_text",
    ]
    assignment = segments[[col for col in base_cols if col in segments.columns]].copy()
    assignment["cpu_baseline_topic_id"] = topic_matrix.argmax(axis=1)
    assignment["cpu_baseline_topic_score"] = topic_matrix.max(axis=1)

    keyword_df = pd.DataFrame(keyword_rows)
    write_csv(keyword_df, output_dir / "cpu_baseline_topic_keywords.csv")
    write_csv(assignment, output_dir / "cpu_baseline_segment_topic_assignments.csv")
    return keyword_df, assignment
