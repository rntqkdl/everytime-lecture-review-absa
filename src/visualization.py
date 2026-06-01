from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.io_utils import resolve_path


def configure_korean_font() -> None:
    plt.rcParams["axes.unicode_minus"] = False
    for font in ("Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"):
        try:
            plt.rcParams["font.family"] = font
            return
        except Exception:
            continue


def _save(path: str | Path) -> Path:
    output_path = resolve_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close()
    return output_path


def save_placeholder(path: str | Path, title: str, message: str) -> Path:
    configure_korean_font()
    plt.figure(figsize=(8, 4))
    plt.axis("off")
    plt.title(title)
    plt.text(0.5, 0.5, message, ha="center", va="center", wrap=True)
    return _save(path)


def plot_count_bar(series: pd.Series, path: str | Path, title: str, xlabel: str = "", ylabel: str = "count") -> Path:
    configure_korean_font()
    counts = series.dropna().astype(str).value_counts()
    if counts.empty:
        return save_placeholder(path, title, "표시할 데이터가 없습니다.")
    plt.figure(figsize=(9, 5))
    counts.plot(kind="bar", color="#3b6ea8")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=30, ha="right")
    return _save(path)


def plot_distribution_table(
    df: pd.DataFrame,
    index_col: str,
    value_col: str,
    path: str | Path,
    title: str,
    normalize: bool = True,
) -> Path:
    configure_korean_font()
    if df.empty or index_col not in df.columns or value_col not in df.columns:
        return save_placeholder(path, title, "표시할 데이터가 없습니다.")
    table = pd.crosstab(df[index_col], df[value_col], normalize="index" if normalize else False)
    if table.empty:
        return save_placeholder(path, title, "표시할 데이터가 없습니다.")
    plt.figure(figsize=(10, max(4, min(12, len(table) * 0.5))))
    table.plot(kind="barh", stacked=True, ax=plt.gca(), colormap="Set2")
    plt.title(title)
    plt.xlabel("ratio" if normalize else "count")
    plt.ylabel(index_col)
    plt.legend(title=value_col, bbox_to_anchor=(1.02, 1), loc="upper left")
    return _save(path)


def plot_rating_signal_negative_ratio(df: pd.DataFrame, path: str | Path) -> Path:
    configure_korean_font()
    required = {"rating_satisfaction_signal", "segment_sentiment_label"}
    if df.empty or not required.issubset(df.columns):
        return save_placeholder(path, "만족도 신호별 부정 segment 비율", "표시할 데이터가 없습니다.")
    order = [
        "VERY_HIGH_SATISFACTION",
        "HIGH_SATISFACTION",
        "MID_SATISFACTION",
        "LOW_SATISFACTION",
        "VERY_LOW_SATISFACTION",
        "RATING_UNKNOWN",
    ]
    ratio = df.groupby("rating_satisfaction_signal")["segment_sentiment_label"].apply(lambda s: (s == "NEGATIVE").mean())
    ratio = ratio.reindex([value for value in order if value in ratio.index])
    if ratio.empty:
        return save_placeholder(path, "만족도 신호별 부정 segment 비율", "표시할 데이터가 없습니다.")
    plt.figure(figsize=(10, 5))
    ratio.plot(kind="line", marker="o", color="#a83b3b")
    plt.title("만족도 신호별 부정 segment 비율")
    plt.xlabel("rating_satisfaction_signal")
    plt.ylabel("negative segment ratio")
    plt.xticks(rotation=30, ha="right")
    return _save(path)


def plot_confusion_matrix(cm_df: pd.DataFrame, path: str | Path, title: str) -> Path:
    configure_korean_font()
    if cm_df.empty:
        return save_placeholder(path, title, "Confusion matrix 데이터가 없습니다.")
    numeric = cm_df.select_dtypes(include="number")
    if numeric.empty:
        return save_placeholder(path, title, "Confusion matrix 데이터가 없습니다.")
    plt.figure(figsize=(6, 5))
    image = plt.imshow(numeric.values, cmap="Blues")
    plt.colorbar(image, fraction=0.046, pad=0.04)
    plt.xticks(range(len(numeric.columns)), numeric.columns, rotation=30, ha="right")
    plt.yticks(range(len(numeric.index)), numeric.index)
    for y in range(numeric.shape[0]):
        for x in range(numeric.shape[1]):
            plt.text(x, y, int(numeric.iloc[y, x]), ha="center", va="center", color="black")
    plt.title(title)
    return _save(path)
