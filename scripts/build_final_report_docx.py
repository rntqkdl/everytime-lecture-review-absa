from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = PROJECT_ROOT / "submission_pack_안성민"
TABLES_DIR = PACK_DIR / "report_assets" / "tables"
FIGURES_DIR = PACK_DIR / "report_assets" / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_DOCX = PROJECT_ROOT / "final_report_안성민.docx"
BER_TOPIC_REPORT_DIR = PROJECT_ROOT / "outputs" / "bertopic_analysis" / "report_analysis"
LEGACY_REPORT_DIR = PROJECT_ROOT / "outputs" / "report_analysis"
REPORT_SOURCE_DIR = BER_TOPIC_REPORT_DIR if BER_TOPIC_REPORT_DIR.exists() else LEGACY_REPORT_DIR

FONT = "Malgun Gothic"
BLUE = RGBColor(46, 116, 181)
DARK_BLUE = RGBColor(31, 77, 120)
MUTED = RGBColor(89, 89, 89)
LIGHT_FILL = "F4F6F9"
HEADER_FILL = "E8EEF5"
BORDER = "B7C4D6"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color: str = BORDER, size: str = "6") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in {"top": top, "start": start, "bottom": bottom, "end": end}.items():
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_table_width(table, width_dxa: int, col_widths_dxa: list[int]) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(width_dxa))
    tbl_w.set(qn("w:type"), "dxa")

    tbl_layout = tbl_pr.find(qn("w:tblLayout"))
    if tbl_layout is None:
        tbl_layout = OxmlElement("w:tblLayout")
        tbl_pr.append(tbl_layout)
    tbl_layout.set(qn("w:type"), "fixed")

    grid = table._tbl.tblGrid
    if grid is None:
        grid = OxmlElement("w:tblGrid")
        table._tbl.insert(0, grid)
    for child in list(grid):
        grid.remove(child)
    for width in col_widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            width = col_widths_dxa[min(idx, len(col_widths_dxa) - 1)]
            cell.width = Inches(width / 1440)
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")


def set_run_font(run, size: float | None = None, bold: bool | None = None, color: RGBColor | None = None) -> None:
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:ascii"), FONT)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def add_para(doc: Document, text: str = "", style: str | None = None, bold: bool = False) -> object:
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.33
    if text:
        run = p.add_run(text)
        set_run_font(run, bold=bold)
    return p


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    if level == 1:
        set_run_font(run, size=16, bold=True, color=BLUE)
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(10)
    elif level == 2:
        set_run_font(run, size=13, bold=True, color=BLUE)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
    else:
        set_run_font(run, size=12, bold=True, color=DARK_BLUE)
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)


def add_caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(text)
    set_run_font(run, size=9.2, bold=True, color=MUTED)


def add_bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.35)
    p.paragraph_format.first_line_indent = Inches(-0.15)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.2
    run = p.add_run(text)
    set_run_font(run, size=10.5)


def style_table(table, header_rows: int = 1) -> None:
    for r, row in enumerate(table.rows):
        for cell in row.cells:
            set_cell_border(cell)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for para in cell.paragraphs:
                para.paragraph_format.space_after = Pt(2)
                para.paragraph_format.line_spacing = 1.15
                for run in para.runs:
                    set_run_font(run, size=8.8 if r else 9, bold=(r < header_rows))
            if r < header_rows:
                set_cell_shading(cell, HEADER_FILL)
            else:
                set_cell_shading(cell, "FFFFFF")


def add_dataframe_table(
    doc: Document,
    df: pd.DataFrame,
    columns: list[str] | None = None,
    widths: list[int] | None = None,
    max_rows: int | None = None,
) -> None:
    if columns is not None:
        df = df[columns].copy()
    if max_rows is not None:
        df = df.head(max_rows).copy()
    table = doc.add_table(rows=1, cols=len(df.columns))
    for i, col in enumerate(df.columns):
        table.rows[0].cells[i].text = str(col)
    for _, row in df.iterrows():
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = "" if pd.isna(value) else str(value)
    if widths is None:
        width = 9360 // len(df.columns)
        widths = [width] * len(df.columns)
    set_table_width(table, sum(widths), widths)
    style_table(table)


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES_DIR / name, encoding="utf-8-sig")


def load_report_data() -> dict[str, pd.DataFrame]:
    data = {
        "overview": load_csv("table02_data_overview.csv"),
        "sentiment": load_csv("table03_sentiment_distribution.csv"),
        "mismatch": load_csv("table04_rating_text_mismatch.csv"),
        "method": load_csv("table08_model_method_summary.csv"),
        "validation": pd.read_csv(TABLES_DIR / "claim_validation_table.csv", encoding="utf-8-sig"),
        "good": pd.read_csv(REPORT_SOURCE_DIR / "groupwise_report_pack/ALL/good_factors.csv", encoding="utf-8-sig"),
        "bad": pd.read_csv(REPORT_SOURCE_DIR / "groupwise_report_pack/ALL/bad_factors.csv", encoding="utf-8-sig"),
        "group": pd.read_csv(REPORT_SOURCE_DIR / "groupwise_report_pack/groupwise_comparison_summary.csv", encoding="utf-8-sig"),
        "method_ref": pd.read_csv(DOCS_DIR / "methodology_reference_table.csv", encoding="utf-8-sig"),
    }
    return data


def format_top_factors(df: pd.DataFrame, count_col: str, n: int = 5) -> str:
    filtered = df[df.get("include_in_report", "Y").astype(str).str.upper().eq("Y")].copy()
    filtered = filtered[~filtered["aspect_label"].astype(str).str.contains("미정|기타", na=False)].copy()
    filtered[count_col] = pd.to_numeric(filtered[count_col], errors="coerce")
    filtered = filtered.sort_values(count_col, ascending=False).drop_duplicates("aspect_label", keep="first").head(n)
    items = [f"{row['aspect_label']}({int(row[count_col]):,}건)" for _, row in filtered.iterrows()]
    return ", ".join(items)


def setup_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.33

    for name, size, color in [
        ("Heading 1", 16, BLUE),
        ("Heading 2", 13, BLUE),
        ("Heading 3", 12, DARK_BLUE),
    ]:
        style = styles[name]
        style.font.name = FONT
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        style.font.size = Pt(size)
        style.font.color.rgb = color
        style.font.bold = True

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer.add_run("언어와 데이터 리터러시 기말 레포트 | 안성민")
    set_run_font(footer_run, size=8.5, color=MUTED)
    return doc


def add_cover(doc: Document) -> None:
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("에브리타임 강의평 분석을 통해 본 좋은 강의의 조건")
    set_run_font(run, size=22, bold=True, color=RGBColor(0, 0, 0))
    p.paragraph_format.space_after = Pt(8)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("글쓰기와 실용영어 강의평을 중심으로")
    set_run_font(run, size=13, color=MUTED)
    p.paragraph_format.space_after = Pt(30)

    meta = [
        ("과목명", "언어와 데이터 리터러시"),
        ("담당 교수", "김정은 교수"),
        ("학과", "IT융합기전공학과"),
        ("학번", "201911347"),
        ("이름", "안성민"),
    ]
    table = doc.add_table(rows=len(meta), cols=2)
    for r, (label, value) in enumerate(meta):
        table.rows[r].cells[0].text = label
        table.rows[r].cells[1].text = value
    set_table_width(table, 6500, [1800, 4700])
    style_table(table, header_rows=0)
    for row in table.rows:
        set_cell_shading(row.cells[0], LIGHT_FILL)
        for run in row.cells[0].paragraphs[0].runs:
            run.bold = True
    doc.add_page_break()


def add_intro(doc: Document) -> None:
    add_heading(doc, "1. 서론", 1)
    add_para(
        doc,
        "대학생들이 강의를 선택하거나 평가할 때 에브리타임 강의평은 중요한 참고 자료로 활용된다. "
        "그러나 강의평은 보통 별점 하나로 요약되기 어렵다. 한 리뷰 안에서도 교수자의 태도는 긍정적으로 평가하면서 "
        "과제나 시험 부담은 부정적으로 말하는 경우가 있고, 반대로 낮은 별점 리뷰 안에도 일부 긍정 경험이 섞여 있을 수 있다. "
        "따라서 좋은 강의의 조건을 이해하려면 별점뿐 아니라 학생들이 실제로 남긴 텍스트의 평가 요인과 감정 방향을 함께 살펴볼 필요가 있다.",
    )
    add_para(
        doc,
        "본 연구의 목적은 글쓰기 계열과 실용영어 계열 강의평을 분석하여 학생들이 생각하는 좋은 강의의 조건을 찾는 것이다. "
        "이를 위해 리뷰를 문장과 절 단위로 나누고, 세그먼트별 감정과 평가 요인을 분리해 살펴보았다. 연구 질문은 다음과 같다.",
    )
    add_bullet(doc, "학생들은 어떤 요인을 좋은 강의의 조건으로 반복해서 언급하는가?")
    add_bullet(doc, "부정 강의평에서는 어떤 불만 요인이 주로 나타나는가?")
    add_bullet(doc, "글쓰기와 실용영어 강의평은 평가 요인과 부담의 성격에서 어떤 차이를 보이는가?")
    add_bullet(doc, "별점과 텍스트 감정은 어느 정도 일치하거나 불일치하는가?")


def add_design_process(doc: Document, data: dict[str, pd.DataFrame]) -> None:
    add_heading(doc, "2. 연구 설계 및 수행 과정", 1)
    add_para(
        doc,
        "분석은 데이터 수집, 전처리, 세그먼트 분리, 문장 임베딩, 평가 요인 군집화, 감정분석, 결과 해석의 순서로 진행했다. "
        "원본 리뷰 데이터와 HTML 원본은 개인정보 가능성과 저작권·윤리 문제를 고려해 GitHub 업로드 대상에서 제외하고, "
        "보고서에는 집계 결과와 검증 가능한 표·그래프만 사용했다.",
    )
    doc.add_picture(str(FIGURES_DIR / "fig01_analysis_process_flow.png"), width=Inches(6.3))
    add_caption(doc, "그림 1. 분석 과정 흐름도")

    add_heading(doc, "2.1 데이터 수집과 전처리", 2)
    add_para(
        doc,
        "데이터 수집은 `collect_writing_lectures_final.py`, `collect_practical_english_lectures_final.py`, "
        "`collect_practical_english_variants_final.py`를 통해 수행했다. 이후 Python, pandas, 정규표현식을 사용해 중복과 불필요한 문자를 정리하고, "
        "분석 가능한 리뷰 텍스트를 구성했다. 교수자 식별 정보는 코드상에서 익명화하거나 별도 식별자로 처리했으며, 원본 리뷰 데이터는 공개 저장소와 최종 문서 본문에서 제외했다.",
    )

    add_heading(doc, "2.2 세그먼트 단위 분석", 2)
    add_para(
        doc,
        "분석 단위는 리뷰 전체가 아니라 문장과 절 단위 세그먼트이다. 하나의 리뷰에 장점과 단점이 함께 나타나는 경우가 많기 때문에, "
        "리뷰 전체를 하나의 감정으로 처리하면 학생들이 언급한 세부 평가 요인을 놓칠 수 있다. 따라서 세그먼트를 기준으로 감정과 평가 요인을 분리했다.",
    )

    add_heading(doc, "2.3 실제 사용 방법과 참고 방법의 구분", 2)
    method_ref = data["method_ref"]
    brief = method_ref[
        method_ref["방법론 또는 모델명"].isin(
            [
                "jhgan/ko-sroberta-multitask",
                "UMAP",
                "HDBSCAN",
                "BERTopic",
                "monologg/koelectra-base-finetuned-nsmc",
                "별점 신호 분석",
                "EduRABSA",
            ]
        )
    ][["방법론 또는 모델명", "직접 사용 여부", "레포트에 넣을 표현"]]
    add_dataframe_table(doc, brief, widths=[2500, 1700, 5160])
    add_caption(doc, "표 1. 실제 사용 방법과 참고 방법의 구분")
    add_para(
        doc,
        "최종본에서는 BERTopic 라이브러리를 직접 실행했다. 다만 BERTopic topic 이름은 자동 결론으로 그대로 확정하지 않고, "
        "topic별 키워드와 대표 문장을 바탕으로 연구자가 평가 요인 이름을 해석했다. 이번 재분석에서는 outlier topic을 제외하고 574개의 평가 요인 topic이 생성되었다. "
        "별점은 감정 정답 라벨이 아니라 전체 만족도 신호로만 사용했다.",
    )


def add_results(doc: Document, data: dict[str, pd.DataFrame]) -> None:
    add_heading(doc, "3. 분석 결과 및 시각자료", 1)

    add_heading(doc, "3.1 분석 데이터 개요", 2)
    add_para(
        doc,
        "최종 분석 데이터는 전체 리뷰 13,751개와 세그먼트 37,808개로 구성되었다. 과목군별로는 글쓰기 세그먼트가 20,646개, "
        "실용영어 세그먼트가 17,162개였다.",
    )
    add_dataframe_table(doc, data["overview"], widths=[2700, 2000, 2000, 2660])
    add_caption(doc, "표 2. 분석 데이터 개요")
    doc.add_picture(str(FIGURES_DIR / "fig02_segment_count_by_group.png"), width=Inches(5.8))
    add_caption(doc, "그림 2. 과목군별 세그먼트 수")

    add_heading(doc, "3.2 감정 분포", 2)
    add_para(
        doc,
        "세그먼트 감정분석 결과, 긍정 세그먼트는 22,263개로 전체의 58.88%였고 부정 세그먼트는 15,545개로 41.12%였다. "
        "긍정 세그먼트가 더 많지만, 부정 세그먼트도 4할 이상을 차지해 강의평 텍스트가 단순한 만족·불만의 한 방향으로만 구성되지 않음을 보여준다.",
    )
    add_dataframe_table(doc, data["sentiment"], widths=[3000, 2100, 2100, 2160])
    add_caption(doc, "표 3. 감정 분포 요약")
    doc.add_picture(str(FIGURES_DIR / "fig03_sentiment_distribution.png"), width=Inches(5.7))
    add_caption(doc, "그림 3. 전체 긍정/부정 세그먼트 분포")

    add_heading(doc, "3.3 별점과 텍스트 감정의 불일치", 2)
    add_para(
        doc,
        "mixed review는 하나의 리뷰 안에 긍정 세그먼트와 부정 세그먼트가 모두 포함된 경우로 정의했다. 실제 데이터에서 mixed review는 5,984개였다. "
        "또한 높은 별점이지만 부정 세그먼트를 포함한 경우는 세그먼트 기준 9,694건, 낮은 별점이지만 긍정 세그먼트를 포함한 경우는 세그먼트 기준 975건이었다. "
        "이 항목은 세그먼트 기준과 리뷰 기준의 값이 다르게 계산되므로, 본 보고서에서는 두 기준을 구분해 기술한다.",
    )
    add_dataframe_table(doc, data["mismatch"], widths=[3300, 1900, 1900, 2260])
    add_caption(doc, "표 4. 별점과 텍스트 불일치 요약")
    doc.add_picture(str(FIGURES_DIR / "fig04_rating_text_mismatch.png"), width=Inches(5.9))
    add_caption(doc, "그림 4. 별점과 텍스트 불일치 분석")

    add_heading(doc, "3.4 좋은 강의 요인과 부정 강의 요인", 2)
    good_top = format_top_factors(data["good"], "positive_count", n=4)
    bad_top = format_top_factors(data["bad"], "negative_count", n=3)
    add_para(
        doc,
        f"좋은 강의 요인에서는 {good_top} 등이 상위에 나타났다. 이를 종합하면 학생들은 교수자의 친절성과 설명 명확성, "
        "수업의 재미, 피드백, 그리고 부담이 과도하지 않은 수업 운영을 긍정적으로 평가하는 경향이 있었다.",
    )
    doc.add_picture(str(FIGURES_DIR / "fig05_good_lecture_factors.png"), width=Inches(6.2))
    add_caption(doc, "그림 5. 좋은 강의 요인 상위 항목")
    add_para(
        doc,
        f"부정 강의 요인에서는 {bad_top} 등이 두드러졌다. 그 밖에도 일부 topic에서는 수업 흥미 저하나 교수자 설명 방식에 대한 "
        "부정 언급이 확인되었다. 부정 평가는 단순히 과제가 많다는 차원을 넘어, 설명을 이해하기 어렵거나 수업 운영이 불안정하고 "
        "평가 기준이 모호하다고 느낄 때 강하게 나타났다.",
    )
    doc.add_picture(str(FIGURES_DIR / "fig06_bad_lecture_factors.png"), width=Inches(6.2))
    add_caption(doc, "그림 6. 좋지 않은 강의 요인 상위 항목")

    add_heading(doc, "3.5 글쓰기와 실용영어 비교", 2)
    group = data["group"][["group_label", "segment_count", "review_count", "positive_ratio_percent", "negative_ratio_percent", "mixed_review_count", "top_good_factor_1", "top_bad_factor_1"]].copy()
    group.columns = ["구분", "세그먼트 수", "리뷰 수", "긍정 비율(%)", "부정 비율(%)", "mixed review 수", "상위 긍정 요인", "상위 부정 요인"]
    add_dataframe_table(doc, group, widths=[1050, 1050, 950, 1100, 1100, 1250, 1900, 1960])
    add_caption(doc, "표 5. 과목군별 요약 비교")
    add_para(
        doc,
        "글쓰기 계열에서는 과제, 첨삭, 결과물 평가와 관련된 부담이 중요하게 나타났다. 실용영어 계열에서는 스피킹, 라이팅, 영어 사용 상황, "
        "시험 방식과 참여 부담이 더 강하게 드러났다. 두 과목군 모두 교수자의 태도, 수업 운영 방식, 평가 기준이 공통 요인으로 확인되었다.",
    )
    doc.add_picture(str(FIGURES_DIR / "fig07_subject_group_comparison.png"), width=Inches(5.9))
    add_caption(doc, "그림 7. 글쓰기와 실용영어 비교")


def add_discussion(doc: Document) -> None:
    add_heading(doc, "4. 논의", 1)
    add_para(
        doc,
        "분석 결과는 학생들이 생각하는 좋은 강의가 단순히 쉬운 강의나 학점을 잘 주는 강의만을 의미하지 않음을 보여준다. "
        "학생들은 교수자가 친절하고 설명이 명확하며 수업 운영이 안정적일 때 강의를 긍정적으로 평가했다. 동시에 과제와 발표 부담, 시험 부담, "
        "평가 기준이 납득 가능할 때 강의 경험을 더 좋게 받아들였다.",
    )
    add_para(
        doc,
        "흥미로운 점은 높은 별점 안에도 부정 세그먼트가 많고, 낮은 별점 안에도 긍정 세그먼트가 존재한다는 것이다. 이는 별점이 리뷰 전체의 종합 만족도를 나타낼 수는 있지만, "
        "세부 경험을 모두 설명하지는 못한다는 뜻이다. 예를 들어 어떤 학생은 교수자의 태도는 좋게 평가하면서도 과제 부담이나 성적 평가에는 불만을 가질 수 있다. "
        "따라서 강의평 분석에서는 별점과 텍스트 감정을 분리해서 보는 것이 중요하다.",
    )
    add_para(
        doc,
        "과목군 비교에서도 차이가 나타났다. 글쓰기 강의에서는 결과물을 제출하고 평가받는 과정 자체가 중요한 경험으로 드러났고, 실용영어 강의에서는 영어를 직접 사용해야 하는 참여 상황이 부담으로 나타났다. "
        "이 차이는 강의 개선 방향도 과목 성격에 맞춰 달라져야 함을 시사한다. 글쓰기 과목은 평가 기준과 피드백의 명확성이 중요하고, 실용영어 과목은 참여 부담을 낮추면서 실제 사용 경험을 설계하는 방식이 중요하다.",
    )


def add_limits(doc: Document) -> None:
    add_heading(doc, "5. 연구의 한계 및 향후 연구 방향", 1)
    add_bullet(doc, "첫째, 분석 대상은 특정 과목군의 에브리타임 강의평에 한정되어 모든 대학 강의로 일반화하기 어렵다.")
    add_bullet(doc, "둘째, 공개 감정분석 모델을 적용했기 때문에 강의평 도메인 특유의 반어, 비속어, 짧은 표현을 완벽히 해석하지 못할 수 있다.")
    add_bullet(doc, "셋째, BERTopic topic 이름은 대표 키워드와 대표 문장을 바탕으로 연구자가 해석한 것이므로 완전 자동 분류 결과가 아니다.")
    add_bullet(doc, "넷째, 대표 문장 수동 검증은 7개 예시를 대상으로 한 방향성 확인이며 전체 데이터 전수 검증은 아니다.")
    add_para(
        doc,
        "향후 연구에서는 더 다양한 과목군으로 분석 대상을 확장하고, 강의평 도메인에 맞춘 수작업 주석 데이터셋을 일부 구축해 모델 결과를 정량적으로 평가할 필요가 있다. "
        "또한 학기별 변화나 교수자·수업 방식의 차이를 함께 분석하면 좋은 강의 조건을 더 구체적으로 파악할 수 있을 것이다.",
    )


def add_references(doc: Document) -> None:
    add_heading(doc, "6. 참고문헌", 1)
    refs = [
        "Campello, R. J. G. B., Moulavi, D., & Sander, J. (2013). Density-based clustering based on hierarchical density estimates. In Advances in Knowledge Discovery and Data Mining (pp. 160-172). Springer.",
        "Grootendorst, M. (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure. arXiv. https://arxiv.org/abs/2203.05794",
        "Ham, J., Choe, Y. J., Park, K., Choi, I., & Soh, H. (2020). KorNLI and KorSTS: New benchmark datasets for Korean natural language understanding. Findings of EMNLP 2020. https://aclanthology.org/2020.findings-emnlp.261/",
        "Jang, D., Seo, J., Byun, S., Kim, T., Kim, M., & Shin, H. (2024). CARBD-Ko: A contextually annotated review benchmark dataset for aspect-level sentiment classification in Korean.",
        "McInnes, L., Healy, J., & Melville, J. (2018). UMAP: Uniform manifold approximation and projection for dimension reduction. arXiv. https://arxiv.org/abs/1802.03426",
        "Park, J. (2020). KoELECTRA: Pretrained ELECTRA model for Korean. GitHub repository. https://github.com/monologg/KoELECTRA",
        "Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. Proceedings of EMNLP-IJCNLP 2019, 3982-3992. https://doi.org/10.18653/v1/D19-1410",
        "Hugging Face. (n.d.). jhgan/ko-sroberta-multitask; monologg/koelectra-base-finetuned-nsmc; cringepnh/koelectra-korean-sentiment; tobykim/koelectra-44emotions; dlckdfuf141/korean-emotion-kluebert-v2.",
        "pandas, NumPy, scikit-learn, matplotlib, transformers, PyTorch, BeautifulSoup4, Playwright, kiwipiepy, openpyxl 공식 문서.",
    ]
    for ref in refs:
        p = add_para(doc, ref)
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.line_spacing = 1.15


def add_appendix(doc: Document) -> None:
    add_heading(doc, "7. 부록", 1)
    add_para(
        doc,
        "부록 자료는 공개 저장소의 코드와 분리해 로컬 분석 산출물로 정리했다. "
        "원본 리뷰 데이터, HTML 원본, 브라우저 프로필, 캐시, 환경 파일은 개인정보와 재현 환경 보호를 위해 제외했다.",
    )
    add_bullet(doc, "`appendix/data`: 최종 분석 데이터셋, 최종 요인 요약, 과목군 비교, 검증표")
    add_bullet(doc, "`appendix/figures`: 보고서용 그림 1부터 그림 8까지")
    add_bullet(doc, "`appendix/tables`: 표 1부터 표 8까지의 CSV와 XLSX")
    add_bullet(doc, "`appendix/code`: 최종 분석 스크립트, 보고서용 그래프 생성 스크립트, 노트북")
    add_bullet(doc, "`appendix/validation`: 대표 문장 수동 검증, 수치 검증 요약, claim validation table")
    doc.add_picture(str(FIGURES_DIR / "fig08_manual_validation_examples.png"), width=Inches(6.3))
    add_caption(doc, "그림 8. 대표 문장 검증 예시")


def main() -> None:
    data = load_report_data()
    doc = setup_document()
    add_cover(doc)
    add_intro(doc)
    add_design_process(doc, data)
    add_results(doc, data)
    add_discussion(doc)
    add_limits(doc)
    add_references(doc)
    add_appendix(doc)
    doc.core_properties.title = "에브리타임 강의평 분석을 통해 본 좋은 강의의 조건"
    doc.core_properties.author = "안성민"
    doc.save(OUTPUT_DOCX)
    print(f"생성 완료: {OUTPUT_DOCX}")


if __name__ == "__main__":
    main()
