from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer


TOPIC_POS_PREFIXES = ("N", "V")


def _kiwi_tokenizer():
    try:
        from kiwipiepy import Kiwi
    except Exception:
        return None
    return Kiwi()


KIWI = _kiwi_tokenizer()


def tokenize_korean_for_topic(text: str) -> list[str]:
    value = "" if text is None else str(text)
    if not value.strip():
        return []

    if KIWI is not None:
        tokens: list[str] = []
        for token in KIWI.tokenize(value):
            if token.tag.startswith(TOPIC_POS_PREFIXES) and len(token.form) >= 2:
                tokens.append(token.form)
        return tokens

    return [token for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", value) if len(token) >= 2]


def build_vectorizer(max_features: int, min_df: int | float, max_df: int | float) -> CountVectorizer:
    return CountVectorizer(
        tokenizer=tokenize_korean_for_topic,
        preprocessor=None,
        token_pattern=None,
        max_features=max_features,
        min_df=min_df,
        max_df=max_df,
    )


def fit_lda(
    texts: Iterable[str],
    n_topics: int = 8,
    max_features: int = 3000,
    min_df: int | float = 3,
    max_df: int | float = 0.85,
    random_state: int = 42,
) -> tuple[LatentDirichletAllocation, CountVectorizer, object]:
    documents = list(texts)
    if not documents:
        raise ValueError("LDA를 실행할 문장이 없습니다.")

    adjusted_min_df = min_df
    if isinstance(min_df, int):
        adjusted_min_df = max(1, min(min_df, len(documents)))

    vectorizer = build_vectorizer(max_features=max_features, min_df=adjusted_min_df, max_df=max_df)
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        vectorizer = build_vectorizer(max_features=max_features, min_df=1, max_df=1.0)
        matrix = vectorizer.fit_transform(documents)

    topic_count = max(1, min(int(n_topics), matrix.shape[0], matrix.shape[1]))
    lda = LatentDirichletAllocation(
        n_components=topic_count,
        random_state=random_state,
        learning_method="batch",
    )
    lda.fit(matrix)
    return lda, vectorizer, matrix


def topic_keywords(lda: LatentDirichletAllocation, vectorizer: CountVectorizer, top_n: int = 15) -> pd.DataFrame:
    feature_names = vectorizer.get_feature_names_out()
    rows: list[dict] = []
    for topic_id, weights in enumerate(lda.components_):
        top_indices = weights.argsort()[::-1][:top_n]
        for rank, index in enumerate(top_indices, start=1):
            rows.append(
                {
                    "topic_id": topic_id,
                    "rank": rank,
                    "keyword": feature_names[index],
                    "weight": float(weights[index]),
                }
            )
    return pd.DataFrame(rows)


def assign_topics(lda: LatentDirichletAllocation, matrix) -> pd.DataFrame:
    probabilities = lda.transform(matrix)
    rows: list[dict] = []
    for row_index, topic_probs in enumerate(probabilities):
        topic_id = int(topic_probs.argmax())
        rows.append(
            {
                "row_index": row_index,
                "topic_id": topic_id,
                "topic_probability": float(topic_probs[topic_id]),
            }
        )
    return pd.DataFrame(rows)


def representative_sentences(
    sentences_df: pd.DataFrame,
    assignments_df: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    if sentences_df.empty or assignments_df.empty:
        return pd.DataFrame()

    merged = sentences_df.reset_index(drop=True).reset_index(names="row_index").merge(assignments_df, on="row_index")
    rows: list[pd.DataFrame] = []
    for topic_id, group in merged.groupby("topic_id"):
        selected = group.sort_values("topic_probability", ascending=False).head(top_n).copy()
        selected.insert(0, "representative_rank", range(1, len(selected) + 1))
        rows.append(selected)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)
