# -*- coding: utf-8 -*-
"""
15_make_cluster_label_mapping_template.py

목적
- aspect cluster 키워드를 보고 보고서/발표용 평가 요인명을 붙일 수 있는
  cluster label mapping template을 생성한다.
- 자동 추천명은 보조용이며, 최종 이름은 사용자가 label_manual 컬럼에 직접 확정한다.

입력
    outputs/report_analysis/aspect_summary.csv
    outputs/report_analysis/course_group_analysis/course_group_aspect_comparison.csv

출력
    outputs/report_analysis/cluster_label_mapping/
        cluster_label_mapping_template.csv
        cluster_label_mapping_template.xlsx

실행
    python scripts\15_make_cluster_label_mapping_template.py
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import numpy as np
import pandas as pd


def read_csv_auto(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    raise RuntimeError(f"CSV를 읽지 못했습니다: {path}")


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


LABEL_RULES = [
    ("교수자의 친절성과 태도", ["천사", "친절", "착하시", "좋으신", "좋으세요", "사랑", "인자", "다정"]),
    ("수업의 재미와 흥미", ["재밌", "재미", "즐거", "흥미", "웃김", "유익"]),
    ("교수 설명의 명확성", ["강의력", "설명", "이해", "상세", "쉽게", "자세히", "명확"]),
    ("설명 이해의 어려움", ["모르겠", "하나도", "무슨", "뭔지", "이해를", "어려웠", "어려움"]),
    ("수업의 지루함", ["지루", "졸림", "노잼", "재미없", "단조"]),
    ("과제 및 발표 부담", ["과제", "발표", "조별", "팀플", "제출", "레포트", "보고서"]),
    ("시험 부담과 난이도", ["시험", "중간", "기말", "퀴즈", "범위", "문제", "난이도"]),
    ("성적 및 평가 기준", ["학점", "성적", "점수", "짜게", "깐깐", "평가", "기준", "a+", "a는"]),
    ("수업 운영 및 사담", ["사담", "잡담", "말이", "말을", "수업시간", "관련없는", "딴길"]),
    ("영어 사용 및 실용영어 활동", ["영어", "스피킹", "라이팅", "원어민", "회화", "토익", "발음"]),
    ("글쓰기 과제 및 피드백", ["글쓰기", "글을", "첨삭", "피드백", "문단", "쓰기", "리포트"]),
    ("출석 및 수업 관리", ["출석", "출결", "지각", "결석", "출튀"]),
    ("수강 추천/비추천", ["듣지마세요", "들으세요", "추천", "비추", "절대", "드랍"]),
]


def suggest_label(keywords: str) -> str:
    text = str(keywords)
    scores = []
    for label, terms in LABEL_RULES:
        score = sum(1 for term in terms if term.lower() in text.lower())
        if score:
            scores.append((score, label))
    if not scores:
        return "평가 요인 미정"
    scores.sort(reverse=True)
    return scores[0][1]


def suggest_category(label: str) -> str:
    if label in {"교수자의 친절성과 태도", "교수 설명의 명확성", "설명 이해의 어려움"}:
        return "교수자/설명"
    if label in {"수업의 재미와 흥미", "수업의 지루함", "수업 운영 및 사담"}:
        return "수업 운영"
    if label in {"과제 및 발표 부담", "시험 부담과 난이도", "성적 및 평가 기준"}:
        return "평가/과제/시험"
    if label in {"영어 사용 및 실용영어 활동"}:
        return "실용영어 특성"
    if label in {"글쓰기 과제 및 피드백"}:
        return "글쓰기 특성"
    if label in {"출석 및 수업 관리", "수강 추천/비추천"}:
        return "수강 경험"
    return "미정"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\every_time")
    args = parser.parse_args()

    root = Path(args.root)
    report_dir = root / "outputs" / "report_analysis"
    out_dir = report_dir / "cluster_label_mapping"
    out_dir.mkdir(parents=True, exist_ok=True)

    aspect_path = report_dir / "aspect_summary.csv"
    comparison_path = report_dir / "course_group_analysis" / "course_group_aspect_comparison.csv"

    if not aspect_path.exists():
        raise FileNotFoundError(f"필수 파일이 없습니다: {aspect_path}")

    aspect = read_csv_auto(aspect_path)
    comparison = read_csv_auto(comparison_path) if comparison_path.exists() else pd.DataFrame()

    if "aspect_cluster_id" not in aspect.columns and "cluster_id" in aspect.columns:
        aspect["aspect_cluster_id"] = aspect["cluster_id"]

    rows = []
    for _, row in aspect.iterrows():
        cid = row.get("aspect_cluster_id")
        keywords = clean_text(row.get("top_keywords", ""))

        comp = comparison[comparison["aspect_cluster_id"].astype(str) == str(cid)] if not comparison.empty else pd.DataFrame()
        comp_row = comp.iloc[0].to_dict() if not comp.empty else {}

        suggested = suggest_label(keywords)

        rows.append({
            "aspect_cluster_id": cid,
            "suggested_label_auto": suggested,
            "label_manual": "",
            "category_auto": suggest_category(suggested),
            "category_manual": "",
            "include_in_report": "Y" if str(cid) != "-1" else "N",
            "confidence_manual_1to5": "",
            "top_keywords": keywords,
            "segment_count": row.get("segment_count", ""),
            "positive_ratio_percent": row.get("positive_ratio_percent", ""),
            "negative_ratio_percent": row.get("negative_ratio_percent", ""),
            "avg_review_rating": row.get("avg_review_rating", ""),
            "dominant_group": comp_row.get("dominant_group", ""),
            "common_factor_flag": comp_row.get("common_factor_flag", ""),
            "writing_segment_count": comp_row.get("글쓰기_segment_count", comp_row.get("WRITING_segment_count", "")),
            "practical_english_segment_count": comp_row.get("실용영어_segment_count", comp_row.get("PRACTICAL_ENGLISH_segment_count", "")),
            "researcher_note": "",
        })

    out = pd.DataFrame(rows)
    out = out.sort_values(["include_in_report", "segment_count"], ascending=[False, False])

    csv_path = out_dir / "cluster_label_mapping_template.csv"
    xlsx_path = out_dir / "cluster_label_mapping_template.xlsx"

    save_csv(out, csv_path)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="mapping_template", index=False)

    print("완료")
    print("CSV :", csv_path)
    print("XLSX:", xlsx_path)
    print("다음 단계: label_manual 컬럼에 최종 평가 요인명을 직접 확정하세요.")


if __name__ == "__main__":
    main()
