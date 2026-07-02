from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "evidence_verification"

FINAL_SEGMENT_PATH = ROOT / "outputs" / "bertopic_analysis" / "report_analysis" / "segment_aspect_sentiment_merged_DIRECT_CHECK.csv"
LEGACY_SEGMENT_PATH = ROOT / "outputs" / "report_analysis" / "segment_aspect_sentiment_merged_DIRECT_CHECK.csv"
TOPIC_INFO_PATH = ROOT / "outputs" / "bertopic_analysis" / "bertopic_topic_info.csv"
TOPIC_RUN_LOG_PATH = ROOT / "outputs" / "bertopic_analysis" / "bertopic_run_log.json"
ASPECT_SUMMARY_PATH = ROOT / "outputs" / "bertopic_analysis" / "report_analysis" / "aspect_summary.csv"
GROUPWISE_SUMMARY_PATH = (
    ROOT / "outputs" / "bertopic_analysis" / "report_analysis" / "groupwise_report_pack" / "groupwise_comparison_summary.csv"
)
GOOD_FACTORS_PATH = (
    ROOT / "outputs" / "bertopic_analysis" / "report_analysis" / "groupwise_report_pack" / "ALL" / "good_factors.csv"
)
BAD_FACTORS_PATH = (
    ROOT / "outputs" / "bertopic_analysis" / "report_analysis" / "groupwise_report_pack" / "ALL" / "bad_factors.csv"
)
MANUAL_VALIDATION_PATH = (
    ROOT
    / "outputs"
    / "bertopic_analysis"
    / "report_analysis"
    / "groupwise_report_pack"
    / "ALL"
    / "manual_validation_7_samples.csv"
)
RATING_CROSSTAB_PATH = (
    ROOT
    / "outputs"
    / "bertopic_analysis"
    / "report_analysis"
    / "groupwise_report_pack"
    / "ALL"
    / "rating_sentiment_crosstab.csv"
)
COLAB_SENTIMENT_PATH = ROOT / "outputs" / "colab_results" / "segment_sentiment_binary_primary.csv"
COLAB_CLUSTER_PATH = ROOT / "outputs" / "colab_results" / "segment_embedding_clusters.csv"
COLAB_KEYWORD_PATH = ROOT / "outputs" / "colab_results" / "aspect_cluster_keywords.csv"


@dataclass(frozen=True)
class ReportClaim:
    item: str
    expected: float | int
    actual: float | int | None
    unit: str
    source_file: Path
    formula: str
    tolerance: float = 0.0


def rel(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, **kwargs)


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"필수 검증 데이터가 없습니다: {path}\n"
            "검증 데이터 zip을 프로젝트 루트에 풀어 같은 경로 구조를 맞춘 뒤 다시 실행하세요."
        )


def normalize_sentiment(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().str.upper()
    text = text.replace({"LABEL_1": "POSITIVE", "1": "POSITIVE", "LABEL_0": "NEGATIVE", "0": "NEGATIVE"})
    return text


def count_unique(df: pd.DataFrame, column: str, mask: pd.Series | None = None) -> int:
    target = df if mask is None else df.loc[mask]
    if column in target.columns:
        return int(target[column].nunique())
    return int(len(target))


def pct(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator) * 100, 2) if denominator else 0.0


def format_number(value: float | int | None, unit: str) -> str:
    if value is None:
        return "계산 불가"
    if unit == "%":
        return f"{float(value):.2f}%"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{float(value):,.2f}"


def status_for(claim: ReportClaim) -> tuple[str, str]:
    if claim.actual is None:
        return "계산 불가", ""
    diff = float(claim.actual) - float(claim.expected)
    matched = abs(diff) <= claim.tolerance
    if claim.unit == "%":
        return ("일치" if matched else "불일치"), f"{diff:+.2f}%"
    return ("일치" if matched else "불일치"), f"{int(round(diff)):+,}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_claims(df: pd.DataFrame, topic_info: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    sentiment = normalize_sentiment(df["predicted_label_standard"])
    pos_mask = sentiment.eq("POSITIVE")
    neg_mask = sentiment.eq("NEGATIVE")
    total_segments = count_unique(df, "segment_id")
    total_reviews = count_unique(df, "review_id")

    mixed_review_count = int(
        df.assign(_sentiment=sentiment)
        .groupby("review_id")["_sentiment"]
        .agg(lambda values: {"POSITIVE", "NEGATIVE"}.issubset(set(values)))
        .sum()
    )

    rating = pd.to_numeric(df["review_rating"], errors="coerce")
    high_rating = rating >= 4.0
    low_rating = rating <= 2.0
    high_neg = high_rating & neg_mask
    low_pos = low_rating & pos_mask

    topic_ids = pd.to_numeric(df["bertopic_topic_id"], errors="coerce")
    topic_info_ids = pd.to_numeric(topic_info["Topic"], errors="coerce") if "Topic" in topic_info.columns else pd.Series(dtype=float)

    actuals: dict[str, Any] = {
        "total_segments": total_segments,
        "total_reviews": total_reviews,
        "positive_segments": count_unique(df, "segment_id", pos_mask),
        "negative_segments": count_unique(df, "segment_id", neg_mask),
        "mixed_reviews": mixed_review_count,
        "writing_segments": count_unique(df, "segment_id", df["course_group"].astype(str).eq("글쓰기")),
        "practical_english_segments": count_unique(df, "segment_id", df["course_group"].astype(str).eq("실용영어")),
        "high_rating_negative_segments": count_unique(df, "segment_id", high_neg),
        "high_rating_negative_reviews": count_unique(df, "review_id", high_neg),
        "low_rating_positive_segments": count_unique(df, "segment_id", low_pos),
        "low_rating_positive_reviews": count_unique(df, "review_id", low_pos),
        "bertopic_topics_without_outlier": int(topic_info_ids[topic_info_ids.ne(-1)].nunique()),
        "bertopic_topics_with_outlier": int(topic_info_ids.nunique()),
        "bertopic_outlier_segments": int(topic_ids.eq(-1).sum()),
    }
    actuals["positive_ratio_percent"] = pct(actuals["positive_segments"], total_segments)
    actuals["negative_ratio_percent"] = pct(actuals["negative_segments"], total_segments)

    claims = [
        ReportClaim("전체 리뷰 수", 13751, actuals["total_reviews"], "건", FINAL_SEGMENT_PATH, "review_id 고유값 수"),
        ReportClaim("전체 세그먼트 수", 37808, actuals["total_segments"], "건", FINAL_SEGMENT_PATH, "segment_id 고유값 수"),
        ReportClaim("글쓰기 세그먼트 수", 20646, actuals["writing_segments"], "건", FINAL_SEGMENT_PATH, "course_group == '글쓰기'"),
        ReportClaim(
            "실용영어 세그먼트 수",
            17162,
            actuals["practical_english_segments"],
            "건",
            FINAL_SEGMENT_PATH,
            "course_group == '실용영어'",
        ),
        ReportClaim("mixed review 수", 5984, actuals["mixed_reviews"], "건", FINAL_SEGMENT_PATH, "한 review_id 안에 POSITIVE와 NEGATIVE가 함께 존재"),
        ReportClaim("긍정 세그먼트 수", 22263, actuals["positive_segments"], "건", FINAL_SEGMENT_PATH, "predicted_label_standard == POSITIVE"),
        ReportClaim("긍정 비율", 58.88, actuals["positive_ratio_percent"], "%", FINAL_SEGMENT_PATH, "긍정 세그먼트 / 전체 세그먼트 * 100", 0.01),
        ReportClaim("부정 세그먼트 수", 15545, actuals["negative_segments"], "건", FINAL_SEGMENT_PATH, "predicted_label_standard == NEGATIVE"),
        ReportClaim("부정 비율", 41.12, actuals["negative_ratio_percent"], "%", FINAL_SEGMENT_PATH, "부정 세그먼트 / 전체 세그먼트 * 100", 0.01),
        ReportClaim("높은 별점의 부정 세그먼트 수", 9694, actuals["high_rating_negative_segments"], "건", FINAL_SEGMENT_PATH, "review_rating >= 4.0 AND NEGATIVE"),
        ReportClaim("높은 별점의 부정 리뷰 수", 5698, actuals["high_rating_negative_reviews"], "건", FINAL_SEGMENT_PATH, "review_rating >= 4.0 AND NEGATIVE인 review_id 고유값"),
        ReportClaim("낮은 별점의 긍정 세그먼트 수", 975, actuals["low_rating_positive_segments"], "건", FINAL_SEGMENT_PATH, "review_rating <= 2.0 AND POSITIVE"),
        ReportClaim("낮은 별점의 긍정 리뷰 수", 602, actuals["low_rating_positive_reviews"], "건", FINAL_SEGMENT_PATH, "review_rating <= 2.0 AND POSITIVE인 review_id 고유값"),
        ReportClaim("BERTopic outlier 제외 topic 수", 574, actuals["bertopic_topics_without_outlier"], "개", TOPIC_INFO_PATH, "Topic != -1 고유 topic 수"),
        ReportClaim("BERTopic outlier 포함 topic 수", 575, actuals["bertopic_topics_with_outlier"], "개", TOPIC_INFO_PATH, "Topic 고유값 수"),
        ReportClaim("BERTopic outlier 세그먼트 수", 15746, actuals["bertopic_outlier_segments"], "건", FINAL_SEGMENT_PATH, "bertopic_topic_id == -1"),
    ]

    rows = []
    for claim in claims:
        status, diff = status_for(claim)
        rows.append(
            {
                "검증 항목": claim.item,
                "보고서 기준 수치": format_number(claim.expected, claim.unit),
                "재계산 수치": format_number(claim.actual, claim.unit),
                "일치 여부": status,
                "차이": diff,
                "단위": claim.unit,
                "사용 파일": rel(claim.source_file),
                "계산식": claim.formula,
            }
        )
    return pd.DataFrame(rows), actuals


def make_groupwise_summary(df: pd.DataFrame) -> pd.DataFrame:
    sentiment = normalize_sentiment(df["predicted_label_standard"])
    rows = []
    groups = [("ALL", "전체 통합", pd.Series(True, index=df.index))]
    for label in ["글쓰기", "실용영어"]:
        groups.append((label, label, df["course_group"].astype(str).eq(label)))

    for key, label, mask in groups:
        part = df.loc[mask].copy()
        part_sentiment = sentiment.loc[mask]
        total = count_unique(part, "segment_id")
        pos = count_unique(part, "segment_id", part_sentiment.eq("POSITIVE"))
        neg = count_unique(part, "segment_id", part_sentiment.eq("NEGATIVE"))
        mixed = int(
            part.assign(_sentiment=part_sentiment)
            .groupby("review_id")["_sentiment"]
            .agg(lambda values: {"POSITIVE", "NEGATIVE"}.issubset(set(values)))
            .sum()
        )
        rows.append(
            {
                "group_key": key,
                "group_label": label,
                "segment_count": total,
                "review_count": count_unique(part, "review_id"),
                "course_count": count_unique(part, "course_name"),
                "positive_count": pos,
                "negative_count": neg,
                "positive_ratio_percent": pct(pos, total),
                "negative_ratio_percent": pct(neg, total),
                "mixed_review_count": mixed,
                "avg_review_rating": round(float(pd.to_numeric(part["review_rating"], errors="coerce").mean()), 3),
            }
        )
    return pd.DataFrame(rows)


def make_top_factor_summary() -> pd.DataFrame:
    frames = []
    for kind, path, count_col in [
        ("좋은 강의 요인", GOOD_FACTORS_PATH, "positive_count"),
        ("부정/불만 요인", BAD_FACTORS_PATH, "negative_count"),
    ]:
        if not path.exists():
            continue
        df = read_csv(path, low_memory=False)
        if "include_in_report" in df.columns:
            df = df[df["include_in_report"].fillna("").astype(str).str.upper().eq("Y")]
        df = df[~df["aspect_label"].astype(str).str.contains("미정|기타", na=False)].copy()
        df[count_col] = pd.to_numeric(df[count_col], errors="coerce")
        cols = [
            "aspect_cluster_id",
            "aspect_label",
            "aspect_category",
            "top_keywords",
            "segment_count",
            "review_count",
            "positive_count",
            "negative_count",
            "positive_ratio_percent",
            "negative_ratio_percent",
            "representative_positive",
            "representative_negative",
        ]
        keep = [col for col in cols if col in df.columns]
        top = df.sort_values(count_col, ascending=False).drop_duplicates("aspect_label", keep="first").head(10)[keep].copy()
        top.insert(0, "검증 영역", kind)
        top.insert(1, "정렬 기준", count_col)
        frames.append(top)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def make_inventory(paths: list[tuple[str, Path, str]]) -> pd.DataFrame:
    rows = []
    for label, path, role in paths:
        row: dict[str, Any] = {
            "구분": label,
            "역할": role,
            "경로": rel(path),
            "존재 여부": "있음" if path.exists() else "없음",
            "파일 크기(bytes)": path.stat().st_size if path.exists() else "",
            "sha256": sha256(path) if path.exists() and path.stat().st_size < 200 * 1024 * 1024 else "",
            "행 수": "",
            "주요 컬럼": "",
        }
        if path.exists() and path.suffix.lower() == ".csv":
            try:
                sample = read_csv(path, nrows=5, low_memory=False)
                row["주요 컬럼"] = ", ".join(sample.columns[:12])
                row["행 수"] = max(0, sum(1 for _ in path.open("rb")) - 1)
            except Exception as exc:
                row["주요 컬럼"] = f"읽기 실패: {exc}"
        rows.append(row)
    return pd.DataFrame(rows)


def compare_colab_with_final(final_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if COLAB_SENTIMENT_PATH.exists():
        sentiment = read_csv(COLAB_SENTIMENT_PATH, low_memory=False)
        rows.append(
            {
                "검증 항목": "Colab KoELECTRA 감정분석 결과 행 수",
                "재계산/확인 수치": len(sentiment),
                "기준": len(final_df),
                "일치 여부": "일치" if len(sentiment) == len(final_df) else "불일치",
                "비고": "segment_sentiment_binary_primary.csv와 최종 분석 세그먼트 수 비교",
            }
        )
        if "segment_id" in sentiment.columns and "segment_id" in final_df.columns:
            overlap = len(set(sentiment["segment_id"]).intersection(set(final_df["segment_id"])))
            rows.append(
                {
                    "검증 항목": "Colab 감정분석 segment_id 교집합",
                    "재계산/확인 수치": overlap,
                    "기준": final_df["segment_id"].nunique(),
                    "일치 여부": "일치" if overlap == final_df["segment_id"].nunique() else "불일치",
                    "비고": "최종 분석 데이터가 Colab 감정분석 결과와 같은 세그먼트를 사용했는지 확인",
                }
            )
        if "predicted_label_standard" in sentiment.columns:
            counts = normalize_sentiment(sentiment["predicted_label_standard"]).value_counts().to_dict()
            rows.append(
                {
                    "검증 항목": "Colab 감정 라벨 분포",
                    "재계산/확인 수치": json.dumps(counts, ensure_ascii=False, sort_keys=True),
                    "기준": "POSITIVE/NEGATIVE",
                    "일치 여부": "확인",
                    "비고": "기획서의 KoELECTRA 기반 감정분석 결과 확인",
                }
            )

    if COLAB_CLUSTER_PATH.exists():
        clusters = read_csv(COLAB_CLUSTER_PATH, low_memory=False)
        rows.append(
            {
                "검증 항목": "Colab 임베딩 클러스터 결과 행 수",
                "재계산/확인 수치": len(clusters),
                "기준": len(final_df),
                "일치 여부": "일치" if len(clusters) == len(final_df) else "불일치",
                "비고": "segment_embedding_clusters.csv와 최종 분석 세그먼트 수 비교",
            }
        )
        if "cluster_id" in clusters.columns:
            rows.append(
                {
                    "검증 항목": "Colab 임베딩 클러스터 수",
                    "재계산/확인 수치": int(clusters["cluster_id"].nunique()),
                    "기준": "참고값",
                    "일치 여부": "확인",
                    "비고": "BERTopic 이전 기획서의 문장 임베딩 기반 요인 군집화 결과",
                }
            )

    if LEGACY_SEGMENT_PATH.exists():
        legacy = read_csv(LEGACY_SEGMENT_PATH, low_memory=False)
        rows.append(
            {
                "검증 항목": "BERTopic 이전 직접 병합 분석 데이터 행 수",
                "재계산/확인 수치": len(legacy),
                "기준": len(final_df),
                "일치 여부": "일치" if len(legacy) == len(final_df) else "불일치",
                "비고": "outputs/report_analysis의 기존 분석 산출물도 같은 세그먼트 기반인지 확인",
            }
        )

    return pd.DataFrame(rows)


def build_summary(
    claim_df: pd.DataFrame,
    group_df: pd.DataFrame,
    top_df: pd.DataFrame,
    pipeline_df: pd.DataFrame,
    output_dir: Path,
) -> str:
    matched = int((claim_df["일치 여부"] == "일치").sum())
    total = len(claim_df)
    failed = claim_df[claim_df["일치 여부"] != "일치"]
    top_good = top_df[top_df["검증 영역"].eq("좋은 강의 요인")].head(3) if not top_df.empty else pd.DataFrame()
    top_bad = top_df[top_df["검증 영역"].eq("부정/불만 요인")].head(3) if not top_df.empty else pd.DataFrame()

    lines = [
        "# 최종 분석 근거 검증 요약",
        "",
        f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 검증 수치 일치: {matched}/{total}",
        f"- 출력 폴더: `{rel(output_dir)}`",
        "",
        "## 1. 보고서 핵심 수치 검증",
        "",
    ]
    for _, row in claim_df.iterrows():
        lines.append(
            f"- {row['검증 항목']}: 보고서 {row['보고서 기준 수치']} / 재계산 {row['재계산 수치']} / {row['일치 여부']}"
        )
    if not failed.empty:
        lines.extend(["", "### 불일치 또는 계산 불가 항목"])
        for _, row in failed.iterrows():
            lines.append(f"- {row['검증 항목']}: 차이 {row['차이']} ({row['계산식']})")

    lines.extend(["", "## 2. 과목군 비교 재계산", ""])
    for _, row in group_df.iterrows():
        lines.append(
            f"- {row['group_label']}: 세그먼트 {int(row['segment_count']):,}건, 리뷰 {int(row['review_count']):,}건, "
            f"긍정 {row['positive_ratio_percent']:.2f}%, 부정 {row['negative_ratio_percent']:.2f}%"
        )

    lines.extend(["", "## 3. 상위 요인 확인", ""])
    if not top_good.empty:
        lines.append("- 좋은 강의 요인 상위 3개: " + ", ".join(top_good["aspect_label"].astype(str)))
    if not top_bad.empty:
        lines.append("- 부정/불만 요인 상위 3개: " + ", ".join(top_bad["aspect_label"].astype(str)))

    lines.extend(["", "## 4. 기획서 분석 흐름 확인 파일", ""])
    for _, row in pipeline_df.iterrows():
        lines.append(f"- {row['검증 항목']}: {row['재계산/확인 수치']} / {row['일치 여부']} - {row['비고']}")

    lines.extend(
        [
            "",
            "## 5. 생성된 상세 파일",
            "",
            "- `report_claim_validation.csv`: 보고서 핵심 수치 재계산표",
            "- `groupwise_recalculated.csv`: 글쓰기/실용영어/전체 과목군 비교 재계산",
            "- `top_factors_recalculated.csv`: 좋은 강의 요인과 부정 요인 상위 항목",
            "- `pipeline_evidence_checks.csv`: BERTopic 외 기존 기획서 분석 산출물 확인",
            "- `evidence_file_inventory.csv`: 검증 데이터 파일 목록, 행 수, sha256",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify report evidence from final analysis CSV files.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for verification outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    require_file(FINAL_SEGMENT_PATH)
    require_file(TOPIC_INFO_PATH)

    final_df = read_csv(FINAL_SEGMENT_PATH, low_memory=False)
    topic_info = read_csv(TOPIC_INFO_PATH, low_memory=False)

    claim_df, _actuals = make_claims(final_df, topic_info)
    group_df = make_groupwise_summary(final_df)
    top_df = make_top_factor_summary()
    pipeline_df = compare_colab_with_final(final_df)

    inventory_df = make_inventory(
        [
            ("최종 BERTopic 세그먼트 데이터", FINAL_SEGMENT_PATH, "보고서 핵심 수치와 BERTopic topic_id 검증"),
            ("BERTopic topic info", TOPIC_INFO_PATH, "topic 수, outlier topic 확인"),
            ("BERTopic 실행 로그", TOPIC_RUN_LOG_PATH, "사용 모델과 실행 규모 확인"),
            ("BERTopic aspect summary", ASPECT_SUMMARY_PATH, "요인별 긍정/부정 분포 확인"),
            ("과목군 비교 요약", GROUPWISE_SUMMARY_PATH, "글쓰기/실용영어 비교 확인"),
            ("좋은 강의 요인", GOOD_FACTORS_PATH, "상위 긍정 요인 확인"),
            ("부정/불만 요인", BAD_FACTORS_PATH, "상위 부정 요인 확인"),
            ("수동 검증 예시", MANUAL_VALIDATION_PATH, "대표 문장 검증 예시 확인"),
            ("별점-감정 교차표", RATING_CROSSTAB_PATH, "별점과 텍스트 감정 관계 확인"),
            ("BERTopic 이전 직접 병합 데이터", LEGACY_SEGMENT_PATH, "기존 기획서 분석 결과 확인"),
            ("Colab KoELECTRA 감정분석", COLAB_SENTIMENT_PATH, "기획서의 감정분석 결과 확인"),
            ("Colab 임베딩 클러스터", COLAB_CLUSTER_PATH, "기획서의 문장 임베딩 군집화 결과 확인"),
            ("Colab cluster keywords", COLAB_KEYWORD_PATH, "기존 클러스터 키워드 확인"),
        ]
    )

    claim_df.to_csv(output_dir / "report_claim_validation.csv", index=False, encoding="utf-8-sig")
    group_df.to_csv(output_dir / "groupwise_recalculated.csv", index=False, encoding="utf-8-sig")
    top_df.to_csv(output_dir / "top_factors_recalculated.csv", index=False, encoding="utf-8-sig")
    pipeline_df.to_csv(output_dir / "pipeline_evidence_checks.csv", index=False, encoding="utf-8-sig")
    inventory_df.to_csv(output_dir / "evidence_file_inventory.csv", index=False, encoding="utf-8-sig")

    summary = build_summary(claim_df, group_df, top_df, pipeline_df, output_dir)
    (output_dir / "verification_summary.md").write_text(summary, encoding="utf-8")

    print(summary)


if __name__ == "__main__":
    main()
