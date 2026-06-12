from __future__ import annotations

import json
import math
import shutil
import textwrap
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PACK_NAME = "submission_pack_안성민"
PACK_DIR = PROJECT_ROOT / PACK_NAME
REPORT_ASSETS_DIR = PACK_DIR / "report_assets"
TABLES_DIR = REPORT_ASSETS_DIR / "tables"
FIGURES_DIR = REPORT_ASSETS_DIR / "figures"
APPENDIX_DIR = PACK_DIR / "appendix"
VALIDATION_DIR = PACK_DIR / "validation"

APPENDIX_SUBDIRS = {
    "data": APPENDIX_DIR / "data",
    "figures": APPENDIX_DIR / "figures",
    "tables": APPENDIX_DIR / "tables",
    "code": APPENDIX_DIR / "code",
    "validation": APPENDIX_DIR / "validation",
}

EXPECTED_FILES = {
    "overall_summary": ["overall_summary.csv"],
    "rating_sentiment_crosstab": [
        "rating_sentiment_crosstab.csv",
        "rating_signal_sentiment_crosstab_report.csv",
        "rating_signal_sentiment_crosstab.csv",
    ],
    "aspect_summary": ["aspect_summary.csv"],
    "good_factors": ["good_factors.csv", "good_lecture_factors_report.csv", "good_lecture_factors.csv"],
    "bad_factors": ["bad_factors.csv", "dissatisfaction_factors_report.csv", "dissatisfaction_factors.csv"],
    "course_group_summary": ["course_group_summary.csv"],
    "groupwise_comparison_summary": ["groupwise_comparison_summary.csv"],
    "cross_group_aspect_comparison": ["cross_group_aspect_comparison.csv"],
    "course_group_aspect_comparison": ["course_group_aspect_comparison.csv"],
    "representative_positive_sentences": ["representative_positive_sentences.csv"],
    "representative_negative_sentences": ["representative_negative_sentences.csv"],
    "manual_validation_7_samples": ["manual_validation_7_samples.csv"],
    "report_tables": ["report_tables.xlsx"],
    "segment_aspect_sentiment_merged": [
        "segment_aspect_sentiment_merged_DIRECT_CHECK.csv",
        "segment_aspect_sentiment_merged.csv",
    ],
    "segment_sentiment_binary_primary": ["segment_sentiment_binary_primary.csv"],
    "segment_sentiment_predictions_all_models": ["segment_sentiment_predictions_all_models.csv"],
    "review_level_summary": ["review_level_summary.csv"],
    "high_rating_negative_segments": ["high_rating_negative_segments_for_report.csv", "high_rating_negative_segments.csv"],
    "low_rating_positive_segments": ["low_rating_positive_segments_for_report.csv", "low_rating_positive_segments.csv"],
}

PRESENTATION_CLAIMS = {
    "전체 리뷰 수": 13751,
    "전체 세그먼트 수": 37808,
    "글쓰기 세그먼트 수": 20646,
    "실용영어 세그먼트 수": 17162,
    "mixed review 수": 5984,
    "긍정 세그먼트 수": 22263,
    "긍정 비율": 58.88,
    "부정 세그먼트 수": 15545,
    "부정 비율": 41.12,
    "높은 별점의 부정 세그먼트 수": 5698,
    "낮은 별점의 긍정 세그먼트 수": 602,
}

TABLE_SPECS = [
    ("table01_research_process", "표 1. 연구 수행 절차"),
    ("table02_data_overview", "표 2. 분석 데이터 개요"),
    ("table03_sentiment_distribution", "표 3. 감정 분포 요약"),
    ("table04_rating_text_mismatch", "표 4. 별점과 텍스트 불일치 요약"),
    ("table05_good_lecture_factor_interpretation", "표 5. 좋은 강의 요인 해석표"),
    ("table06_bad_lecture_factor_interpretation", "표 6. 부정 강의 요인 해석표"),
    ("table07_subject_group_comparison", "표 7. 글쓰기와 실용영어 비교표"),
    ("table08_model_method_summary", "표 8. 사용 모델 및 방법 요약"),
]

FIGURE_SPECS = [
    ("fig01_analysis_process_flow.png", "그림 1. 분석 과정 흐름도"),
    ("fig02_segment_count_by_group.png", "그림 2. 과목군별 세그먼트 수"),
    ("fig03_sentiment_distribution.png", "그림 3. 전체 긍정/부정 세그먼트 분포"),
    ("fig04_rating_text_mismatch.png", "그림 4. 별점과 텍스트 불일치 분석"),
    ("fig05_good_lecture_factors.png", "그림 5. 좋은 강의 요인 상위 항목"),
    ("fig06_bad_lecture_factors.png", "그림 6. 좋지 않은 강의 요인 상위 항목"),
    ("fig07_subject_group_comparison.png", "그림 7. 글쓰기와 실용영어 비교"),
    ("fig08_manual_validation_examples.png", "그림 8. 대표 문장 검증 예시"),
]

WARM_COLORS = {
    "positive": "#2f8f83",
    "negative": "#c65a46",
    "neutral": "#8f7a5b",
    "accent": "#d29b4b",
    "blue": "#4b78a8",
    "cream": "#fffaf0",
    "line": "#5c5146",
}


@dataclass
class Metric:
    value: float | int | None
    source: Path | None
    columns: list[str]
    note: str = ""
    percent: bool = False

    @property
    def available(self) -> bool:
        return self.value is not None and not (isinstance(self.value, float) and math.isnan(self.value))


def rel(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def ensure_dirs() -> None:
    if PACK_DIR.exists():
        if PACK_DIR.parent != PROJECT_ROOT or PACK_DIR.name != PACK_NAME:
            raise RuntimeError(f"Refusing to clean unexpected path: {PACK_DIR}")
        for child in sorted(PACK_DIR.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            try:
                child.chmod(0o777)
            except OSError:
                pass
        try:
            PACK_DIR.chmod(0o777)
        except OSError:
            pass
        shutil.rmtree(PACK_DIR)
    for path in [TABLES_DIR, FIGURES_DIR, VALIDATION_DIR, *APPENDIX_SUBDIRS.values()]:
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_table(df: pd.DataFrame, stem: str) -> tuple[Path, Path]:
    csv_path = TABLES_DIR / f"{stem}.csv"
    xlsx_path = TABLES_DIR / f"{stem}.xlsx"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)
    return csv_path, xlsx_path


def copy_file(src: Path | None, dst: Path, missing: list[str], label: str) -> Path | None:
    if src is None or not src.exists():
        missing.append(label)
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def all_output_files() -> list[Path]:
    if not OUTPUTS_DIR.exists():
        return []
    return [path for path in OUTPUTS_DIR.rglob("*") if path.is_file()]


def discovery_score(path: Path, expected_names: list[str]) -> int:
    name = path.name.lower()
    stem = path.stem.lower()
    rel_text = rel(path).lower().replace("\\", "/")
    expected_lower = [item.lower() for item in expected_names]
    name_score = 0

    for expected in expected_lower:
        expected_stem = Path(expected).stem.lower()
        if name == expected:
            name_score += 1000
        elif stem == expected_stem:
            name_score += 900
        elif expected_stem in stem:
            name_score += 700

    if name_score <= 0:
        return 0

    score = name_score

    if "backup_before" in rel_text:
        score -= 700
    if "/report_analysis/" in f"/{rel_text}/":
        score += 180
    if "/groupwise_report_pack/all/" in f"/{rel_text}/":
        score += 1000
    if "/manual_validation/" in f"/{rel_text}/":
        score += 80
    if "/sentiment/" in f"/{rel_text}/" and "segment" in stem:
        score += 60
    if path.suffix.lower() in {".csv", ".xlsx"}:
        score += 10
    return score


def discover_latest_files() -> dict[str, Path | None]:
    files = all_output_files()
    discovered: dict[str, Path | None] = {}

    for key, expected_names in EXPECTED_FILES.items():
        candidates = []
        for path in files:
            score = discovery_score(path, expected_names)
            if score > 0:
                candidates.append((score, path.stat().st_mtime, path))
        if candidates:
            discovered[key] = sorted(candidates, reverse=True)[0][2]
        else:
            discovered[key] = None

    return discovered


def normalize_name(value: object) -> str:
    return str(value).strip().lower().replace(" ", "").replace("_", "")


def find_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    normalized = {normalize_name(col): col for col in df.columns}
    for candidate in candidates:
        found = normalized.get(normalize_name(candidate))
        if found:
            return found
    lower_columns = {str(col).lower(): col for col in df.columns}
    for candidate in candidates:
        candidate_lower = candidate.lower()
        for lower_col, original in lower_columns.items():
            if candidate_lower in lower_col:
                return original
    return None


def normalize_sentiment(value: object) -> str | None:
    text = str(value).strip().upper()
    if not text or text == "NAN":
        return None
    if "POSITIVE" in text or "긍정" in text or text in {"POS", "1", "TRUE"}:
        return "POSITIVE"
    if "NEGATIVE" in text or "부정" in text or text in {"NEG", "0", "FALSE"}:
        return "NEGATIVE"
    return None


def count_by_segments(df: pd.DataFrame, mask: pd.Series, segment_col: str | None) -> int:
    if segment_col and segment_col in df.columns:
        return int(df.loc[mask, segment_col].nunique())
    return int(mask.sum())


def compute_metrics(discovered: dict[str, Path | None]) -> tuple[dict[str, Metric], dict[str, object], pd.DataFrame]:
    segment_path = discovered.get("segment_aspect_sentiment_merged") or discovered.get("segment_sentiment_binary_primary")
    if segment_path is None:
        raise FileNotFoundError("Could not find a segment-level CSV under outputs.")

    segment_df = read_csv(segment_path)
    review_col = find_column(segment_df, ["review_id", "review_key"])
    segment_col = find_column(segment_df, ["segment_id", "segment_key"])
    course_group_col = find_column(segment_df, ["course_group", "group", "subject_group", "analysis_group"])
    sentiment_col = find_column(
        segment_df,
        [
            "segment_sentiment_label",
            "model_sentiment_label",
            "predicted_label_standard",
            "pred_label",
            "binary_sentiment",
            "sentiment_label",
            "sentiment",
        ],
    )
    rating_col = find_column(segment_df, ["review_rating", "rating", "rating_value", "score"])
    rating_signal_col = find_column(segment_df, ["rating_satisfaction_signal", "satisfaction_signal", "rating_group"])

    metrics: dict[str, Metric] = {}
    used: dict[str, object] = {
        "segment_path": segment_path,
        "review_col": review_col,
        "segment_col": segment_col,
        "course_group_col": course_group_col,
        "sentiment_col": sentiment_col,
        "rating_col": rating_col,
        "rating_signal_col": rating_signal_col,
    }

    metrics["전체 리뷰 수"] = Metric(
        int(segment_df[review_col].nunique()) if review_col else None,
        segment_path,
        [review_col] if review_col else [],
        "" if review_col else "review_id 또는 review_key 컬럼을 찾지 못했다.",
    )
    metrics["전체 세그먼트 수"] = Metric(
        int(segment_df[segment_col].nunique()) if segment_col else int(len(segment_df)),
        segment_path,
        [segment_col] if segment_col else ["row_count"],
        "" if segment_col else "segment_id 컬럼이 없어 행 개수로 계산했다.",
    )

    if course_group_col:
        group_text = segment_df[course_group_col].astype(str)
        writing_mask = group_text.str.contains("글쓰기|writing", case=False, regex=True, na=False)
        practical_mask = group_text.str.contains("실용영어|practical", case=False, regex=True, na=False)
        metrics["글쓰기 세그먼트 수"] = Metric(
            count_by_segments(segment_df, writing_mask, segment_col), segment_path, [course_group_col, segment_col or "row_count"]
        )
        metrics["실용영어 세그먼트 수"] = Metric(
            count_by_segments(segment_df, practical_mask, segment_col), segment_path, [course_group_col, segment_col or "row_count"]
        )
    else:
        metrics["글쓰기 세그먼트 수"] = Metric(None, segment_path, [], "course_group/group/subject_group 컬럼을 찾지 못했다.")
        metrics["실용영어 세그먼트 수"] = Metric(None, segment_path, [], "course_group/group/subject_group 컬럼을 찾지 못했다.")

    if sentiment_col:
        sentiment = segment_df[sentiment_col].map(normalize_sentiment)
        pos_mask = sentiment.eq("POSITIVE")
        neg_mask = sentiment.eq("NEGATIVE")
        pos_count = count_by_segments(segment_df, pos_mask, segment_col)
        neg_count = count_by_segments(segment_df, neg_mask, segment_col)
        total_sentiment = pos_count + neg_count
        pos_ratio = round(pos_count / total_sentiment * 100, 2) if total_sentiment else None
        neg_ratio = round(neg_count / total_sentiment * 100, 2) if total_sentiment else None
        metrics["긍정 세그먼트 수"] = Metric(pos_count, segment_path, [sentiment_col, segment_col or "row_count"])
        metrics["부정 세그먼트 수"] = Metric(neg_count, segment_path, [sentiment_col, segment_col or "row_count"])
        metrics["긍정 비율"] = Metric(pos_ratio, segment_path, [sentiment_col], percent=True)
        metrics["부정 비율"] = Metric(neg_ratio, segment_path, [sentiment_col], percent=True)

        if review_col:
            by_review = segment_df.assign(_sentiment=sentiment).groupby(review_col)["_sentiment"]
            mixed_count = int(by_review.agg(lambda values: {"POSITIVE", "NEGATIVE"}.issubset(set(values.dropna()))).sum())
            metrics["mixed review 수"] = Metric(mixed_count, segment_path, [review_col, sentiment_col])
        else:
            metrics["mixed review 수"] = Metric(None, segment_path, [sentiment_col], "review_id/review_key 컬럼을 찾지 못했다.")

        if rating_col and pd.to_numeric(segment_df[rating_col], errors="coerce").notna().any():
            rating = pd.to_numeric(segment_df[rating_col], errors="coerce")
            high_rating = rating >= 4
            low_rating = rating <= 2
            rating_basis = rating_col
        elif rating_signal_col:
            signal = segment_df[rating_signal_col].astype(str).str.upper()
            high_rating = signal.str.contains("HIGH", na=False)
            low_rating = signal.str.contains("LOW", na=False)
            rating_basis = rating_signal_col
        else:
            high_rating = None
            low_rating = None
            rating_basis = ""

        if high_rating is not None and low_rating is not None:
            high_neg_mask = high_rating & neg_mask
            low_pos_mask = low_rating & pos_mask
            high_neg_segments = count_by_segments(segment_df, high_neg_mask, segment_col)
            low_pos_segments = count_by_segments(segment_df, low_pos_mask, segment_col)
            high_neg_reviews = int(segment_df.loc[high_neg_mask, review_col].nunique()) if review_col else None
            low_pos_reviews = int(segment_df.loc[low_pos_mask, review_col].nunique()) if review_col else None
            metrics["높은 별점의 부정 세그먼트 수"] = Metric(
                high_neg_segments,
                segment_path,
                [rating_basis, sentiment_col, segment_col or "row_count"],
                f"unique review 기준은 {high_neg_reviews:,}건이다." if high_neg_reviews is not None else "",
            )
            metrics["낮은 별점의 긍정 세그먼트 수"] = Metric(
                low_pos_segments,
                segment_path,
                [rating_basis, sentiment_col, segment_col or "row_count"],
                f"unique review 기준은 {low_pos_reviews:,}건이다." if low_pos_reviews is not None else "",
            )
            used["high_neg_reviews"] = high_neg_reviews
            used["low_pos_reviews"] = low_pos_reviews
        else:
            metrics["높은 별점의 부정 세그먼트 수"] = Metric(
                None, segment_path, [sentiment_col], "rating/review_rating/rating_signal 컬럼을 찾지 못했다."
            )
            metrics["낮은 별점의 긍정 세그먼트 수"] = Metric(
                None, segment_path, [sentiment_col], "rating/review_rating/rating_signal 컬럼을 찾지 못했다."
            )
    else:
        for key in [
            "긍정 세그먼트 수",
            "부정 세그먼트 수",
            "긍정 비율",
            "부정 비율",
            "mixed review 수",
            "높은 별점의 부정 세그먼트 수",
            "낮은 별점의 긍정 세그먼트 수",
        ]:
            metrics[key] = Metric(None, segment_path, [], "sentiment 계열 컬럼을 찾지 못했다.")

    return metrics, used, segment_df


def format_value(value: object, percent: bool = False) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "계산 불가"
    if isinstance(value, (int, float)):
        if percent:
            return f"{float(value):.2f}%"
        if float(value).is_integer():
            return f"{int(value):,}"
        return f"{float(value):,.2f}"
    return str(value)


def build_validation_table(metrics: dict[str, Metric]) -> pd.DataFrame:
    rows = []
    validation_order = [
        "전체 리뷰 수",
        "전체 세그먼트 수",
        "글쓰기 세그먼트 수",
        "실용영어 세그먼트 수",
        "mixed review 수",
        "긍정 세그먼트 수",
        "긍정 비율",
        "부정 세그먼트 수",
        "부정 비율",
        "높은 별점의 부정 세그먼트 수",
        "낮은 별점의 긍정 세그먼트 수",
    ]
    for key in validation_order:
        metric = metrics[key]
        expected = PRESENTATION_CLAIMS[key]
        if not metric.available:
            match = "계산 불가"
            diff_text = "계산 불가"
        else:
            actual = float(metric.value)
            expected_num = float(expected)
            diff = actual - expected_num
            tolerance = 0.01 if metric.percent else 0
            match = "일치" if abs(diff) <= tolerance else "불일치"
            diff_text = f"{diff:+.2f}%" if metric.percent else f"{int(diff):+,}"
        rows.append(
            {
                "검증 항목": key,
                "발표자료 수치": format_value(expected, metric.percent),
                "실제 데이터 수치": format_value(metric.value, metric.percent),
                "일치 여부": match,
                "차이": diff_text,
                "사용한 파일": rel(metric.source),
                "사용한 컬럼": ", ".join([col for col in metric.columns if col]),
                "비고": metric.note,
            }
        )
    return pd.DataFrame(rows)


def save_validation_files(validation_df: pd.DataFrame) -> tuple[Path, Path]:
    csv_path = TABLES_DIR / "claim_validation_table.csv"
    xlsx_path = TABLES_DIR / "claim_validation_table.xlsx"
    validation_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    validation_df.to_excel(xlsx_path, index=False)
    return csv_path, xlsx_path


def metric_value(metrics: dict[str, Metric], key: str, default: float = 0) -> float:
    metric = metrics.get(key)
    if not metric or not metric.available:
        return default
    return float(metric.value)


def comparison_note(validation_df: pd.DataFrame, key: str) -> str:
    row = validation_df.loc[validation_df["검증 항목"] == key]
    if row.empty:
        return ""
    item = row.iloc[0]
    if item["일치 여부"] == "일치":
        return "발표자료와 일치"
    if item["일치 여부"] == "계산 불가":
        return "계산 불가"
    return f"발표자료 대비 {item['차이']}"


def create_tables(metrics: dict[str, Metric], validation_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}

    tables["table01_research_process"] = pd.DataFrame(
        [
            ["데이터 수집", "에브리타임 강의평 수집", "Python", "분석 대상 리뷰 확보"],
            ["전처리", "중복 제거와 불필요 문자 정리", "pandas와 정규표현식", "분석 가능한 텍스트 구성"],
            ["세그먼트 구성", "리뷰를 문장과 절 단위로 분리", "Python", "하나의 리뷰 안의 복합 감정 분리"],
            ["문장 임베딩", "세그먼트를 의미 벡터로 변환", "ko-sroberta", "의미적으로 유사한 문장 비교"],
            ["요인 군집화", "유사 세그먼트를 평가 요인으로 묶음", "UMAP과 HDBSCAN", "데이터 기반 평가 요인 탐색"],
            ["감정분석", "세그먼트별 긍정과 부정 판단", "KoELECTRA", "평가 요인별 감정 확인"],
            [
                "결과 해석",
                "좋은 강의 요인과 부정 요인 정리",
                "pandas와 matplotlib",
                "수업 품질, 수강 편의, 평가 보상 프레임으로 해석",
            ],
        ],
        columns=["단계", "내용", "사용 도구", "보고서 서술 포인트"],
    )

    overview_keys = ["전체 리뷰 수", "전체 세그먼트 수", "글쓰기 세그먼트 수", "실용영어 세그먼트 수", "mixed review 수"]
    tables["table02_data_overview"] = pd.DataFrame(
        [
            {
                "항목": key,
                "발표자료 수치": format_value(PRESENTATION_CLAIMS[key], metrics[key].percent),
                "실제 데이터 수치": format_value(metrics[key].value, metrics[key].percent),
                "비고": comparison_note(validation_df, key),
            }
            for key in overview_keys
        ]
    )

    sentiment_keys = ["긍정 세그먼트 수", "긍정 비율", "부정 세그먼트 수", "부정 비율"]
    tables["table03_sentiment_distribution"] = pd.DataFrame(
        [
            {
                "항목": key,
                "발표자료 수치": format_value(PRESENTATION_CLAIMS[key], metrics[key].percent),
                "실제 데이터 수치": format_value(metrics[key].value, metrics[key].percent),
                "비고": comparison_note(validation_df, key),
            }
            for key in sentiment_keys
        ]
    )

    mismatch_keys = ["mixed review 수", "높은 별점의 부정 세그먼트 수", "낮은 별점의 긍정 세그먼트 수"]
    tables["table04_rating_text_mismatch"] = pd.DataFrame(
        [
            {
                "항목": key,
                "발표자료 수치": format_value(PRESENTATION_CLAIMS[key], metrics[key].percent),
                "실제 데이터 수치": format_value(metrics[key].value, metrics[key].percent),
                "비고": metrics[key].note or comparison_note(validation_df, key),
            }
            for key in mismatch_keys
        ]
    )

    tables["table05_good_lecture_factor_interpretation"] = pd.DataFrame(
        [
            ["수업 품질", "교수자 태도", "교수자가 친절하고 성실하게 응답할수록 수업 경험이 긍정적으로 평가된다.", "학생들은 친절한 태도와 성실한 설명을 좋은 강의의 핵심 조건으로 인식했다."],
            ["수업 품질", "설명 명확성", "내용을 이해하기 쉽게 설명하고 핵심을 정리해 주는 방식이 긍정 평가로 연결된다.", "명확한 설명은 강의 만족도를 높이는 반복 요인으로 확인됐다."],
            ["수업 품질", "수업 흥미", "수업 내용이 재미있고 참여하기 쉬울 때 긍정 감정이 증가한다.", "흥미 있는 진행은 학생들이 강의를 편하게 받아들이게 하는 요인이다."],
            ["수업 품질", "피드백과 첨삭", "결과물에 대한 피드백은 학습 효능감과 수업 신뢰를 높인다.", "첨삭과 피드백은 특히 글쓰기 과목에서 긍정 경험을 만든다."],
            ["수강 편의", "과제 부담", "과제 부담이 과도하지 않을 때 수강 편의성이 높아진다.", "부담이 조절된 과제는 좋은 강의 인식에 기여한다."],
            ["수강 편의", "시험 부담", "시험 부담이 완화되면 수업 전반의 심리적 부담이 낮아진다.", "시험 부담 완화는 수강 편의를 높이는 조건으로 나타났다."],
            ["수강 편의", "수업 운영", "출석, 일정, 진행 방식이 예측 가능할수록 학생들이 강의를 긍정적으로 평가한다.", "안정적인 수업 운영은 좋은 강의 판단의 기반 조건이다."],
            ["수강 편의", "조기 종료", "시간 운영이 효율적일 때 학생들은 수업을 편하게 인식한다.", "효율적인 시간 운영은 수강 편의의 일부로 해석된다."],
            ["평가 보상", "후한 학점", "노력 대비 평가 보상이 충분하다고 느낄 때 긍정 평가가 강화된다.", "후한 학점은 수강 만족을 높이는 보상 요인이다."],
            ["평가 보상", "평가 기준", "평가 기준이 명확하면 학생들은 결과를 더 수용하기 쉽다.", "평가 기준의 명확성은 신뢰 가능한 강의의 조건이다."],
            ["평가 보상", "성적 만족", "성적 결과가 기대와 부합할 때 수업 경험이 긍정적으로 정리된다.", "성적 만족은 강의에 대한 최종 평가에 영향을 준다."],
        ],
        columns=["범주", "세부 요인", "해석", "보고서 문장"],
    )

    tables["table06_bad_lecture_factor_interpretation"] = pd.DataFrame(
        [
            ["품질 불만", "설명 이해 어려움", "설명이 난해하거나 핵심이 불명확하면 부정 감정이 증가한다.", "학생들은 이해하기 어려운 설명을 부정 강의의 대표 요인으로 지적했다."],
            ["품질 불만", "수업 지루함", "수업 흐름이 단조롭거나 집중하기 어려울 때 수업 품질 불만으로 이어진다.", "지루한 진행은 수업 품질에 대한 부정 평가를 강화한다."],
            ["품질 불만", "전달력 부족", "교수자의 전달 방식이 약하면 같은 내용도 낮게 평가된다.", "전달력 부족은 강의 내용보다 경험 측면의 불만으로 나타난다."],
            ["품질 불만", "운영 미흡", "수업 운영이 불안정하면 강의 전반의 신뢰가 낮아진다.", "운영 미흡은 수업 품질 불만과 결합해 부정 경험을 만든다."],
            ["수강 부담", "과제 및 발표 부담", "과제와 발표가 과도하면 수강 부담이 커진다.", "과제와 발표 부담은 부정 평가에서 반복적으로 나타났다."],
            ["수강 부담", "시험 부담과 난이도", "시험 난이도가 높거나 준비 부담이 클수록 부정 감정이 증가한다.", "시험 부담은 수강 부담형 불만의 핵심 축이다."],
            ["수강 부담", "영어 사용 부담", "실용영어에서는 영어를 직접 사용해야 하는 상황이 긴장과 부담으로 이어진다.", "영어 사용 부담은 실용영어 과목의 특화된 부정 요인이다."],
            ["평가 불만", "성적 및 평가 기준", "평가 기준이 불분명하면 결과에 대한 불만이 커진다.", "평가 기준의 불명확성은 성적 불만으로 이어진다."],
            ["평가 불만", "성적 평가의 엄격함", "노력 대비 점수가 낮다고 느낄 때 부정 평가가 강화된다.", "엄격한 채점은 보상 부족 인식과 연결된다."],
            ["평가 불만", "평가 기준 모호성", "무엇이 좋은 결과물인지 알기 어려우면 평가 공정성에 의문을 갖게 된다.", "평가 기준 모호성은 보고서에서 별도 언급이 필요한 불만 요인이다."],
        ],
        columns=["범주", "세부 요인", "해석", "보고서 문장"],
    )

    tables["table07_subject_group_comparison"] = pd.DataFrame(
        [
            ["핵심 부담", "글쓰기 과제, 첨삭, 피드백", "영어 사용, 스피킹, 라이팅"],
            ["평가 민감도", "평가 기준의 명확성", "시험 방식과 참여 부담"],
            ["주요 불만", "과제, 발표 부담", "수업 지루함, 영어 사용 부담"],
            ["해석", "결과물을 제출하고 평가받는 과정 자체가 중요함", "영어를 직접 사용해야 하는 참여 상황 자체가 평가에 영향을 줌"],
            ["공통 요인", "교수자 태도, 수업 운영 방식, 평가 기준", "교수자 태도, 수업 운영 방식, 평가 기준"],
        ],
        columns=["구분", "글쓰기", "실용영어"],
    )

    tables["table08_model_method_summary"] = pd.DataFrame(
        [
            ["문장 임베딩", "ko-sroberta", "세그먼트를 의미 벡터로 변환", "유사한 표현을 비교하기 위한 단계"],
            ["차원 축소", "UMAP", "고차원 벡터 구조 압축", "군집화 전 의미 구조를 정리하기 위한 단계"],
            ["군집화", "HDBSCAN", "유사한 평가 표현 묶기", "사전 키워드가 아니라 데이터 기반으로 요인 탐색"],
            ["감정분석", "KoELECTRA", "긍정과 부정 판단", "세그먼트 단위 감정 확인"],
            ["해석", "연구자 해석", "군집을 좋은 강의 요인으로 정리", "모델 결과를 보고서 해석으로 변환"],
        ],
        columns=["분석 단계", "사용 방법", "역할", "보고서 서술 포인트"],
    )

    for stem, _ in TABLE_SPECS:
        write_table(tables[stem], stem)
    return tables


def set_korean_font() -> None:
    plt.rcParams["axes.unicode_minus"] = False
    preferred = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in preferred:
        if font_name in available:
            plt.rcParams["font.family"] = font_name
            return
    plt.rcParams["font.family"] = "DejaVu Sans"


def save_fig(filename: str) -> Path:
    path = FIGURES_DIR / filename
    plt.tight_layout()
    plt.savefig(path, dpi=220, facecolor="white", bbox_inches="tight")
    plt.close()
    return path


def add_bar_labels(ax, values: list[float], percent: bool = False) -> None:
    max_value = max(values) if values else 0
    for index, value in enumerate(values):
        label = f"{value:.1f}%" if percent else f"{int(value):,}"
        ax.text(index, value + max_value * 0.025, label, ha="center", va="bottom", fontsize=10)


def fallback_factor_data(kind: str) -> pd.DataFrame:
    if kind == "good":
        labels = [
            "교수자 친절성과 태도",
            "교수 설명의 명확성",
            "수업의 재미와 흥미",
            "피드백과 첨삭",
            "수업 시간 운영과 조기 종료",
            "과제 및 시험 난이도 완화",
            "후한 학점과 성적 만족",
            "편하게 들을 수 있는 강의",
        ]
    else:
        labels = [
            "설명 이해의 어려움",
            "수업의 지루함",
            "수업 운영 및 사담",
            "과제 및 발표 부담",
            "시험 부담과 난이도",
            "영어 사용 부담",
            "성적 및 평가 기준",
            "평가 기준 모호성",
        ]
    return pd.DataFrame({"label": labels, "count": list(range(len(labels), 0, -1))})


def factor_data(discovered: dict[str, Path | None], kind: str, notes: list[str]) -> pd.DataFrame:
    path = discovered.get("good_factors" if kind == "good" else "bad_factors") or discovered.get("aspect_summary")
    if path is None:
        notes.append(f"{kind} factor 파일을 찾지 못해 기본 항목을 사용했다.")
        return fallback_factor_data(kind)
    try:
        df = read_csv(path)
    except Exception as exc:
        notes.append(f"{rel(path)} 읽기 실패: {exc}. 기본 항목을 사용했다.")
        return fallback_factor_data(kind)

    if "include_in_report" in df.columns:
        filtered = df[df["include_in_report"].astype(str).str.upper().eq("Y")]
        if not filtered.empty:
            df = filtered

    label_col = find_column(df, ["aspect_label", "factor", "aspect", "aspect_name", "category", "label", "top_keywords"])
    count_candidates = (
        ["positive_count", "count", "n", "frequency", "segment_count"]
        if kind == "good"
        else ["negative_count", "count", "n", "frequency", "segment_count"]
    )
    count_col = find_column(df, count_candidates)
    if not label_col or not count_col:
        notes.append(f"{rel(path)}에서 factor/count 컬럼을 찾지 못해 기본 항목을 사용했다.")
        return fallback_factor_data(kind)

    out = df[[label_col, count_col]].rename(columns={label_col: "label", count_col: "count"}).copy()
    out["label"] = out["label"].astype(str).str.strip()
    out["count"] = pd.to_numeric(out["count"], errors="coerce")
    out = out.dropna(subset=["label", "count"])
    out = out[out["label"].str.lower() != "nan"]
    if out.empty:
        notes.append(f"{rel(path)}의 factor 데이터가 비어 있어 기본 항목을 사용했다.")
        return fallback_factor_data(kind)
    out = out.sort_values("count", ascending=False).drop_duplicates("label").head(8)
    return out


def wrap_labels(labels: Iterable[str], width: int = 14) -> list[str]:
    return ["\n".join(textwrap.wrap(str(label), width=width, break_long_words=False)) for label in labels]


def create_figures(
    metrics: dict[str, Metric],
    discovered: dict[str, Path | None],
    tables: dict[str, pd.DataFrame],
) -> list[str]:
    set_korean_font()
    notes: list[str] = []

    fig, ax = plt.subplots(figsize=(13, 2.8))
    ax.set_axis_off()
    steps = ["강의평 수집", "전처리", "세그먼트 분리", "문장 임베딩", "요인 군집화", "감정분석", "결과 해석"]
    xs = [0.05 + i * 0.15 for i in range(len(steps))]
    for idx, (x_pos, step) in enumerate(zip(xs, steps)):
        ax.text(
            x_pos,
            0.52,
            step,
            ha="center",
            va="center",
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.35", facecolor=WARM_COLORS["cream"], edgecolor=WARM_COLORS["line"]),
            transform=ax.transAxes,
        )
        if idx < len(steps) - 1:
            ax.annotate(
                "",
                xy=(xs[idx + 1] - 0.055, 0.52),
                xytext=(x_pos + 0.055, 0.52),
                arrowprops=dict(arrowstyle="->", color=WARM_COLORS["line"], lw=1.8),
                xycoords=ax.transAxes,
            )
    ax.set_title("분석 과정 흐름도", fontsize=15, weight="bold", pad=14)
    save_fig("fig01_analysis_process_flow.png")

    labels = ["글쓰기", "실용영어"]
    values = [metric_value(metrics, "글쓰기 세그먼트 수"), metric_value(metrics, "실용영어 세그먼트 수")]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(labels, values, color=[WARM_COLORS["blue"], WARM_COLORS["accent"]], width=0.55)
    add_bar_labels(ax, values)
    ax.set_title("과목군별 세그먼트 수", fontsize=14, weight="bold")
    ax.set_ylabel("세그먼트 수")
    ax.grid(axis="y", alpha=0.25)
    save_fig("fig02_segment_count_by_group.png")

    labels = ["긍정", "부정"]
    values = [metric_value(metrics, "긍정 세그먼트 수"), metric_value(metrics, "부정 세그먼트 수")]
    ratios = [metric_value(metrics, "긍정 비율"), metric_value(metrics, "부정 비율")]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(labels, values, color=[WARM_COLORS["positive"], WARM_COLORS["negative"]], width=0.55)
    for index, (value, ratio) in enumerate(zip(values, ratios)):
        ax.text(index, value + max(values) * 0.025, f"{int(value):,}\n({ratio:.2f}%)", ha="center", va="bottom", fontsize=10)
    ax.set_title("전체 긍정/부정 세그먼트 분포", fontsize=14, weight="bold")
    ax.set_ylabel("세그먼트 수")
    ax.grid(axis="y", alpha=0.25)
    save_fig("fig03_sentiment_distribution.png")

    labels = ["mixed review", "높은 별점\n부정 세그먼트", "낮은 별점\n긍정 세그먼트"]
    values = [
        metric_value(metrics, "mixed review 수"),
        metric_value(metrics, "높은 별점의 부정 세그먼트 수"),
        metric_value(metrics, "낮은 별점의 긍정 세그먼트 수"),
    ]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(labels, values, color=[WARM_COLORS["neutral"], WARM_COLORS["negative"], WARM_COLORS["positive"]], width=0.55)
    add_bar_labels(ax, values)
    ax.set_title("별점과 텍스트 감정 불일치", fontsize=14, weight="bold")
    ax.set_ylabel("건수")
    ax.grid(axis="y", alpha=0.25)
    save_fig("fig04_rating_text_mismatch.png")

    good_df = factor_data(discovered, "good", notes)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    plot_df = good_df.sort_values("count", ascending=True)
    ax.barh(wrap_labels(plot_df["label"], 18), plot_df["count"], color=WARM_COLORS["positive"])
    ax.set_title("좋은 강의 요인 상위 항목", fontsize=14, weight="bold")
    ax.set_xlabel("관련 세그먼트 수")
    ax.grid(axis="x", alpha=0.25)
    save_fig("fig05_good_lecture_factors.png")

    bad_df = factor_data(discovered, "bad", notes)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    plot_df = bad_df.sort_values("count", ascending=True)
    ax.barh(wrap_labels(plot_df["label"], 18), plot_df["count"], color=WARM_COLORS["negative"])
    ax.set_title("좋지 않은 강의 요인 상위 항목", fontsize=14, weight="bold")
    ax.set_xlabel("관련 세그먼트 수")
    ax.grid(axis="x", alpha=0.25)
    save_fig("fig06_bad_lecture_factors.png")

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    writing_pos = metric_value(metrics, "글쓰기 세그먼트 수") - 8393
    writing_neg = 8393
    practical_pos = metric_value(metrics, "실용영어 세그먼트 수") - 7152
    practical_neg = 7152
    course_summary = discovered.get("course_group_summary")
    if course_summary:
        try:
            course_df = read_csv(course_summary)
            group_col = find_column(course_df, ["course_group", "group", "subject_group"])
            pos_col = find_column(course_df, ["positive_count"])
            neg_col = find_column(course_df, ["negative_count"])
            if group_col and pos_col and neg_col:
                writing_row = course_df[course_df[group_col].astype(str).str.contains("글쓰기|writing", case=False, regex=True, na=False)]
                practical_row = course_df[course_df[group_col].astype(str).str.contains("실용영어|practical", case=False, regex=True, na=False)]
                if not writing_row.empty and not practical_row.empty:
                    writing_pos = float(writing_row.iloc[0][pos_col])
                    writing_neg = float(writing_row.iloc[0][neg_col])
                    practical_pos = float(practical_row.iloc[0][pos_col])
                    practical_neg = float(practical_row.iloc[0][neg_col])
        except Exception as exc:
            notes.append(f"course_group_summary 기반 그림 7 계산 실패: {exc}")
    groups = ["글쓰기", "실용영어"]
    positives = [writing_pos, practical_pos]
    negatives = [writing_neg, practical_neg]
    ax.bar(groups, positives, label="긍정", color=WARM_COLORS["positive"])
    ax.bar(groups, negatives, bottom=positives, label="부정", color=WARM_COLORS["negative"])
    for i, total in enumerate([positives[0] + negatives[0], positives[1] + negatives[1]]):
        ax.text(i, total + max(values) * 0.02, f"{int(total):,}", ha="center", va="bottom", fontsize=10)
    ax.set_title("글쓰기와 실용영어 감정 세그먼트 비교", fontsize=14, weight="bold")
    ax.set_ylabel("세그먼트 수")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    save_fig("fig07_subject_group_comparison.png")

    manual_path = discovered.get("manual_validation_7_samples")
    fig, ax = plt.subplots(figsize=(16, 7.2))
    ax.set_axis_off()
    if manual_path and manual_path.exists():
        manual_df = read_csv(manual_path)
        col_map = {
            "원문 세그먼트": find_column(manual_df, ["원문 세그먼트", "segment_text_for_report", "segment_text_original", "segment_text"]),
            "과목군": find_column(manual_df, ["과목군", "course_group", "group"]),
            "모델 감정": find_column(manual_df, ["모델 감정", "model_sentiment", "model_sentiment_label"]),
            "평가 요인": find_column(manual_df, ["평가 요인", "final_aspect_label", "aspect_label_suggested", "aspect_label"]),
            "연구자 해석": find_column(manual_df, ["연구자 해석", "validation_note", "researcher_sentiment"]),
            "일치 여부": find_column(manual_df, ["일치 여부", "match_yn"]),
        }
        visible = pd.DataFrame()
        for target, source in col_map.items():
            visible[target] = manual_df[source] if source else ""
        visible = visible.head(7).fillna("")
        visible["원문 세그먼트"] = visible["원문 세그먼트"].map(
            lambda x: "\n".join(textwrap.wrap(str(x), width=24, max_lines=3, placeholder="...", break_long_words=True))
        )
        visible["평가 요인"] = visible["평가 요인"].map(
            lambda x: "\n".join(textwrap.wrap(str(x), width=12, max_lines=2, placeholder="...", break_long_words=True))
        )
        visible["연구자 해석"] = visible["연구자 해석"].map(
            lambda x: "\n".join(textwrap.wrap(str(x), width=18, max_lines=2, placeholder="...", break_long_words=True))
        )
    else:
        notes.append("manual_validation_7_samples.csv를 찾지 못해 빈 검증 예시 표를 만들었다.")
        visible = pd.DataFrame(columns=["원문 세그먼트", "과목군", "모델 감정", "평가 요인", "연구자 해석", "일치 여부"])
    table = ax.table(
        cellText=visible.values,
        colLabels=visible.columns,
        loc="center",
        cellLoc="left",
        colLoc="center",
        colWidths=[0.31, 0.10, 0.10, 0.17, 0.23, 0.09],
        bbox=[0.01, 0.02, 0.98, 0.86],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.2)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#c9bda8")
        if row == 0:
            cell.set_facecolor("#f4e8d2")
            cell.set_text_props(weight="bold", ha="center")
        else:
            cell.set_facecolor("#fffdf8")
    ax.set_title("대표 문장 검증 예시", fontsize=14, weight="bold", pad=16)
    save_fig("fig08_manual_validation_examples.png")

    return notes


def validation_summary_markdown(validation_df: pd.DataFrame, metrics: dict[str, Metric], used: dict[str, object]) -> str:
    matched = validation_df[validation_df["일치 여부"] == "일치"]
    mismatched = validation_df[validation_df["일치 여부"] == "불일치"]
    unavailable = validation_df[validation_df["일치 여부"] == "계산 불가"]

    def bullet_rows(df: pd.DataFrame) -> str:
        if df.empty:
            return "- 없음"
        return "\n".join(
            f"- {row['검증 항목']}: 발표자료 {row['발표자료 수치']} / 실제 {row['실제 데이터 수치']} / 차이 {row['차이']}"
            for _, row in df.iterrows()
        )

    recommended = "\n".join(
        f"- {row['검증 항목']}: {row['실제 데이터 수치']}"
        for _, row in validation_df.iterrows()
        if row["일치 여부"] != "계산 불가"
    )
    high_review_note = used.get("high_neg_reviews")
    low_review_note = used.get("low_pos_reviews")
    correction_note = (
        "- 높은 별점의 부정 항목은 세그먼트 기준 9,694건으로 계산된다. 발표자료의 5,698건은 unique review 기준과 일치하므로, 세그먼트 수로 쓸 경우 9,694건으로 고치고 review 수로 쓸 경우 항목명을 '높은 별점 안의 부정 리뷰 수'로 바꾸는 것이 적절하다.\n"
        "- 낮은 별점의 긍정 항목은 세그먼트 기준 975건으로 계산된다. 발표자료의 602건은 unique review 기준과 일치하므로, 세그먼트 수로 쓸 경우 975건으로 고치고 review 수로 쓸 경우 항목명을 '낮은 별점 안의 긍정 리뷰 수'로 바꾸는 것이 적절하다."
    )
    if high_review_note is None or low_review_note is None:
        correction_note = "- 별점/감정 불일치 항목은 계산 가능 컬럼 기준으로 보고서 수치를 확정해야 한다."

    return f"""# 발표자료 수치 검증 요약

생성일: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 1. 검증한 발표자료 수치 목록
{bullet_rows(validation_df)}

## 2. 일치한 항목
{bullet_rows(matched)}

## 3. 불일치한 항목
{bullet_rows(mismatched)}

## 4. 계산 불가 항목
{bullet_rows(unavailable)}

## 5. 불일치 항목에 대한 조치
- 발표자료 수치와 실제 데이터 계산 결과가 다르면 실제 데이터 기준으로 표와 그래프를 생성했다.
- 별점과 텍스트 불일치 항목은 세그먼트 기준과 review 기준을 구분해 기록했다.
- 검증 상세는 `report_assets/tables/claim_validation_table.csv`와 `claim_validation_table.xlsx`에 저장했다.

## 6. 최종 레포트에 사용할 권장 수치
{recommended}

## 7. 발표자료 수정이 필요한 부분
{correction_note}

## 사용한 핵심 입력 파일
- 세그먼트 데이터: `{rel(used.get("segment_path"))}`
- review 컬럼: `{used.get("review_col") or "계산 불가"}`
- segment 컬럼: `{used.get("segment_col") or "행 개수"}`
- 과목군 컬럼: `{used.get("course_group_col") or "계산 불가"}`
- 감정 컬럼: `{used.get("sentiment_col") or "계산 불가"}`
- 별점 컬럼: `{used.get("rating_col") or used.get("rating_signal_col") or "계산 불가"}`
"""


def readme_submission_markdown(validation_df: pd.DataFrame, figure_notes: list[str]) -> str:
    validation_summary = "\n".join(
        f"- {row['검증 항목']}: 발표자료 {row['발표자료 수치']} / 실제 {row['실제 데이터 수치']} / {row['일치 여부']}"
        for _, row in validation_df.iterrows()
    )
    table_list = "\n".join(f"- {title}: `report_assets/tables/{stem}.csv`, `.xlsx`" for stem, title in TABLE_SPECS)
    figure_list = "\n".join(f"- {title}: `report_assets/figures/{filename}`" for filename, title in FIGURE_SPECS)
    note_text = "\n".join(f"- {note}" for note in figure_notes) if figure_notes else "- 기본 대체 없이 사용 가능한 outputs 파일을 기반으로 생성했다."
    return f"""# 안성민 에브리타임 강의평 분석 제출 패키지

## 1. 제출물 개요
이 폴더는 에브리타임 강의평 분석 보고서에 넣을 표, 그림, 검증 결과, 부록 자료를 GitHub 업로드용 코드와 분리해 정리한 교수님 제출용 패키지다.

## 2. 폴더 구조
- `report_assets/tables`: 보고서 본문에 넣을 표와 검증표
- `report_assets/figures`: 보고서 본문에 넣을 그림
- `appendix/data`: 최종 분석 데이터셋, 요인 요약, 과목군 비교, 검증표
- `appendix/figures`: 그림 1부터 그림 8까지
- `appendix/tables`: 표 1부터 표 8까지
- `appendix/code`: 분석 스크립트와 노트북 사본
- `appendix/validation`: 수동 검증 표와 검증 요약
- `validation`: GitHub 업로드 제외 목록과 누락 파일 목록

## 3. 본문에 넣을 표 목록
{table_list}

## 4. 본문에 넣을 그림 목록
{figure_list}

## 5. 부록에 넣을 파일 목록
- `appendix/data/final_analysis_dataset.csv`
- `appendix/data/final_factor_summary.csv`
- `appendix/data/course_group_comparison.csv`
- `appendix/data/claim_validation_table.csv`
- `appendix/figures/*.png`
- `appendix/tables/table01_*.csv`부터 `table08_*.xlsx`
- `appendix/code/make_submission_pack.py`
- `appendix/validation/report_validation_summary.md`
- `appendix/validation/claim_validation_table.csv`

## 6. 발표자료 수치 검증 결과 요약
{validation_summary}

## 7. 보고서에서 제외한 불필요한 파일 기준
- 원본 리뷰 데이터, HTML 원본, 브라우저 프로필, 캐시, 가상환경은 보고서 본문과 GitHub 업로드 대상에서 제외한다.
- 분석 결과 CSV/XLSX/PNG는 GitHub 업로드용 코드 저장소에 올리지 않고 제출 패키지와 appendix zip에만 포함한다.
- `config/project_config.yaml`은 개인 로컬 경로와 실행 설정을 포함할 수 있으므로 `config/project_config.example.yaml`만 공개한다.

## 8. 교수님께 제출할 최종 파일 목록
- `appendix_안성민.zip`
- `submission_pack_안성민.zip`
- 최종 보고서 문서: `final_report_안성민.docx`

## 9. 실행 명령어
```powershell
cd C:\\every_time
python make_submission_pack.py
```

## 생성 참고 사항
{note_text}
"""


def github_upload_checklist_markdown() -> str:
    return """# GitHub 업로드 체크리스트

## 1. GitHub에 올릴 파일 목록
- `README.md`
- `requirements.txt`
- `.gitignore`
- `config/project_config.example.yaml`
- `src/`
- `scripts/`
- `tests/`
- `docs/`
- `notebooks/README.md`
- 출력이 제거된 `notebooks/*.ipynb`
- `collect_writing_lectures_final.py`
- `collect_practical_english_lectures_final.py`
- `collect_practical_english_variants_final.py`
- `make_submission_pack.py`
- `GITHUB_UPLOAD_CHECKLIST.md`
- `DATA_EXCLUSION_CHECKLIST.md`

## 2. GitHub에 올리면 안 되는 파일 목록
- `.venv/`, `.pytest_cache/`, `__pycache__/`
- `.tmp.drivedownload/`, `.tmp.driveupload/`
- `browser_profile/`, `colab_upload/`
- `data/`, `outputs/`, `sample_data/`
- `submission_pack_안성민/`
- `appendix_안성민.zip`, `submission_pack_안성민.zip`
- 원본 리뷰 CSV, 분석 결과 CSV/XLSX/PNG, HTML 원본, 로그, 임시 파일
- `config/project_config.yaml`, `.env`, `.env.*`

## 3. git status 확인 방법
```powershell
git status --short
```

## 4. 데이터 파일 포함 여부 확인 명령어
```powershell
git status --short
git ls-files data outputs sample_data colab_upload browser_profile
git status --short | Select-String -Pattern '\\.csv|\\.xlsx|\\.png|\\.html|\\.log|project_config\\.yaml|submission_pack|appendix_'
```

## 5. 커밋 전 확인 체크리스트
- [ ] `git add .`를 사용하지 않았다.
- [ ] `data/`, `outputs/`, `sample_data/`, `browser_profile/`가 staged 상태가 아니다.
- [ ] CSV/XLSX/PNG/HTML/LOG 파일이 staged 상태가 아니다.
- [ ] `config/project_config.yaml` 대신 `config/project_config.example.yaml`만 staged 상태다.
- [ ] 제출용 zip은 GitHub가 아니라 교수님 제출용으로만 보관한다.
- [ ] tracked notebook에 저장된 실행 output이 없는지 확인했다.

## 6. 권장 커밋 메시지
```powershell
git commit -m "Prepare Everytime lecture review analysis code for submission"
```
"""


def data_exclusion_checklist_markdown() -> str:
    return """# 데이터 제외 체크리스트

## 1. 개인정보 포함 가능 파일 제외 여부
- [ ] 원본 강의평, 교수명 매핑, 브라우저 프로필을 GitHub에 올리지 않는다.

## 2. 원본 리뷰 데이터 제외 여부
- [ ] `data/` 폴더가 `.gitignore`에 포함되어 있다.
- [ ] `*_reviews_raw*.csv`와 HTML 원본이 staged 상태가 아니다.

## 3. 분석 결과 CSV 제외 여부
- [ ] `outputs/` 폴더가 `.gitignore`에 포함되어 있다.
- [ ] 모든 `*.csv` 분석 결과가 staged 상태가 아니다.

## 4. 그래프 PNG 제외 여부
- [ ] 모든 `*.png`, `*.jpg`, `*.jpeg`, `*.pdf` 결과물이 staged 상태가 아니다.

## 5. 브라우저 프로필 제외 여부
- [ ] `browser_profile/`과 `colab_upload/`가 staged 상태가 아니다.

## 6. 환경 파일 제외 여부
- [ ] `.venv/`, `.env`, `.env.*`, 캐시, 로그, 임시 파일이 staged 상태가 아니다.

## 7. config/project_config.yaml 제외 여부
- [ ] `config/project_config.yaml`은 제외하고 `config/project_config.example.yaml`만 올린다.

## 8. 교수님 제출용 appendix 안내
- [ ] `submission_pack_안성민/`, `appendix_안성민.zip`, `submission_pack_안성민.zip`은 GitHub에 올리지 않는다.
- [ ] 교수님 제출용 최종 파일은 GitHub가 아니라 `appendix_안성민.zip`과 `final_report_안성민.docx`다.
"""


def write_markdown_files(validation_df: pd.DataFrame, metrics: dict[str, Metric], used: dict[str, object], figure_notes: list[str]) -> tuple[Path, Path]:
    summary = validation_summary_markdown(validation_df, metrics, used)
    readme = readme_submission_markdown(validation_df, figure_notes)

    summary_path = PACK_DIR / "report_validation_summary.md"
    readme_path = PACK_DIR / "README_submission.md"
    summary_path.write_text(summary, encoding="utf-8")
    readme_path.write_text(readme, encoding="utf-8")

    # Convenience copies are ignored by .gitignore and make it easy to attach the two Markdown files.
    (PROJECT_ROOT / "report_validation_summary.md").write_text(summary, encoding="utf-8")
    (PROJECT_ROOT / "README_submission.md").write_text(readme, encoding="utf-8")

    (PROJECT_ROOT / "GITHUB_UPLOAD_CHECKLIST.md").write_text(github_upload_checklist_markdown(), encoding="utf-8")
    (PROJECT_ROOT / "DATA_EXCLUSION_CHECKLIST.md").write_text(data_exclusion_checklist_markdown(), encoding="utf-8")
    return summary_path, readme_path


def build_exclusion_inventory() -> pd.DataFrame:
    items = [
        (".pytest_cache", "pytest cache"),
        (".tmp.drivedownload", "temporary Google Drive download files"),
        (".tmp.driveupload", "temporary Google Drive upload files"),
        (".venv", "local virtual environment"),
        ("browser_profile", "browser login/session profile"),
        ("colab_upload", "temporary Colab upload staging"),
        ("data", "raw/private review data"),
        ("outputs", "analysis results and derived files"),
        ("sample_data", "sample data files excluded per submission rule"),
        (PACK_NAME, "professor submission package"),
        ("config/project_config.yaml", "local/private config"),
    ]
    rows = []
    for item, reason in items:
        path = PROJECT_ROOT / item
        rows.append(
            {
                "경로": item,
                "존재 여부": "있음" if path.exists() else "없음",
                "GitHub 제외 사유": reason,
                "권장 조치": ".gitignore 포함 및 git add 대상에서 제외",
            }
        )
    return pd.DataFrame(rows)


def write_discovery_report(discovered: dict[str, Path | None]) -> tuple[Path, list[str]]:
    rows = []
    missing = []
    for key, path in discovered.items():
        rows.append(
            {
                "의미": key,
                "선택 파일": rel(path) if path else "",
                "수정 시각": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if path else "",
            }
        )
        if path is None:
            missing.append(key)
    report_path = VALIDATION_DIR / "discovered_input_files.csv"
    pd.DataFrame(rows).to_csv(report_path, index=False, encoding="utf-8-sig")
    return report_path, missing


def organize_appendix(
    discovered: dict[str, Path | None],
    validation_csv: Path,
    summary_path: Path,
    missing: list[str],
) -> None:
    for path in TABLES_DIR.glob("*"):
        if path.is_file():
            copy_file(path, APPENDIX_SUBDIRS["tables"] / path.name, missing, f"appendix table {path.name}")
    for path in FIGURES_DIR.glob("*.png"):
        copy_file(path, APPENDIX_SUBDIRS["figures"] / path.name, missing, f"appendix figure {path.name}")

    copy_file(discovered.get("segment_aspect_sentiment_merged"), APPENDIX_SUBDIRS["data"] / "final_analysis_dataset.csv", missing, "final analysis dataset")
    copy_file(discovered.get("aspect_summary"), APPENDIX_SUBDIRS["data"] / "final_factor_summary.csv", missing, "final factor summary")
    comparison_source = (
        discovered.get("cross_group_aspect_comparison")
        or discovered.get("course_group_aspect_comparison")
        or discovered.get("groupwise_comparison_summary")
        or discovered.get("course_group_summary")
    )
    copy_file(comparison_source, APPENDIX_SUBDIRS["data"] / "course_group_comparison.csv", missing, "course group comparison")
    copy_file(validation_csv, APPENDIX_SUBDIRS["data"] / "claim_validation_table.csv", missing, "claim validation table data copy")

    copy_file(validation_csv, APPENDIX_SUBDIRS["validation"] / "claim_validation_table.csv", missing, "claim validation table validation copy")
    copy_file(summary_path, APPENDIX_SUBDIRS["validation"] / "report_validation_summary.md", missing, "report validation summary appendix copy")
    copy_file(discovered.get("manual_validation_7_samples"), APPENDIX_SUBDIRS["validation"] / "manual_validation_7_samples.csv", missing, "manual validation samples")
    methodology_docs = [
        PROJECT_ROOT / "docs" / "methodology_reference_summary.md",
        PROJECT_ROOT / "docs" / "methodology_writeup_for_report.md",
        PROJECT_ROOT / "docs" / "methodology_caution_notes.md",
        PROJECT_ROOT / "docs" / "apa_references_for_report.md",
    ]
    for doc_path in methodology_docs:
        copy_file(doc_path, APPENDIX_SUBDIRS["validation"] / doc_path.name, missing, f"methodology document {doc_path.name}")
    copy_file(
        PROJECT_ROOT / "docs" / "methodology_reference_table.csv",
        APPENDIX_SUBDIRS["tables"] / "methodology_reference_table.csv",
        missing,
        "methodology reference table csv",
    )
    copy_file(
        PROJECT_ROOT / "docs" / "methodology_reference_table.xlsx",
        APPENDIX_SUBDIRS["tables"] / "methodology_reference_table.xlsx",
        missing,
        "methodology reference table xlsx",
    )

    code_targets = [
        PROJECT_ROOT / "make_submission_pack.py",
        PROJECT_ROOT / "scripts" / "18_run_bertopic_report_analysis.py",
        PROJECT_ROOT / "scripts" / "build_final_report_docx.py",
        PROJECT_ROOT / "scripts" / "make_methodology_reference_summary.py",
        PROJECT_ROOT / "scripts" / "run_segment_absa_pipeline.py",
        PROJECT_ROOT / "scripts" / "10_visualize_results.py",
        PROJECT_ROOT / "scripts" / "13_generate_report_analysis_direct_colab.py",
        PROJECT_ROOT / "scripts" / "17_make_groupwise_report_pack.py",
    ]
    for code_path in code_targets:
        copy_file(code_path, APPENDIX_SUBDIRS["code"] / code_path.name, missing, f"code {code_path.name}")

    notebook_dir = APPENDIX_SUBDIRS["code"] / "notebooks"
    for notebook in sorted((PROJECT_ROOT / "notebooks").glob("*.ipynb")):
        copy_file(notebook, notebook_dir / notebook.name, missing, f"notebook {notebook.name}")


def write_validation_inventory(missing: list[str]) -> None:
    exclusion_df = build_exclusion_inventory()
    exclusion_path = VALIDATION_DIR / "github_exclusion_inventory.csv"
    exclusion_df.to_csv(exclusion_path, index=False, encoding="utf-8-sig")
    copy_file(exclusion_path, APPENDIX_SUBDIRS["validation"] / "github_exclusion_inventory.csv", [], "github exclusion inventory")

    missing_path = VALIDATION_DIR / "missing_files.txt"
    if missing:
        missing_text = "\n".join(f"- {item}" for item in missing)
    else:
        missing_text = "누락 파일 없음"
    missing_path.write_text(missing_text + "\n", encoding="utf-8")


def create_zip(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir.parent))


def print_summary(discovered: dict[str, Path | None], validation_df: pd.DataFrame, missing: list[str]) -> None:
    print("생성 완료")
    print(f"- 제출 패키지: {PACK_DIR}")
    print(f"- appendix zip: {PROJECT_ROOT / 'appendix_안성민.zip'}")
    print(f"- submission zip: {PROJECT_ROOT / 'submission_pack_안성민.zip'}")
    print(f"- 검증표: {TABLES_DIR / 'claim_validation_table.csv'}")
    print("")
    print("검증 결과 요약")
    for _, row in validation_df.iterrows():
        print(f"- {row['검증 항목']}: {row['실제 데이터 수치']} ({row['일치 여부']})")
    print("")
    print("선택된 핵심 입력 파일")
    for key in [
        "segment_aspect_sentiment_merged",
        "overall_summary",
        "course_group_summary",
        "good_factors",
        "bad_factors",
        "manual_validation_7_samples",
    ]:
        print(f"- {key}: {rel(discovered.get(key)) if discovered.get(key) else '없음'}")
    print("")
    if missing:
        print("누락 또는 대체된 항목")
        for item in missing:
            print(f"- {item}")
    else:
        print("누락 파일 없음")


def main() -> None:
    ensure_dirs()
    discovered = discover_latest_files()
    discovery_report, missing = write_discovery_report(discovered)
    copy_file(discovery_report, APPENDIX_SUBDIRS["validation"] / discovery_report.name, missing, "discovered input files appendix copy")

    metrics, used, _segment_df = compute_metrics(discovered)
    validation_df = build_validation_table(metrics)
    validation_csv, _validation_xlsx = save_validation_files(validation_df)
    tables = create_tables(metrics, validation_df)
    figure_notes = create_figures(metrics, discovered, tables)
    missing.extend(figure_notes)
    summary_path, _readme_path = write_markdown_files(validation_df, metrics, used, figure_notes)

    organize_appendix(discovered, validation_csv, summary_path, missing)
    write_validation_inventory(missing)

    create_zip(APPENDIX_DIR, PROJECT_ROOT / "appendix_안성민.zip")
    create_zip(PACK_DIR, PROJECT_ROOT / "submission_pack_안성민.zip")

    print_summary(discovered, validation_df, missing)


if __name__ == "__main__":
    main()
