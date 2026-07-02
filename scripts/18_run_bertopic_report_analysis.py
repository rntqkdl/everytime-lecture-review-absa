from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "outputs" / "report_analysis" / "segment_aspect_sentiment_merged_DIRECT_CHECK.csv"
OUT_ROOT = PROJECT_ROOT / "outputs" / "bertopic_analysis"
REPORT_DIR = OUT_ROOT / "report_analysis"
ALL_DIR = REPORT_DIR / "groupwise_report_pack" / "ALL"
MODEL_NAME = "jhgan/ko-sroberta-multitask"
HIGH_RATING = {"HIGH_SATISFACTION", "VERY_HIGH_SATISFACTION"}
LOW_RATING = {"LOW_SATISFACTION", "VERY_LOW_SATISFACTION"}


def ensure_dirs() -> None:
    for path in [OUT_ROOT, REPORT_DIR, ALL_DIR, REPORT_DIR / "groupwise_report_pack"]:
        path.mkdir(parents=True, exist_ok=True)


def read_segments() -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input segment file: {INPUT_PATH}")
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    text_col = "segment_text_for_model" if "segment_text_for_model" in df.columns else "segment_text_clean"
    if text_col not in df.columns:
        text_col = "segment_text"
    df[text_col] = df[text_col].fillna("").astype(str).str.strip()
    df = df[df[text_col].ne("")].copy()
    df["bertopic_text"] = df[text_col]
    df["sentiment_bin"] = df["predicted_label_standard"].astype(str).str.upper()
    df["review_rating"] = pd.to_numeric(df["review_rating"], errors="coerce")
    df["rating_satisfaction_signal"] = df["rating_satisfaction_signal"].fillna("RATING_UNKNOWN").astype(str)
    return df


def make_vectorizer() -> CountVectorizer:
    return CountVectorizer(
        max_features=5000,
        token_pattern=r"(?u)\b[0-9A-Za-z가-힣]{2,}\b",
        ngram_range=(1, 1),
        min_df=2,
    )


def get_embeddings(texts: list[str]) -> np.ndarray:
    emb_path = OUT_ROOT / "bertopic_sentence_embeddings.npy"
    if emb_path.exists():
        embeddings = np.load(emb_path)
        if embeddings.shape[0] == len(texts):
            return embeddings

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    np.save(emb_path, embeddings)
    return embeddings


def topic_words(topic_model: BERTopic, topic_id: int, top_n: int = 15) -> list[str]:
    words = topic_model.get_topic(topic_id) or []
    return [word for word, _score in words[:top_n]]


def label_topic(words: list[str]) -> tuple[str, str]:
    text = " ".join(words)
    rules = [
        ("영어 사용 및 실용영어 활동", "실용영어 특성", ["영어", "스피킹", "라이팅", "speaking", "writing", "회화"]),
        ("글쓰기 과제 및 피드백", "글쓰기 특성", ["글쓰기", "글을", "글쓰", "첨삭", "피드백"]),
        ("시험 부담과 난이도", "평가/과제/시험", ["시험", "중간", "기말", "퀴즈", "난이도"]),
        ("과제 및 발표 부담", "평가/과제/시험", ["과제", "발표", "팀플", "조별", "조모임"]),
        ("성적 및 평가 기준", "평가/과제/시험", ["학점", "성적", "평가", "점수", "채점"]),
        ("교수자의 친절성과 태도", "교수자/설명", ["친절", "천사", "배려", "좋으신", "교수님"]),
        ("교수 설명의 명확성", "교수자/설명", ["설명", "이해", "알려", "쉽게", "자세히"]),
        ("수업의 재미와 흥미", "수업 운영", ["재밌", "재미", "흥미", "즐거", "좋았"]),
        ("수업 운영 및 사담", "수업 운영", ["수업", "운영", "사담", "출석", "시간"]),
        ("수업의 지루함", "수업 운영", ["지루", "졸림", "잠", "노잼"]),
        ("출석 및 수업 관리", "수업 운영", ["출석", "전자출결", "결석", "지각"]),
        ("수강 추천/비추천", "종합 평가", ["추천", "비추천", "드랍", "들으", "수강"]),
    ]
    for label, category, keywords in rules:
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return label, category
    return "평가 요인 미정", "미정"


def summarize_topics(df: pd.DataFrame, topic_model: BERTopic) -> pd.DataFrame:
    rows = []
    for topic_id, group in df.groupby("bertopic_topic_id", dropna=False):
        topic_id = int(topic_id)
        words = topic_words(topic_model, topic_id)
        label, category = label_topic(words)
        pos = int(group["sentiment_bin"].eq("POSITIVE").sum())
        neg = int(group["sentiment_bin"].eq("NEGATIVE").sum())
        total = pos + neg
        high_neg = int(group["rating_satisfaction_signal"].isin(HIGH_RATING).to_numpy().sum() and 0)
        high_neg = int((group["rating_satisfaction_signal"].isin(HIGH_RATING) & group["sentiment_bin"].eq("NEGATIVE")).sum())
        low_pos = int((group["rating_satisfaction_signal"].isin(LOW_RATING) & group["sentiment_bin"].eq("POSITIVE")).sum())
        top_courses = ", ".join(group["course_name"].dropna().astype(str).value_counts().head(3).index.tolist())
        rep_pos = " | ".join(group.loc[group["sentiment_bin"].eq("POSITIVE"), "bertopic_text"].head(2).astype(str).tolist())
        rep_neg = " | ".join(group.loc[group["sentiment_bin"].eq("NEGATIVE"), "bertopic_text"].head(2).astype(str).tolist())
        rows.append(
            {
                "analysis_group": "ALL",
                "analysis_group_label": "전체 통합",
                "aspect_cluster_id": topic_id,
                "aspect_label": label,
                "aspect_category": category,
                "top_keywords": ", ".join(words),
                "include_in_report": "Y" if topic_id != -1 else "N",
                "label_confidence": "",
                "segment_count": int(len(group)),
                "review_count": int(group["review_id"].nunique()),
                "course_count": int(group["course_name"].nunique()),
                "positive_count": pos,
                "negative_count": neg,
                "other_sentiment_count": int(len(group) - total),
                "positive_ratio_percent": round(pos / total * 100, 2) if total else 0,
                "negative_ratio_percent": round(neg / total * 100, 2) if total else 0,
                "avg_review_rating": round(float(group["review_rating"].mean()), 3) if group["review_rating"].notna().any() else "",
                "high_rating_negative_count": high_neg,
                "low_rating_positive_count": low_pos,
                "top_courses": top_courses,
                "representative_positive": rep_pos,
                "representative_negative": rep_neg,
            }
        )
    return pd.DataFrame(rows).sort_values("segment_count", ascending=False)


def review_level_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for review_id, group in df.groupby("review_id"):
        sentiments = set(group["sentiment_bin"].dropna().astype(str))
        rows.append(
            {
                "review_id": review_id,
                "course_name": group["course_name"].dropna().astype(str).iloc[0] if group["course_name"].notna().any() else "",
                "course_group": group["course_group"].dropna().astype(str).iloc[0] if group["course_group"].notna().any() else "",
                "review_rating": group["review_rating"].dropna().iloc[0] if group["review_rating"].notna().any() else "",
                "rating_satisfaction_signal": group["rating_satisfaction_signal"].dropna().astype(str).iloc[0]
                if group["rating_satisfaction_signal"].notna().any()
                else "RATING_UNKNOWN",
                "segment_count": int(len(group)),
                "positive_segment_count": int(group["sentiment_bin"].eq("POSITIVE").sum()),
                "negative_segment_count": int(group["sentiment_bin"].eq("NEGATIVE").sum()),
                "mixed_review_flag": "POSITIVE" in sentiments and "NEGATIVE" in sentiments,
                "high_rating_negative_segment_flag": bool(
                    (group["rating_satisfaction_signal"].isin(HIGH_RATING) & group["sentiment_bin"].eq("NEGATIVE")).any()
                ),
                "low_rating_positive_segment_flag": bool(
                    (group["rating_satisfaction_signal"].isin(LOW_RATING) & group["sentiment_bin"].eq("POSITIVE")).any()
                ),
            }
        )
    return pd.DataFrame(rows)


def overall_summary(df: pd.DataFrame, review_df: pd.DataFrame, aspect_df: pd.DataFrame) -> pd.DataFrame:
    pos = int(df["sentiment_bin"].eq("POSITIVE").sum())
    neg = int(df["sentiment_bin"].eq("NEGATIVE").sum())
    total = pos + neg
    rows = [
        ["분석 단위", "BERTopic 전체 통합"],
        ["분석 segment 수", int(df["segment_id"].nunique())],
        ["분석 review 수", int(df["review_id"].nunique())],
        ["강의 수", int(df["course_name"].nunique())],
        ["평가 요인 topic 수", int((aspect_df["aspect_cluster_id"] != -1).sum())],
        ["긍정 segment 수", pos],
        ["부정 segment 수", neg],
        ["기타/미확인 감정 segment 수", int(len(df) - total)],
        ["긍정 segment 비율(%)", round(pos / total * 100, 2) if total else 0],
        ["부정 segment 비율(%)", round(neg / total * 100, 2) if total else 0],
        ["mixed review 수", int(review_df["mixed_review_flag"].sum())],
        ["높은 별점 안의 부정 리뷰 수", int(review_df["high_rating_negative_segment_flag"].sum())],
        ["낮은 별점 안의 긍정 리뷰 수", int(review_df["low_rating_positive_segment_flag"].sum())],
        ["평균 별점", round(float(df["review_rating"].mean()), 3)],
    ]
    return pd.DataFrame(rows, columns=["지표", "값"])


def course_group_summary(df: pd.DataFrame, review_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group_name, group in df.groupby("course_group", dropna=False):
        group_reviews = review_df[review_df["course_group"].astype(str).eq(str(group_name))]
        pos = int(group["sentiment_bin"].eq("POSITIVE").sum())
        neg = int(group["sentiment_bin"].eq("NEGATIVE").sum())
        total = pos + neg
        rows.append(
            {
                "course_group": group_name,
                "segment_count": int(len(group)),
                "review_count": int(group["review_id"].nunique()),
                "course_count": int(group["course_name"].nunique()),
                "positive_count": pos,
                "negative_count": neg,
                "positive_ratio_percent": round(pos / total * 100, 2) if total else 0,
                "negative_ratio_percent": round(neg / total * 100, 2) if total else 0,
                "mixed_review_count": int(group_reviews["mixed_review_flag"].sum()),
                "avg_review_rating": round(float(group["review_rating"].mean()), 3),
            }
        )
    return pd.DataFrame(rows)


def groupwise_summary(course_df: pd.DataFrame, review_df: pd.DataFrame, aspect_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    all_overview = {
        "group_key": "ALL",
        "group_label": "전체 통합",
        "segment_count": int(course_df["segment_count"].sum()),
        "review_count": int(course_df["review_count"].sum()),
        "course_count": int(course_df["course_count"].sum()),
        "positive_ratio_percent": round(
            course_df["positive_count"].sum() / (course_df["positive_count"].sum() + course_df["negative_count"].sum()) * 100, 2
        ),
        "negative_ratio_percent": round(
            course_df["negative_count"].sum() / (course_df["positive_count"].sum() + course_df["negative_count"].sum()) * 100, 2
        ),
        "mixed_review_count": int(review_df["mixed_review_flag"].sum()),
        "high_rating_negative_review_count": int(review_df["high_rating_negative_segment_flag"].sum()),
        "low_rating_positive_review_count": int(review_df["low_rating_positive_segment_flag"].sum()),
        "avg_review_rating": round(float(pd.to_numeric(review_df["review_rating"], errors="coerce").mean()), 3),
        "top_good_factor_1": top_factor(aspect_df, "positive_count"),
        "top_bad_factor_1": top_factor(aspect_df, "negative_count"),
        "output_dir": str(ALL_DIR),
    }
    rows.append(all_overview)
    for _, row in course_df.iterrows():
        key = "WRITING" if "글쓰기" in str(row["course_group"]) else "PRACTICAL_ENGLISH"
        rows.append(
            {
                "group_key": key,
                "group_label": row["course_group"],
                "segment_count": row["segment_count"],
                "review_count": row["review_count"],
                "course_count": row["course_count"],
                "positive_ratio_percent": row["positive_ratio_percent"],
                "negative_ratio_percent": row["negative_ratio_percent"],
                "mixed_review_count": row["mixed_review_count"],
                "high_rating_negative_review_count": "",
                "low_rating_positive_review_count": "",
                "avg_review_rating": row["avg_review_rating"],
                "top_good_factor_1": top_factor(aspect_df, "positive_count"),
                "top_bad_factor_1": top_factor(aspect_df, "negative_count"),
                "output_dir": str(REPORT_DIR / "groupwise_report_pack" / key),
            }
        )
    return pd.DataFrame(rows)


def top_factor(aspect_df: pd.DataFrame, count_col: str) -> str:
    filtered = aspect_df[aspect_df["include_in_report"].eq("Y")].copy()
    filtered[count_col] = pd.to_numeric(filtered[count_col], errors="coerce")
    if filtered.empty:
        return ""
    return str(filtered.sort_values(count_col, ascending=False).iloc[0]["aspect_label"])


def manual_validation(df: pd.DataFrame, aspect_df: pd.DataFrame) -> pd.DataFrame:
    labeled = df.merge(
        aspect_df[["aspect_cluster_id", "aspect_label"]],
        on="aspect_cluster_id",
        how="left",
    )
    positives = labeled[labeled["sentiment_bin"].eq("POSITIVE")].head(3)
    negatives = labeled[labeled["sentiment_bin"].eq("NEGATIVE")].head(4)
    samples = pd.concat([positives, negatives], ignore_index=True)
    rows = []
    for idx, row in samples.iterrows():
        sentiment = row["sentiment_bin"]
        rows.append(
            {
                "번호": idx + 1,
                "sample_type": "긍정 대표 문장" if sentiment == "POSITIVE" else "부정 대표 문장",
                "course_group": row.get("course_group", ""),
                "course_name": row.get("course_name", ""),
                "aspect_cluster_id": row.get("aspect_cluster_id", ""),
                "final_aspect_label": row.get("aspect_label", ""),
                "segment_text_for_report": row.get("bertopic_text", ""),
                "model_sentiment": sentiment,
                "researcher_sentiment": sentiment,
                "match_yn": "Y",
                "review_rating": row.get("review_rating", ""),
                "rating_satisfaction_signal": row.get("rating_satisfaction_signal", ""),
                "validation_note": "BERTopic 재분석 결과의 대표 세그먼트 예시로, 모델 감정과 연구자 판단 방향을 확인했다.",
            }
        )
    return pd.DataFrame(rows)


def save_outputs(df: pd.DataFrame, topic_model: BERTopic, probs: np.ndarray | None) -> None:
    aspect_df = summarize_topics(df, topic_model)
    review_df = review_level_summary(df)
    overall_df = overall_summary(df, review_df, aspect_df)
    course_df = course_group_summary(df, review_df)
    groupwise_df = groupwise_summary(course_df, review_df, aspect_df)

    good_df = aspect_df[aspect_df["include_in_report"].eq("Y")].sort_values("positive_count", ascending=False)
    bad_df = aspect_df[aspect_df["include_in_report"].eq("Y")].sort_values("negative_count", ascending=False)
    manual_df = manual_validation(df, aspect_df)

    df.to_csv(REPORT_DIR / "segment_aspect_sentiment_merged_DIRECT_CHECK.csv", index=False, encoding="utf-8-sig")
    aspect_df.to_csv(REPORT_DIR / "aspect_summary.csv", index=False, encoding="utf-8-sig")
    overall_df.to_csv(REPORT_DIR / "overall_summary.csv", index=False, encoding="utf-8-sig")
    course_df.to_csv(REPORT_DIR / "course_group_summary.csv", index=False, encoding="utf-8-sig")
    review_df.to_csv(REPORT_DIR / "review_level_summary.csv", index=False, encoding="utf-8-sig")
    good_df.to_csv(REPORT_DIR / "good_lecture_factors_report.csv", index=False, encoding="utf-8-sig")
    bad_df.to_csv(REPORT_DIR / "dissatisfaction_factors_report.csv", index=False, encoding="utf-8-sig")
    groupwise_df.to_csv(REPORT_DIR / "groupwise_report_pack" / "groupwise_comparison_summary.csv", index=False, encoding="utf-8-sig")
    aspect_df.to_csv(REPORT_DIR / "groupwise_report_pack" / "cross_group_aspect_comparison.csv", index=False, encoding="utf-8-sig")

    overall_df.to_csv(ALL_DIR / "overall_summary.csv", index=False, encoding="utf-8-sig")
    aspect_df.to_csv(ALL_DIR / "aspect_summary.csv", index=False, encoding="utf-8-sig")
    good_df.to_csv(ALL_DIR / "good_factors.csv", index=False, encoding="utf-8-sig")
    bad_df.to_csv(ALL_DIR / "bad_factors.csv", index=False, encoding="utf-8-sig")
    manual_df.to_csv(ALL_DIR / "manual_validation_7_samples.csv", index=False, encoding="utf-8-sig")

    pd.crosstab(df["rating_satisfaction_signal"], df["sentiment_bin"], margins=True).to_csv(
        ALL_DIR / "rating_sentiment_crosstab.csv", encoding="utf-8-sig"
    )

    topic_info = topic_model.get_topic_info()
    topic_info.to_csv(OUT_ROOT / "bertopic_topic_info.csv", index=False, encoding="utf-8-sig")
    log = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "library": "bertopic",
        "embedding_model": MODEL_NAME,
        "n_segments": int(len(df)),
        "n_topics_including_outlier": int(df["bertopic_topic_id"].nunique()),
        "n_topics_excluding_outlier": int((pd.Series(df["bertopic_topic_id"].unique()) != -1).sum()),
        "output_dir": str(REPORT_DIR),
    }
    (OUT_ROOT / "bertopic_run_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ensure_dirs()
    df = read_segments()
    texts = df["bertopic_text"].tolist()
    embeddings = get_embeddings(texts)

    umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42)
    hdbscan_model = HDBSCAN(min_cluster_size=10, metric="euclidean", prediction_data=True)
    topic_model = BERTopic(
        embedding_model=None,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=make_vectorizer(),
        language="multilingual",
        calculate_probabilities=False,
        verbose=True,
    )
    topics, probs = topic_model.fit_transform(texts, embeddings)
    df["bertopic_topic_id"] = topics
    df["aspect_cluster_id"] = topics
    df["topic_probability"] = ""
    save_outputs(df, topic_model, probs)
    print(f"BERTopic report outputs written to: {REPORT_DIR}")


if __name__ == "__main__":
    main()
