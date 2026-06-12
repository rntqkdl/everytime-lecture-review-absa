# -*- coding: utf-8 -*-
"""
16_make_manual_validation_table.py

목적
- 보고서/발표에 넣을 대표 문장 7개 수동 검증표를 생성한다.
- 기본 구성:
  긍정 대표 문장 3개 + 부정 대표 문장 3개 + 별점-감정 불일치 사례 1개

입력
    outputs/report_analysis/representative_positive_sentences.csv
    outputs/report_analysis/representative_negative_sentences.csv
    outputs/report_analysis/high_rating_negative_segments_for_report.csv
    outputs/report_analysis/low_rating_positive_segments_for_report.csv
    outputs/report_analysis/cluster_label_mapping/cluster_label_mapping_template.csv

출력
    outputs/report_analysis/manual_validation/
        manual_validation_7_samples.csv
        manual_validation_7_samples.xlsx
        manual_validation_guide.md

실행
    python scripts\16_make_manual_validation_table.py
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pandas as pd


def read_csv_auto(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.DataFrame()


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


def save_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].apply(clean_text)
    out.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL, lineterminator="\n")


def load_label_map(path: Path):
    df = read_csv_auto(path)
    if df.empty:
        return {}
    label_col = "label_manual" if "label_manual" in df.columns else "suggested_label_auto"
    labels = {}
    for _, row in df.iterrows():
        manual = clean_text(row.get("label_manual", ""))
        auto = clean_text(row.get("suggested_label_auto", ""))
        label = manual or auto
        labels[str(row.get("aspect_cluster_id"))] = label
    return labels


def choose_unique_clusters(df: pd.DataFrame, n: int):
    if df.empty:
        return df
    out_rows = []
    used = set()
    sort_cols = [c for c in ["predicted_score", "review_rating"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, ascending=[False] * len(sort_cols), na_position="last")
    for _, row in df.iterrows():
        cid = str(row.get("aspect_cluster_id", ""))
        if cid in used:
            continue
        out_rows.append(row)
        used.add(cid)
        if len(out_rows) >= n:
            break
    return pd.DataFrame(out_rows)


def choose_mismatch_case(high_neg: pd.DataFrame, low_pos: pd.DataFrame):
    # 발표 설득력은 "높은 별점인데 부정 문장"이 더 직관적이라 우선 선택
    preference_terms = ["과제", "시험", "조별", "성적", "지루", "모르", "이해", "깐깐", "수업"]
    if not high_neg.empty:
        df = high_neg.copy()
        df["preference_score"] = df["segment_text"].fillna("").astype(str).apply(
            lambda x: sum(1 for t in preference_terms if t in x)
        )
        sort_cols = ["preference_score"]
        asc = [False]
        if "predicted_score" in df.columns:
            sort_cols.append("predicted_score")
            asc.append(False)
        return df.sort_values(sort_cols, ascending=asc, na_position="last").head(1), "높은 별점 안의 부정 문장"

    if not low_pos.empty:
        df = low_pos.copy()
        sort_cols = ["predicted_score"] if "predicted_score" in df.columns else []
        if sort_cols:
            df = df.sort_values(sort_cols, ascending=False, na_position="last")
        return df.head(1), "낮은 별점 안의 긍정 문장"

    return pd.DataFrame(), ""


def maybe_mask_text(text: str):
    # 완전 자동 익명화는 위험하므로 최소한의 안내성 마스킹만 수행
    text = clean_text(text)
    # 이메일/전화번호/학번 유사 패턴 제거
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[이메일]", text)
    text = re.sub(r"01[016789]-?\d{3,4}-?\d{4}", "[전화번호]", text)
    text = re.sub(r"\b20\d{6,10}\b", "[학번추정]", text)
    return text


def row_to_validation(row, sample_type, label_map):
    cid = row.get("aspect_cluster_id", "")
    model_sentiment = row.get("sentiment", row.get("predicted_label_standard", ""))
    text = row.get("segment_text", "")
    return {
        "번호": "",
        "sample_type": sample_type,
        "course_group": row.get("course_group", ""),
        "course_name": row.get("course_name", ""),
        "aspect_cluster_id": cid,
        "aspect_label_suggested": label_map.get(str(cid), ""),
        "segment_text_original": clean_text(text, 260),
        "segment_text_for_report": maybe_mask_text(text),
        "model_sentiment": model_sentiment,
        "model_score": row.get("predicted_score", ""),
        "review_rating": row.get("review_rating", ""),
        "rating_satisfaction_signal": row.get("rating_satisfaction_signal", ""),
        "researcher_sentiment": "",
        "match_yn": "",
        "final_aspect_label": "",
        "validation_note": "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\every_time")
    args = parser.parse_args()

    root = Path(args.root)
    report_dir = root / "outputs" / "report_analysis"
    out_dir = report_dir / "manual_validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    pos = read_csv_auto(report_dir / "representative_positive_sentences.csv")
    neg = read_csv_auto(report_dir / "representative_negative_sentences.csv")
    high_neg = read_csv_auto(report_dir / "high_rating_negative_segments_for_report.csv")
    low_pos = read_csv_auto(report_dir / "low_rating_positive_segments_for_report.csv")
    label_map = load_label_map(report_dir / "cluster_label_mapping" / "cluster_label_mapping_template.csv")

    selected_rows = []

    pos_sel = choose_unique_clusters(pos, 3)
    for _, row in pos_sel.iterrows():
        selected_rows.append(row_to_validation(row, "긍정 대표 문장", label_map))

    neg_sel = choose_unique_clusters(neg, 3)
    for _, row in neg_sel.iterrows():
        selected_rows.append(row_to_validation(row, "부정 대표 문장", label_map))

    mismatch, mismatch_type = choose_mismatch_case(high_neg, low_pos)
    if not mismatch.empty:
        selected_rows.append(row_to_validation(mismatch.iloc[0], mismatch_type, label_map))

    out = pd.DataFrame(selected_rows)
    if not out.empty:
        out["번호"] = range(1, len(out) + 1)

    csv_path = out_dir / "manual_validation_7_samples.csv"
    xlsx_path = out_dir / "manual_validation_7_samples.xlsx"
    guide_path = out_dir / "manual_validation_guide.md"

    save_csv(out, csv_path)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="manual_validation", index=False)

    guide = """# 대표 문장 7개 수동 검증 가이드

## 목적

자동 감정분석 모델 결과의 신뢰도를 보조적으로 확인하기 위해 대표 문장 7개를 사람이 직접 검토한다.

## 검증 방식

1. segment_text_for_report를 읽는다.
2. model_sentiment가 문장의 실제 감정과 맞는지 확인한다.
3. researcher_sentiment에 사람이 판단한 감정을 입력한다.
4. match_yn에 일치하면 Y, 불일치하면 N을 입력한다.
5. final_aspect_label에는 보고서에 사용할 최종 평가 요인명을 입력한다.

## 권장 구성

- 긍정 대표 문장 3개
- 부정 대표 문장 3개
- 별점과 문장 감정이 엇갈리는 사례 1개

## 보고서 작성 문장 예시

모델 결과의 신뢰도를 보조적으로 확인하기 위해 대표 문장 7개를 선정하여 연구자가 수동 검토하였다. 전체 라벨링을 수행하지는 않았지만, 주요 평가 요인과 별점-감정 불일치 사례를 중심으로 모델 판단과 연구자 판단의 일치 여부를 확인하였다.

## 주의

실제 강의평 원문에는 교수자 또는 개인을 유추할 수 있는 표현이 포함될 수 있으므로, 보고서에 인용할 때는 교수명과 과도하게 특정적인 표현을 마스킹한다.
"""
    guide_path.write_text(guide, encoding="utf-8")

    print("완료")
    print("CSV :", csv_path)
    print("XLSX:", xlsx_path)
    print("GUIDE:", guide_path)


if __name__ == "__main__":
    main()
