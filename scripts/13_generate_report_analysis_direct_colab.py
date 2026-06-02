# -*- coding: utf-8 -*-
"""
12_generate_report_analysis_direct_colab.py

목적
- 기존 outputs/sentiment/segment_aspect_sentiment_merged.csv를 무시한다.
- 반드시 outputs/colab_results/segment_embedding_clusters.csv 와
  outputs/colab_results/segment_sentiment_binary_primary.csv 를 직접 병합한다.
- 감정분석 결과가 UNKNOWN으로만 나오는 문제를 방지한다.

실행 위치
    C:\every_time

실행
    python scripts\12_generate_report_analysis_direct_colab.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"C:\every_time")
COLAB_DIR = ROOT / "outputs" / "colab_results"
OUT_DIR = ROOT / "outputs" / "report_analysis"
FIG_DIR = OUT_DIR / "figures"

HIGH_RATING = {"VERY_HIGH_SATISFACTION", "HIGH_SATISFACTION"}
LOW_RATING = {"LOW_SATISFACTION", "VERY_LOW_SATISFACTION"}


def clean_text(value, max_len=None):
    if pd.isna(value):
        return ""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if max_len and len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text


def read_csv_auto(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="utf-8-sig")


def save_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].apply(clean_text)
    out.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
        quoting=csv.QUOTE_ALL,
        lineterminator="\n",
    )


def normalize_sentiment(value):
    if pd.isna(value):
        return "UNKNOWN"

    text = str(value).strip()
    low = text.lower()

    if low in {"positive", "pos", "label_1", "1", "긍정"}:
        return "POSITIVE"
    if low in {"negative", "neg", "label_0", "0", "부정"}:
        return "NEGATIVE"

    if "positive" in low or "긍정" in text:
        return "POSITIVE"
    if "negative" in low or "부정" in text:
        return "NEGATIVE"

    return text or "UNKNOWN"


def pct(n, d):
    return round(float(n) / float(d) * 100, 2) if d else 0.0


def require_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"필수 파일이 없습니다: {path}")
    return path


def load_direct_colab_results():
    aspect_path = require_file(COLAB_DIR / "segment_embedding_clusters.csv")
    sentiment_path = require_file(COLAB_DIR / "segment_sentiment_binary_primary.csv")
    keyword_path = require_file(COLAB_DIR / "aspect_cluster_keywords.csv")

    print("[LOAD aspect]   ", aspect_path)
    print("[LOAD sentiment]", sentiment_path)
    print("[LOAD keywords] ", keyword_path)

    aspect = read_csv_auto(aspect_path)
    sentiment = read_csv_auto(sentiment_path)
    keywords = read_csv_auto(keyword_path)

    print("[CHECK] aspect rows:", len(aspect))
    print("[CHECK] sentiment rows:", len(sentiment))

    if "segment_id" not in aspect.columns:
        raise KeyError("segment_embedding_clusters.csv에 segment_id 컬럼이 없습니다.")
    if "segment_id" not in sentiment.columns:
        raise KeyError("segment_sentiment_binary_primary.csv에 segment_id 컬럼이 없습니다.")
    if "predicted_label_standard" not in sentiment.columns:
        raise KeyError("segment_sentiment_binary_primary.csv에 predicted_label_standard 컬럼이 없습니다.")

    print("[CHECK] sentiment label counts")
    print(sentiment["predicted_label_standard"].value_counts(dropna=False).to_string())

    sentiment_keep = [
        "segment_id",
        "model_name",
        "hf_model",
        "task",
        "predicted_label_original",
        "predicted_label_standard",
        "predicted_score",
        "all_scores_json",
        "run_status",
        "error_message",
    ]
    sentiment_keep = [c for c in sentiment_keep if c in sentiment.columns]

    merged = aspect.merge(sentiment[sentiment_keep], on="segment_id", how="left")

    if "aspect_cluster_id" not in merged.columns and "cluster_id" in merged.columns:
        merged["aspect_cluster_id"] = merged["cluster_id"]

    if "segment_text" not in merged.columns and "segment_text_for_model" in merged.columns:
        merged["segment_text"] = merged["segment_text_for_model"]

    if "course_name" not in merged.columns:
        merged["course_name"] = ""

    if "course_group" not in merged.columns:
        # course_name 기준 간단 분류
        def group_course(name):
            name = str(name)
            if "글쓰기" in name:
                return "WRITING"
            if "영어" in name or "English" in name or "Practical" in name:
                return "PRACTICAL_ENGLISH"
            return "OTHER"
        merged["course_group"] = merged["course_name"].apply(group_course)

    if "professor_id" not in merged.columns:
        merged["professor_id"] = ""

    if "review_rating" not in merged.columns:
        merged["review_rating"] = np.nan

    if "rating_satisfaction_signal" not in merged.columns:
        merged["rating_satisfaction_signal"] = "RATING_UNKNOWN"

    merged["sentiment_bin"] = merged["predicted_label_standard"].apply(normalize_sentiment)
    merged["review_rating"] = pd.to_numeric(merged["review_rating"], errors="coerce")
    merged["predicted_score"] = pd.to_numeric(merged.get("predicted_score", np.nan), errors="coerce")
    merged["segment_text"] = merged["segment_text"].apply(clean_text)

    print("[CHECK] merged rows:", len(merged))
    print("[CHECK] merged sentiment counts")
    print(merged["sentiment_bin"].value_counts(dropna=False).to_string())

    if (merged["sentiment_bin"] == "UNKNOWN").sum() == len(merged):
        raise RuntimeError(
            "직접 병합 후에도 감정이 전부 UNKNOWN입니다. "
            "segment_sentiment_binary_primary.csv의 predicted_label_standard 값을 확인하세요."
        )

    return merged, keywords


def build_keyword_map(keywords):
    kw = keywords.copy()
    if "aspect_cluster_id" not in kw.columns and "cluster_id" in kw.columns:
        kw["aspect_cluster_id"] = kw["cluster_id"]
    if "top_keywords" not in kw.columns:
        kw["top_keywords"] = ""
    return {
        str(row["aspect_cluster_id"]): clean_text(row["top_keywords"])
        for _, row in kw.iterrows()
    }


def make_overall(df):
    total = len(df)
    pos = int((df["sentiment_bin"] == "POSITIVE").sum())
    neg = int((df["sentiment_bin"] == "NEGATIVE").sum())
    unk = int((~df["sentiment_bin"].isin(["POSITIVE", "NEGATIVE"])).sum())

    return pd.DataFrame([
        ["분석 segment 수", total],
        ["분석 review 수", df["review_id"].nunique() if "review_id" in df.columns else ""],
        ["강의 수", df["course_name"].nunique()],
        ["평가 요인 cluster 수", df["aspect_cluster_id"].nunique()],
        ["긍정 segment 수", pos],
        ["부정 segment 수", neg],
        ["기타/미확인 감정 segment 수", unk],
        ["긍정 segment 비율(%)", pct(pos, total)],
        ["부정 segment 비율(%)", pct(neg, total)],
        ["평균 별점", round(float(df["review_rating"].dropna().mean()), 3) if df["review_rating"].notna().any() else ""],
    ], columns=["지표", "값"])


def make_aspect_summary(df, keywords):
    kmap = build_keyword_map(keywords)
    rows = []

    for cid, g in df.groupby("aspect_cluster_id"):
        n = len(g)
        pos = int((g["sentiment_bin"] == "POSITIVE").sum())
        neg = int((g["sentiment_bin"] == "NEGATIVE").sum())
        high_neg = int((g["rating_satisfaction_signal"].isin(HIGH_RATING) & (g["sentiment_bin"] == "NEGATIVE")).sum())
        low_pos = int((g["rating_satisfaction_signal"].isin(LOW_RATING) & (g["sentiment_bin"] == "POSITIVE")).sum())

        rows.append({
            "aspect_cluster_id": cid,
            "top_keywords": kmap.get(str(cid), ""),
            "segment_count": n,
            "review_count": g["review_id"].nunique() if "review_id" in g.columns else "",
            "course_count": g["course_name"].nunique(),
            "positive_count": pos,
            "negative_count": neg,
            "other_sentiment_count": n - pos - neg,
            "positive_ratio_percent": pct(pos, n),
            "negative_ratio_percent": pct(neg, n),
            "avg_review_rating": round(float(g["review_rating"].dropna().mean()), 3) if g["review_rating"].notna().any() else np.nan,
            "high_rating_negative_count": high_neg,
            "low_rating_positive_count": low_pos,
            "course_group_distribution": json.dumps(g["course_group"].value_counts().to_dict(), ensure_ascii=False),
            "top_courses": ", ".join(g["course_name"].dropna().astype(str).value_counts().head(3).index.tolist()),
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["segment_count", "positive_ratio_percent"], ascending=[False, False])
    return out


def make_course_group_summary(df):
    rows = []

    for group_name, g in df.groupby("course_group"):
        n = len(g)
        pos = int((g["sentiment_bin"] == "POSITIVE").sum())
        neg = int((g["sentiment_bin"] == "NEGATIVE").sum())
        mixed_reviews = 0

        if "review_id" in g.columns:
            for _, rg in g.groupby("review_id"):
                s = set(rg["sentiment_bin"])
                if "POSITIVE" in s and "NEGATIVE" in s:
                    mixed_reviews += 1

        rows.append({
            "course_group": group_name,
            "segment_count": n,
            "review_count": g["review_id"].nunique() if "review_id" in g.columns else "",
            "course_count": g["course_name"].nunique(),
            "positive_count": pos,
            "negative_count": neg,
            "positive_ratio_percent": pct(pos, n),
            "negative_ratio_percent": pct(neg, n),
            "mixed_review_count": mixed_reviews,
            "avg_review_rating": round(float(g["review_rating"].dropna().mean()), 3) if g["review_rating"].notna().any() else np.nan,
        })

    return pd.DataFrame(rows)


def make_review_summary(df):
    rows = []
    if "review_id" not in df.columns:
        return pd.DataFrame()

    for rid, g in df.groupby("review_id"):
        sentiments = set(g["sentiment_bin"])
        signal = g["rating_satisfaction_signal"].dropna().astype(str).iloc[0] if g["rating_satisfaction_signal"].notna().any() else "RATING_UNKNOWN"

        rows.append({
            "review_id": rid,
            "course_name": g["course_name"].dropna().astype(str).iloc[0] if len(g) else "",
            "course_group": g["course_group"].dropna().astype(str).iloc[0] if len(g) else "",
            "review_rating": g["review_rating"].dropna().mean() if g["review_rating"].notna().any() else np.nan,
            "rating_satisfaction_signal": signal,
            "segment_count": len(g),
            "positive_segment_count": int((g["sentiment_bin"] == "POSITIVE").sum()),
            "negative_segment_count": int((g["sentiment_bin"] == "NEGATIVE").sum()),
            "mixed_review_flag": "POSITIVE" in sentiments and "NEGATIVE" in sentiments,
            "high_rating_negative_segment_flag": signal in HIGH_RATING and "NEGATIVE" in sentiments,
            "low_rating_positive_segment_flag": signal in LOW_RATING and "POSITIVE" in sentiments,
        })

    return pd.DataFrame(rows)


def top_factor_tables(aspect):
    valid = aspect[(aspect["segment_count"] >= 5) & (aspect["aspect_cluster_id"].astype(str) != "-1")].copy()
    if valid.empty:
        valid = aspect.copy()

    good = valid.sort_values(
        ["positive_ratio_percent", "positive_count", "segment_count"],
        ascending=[False, False, False],
    )
    bad = valid.sort_values(
        ["negative_ratio_percent", "negative_count", "high_rating_negative_count"],
        ascending=[False, False, False],
    )
    return good, bad


def representative_sentences(df, factors, sentiment, n_per_cluster=3):
    rows = []
    for cid in factors["aspect_cluster_id"].head(10):
        g = df[(df["aspect_cluster_id"].astype(str) == str(cid)) & (df["sentiment_bin"] == sentiment)].copy()
        if g.empty:
            continue
        g = g.sort_values(["predicted_score", "review_rating"], ascending=[False, False], na_position="last")
        for rank, (_, r) in enumerate(g.head(n_per_cluster).iterrows(), 1):
            rows.append({
                "aspect_cluster_id": cid,
                "rank": rank,
                "sentiment": sentiment,
                "course_group": r.get("course_group", ""),
                "course_name": r.get("course_name", ""),
                "review_rating": r.get("review_rating", ""),
                "rating_satisfaction_signal": r.get("rating_satisfaction_signal", ""),
                "predicted_score": r.get("predicted_score", ""),
                "segment_text": clean_text(r.get("segment_text", ""), 220),
            })
    return pd.DataFrame(rows)


def make_graphs(good, bad, cross):
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    FIG_DIR.mkdir(parents=True, exist_ok=True)

    available = {f.name for f in fm.fontManager.ttflist}
    for font in ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]:
        if font in available:
            plt.rcParams["font.family"] = font
            break
    plt.rcParams["axes.unicode_minus"] = False

    def barh(data, value_col, title, fname):
        if data.empty:
            return
        d = data.head(10).copy()
        labels = d["top_keywords"].fillna("").astype(str).map(lambda x: clean_text(x, 30))
        labels = labels.mask(labels.eq(""), d["aspect_cluster_id"].astype(str))
        values = pd.to_numeric(d[value_col], errors="coerce").fillna(0)

        fig, ax = plt.subplots(figsize=(10, max(5, len(d) * 0.48)))
        ax.barh(range(len(d)), values)
        ax.set_yticks(range(len(d)))
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel(value_col)
        fig.tight_layout()
        fig.savefig(FIG_DIR / fname, dpi=200, bbox_inches="tight")
        plt.close(fig)

    barh(good, "positive_ratio_percent", "좋은 강의 요인 Top 10", "good_lecture_factors.png")
    barh(bad, "negative_ratio_percent", "불만 요인 Top 10", "dissatisfaction_factors.png")


def write_report(overall, good, bad, reviews, course_group_summary):
    def metric(name):
        found = overall.loc[overall["지표"] == name, "값"]
        return found.iloc[0] if len(found) else ""

    mixed = int(reviews["mixed_review_flag"].sum()) if not reviews.empty else 0
    high_neg = int(reviews["high_rating_negative_segment_flag"].sum()) if not reviews.empty else 0
    low_pos = int(reviews["low_rating_positive_segment_flag"].sum()) if not reviews.empty else 0

    lines = [
        "# 에브리타임 강의평 분석 결과 보고서 초안",
        "",
        "## 1. 분석 목적",
        "본 분석은 에브리타임 강의평을 문장 및 절 단위로 나누고, 각 문장이 어떤 평가 요인을 말하는지와 해당 감정이 긍정인지 부정인지 파악하기 위해 수행하였다. 별점은 문장 감정의 정답 라벨로 사용하지 않고, 리뷰 전체 만족도를 나타내는 보조 신호로만 활용하였다.",
        "",
        "## 2. 분석 데이터 개요",
        f"- 분석 segment 수: {metric('분석 segment 수')}개",
        f"- 분석 review 수: {metric('분석 review 수')}개",
        f"- 평가 요인 cluster 수: {metric('평가 요인 cluster 수')}개",
        f"- 긍정 segment 수: {metric('긍정 segment 수')}개",
        f"- 부정 segment 수: {metric('부정 segment 수')}개",
        f"- 긍정 segment 비율: {metric('긍정 segment 비율(%)')}%",
        f"- 부정 segment 비율: {metric('부정 segment 비율(%)')}%",
        "",
        "## 3. 별점만으로는 부족한 이유",
        f"- 긍정과 부정이 한 리뷰 안에 함께 나타난 mixed review는 {mixed}개로 확인되었다.",
        f"- 높은 별점 리뷰 안에서도 부정 segment가 포함된 사례는 {high_neg}개로 확인되었다.",
        f"- 낮은 별점 리뷰 안에서도 긍정 segment가 포함된 사례는 {low_pos}개로 확인되었다.",
        "따라서 별점은 감정 정답 라벨이 아니라 전체 만족도 신호로만 해석하는 것이 적절하다.",
        "",
        "## 4. 좋은 강의 요인",
    ]

    for i, (_, r) in enumerate(good.head(10).iterrows(), 1):
        kw = clean_text(r.get("top_keywords", "")) or f"cluster {r.get('aspect_cluster_id')}"
        lines.append(f"{i}. {kw} - 긍정 비율 {r.get('positive_ratio_percent')}%, segment {r.get('segment_count')}개")

    lines += ["", "## 5. 불만 요인"]

    for i, (_, r) in enumerate(bad.head(10).iterrows(), 1):
        kw = clean_text(r.get("top_keywords", "")) or f"cluster {r.get('aspect_cluster_id')}"
        lines.append(f"{i}. {kw} - 부정 비율 {r.get('negative_ratio_percent')}%, segment {r.get('segment_count')}개")

    lines += [
        "",
        "## 6. 과목군 비교",
        "글쓰기와 실용영어 계열을 분리하여 비교하면, 과목군별로 학생들이 중요하게 언급하는 요인이 다르게 나타날 수 있다. 글쓰기 계열은 글쓰기 과제, 첨삭, 평가 기준이 중요하고, 실용영어 계열은 영어 사용 부담, 스피킹/라이팅 시험, 원어민 수업 방식 등이 주요 요인으로 해석될 수 있다.",
        "",
    ]

    if not course_group_summary.empty:
        for _, r in course_group_summary.iterrows():
            lines.append(
                f"- {r.get('course_group')}: segment {r.get('segment_count')}개, "
                f"긍정 {r.get('positive_ratio_percent')}%, 부정 {r.get('negative_ratio_percent')}%, "
                f"평균 별점 {r.get('avg_review_rating')}"
            )

    lines += [
        "",
        "## 7. 결론",
        "분석 결과, 학생들의 강의 평가는 단순히 좋다 또는 나쁘다로만 나뉘지 않았다. 하나의 리뷰 안에서도 교수 설명, 수업 운영, 과제 부담, 시험 난이도, 평가 방식 등 여러 요인에 대한 감정이 동시에 나타났다. 따라서 강의평 분석에서는 별점보다 문장 및 절 단위의 평가 요인과 감정을 함께 보는 방식이 더 적절하다.",
        "",
        "## 8. 한계 및 향후 방향",
        "- 자동 감정분석 모델 결과이므로 일부 오분류가 존재할 수 있다.",
        "- cluster 이름은 대표 키워드와 대표 문장을 보고 연구자가 최종 명명해야 한다.",
        "- 추후 대표 문장 7개 정도를 수동 검증하여 모델 결과의 신뢰도를 보완할 필요가 있다.",
    ]

    (OUT_DIR / "report_conclusion_draft.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("직접 Colab 결과 기반 보고서 분석 시작")
    print("COLAB_DIR:", COLAB_DIR)
    print("OUT_DIR:", OUT_DIR)
    print("=" * 80)

    merged, keywords = load_direct_colab_results()

    # 직접 병합한 파일도 저장해서 이후 확인 가능하게 함
    save_csv(merged, OUT_DIR / "segment_aspect_sentiment_merged_DIRECT_CHECK.csv")

    overall = make_overall(merged)
    aspect = make_aspect_summary(merged, keywords)
    course_group_summary = make_course_group_summary(merged)
    reviews = make_review_summary(merged)
    good, bad = top_factor_tables(aspect)

    crosstab = pd.crosstab(
        merged["rating_satisfaction_signal"],
        merged["sentiment_bin"],
        margins=True,
    ).reset_index()

    rep_pos = representative_sentences(merged, good, "POSITIVE")
    rep_neg = representative_sentences(merged, bad, "NEGATIVE")

    case_cols = [c for c in [
        "segment_id", "review_id", "aspect_cluster_id", "course_group", "course_name", "professor_id",
        "review_rating", "rating_satisfaction_signal", "predicted_label_standard",
        "predicted_score", "segment_text"
    ] if c in merged.columns]

    high_neg = merged[
        merged["rating_satisfaction_signal"].isin(HIGH_RATING)
        & (merged["sentiment_bin"] == "NEGATIVE")
    ][case_cols].copy()

    low_pos = merged[
        merged["rating_satisfaction_signal"].isin(LOW_RATING)
        & (merged["sentiment_bin"] == "POSITIVE")
    ][case_cols].copy()

    save_csv(overall, OUT_DIR / "overall_summary.csv")
    save_csv(aspect, OUT_DIR / "aspect_summary.csv")
    save_csv(course_group_summary, OUT_DIR / "course_group_summary.csv")
    save_csv(reviews, OUT_DIR / "review_level_summary.csv")
    save_csv(good, OUT_DIR / "good_lecture_factors_report.csv")
    save_csv(bad, OUT_DIR / "dissatisfaction_factors_report.csv")
    save_csv(crosstab, OUT_DIR / "rating_signal_sentiment_crosstab_report.csv")
    save_csv(rep_pos, OUT_DIR / "representative_positive_sentences.csv")
    save_csv(rep_neg, OUT_DIR / "representative_negative_sentences.csv")
    save_csv(high_neg, OUT_DIR / "high_rating_negative_segments_for_report.csv")
    save_csv(low_pos, OUT_DIR / "low_rating_positive_segments_for_report.csv")

    make_graphs(good, bad, crosstab)
    write_report(overall, good, bad, reviews, course_group_summary)

    xlsx_path = OUT_DIR / "report_tables.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        overall.to_excel(writer, sheet_name="overall", index=False)
        course_group_summary.to_excel(writer, sheet_name="course_group", index=False)
        aspect.head(300).to_excel(writer, sheet_name="aspect_summary", index=False)
        good.head(100).to_excel(writer, sheet_name="good_factors", index=False)
        bad.head(100).to_excel(writer, sheet_name="bad_factors", index=False)
        crosstab.to_excel(writer, sheet_name="rating_sentiment", index=False)
        reviews.head(5000).to_excel(writer, sheet_name="review_summary", index=False)
        rep_pos.head(1000).to_excel(writer, sheet_name="positive_sentences", index=False)
        rep_neg.head(1000).to_excel(writer, sheet_name="negative_sentences", index=False)
        high_neg.head(1000).to_excel(writer, sheet_name="high_rating_negative", index=False)
        low_pos.head(1000).to_excel(writer, sheet_name="low_rating_positive", index=False)

    print("=" * 80)
    print("완료")
    print("보고서 초안:", OUT_DIR / "report_conclusion_draft.md")
    print("통합 엑셀:", xlsx_path)
    print("검사용 직접 병합 파일:", OUT_DIR / "segment_aspect_sentiment_merged_DIRECT_CHECK.csv")
    print("=" * 80)


if __name__ == "__main__":
    main()
