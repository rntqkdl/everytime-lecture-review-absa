from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import ensure_output_dirs, load_config, read_csv_safely
from src.visualization import configure_korean_font, plot_rating_signal_negative_ratio, save_placeholder


def read_optional(path: Path) -> pd.DataFrame:
    return read_csv_safely(path) if path.exists() else pd.DataFrame()


def save_bar(df: pd.DataFrame, label_col: str, value_col: str, path: Path, title: str, xlabel: str) -> None:
    configure_korean_font()
    if df.empty or label_col not in df.columns or value_col not in df.columns:
        save_placeholder(path, title, "표시할 데이터가 없습니다.")
        return
    data = df.copy().head(15)
    labels = data[label_col].fillna("").astype(str)
    values = pd.to_numeric(data[value_col], errors="coerce").fillna(0)
    plt.figure(figsize=(10, max(4, len(data) * 0.45)))
    plt.barh(labels, values, color="#4c78a8")
    plt.gca().invert_yaxis()
    plt.title(title)
    plt.xlabel(xlabel)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_mixed_ratio(mixed: pd.DataFrame, merged: pd.DataFrame, path: Path) -> None:
    configure_korean_font()
    if merged.empty or "review_id" not in merged.columns:
        save_placeholder(path, "복합 감정 리뷰 비율", "표시할 데이터가 없습니다.")
        return
    total = merged["review_id"].nunique()
    mixed_count = mixed["review_id"].nunique() if not mixed.empty and "review_id" in mixed.columns else 0
    normal_count = max(0, total - mixed_count)
    plt.figure(figsize=(6, 4))
    plt.bar(["복합 감정", "그 외"], [mixed_count, normal_count], color=["#f58518", "#4c78a8"])
    plt.title("복합 감정 리뷰 비율")
    plt.ylabel("리뷰 수")
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_aspect_sentiment_distribution(merged: pd.DataFrame, path: Path) -> None:
    configure_korean_font()
    if merged.empty or "cluster_id" not in merged.columns or "segment_sentiment_label" not in merged.columns:
        save_placeholder(path, "평가 요인별 감정 분포", "표시할 데이터가 없습니다.")
        return
    top_clusters = merged["cluster_id"].value_counts().head(12).index
    data = merged[merged["cluster_id"].isin(top_clusters)].copy()
    table = pd.crosstab(data["cluster_id"], data["segment_sentiment_label"], normalize="index")
    plt.figure(figsize=(10, max(4, len(table) * 0.45)))
    table.plot(kind="barh", stacked=True, ax=plt.gca(), colormap="Set2")
    plt.title("평가 요인 cluster별 감정 분포")
    plt.xlabel("비율")
    plt.ylabel("cluster_id")
    plt.legend(title="감정", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def main() -> None:
    config = load_config()
    ensure_output_dirs(config)
    sentiment_dir = Path(config["output_dirs"]["sentiment"])
    insights_dir = Path(config["output_dirs"]["insights"])
    figures_dir = Path(config["output_dirs"]["figures"])

    merged = read_optional(sentiment_dir / "segment_aspect_sentiment_merged.csv")
    mixed = read_optional(sentiment_dir / "mixed_sentiment_reviews.csv")
    good = read_optional(insights_dir / "good_lecture_factors.csv")
    bad = read_optional(insights_dir / "dissatisfaction_factors.csv")
    course_summary = read_optional(insights_dir / "course_factor_summary.csv")
    high_bad = read_optional(insights_dir / "high_rating_negative_factor_summary.csv")
    low_good = read_optional(insights_dir / "low_rating_positive_factor_summary.csv")

    save_bar(good, "interpretation_hint", "positive_ratio", figures_dir / "good_lecture_factors.png", "좋은 강의 요인", "긍정 비율")
    save_bar(bad, "interpretation_hint", "negative_ratio", figures_dir / "dissatisfaction_factors.png", "불만 요인", "부정 비율")
    plot_aspect_sentiment_distribution(merged, figures_dir / "aspect_sentiment_distribution.png")
    plot_mixed_ratio(mixed, merged, figures_dir / "mixed_sentiment_ratio.png")
    plot_rating_signal_negative_ratio(merged, figures_dir / "rating_signal_vs_negative_ratio.png")
    save_bar(high_bad, "cluster_id", "segment_count", figures_dir / "high_rating_negative_factors.png", "높은 별점 리뷰 안의 부정 요인", "segment 수")
    save_bar(low_good, "cluster_id", "segment_count", figures_dir / "low_rating_positive_factors.png", "낮은 별점 리뷰 안의 긍정 요인", "segment 수")
    save_bar(course_summary, "aspect_cluster_id", "segment_count", figures_dir / "course_factor_summary.png", "강의군별 요인 요약", "segment 수")
    print(f"시각화 저장 완료: {figures_dir}")


if __name__ == "__main__":
    main()
