# collect_practical_english_lectures_final.py
# 실용영어 강의평 최종 스크래핑 코드
# 핵심 반영:
# - 개요 페이지의 section.review .rating .title span.count 예: (33개)에서 전체 강의평 수를 먼저 추출
# - 강의평 더 보기/강의평 탭 진입 후 현재 로딩된 강의평 수가 전체 수와 일치할 때까지만 스크롤
# - 강의명, 교수명, 평균 별점, 별점 분포, 과제/조모임/성적/출결/시험, 교재, 시험 정보, 개별 강의평 저장

from pathlib import Path
import re
import time
import random
import json
from datetime import datetime
from urllib.parse import unquote

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# =========================================================
# 0. 기본 설정
# =========================================================

BASE_URL = "https://everytime.kr"

ROOT_DIR = Path(r"C:\every_time")
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = DATA_DIR / "practical_english_output"
HTML_DIR = DATA_DIR / "practical_english_lecture_html"
DEBUG_DIR = DATA_DIR / "practical_english_debug"

for folder in [DATA_DIR, OUTPUT_DIR, HTML_DIR, DEBUG_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

USER_DATA_DIR = str(ROOT_DIR / "browser_profile")

HEADLESS = False

# 검색어와 최종 수집 대상 과목명
# 실용영어만 검색하고, 검색 결과 중 과목명이 정확히 실용영어로 정규화되는 것만 수집
SEARCH_KEYWORDS = ["실용영어"]
TARGET_COURSE_NAMES = ["실용영어"]

INCLUDE_PARENTHESES_VARIANTS = True
MAX_LECTURE_IDS = None
SAVE_LECTURE_HTML = True

SEARCH_SCROLL_ROUNDS = 12
REVIEW_MAX_SCROLL_ROUNDS = 100
REVIEW_STABLE_LIMIT = 6

MIN_SLEEP = 3
MAX_SLEEP = 7


# =========================================================
# 1. 공통 유틸
# =========================================================

def clean_text(text):
    if text is None:
        return None
    return re.sub(r"\s+", " ", str(text)).strip()


def safe_filename(name):
    name = clean_text(name) or "unknown"
    return re.sub(r'[\\/:*?"<>|, ]+', "_", name)


def safe_int(value):
    value = clean_text(value)
    if not value:
        return None
    value = value.replace(",", "")
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def safe_float(value):
    value = clean_text(value)
    try:
        return float(value)
    except Exception:
        return None


def random_sleep(a=MIN_SLEEP, b=MAX_SLEEP):
    time.sleep(random.uniform(a, b))


def extract_width_percent(style):
    if not style:
        return None
    match = re.search(r"width:\s*([\d.]+)%", style)
    return float(match.group(1)) if match else None


def rating_from_style(style):
    width = extract_width_percent(style)
    if width is None:
        return None
    return round(width / 20, 2)


def percent_to_float(text):
    text = clean_text(text)
    if not text:
        return None
    match = re.search(r"([\d.]+)\s*%", text)
    return float(match.group(1)) if match else None


def count_from_text(text):
    text = clean_text(text)
    if not text:
        return None
    match = re.search(r"(\d+)", text.replace(",", ""))
    return int(match.group(1)) if match else None


def extract_lecture_id_from_href(href):
    if not href:
        return None
    match = re.search(r"/lecture/view/(\d+)", href)
    return match.group(1) if match else None


def make_overview_url(lecture_id):
    return f"{BASE_URL}/lecture/view/{lecture_id}"


def make_article_url(lecture_id):
    return f"{BASE_URL}/lecture/view/{lecture_id}?tab=article"


def make_exam_url(lecture_id):
    return f"{BASE_URL}/lecture/view/{lecture_id}?tab=exam"


def normalize_course_name(name):
    name = clean_text(name)
    if not name:
        return None
    name = name.replace(" ", "")
    if INCLUDE_PARENTHESES_VARIANTS:
        name = re.sub(r"\(.*?\)", "", name).strip()
    return name


def safe_goto(page, url, timeout=60000):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        page.wait_for_timeout(2500)
        return True
    except Exception as e:
        print("페이지 이동 실패:", url)
        print("이유:", e)
        return False


def save_debug_page(page, name):
    html_path = DEBUG_DIR / f"{name}.html"
    png_path = DEBUG_DIR / f"{name}.png"
    try:
        html_path.write_text(page.content(), encoding="utf-8")
    except Exception as e:
        print("디버그 HTML 저장 실패:", e)
    try:
        page.screenshot(path=str(png_path), full_page=True)
    except Exception as e:
        print("디버그 스크린샷 저장 실패:", e)
    print("디버그 저장:", html_path)
    print("디버그 저장:", png_path)


# =========================================================
# 2. /lecture 검색 페이지 제어
# =========================================================

def open_lecture_page(page):
    return safe_goto(page, BASE_URL + "/lecture", timeout=60000)


def ensure_name_search_mode(page):
    selectors = [
        'input[value="name"]',
        'input[name="condition"][value="name"]',
    ]
    for selector in selectors:
        try:
            radio = page.locator(selector).first
            if radio.count() > 0:
                radio.check(force=True, timeout=3000)
                page.wait_for_timeout(500)
                return True
        except Exception:
            pass
    try:
        page.evaluate("""
        () => {
            const radio = document.querySelector('input[value="name"]')
                || document.querySelector('input[name="condition"][value="name"]');
            if (radio) {
                radio.checked = true;
                radio.dispatchEvent(new Event('change', { bubbles: true }));
                radio.dispatchEvent(new Event('click', { bubbles: true }));
            }
        }
        """)
        page.wait_for_timeout(500)
        return True
    except Exception:
        return False


def search_lecture_keyword(page, keyword):
    print(f"\n검색어 입력: {keyword}")
    try:
        ensure_name_search_mode(page)
        search_selectors = [
            "form.searchbar input[type='search']",
            "input[type='search']",
            "input[name='keyword']",
        ]
        search_input = None
        for selector in search_selectors:
            loc = page.locator(selector).first
            if loc.count() > 0:
                search_input = loc
                break
        if search_input is None:
            print("검색창을 찾지 못했습니다.")
            save_debug_page(page, f"failed_find_searchbar_{safe_filename(keyword)}")
            return False
        search_input.click(timeout=3000)
        page.wait_for_timeout(500)
        search_input.fill("")
        page.wait_for_timeout(500)
        search_input.fill(keyword)
        page.wait_for_timeout(500)
        search_input.press("Enter")
        page.wait_for_timeout(4000)
        return True
    except Exception as e:
        print("검색어 입력 실패:", e)
        save_debug_page(page, f"failed_search_{safe_filename(keyword)}")
        return False


def get_search_card_count(page):
    count = 0
    for selector in [".lectures a.lecture", ".articles a.article"]:
        try:
            count += page.locator(selector).count()
        except Exception:
            pass
    return count


def scroll_lecture_results(page, max_rounds=SEARCH_SCROLL_ROUNDS):
    previous_count = -1
    stable_count = 0
    for i in range(max_rounds):
        current_count = get_search_card_count(page)
        print(f"검색 결과 스크롤 {i + 1}/{max_rounds}, 현재 카드 수: {current_count}")
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(random.randint(1200, 2200))
        except Exception:
            pass
        new_count = get_search_card_count(page)
        if new_count == previous_count:
            stable_count += 1
        else:
            stable_count = 0
        previous_count = new_count
        if stable_count >= 3:
            break


# =========================================================
# 3. 검색 결과에서 lecture_id 추출
# =========================================================

def extract_target_cards_from_current_page(page, search_keyword=None):
    cards = page.evaluate(
        """
        ({ targetNames, includeParenthesesVariants }) => {
            const result = [];
            function normalizeName(text) {
                if (!text) return "";
                let name = text.replace(/\s+/g, "").trim();
                if (includeParenthesesVariants) {
                    name = name.replace(/\(.*?\)/g, "").trim();
                }
                return name;
            }
            document.querySelectorAll('.lectures a.lecture').forEach(a => {
                const nameEl = a.querySelector('.name');
                const profEl = a.querySelector('.professor');
                const starOn = a.querySelector('.rate .star .on');
                const rawCourseName = nameEl ? nameEl.textContent.trim() : '';
                const normalizedCourseName = normalizeName(rawCourseName);
                const professor = profEl ? profEl.textContent.trim() : '';
                const href = a.getAttribute('href') || '';
                const starStyle = starOn ? starOn.getAttribute('style') : '';
                if (targetNames.includes(normalizedCourseName)) {
                    result.push({
                        source_type: 'lecture_card',
                        raw_course_name: rawCourseName,
                        normalized_course_name: normalizedCourseName,
                        professor_raw: professor,
                        href: href,
                        star_style: starStyle,
                        semester: '',
                        posvote: '',
                        preview_text: ''
                    });
                }
            });
            document.querySelectorAll('.articles a.article').forEach(a => {
                const nameEl = a.querySelector('.articlename');
                const profEl = a.querySelector('.professor');
                const semesterEl = a.querySelector('.info .semester');
                const posvoteEl = a.querySelector('.info .posvote');
                const textEl = a.querySelector('.text');
                const starOn = a.querySelector('.rate .star .on');
                const rawCourseName = nameEl ? nameEl.textContent.trim() : '';
                const normalizedCourseName = normalizeName(rawCourseName);
                const professor = profEl ? profEl.textContent.trim() : '';
                const semester = semesterEl ? semesterEl.textContent.trim() : '';
                const posvote = posvoteEl ? posvoteEl.textContent.trim() : '';
                const previewText = textEl ? textEl.textContent.trim() : '';
                const href = a.getAttribute('href') || '';
                const starStyle = starOn ? starOn.getAttribute('style') : '';
                if (targetNames.includes(normalizedCourseName)) {
                    result.push({
                        source_type: 'article_card',
                        raw_course_name: rawCourseName,
                        normalized_course_name: normalizedCourseName,
                        professor_raw: professor,
                        href: href,
                        star_style: starStyle,
                        semester: semester,
                        posvote: posvote,
                        preview_text: previewText
                    });
                }
            });
            return result;
        }
        """,
        {
            "targetNames": TARGET_COURSE_NAMES,
            "includeParenthesesVariants": INCLUDE_PARENTHESES_VARIANTS,
        },
    )
    rows = []
    for card in cards:
        href = card.get("href")
        lecture_id = extract_lecture_id_from_href(href)
        if not lecture_id:
            continue
        semester = clean_text(card.get("semester"))
        preview_year = None
        preview_semester_type = None
        if semester:
            year_match = re.search(r"(\d{2})년", semester)
            if year_match:
                preview_year = 2000 + int(year_match.group(1))
            sem_match = re.search(r"([12])학기", semester)
            if sem_match:
                preview_semester_type = f"{sem_match.group(1)}학기"
        rows.append({
            "search_keyword": search_keyword,
            "source_type": clean_text(card.get("source_type")),
            "course_name": clean_text(card.get("normalized_course_name")),
            "raw_course_name": clean_text(card.get("raw_course_name")),
            "professor_raw": clean_text(card.get("professor_raw")),
            "lecture_id": lecture_id,
            "lecture_url_overview": make_overview_url(lecture_id),
            "lecture_url_article": make_article_url(lecture_id),
            "lecture_url_exam": make_exam_url(lecture_id),
            "preview_semester": semester,
            "preview_year": preview_year,
            "preview_semester_type": preview_semester_type,
            "preview_posvote": safe_int(card.get("posvote")),
            "preview_text": clean_text(card.get("preview_text")),
            "lecture_card_rating": rating_from_style(card.get("star_style")),
            "lecture_card_rating_width_percent": extract_width_percent(card.get("star_style")),
        })
    return pd.DataFrame(rows)


def collect_target_lecture_ids(page):
    all_results = []
    for keyword in SEARCH_KEYWORDS:
        print(f"\n===== 검색 시작: {keyword} =====")
        if not open_lecture_page(page):
            continue
        if not search_lecture_keyword(page, keyword):
            continue
        page.wait_for_timeout(3000)
        scroll_lecture_results(page, max_rounds=SEARCH_SCROLL_ROUNDS)
        df_one = extract_target_cards_from_current_page(page, search_keyword=keyword)
        print(f"{keyword}: 실용영어 카드 수 {len(df_one)}")
        if df_one.empty:
            save_debug_page(page, f"no_target_cards_{safe_filename(keyword)}")
            continue
        all_results.append(df_one)
        random_sleep(2, 5)
    if not all_results:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df_search_results = pd.concat(all_results, ignore_index=True)
    df_search_results = (
        df_search_results
        .drop_duplicates(subset=["course_name", "raw_course_name", "professor_raw", "lecture_id"])
        .reset_index(drop=True)
    )
    df_search_results.to_csv(OUTPUT_DIR / "practical_english_lecture_search_results.csv", index=False, encoding="utf-8-sig")
    df_summary = (
        df_search_results
        .groupby(["course_name", "lecture_id", "lecture_url_overview", "lecture_url_article", "lecture_url_exam"], dropna=False)
        .agg(
            raw_course_name=("raw_course_name", "first"),
            professor_raw=("professor_raw", "first"),
            first_preview_year=("preview_year", "min"),
            last_preview_year=("preview_year", "max"),
            preview_year_count=("preview_year", lambda x: x.dropna().nunique()),
            preview_count=("lecture_id", "count"),
            lecture_card_rating=("lecture_card_rating", "first"),
            lecture_card_rating_width_percent=("lecture_card_rating_width_percent", "first"),
        )
        .reset_index()
        .sort_values(["course_name", "preview_year_count", "preview_count", "lecture_card_rating"], ascending=[True, False, False, False])
    )
    df_summary.to_csv(OUTPUT_DIR / "practical_english_lecture_id_summary.csv", index=False, encoding="utf-8-sig")
    df_targets = (
        df_search_results
        .dropna(subset=["lecture_id"])
        .drop_duplicates(subset=["lecture_id"])
        .reset_index(drop=True)
    )
    if MAX_LECTURE_IDS is not None:
        df_targets = df_targets.head(MAX_LECTURE_IDS)
    df_targets.to_csv(OUTPUT_DIR / "practical_english_lecture_targets.csv", index=False, encoding="utf-8-sig")
    print("\n강의평 수집 대상")
    show_cols = ["course_name", "raw_course_name", "professor_raw", "lecture_id", "lecture_url_overview", "lecture_card_rating"]
    print(df_targets[show_cols])
    print("\n강의평 수집 대상 lecture_id 수:", len(df_targets))
    return df_search_results, df_summary, df_targets


# =========================================================
# 4. 강의 개요 페이지 파싱
# =========================================================

def parse_lecture_info_from_initial_state(soup):
    state_el = soup.select_one("script#__INITIAL_STATE__")
    if not state_el:
        return {}
    try:
        raw = state_el.get_text(strip=True)
        decoded = unquote(raw)
        data = json.loads(decoded)
        lecture = data.get("lecture", {}) or {}
        return {
            "state_lecture_id": lecture.get("id"),
            "state_course_name": lecture.get("name"),
            "state_professor_raw": lecture.get("professor"),
            "state_professors": "|".join(lecture.get("professors", []) or []),
        }
    except Exception:
        return {}


def get_total_review_count_from_overview_page(page):
    """
    개요 페이지의 span.count에서 전체 강의평 수 추출.
    예: <span class="count">(33개)</span> -> 33
    반드시 강의평 더 보기 클릭 전에 실행.
    """
    try:
        result = page.evaluate("""
        () => {
            function parseNumber(text) {
                if (!text) return null;
                const cleaned = text.replace(/,/g, '').trim();
                let m = cleaned.match(/(\d+)\s*개/);
                if (m) return parseInt(m[1], 10);
                m = cleaned.match(/\d+/);
                if (m) return parseInt(m[0], 10);
                return null;
            }
            const selectors = [
                'section.review .rating .title span.count',
                'section.review span.count',
                '.review .count',
                'span.count'
            ];
            for (const selector of selectors) {
                const els = Array.from(document.querySelectorAll(selector));
                for (const el of els) {
                    const text = (el.innerText || el.textContent || '').trim();
                    const num = parseNumber(text);
                    if (num !== null && num > 0) {
                        return { total: num, selector: selector, text: text };
                    }
                }
            }
            return { total: null, selector: null, text: null };
        }
        """)
        return result
    except Exception as e:
        print("개요 페이지 span.count 추출 실패:", e)
        return {"total": None, "selector": None, "text": None}


def parse_lecture_overview_page(html_text, lecture_id=None, source_url=None):
    soup = BeautifulSoup(html_text, "lxml")
    state_info = parse_lecture_info_from_initial_state(soup)
    course_name = None
    professor_raw = None
    title_el = soup.select_one(".bottombar > .title")
    if title_el:
        course_name = clean_text(title_el.get_text(" ", strip=True))
    for item in soup.select("section.info .item"):
        label_el = item.select_one("label")
        value_el = item.select_one("span")
        label = clean_text(label_el.get_text(" ", strip=True)) if label_el else None
        value = clean_text(value_el.get_text(" ", strip=True)) if value_el else None
        if label == "과목명":
            course_name = value
        elif label == "교수명":
            professor_raw = value
    if not course_name:
        course_name = state_info.get("state_course_name")
    if not professor_raw:
        professor_raw = state_info.get("state_professor_raw")
    avg_rating = None
    review_count_total = None
    avg_rating_width_percent = None
    avg_el = soup.select_one("section.review .rating .title .average")
    if avg_el:
        avg_rating = safe_float(avg_el.get_text())
    count_el = soup.select_one("section.review .rating .title .count")
    if count_el:
        review_count_total = count_from_text(count_el.get_text())
    avg_star_on = soup.select_one("section.review .rating .title .star .on")
    if avg_star_on:
        avg_rating_width_percent = extract_width_percent(avg_star_on.get("style", ""))
    lecture_summary = {
        "lecture_id": lecture_id or state_info.get("state_lecture_id"),
        "source_url": source_url,
        "course_name": course_name,
        "professor_raw": professor_raw,
        "professors_raw": state_info.get("state_professors"),
        "avg_rating": avg_rating,
        "avg_rating_width_percent": avg_rating_width_percent,
        "review_count_total": review_count_total,
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    rating_distribution_rows = []
    for rate in soup.select("section.review .rating .rates .rate"):
        value_el = rate.select_one(".value")
        vote_el = rate.select_one(".vote")
        gauge_el = rate.select_one(".gauge")
        value_classes = value_el.get("class", []) if value_el else []
        vote_classes = vote_el.get("class", []) if vote_el else []
        rating_distribution_rows.append({
            "lecture_id": lecture_id,
            "course_name": course_name,
            "professor_raw": professor_raw,
            "rating_value": safe_int(value_el.get_text()) if value_el else None,
            "vote_percent": percent_to_float(vote_el.get_text()) if vote_el else None,
            "gauge_percent": extract_width_percent(gauge_el.get("style", "")) if gauge_el else None,
            "is_winner": "winner" in value_classes or "winner" in vote_classes,
        })
    subjective_rows = []
    objective_rows = []
    for detail in soup.select("section.review .assessment .detail"):
        category_el = detail.select_one("h3")
        category = clean_text(category_el.get_text(" ", strip=True)) if category_el else None
        if not category:
            continue
        if "subjective" in detail.get("class", []):
            for item in detail.select(".items .item"):
                gauge_el = item.select_one(".gauge")
                option_el = item.select_one(".gauge span")
                vote_el = item.select_one(".vote")
                gauge_classes = gauge_el.get("class", []) if gauge_el else []
                vote_classes = vote_el.get("class", []) if vote_el else []
                sentiment_type = None
                for cls in gauge_classes + vote_classes:
                    if cls in ["positive", "neutral", "negative"]:
                        sentiment_type = cls
                subjective_rows.append({
                    "lecture_id": lecture_id,
                    "course_name": course_name,
                    "professor_raw": professor_raw,
                    "assessment_category": category,
                    "assessment_option": clean_text(option_el.get_text(" ", strip=True)) if option_el else None,
                    "vote_percent": percent_to_float(vote_el.get_text()) if vote_el else None,
                    "gauge_percent": extract_width_percent(gauge_el.get("style", "")) if gauge_el else None,
                    "sentiment_type": sentiment_type,
                    "is_winner": "winner" in gauge_classes or "winner" in vote_classes,
                })
        elif "objective" in detail.get("class", []):
            for span in detail.select(".options span"):
                classes = span.get("class", []) or []
                objective_rows.append({
                    "lecture_id": lecture_id,
                    "course_name": course_name,
                    "professor_raw": professor_raw,
                    "assessment_category": category,
                    "assessment_option": clean_text(span.get_text(" ", strip=True)),
                    "is_majority": "majority" in classes,
                })
    preview_reviews = parse_reviews_from_lecture_page(
        html_text,
        lecture_id=lecture_id,
        source_url=source_url,
        default_course_name=course_name,
        default_professor_raw=professor_raw,
        source_tab="overview"
    )
    book_rows = []
    for book in soup.select("section.book a.item"):
        title_el = book.select_one(".info .title")
        author_el = book.select_one(".info .author")
        publisher_el = book.select_one(".info .publisher")
        selling_el = book.select_one(".price .selling")
        production_el = book.select_one(".price .production")
        book_rows.append({
            "lecture_id": lecture_id,
            "course_name": course_name,
            "professor_raw": professor_raw,
            "book_title": clean_text(title_el.get_text(" ", strip=True)) if title_el else None,
            "book_author": clean_text(author_el.get_text(" ", strip=True)) if author_el else None,
            "book_publisher": clean_text(publisher_el.get_text(" ", strip=True)) if publisher_el else None,
            "book_selling_price": clean_text(selling_el.get_text(" ", strip=True)) if selling_el else None,
            "book_original_price": clean_text(production_el.get_text(" ", strip=True)) if production_el else None,
            "book_url": book.get("href"),
        })
    exam_rows = []
    for question in soup.select("section.exam .contents .question"):
        exam_part_el = question.select_one("h3")
        exam_part = clean_text(exam_part_el.get_text(" ", strip=True)) if exam_part_el else None
        for option_el in question.select(".options span"):
            classes = option_el.get("class", []) or []
            exam_rows.append({
                "lecture_id": lecture_id,
                "course_name": course_name,
                "professor_raw": professor_raw,
                "exam_section": exam_part,
                "exam_item_type": "option",
                "exam_option": clean_text(option_el.get_text(" ", strip=True)),
                "is_majority": "majority" in classes,
                "exam_text": None,
                "source_tab": "overview_or_exam",
            })
    knowhow = soup.select_one("section.exam .contents .knowhow")
    if knowhow:
        h3_el = knowhow.select_one("h3")
        text_el = knowhow.select_one(".text")
        exam_rows.append({
            "lecture_id": lecture_id,
            "course_name": course_name,
            "professor_raw": professor_raw,
            "exam_section": clean_text(h3_el.get_text(" ", strip=True)) if h3_el else "전략",
            "exam_item_type": "text",
            "exam_option": None,
            "is_majority": None,
            "exam_text": clean_text(text_el.get_text(" ", strip=True)) if text_el else None,
            "source_tab": "overview_or_exam",
        })
    return {
        "lecture_summary": lecture_summary,
        "rating_distribution": pd.DataFrame(rating_distribution_rows),
        "assessment_subjective": pd.DataFrame(subjective_rows),
        "assessment_objective": pd.DataFrame(objective_rows),
        "preview_reviews": preview_reviews,
        "books": pd.DataFrame(book_rows),
        "exam_info": pd.DataFrame(exam_rows),
    }


# =========================================================
# 5. 강의평 진입 / 카운트 매칭 스크롤
# =========================================================

def enter_review_page(page, article_url):
    selectors = [
        "a.more:has-text('강의평 더 보기')",
        "text=강의평 더 보기",
        "text=강의평 더보기",
        "a[href*='tab=article']",
        ".tabbar a:has-text('강의평')",
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0 and loc.is_visible():
                print("강의평 진입 클릭 후보 발견:", selector)
                try:
                    loc.click(timeout=3000)
                except Exception:
                    loc.evaluate("(el) => el.click()")
                page.wait_for_timeout(4000)
                loaded_count = get_loaded_review_count(page)
                print("클릭 후 로딩된 강의평 수:", loaded_count)
                if loaded_count > 0:
                    return True
        except Exception:
            pass
    print("클릭 진입 실패. 강의평 탭 URL로 직접 이동합니다.")
    ok = safe_goto(page, article_url, timeout=30000)
    page.wait_for_timeout(4000)
    loaded_count = get_loaded_review_count(page)
    print("직접 이동 후 로딩된 강의평 수:", loaded_count)
    return ok and loaded_count > 0


def get_loaded_review_count(page):
    try:
        data = page.evaluate("""
        () => {
            const selectors = [
                'section.review .articles .article',
                'section.review article',
                '.articles .article',
                'a.article',
                'div.article'
            ];
            const seen = new Set();
            for (const selector of selectors) {
                document.querySelectorAll(selector).forEach(article => {
                    const textEl = article.querySelector('.text');
                    if (!textEl) return;
                    const text = (textEl.innerText || textEl.textContent || '').trim();
                    if (!text) return;
                    const semesterEl = article.querySelector('.info .semester');
                    const semester = semesterEl ? (semesterEl.innerText || semesterEl.textContent || '').trim() : '';
                    const starEl = article.querySelector('.rate .star .on');
                    const starStyle = starEl ? starEl.getAttribute('style') || '' : '';
                    const key = semester + '|' + starStyle + '|' + text;
                    seen.add(key);
                });
            }
            return { count: seen.size };
        }
        """)
        return data.get("count", 0)
    except Exception:
        return 0


def scroll_review_area(page):
    try:
        result = page.evaluate("""
        () => {
            function info(el) {
                if (!el) return null;
                return {
                    tag: el.tagName,
                    id: el.id || '',
                    className: String(el.className || ''),
                    scrollTop: el.scrollTop || 0,
                    scrollHeight: el.scrollHeight || 0,
                    clientHeight: el.clientHeight || 0
                };
            }
            const candidates = [];
            const prioritySelectors = [
                'section.review .articles',
                'section.review',
                '.articles',
                '.pane',
                '.container',
                'main',
                '#app',
                'body'
            ];
            for (const selector of prioritySelectors) {
                const el = document.querySelector(selector);
                if (el) candidates.push(el);
            }
            const scrollables = Array.from(document.querySelectorAll('div, section, main, article'))
                .filter(el => {
                    const style = window.getComputedStyle(el);
                    const overflowY = style.overflowY;
                    return (
                        el.scrollHeight > el.clientHeight + 50 &&
                        ['auto', 'scroll', 'overlay'].includes(overflowY)
                    );
                });
            candidates.push(...scrollables);
            let target = null;
            for (const el of candidates) {
                if (!el) continue;
                if (el.scrollHeight > el.clientHeight + 50) {
                    target = el;
                    break;
                }
            }
            const before = { windowY: window.scrollY, target: info(target) };
            if (target && target !== document.body) {
                const move = Math.max(300, Math.floor(target.clientHeight * 0.9));
                target.scrollTop = target.scrollTop + move;
                target.dispatchEvent(new Event('scroll', { bubbles: true }));
            }
            const windowMove = Math.max(500, Math.floor(window.innerHeight * 0.9));
            window.scrollBy(0, windowMove);
            window.dispatchEvent(new Event('scroll', { bubbles: true }));
            document.dispatchEvent(new Event('scroll', { bubbles: true }));
            const after = { windowY: window.scrollY, target: info(target) };
            return { before, after };
        }
        """)
        try:
            page.mouse.wheel(0, random.randint(1200, 2200))
        except Exception:
            pass
        page.wait_for_timeout(random.randint(1200, 2500))
        return result
    except Exception as e:
        print("스크롤 실패:", e)
        return None


def wait_for_review_count_change(page, before_count, timeout_sec=8):
    start = time.time()
    while time.time() - start < timeout_sec:
        current_count = get_loaded_review_count(page)
        if current_count > before_count:
            return current_count, True
        page.wait_for_timeout(500)
    return get_loaded_review_count(page), False


def scroll_until_count_match(page, lecture_id, total_count, max_rounds=REVIEW_MAX_SCROLL_ROUNDS):
    logs = []
    stable_count = 0
    previous_loaded_count = -1
    print("\n강의평 스크롤 매칭 시작")
    print("목표 전체 강의평 수:", total_count)
    for round_idx in range(1, max_rounds + 1):
        loaded_count = get_loaded_review_count(page)
        print(f"[{round_idx}/{max_rounds}] 현재 로딩 수: {loaded_count}, 목표 수: {total_count}")
        logs.append({
            "lecture_id": lecture_id,
            "round": round_idx,
            "stage": "before_scroll",
            "loaded_count": loaded_count,
            "total_count": total_count,
            "is_match": loaded_count == total_count if total_count is not None else None,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        if total_count is not None and loaded_count == total_count:
            print("현재 로딩 수와 전체 수가 일치합니다. 스크롤 종료.")
            break
        if total_count is not None and loaded_count > total_count:
            print("현재 로딩 수가 전체 수보다 큽니다. 중복 카운트 가능성이 있어 종료합니다.")
            break
        if loaded_count == previous_loaded_count:
            stable_count += 1
        else:
            stable_count = 0
        previous_loaded_count = loaded_count
        if stable_count >= REVIEW_STABLE_LIMIT:
            print(f"{REVIEW_STABLE_LIMIT}회 연속 증가 없음. 예외 종료합니다.")
            save_debug_page(page, f"stable_stop_{lecture_id}_{loaded_count}")
            break
        before_count = loaded_count
        scroll_result = scroll_review_area(page)
        after_count, changed = wait_for_review_count_change(page, before_count=before_count, timeout_sec=8)
        print(f"스크롤 결과: {before_count} -> {after_count} {'(증가)' if changed else '(증가 없음)'}")
        logs.append({
            "lecture_id": lecture_id,
            "round": round_idx,
            "stage": "after_scroll",
            "loaded_count": after_count,
            "total_count": total_count,
            "is_match": after_count == total_count if total_count is not None else None,
            "changed": changed,
            "scroll_result": str(scroll_result),
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        if total_count is not None and after_count == total_count:
            print("스크롤 후 전체 수와 일치합니다. 종료합니다.")
            break
        if round_idx % 10 == 0:
            save_debug_page(page, f"review_scroll_round_{round_idx}_{lecture_id}_{after_count}")
    return pd.DataFrame(logs)


# =========================================================
# 6. 강의평 파싱
# =========================================================

def parse_reviews_from_lecture_page(html_text, lecture_id=None, source_url=None, default_course_name=None, default_professor_raw=None, source_tab="article"):
    soup = BeautifulSoup(html_text, "lxml")
    detail_course_name = default_course_name
    detail_professor_raw = default_professor_raw
    if not detail_course_name:
        title_el = soup.select_one(".bottombar > .title")
        if title_el:
            detail_course_name = clean_text(title_el.get_text(" ", strip=True))
    if not detail_professor_raw:
        for item in soup.select("section.info .item"):
            label_el = item.select_one("label")
            value_el = item.select_one("span")
            label = clean_text(label_el.get_text(" ", strip=True)) if label_el else None
            value = clean_text(value_el.get_text(" ", strip=True)) if value_el else None
            if label == "교수명":
                detail_professor_raw = value
    rows = []
    seen = set()
    article_selectors = [
        "section.review .articles .article",
        "section.review article",
        ".articles .article",
        "a.article",
        "div.article",
    ]
    for selector in article_selectors:
        for article in soup.select(selector):
            text_el = article.select_one(".text")
            if not text_el:
                continue
            review_text = clean_text(text_el.get_text(" ", strip=True))
            if not review_text:
                continue
            semester_el = article.select_one(".info .semester")
            posvote_el = article.select_one(".info .posvote")
            star_on = article.select_one(".rate .star .on")
            review_semester = clean_text(semester_el.get_text(" ", strip=True)) if semester_el else None
            posvote = clean_text(posvote_el.get_text(" ", strip=True)) if posvote_el else None
            star_style = star_on.get("style", "") if star_on else ""
            review_rating_width_percent = extract_width_percent(star_style)
            review_rating = rating_from_style(star_style)
            review_year = None
            review_semester_type = None
            if review_semester:
                year_match = re.search(r"(\d{2})년", review_semester)
                if year_match:
                    review_year = 2000 + int(year_match.group(1))
                sem_match = re.search(r"([12])학기", review_semester)
                if sem_match:
                    review_semester_type = f"{sem_match.group(1)}학기"
            key = (lecture_id, review_semester, review_rating, review_text)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "lecture_id": lecture_id,
                "source_url": source_url,
                "source_tab": source_tab,
                "course_name": detail_course_name,
                "professor_raw": detail_professor_raw,
                "review_semester": review_semester,
                "review_year": review_year,
                "review_semester_type": review_semester_type,
                "review_rating": review_rating,
                "review_rating_width_percent": review_rating_width_percent,
                "posvote": safe_int(posvote),
                "review_text": review_text,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
    return pd.DataFrame(rows)


# =========================================================
# 7. 저장 함수
# =========================================================

def save_lecture_detail_outputs(lecture_id, course_name, professor_raw, detail_data, full_reviews_df=None, scroll_logs_df=None):
    lecture_folder_name = f"{lecture_id}_{safe_filename(course_name)}_{safe_filename(professor_raw)}"
    lecture_dir = OUTPUT_DIR / "by_lecture" / lecture_folder_name
    lecture_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([detail_data["lecture_summary"]]).to_csv(lecture_dir / "lecture_summary.csv", index=False, encoding="utf-8-sig")
    detail_data["rating_distribution"].to_csv(lecture_dir / "rating_distribution.csv", index=False, encoding="utf-8-sig")
    detail_data["assessment_subjective"].to_csv(lecture_dir / "assessment_subjective.csv", index=False, encoding="utf-8-sig")
    detail_data["assessment_objective"].to_csv(lecture_dir / "assessment_objective.csv", index=False, encoding="utf-8-sig")
    detail_data["preview_reviews"].to_csv(lecture_dir / "preview_reviews.csv", index=False, encoding="utf-8-sig")
    if full_reviews_df is not None and not full_reviews_df.empty:
        full_reviews_df.to_csv(lecture_dir / "reviews_full.csv", index=False, encoding="utf-8-sig")
    if scroll_logs_df is not None and not scroll_logs_df.empty:
        scroll_logs_df.to_csv(lecture_dir / "review_scroll_log.csv", index=False, encoding="utf-8-sig")
    detail_data["books"].to_csv(lecture_dir / "books.csv", index=False, encoding="utf-8-sig")
    detail_data["exam_info"].to_csv(lecture_dir / "exam_info.csv", index=False, encoding="utf-8-sig")
    return lecture_dir


def anonymize_reviews(df_reviews):
    if df_reviews.empty:
        return pd.DataFrame(), pd.DataFrame()
    professor_candidates = []
    for col in ["professor_raw", "target_professor_raw"]:
        if col in df_reviews.columns:
            professor_candidates.extend(df_reviews[col].dropna().tolist())
    professors = sorted(set(professor_candidates))
    mapping = {name: f"P{i:03d}" for i, name in enumerate(professors, start=1)}
    df = df_reviews.copy()
    if "professor_raw" in df.columns:
        df["professor_id"] = df["professor_raw"].map(mapping)
    if "target_professor_raw" in df.columns:
        df["target_professor_id"] = df["target_professor_raw"].map(mapping)
    mapping_df = pd.DataFrame([{"professor_raw": name, "professor_id": pid} for name, pid in mapping.items()])
    drop_cols = [col for col in ["professor_raw", "target_professor_raw"] if col in df.columns]
    df_public = df.drop(columns=drop_cols)
    df_public.to_csv(OUTPUT_DIR / "practical_english_reviews_anonymized.csv", index=False, encoding="utf-8-sig")
    mapping_df.to_csv(OUTPUT_DIR / "professor_mapping_private.csv", index=False, encoding="utf-8-sig")
    return df_public, mapping_df


# =========================================================
# 8. 강의별 전체 수집
# =========================================================

def collect_full_details_for_targets(page, df_targets):
    all_lecture_summaries = []
    all_rating_distributions = []
    all_assessment_subjective = []
    all_assessment_objective = []
    all_preview_reviews = []
    all_full_reviews = []
    all_books = []
    all_exam_info = []
    all_scroll_logs = []
    for idx, row in df_targets.iterrows():
        lecture_id = row["lecture_id"]
        lecture_url_overview = make_overview_url(lecture_id)
        lecture_url_article = make_article_url(lecture_id)
        lecture_url_exam = make_exam_url(lecture_id)
        print(f"\n[{idx + 1}/{len(df_targets)}] 강의 전체 정보 수집")
        print("검색 과목명:", row.get("course_name"))
        print("원본 과목명:", row.get("raw_course_name"))
        print("교수:", row.get("professor_raw"))
        print("개요 URL:", lecture_url_overview)
        full_reviews_df = pd.DataFrame()
        scroll_logs_df = pd.DataFrame()
        try:
            ok = safe_goto(page, lecture_url_overview, timeout=30000)
            if not ok:
                continue
            page.wait_for_timeout(random.randint(3000, 6000))
            total_data = get_total_review_count_from_overview_page(page)
            total_review_count_from_span = total_data.get("total")
            print("개요 span.count:", total_data)
            overview_html = page.content()
            if SAVE_LECTURE_HTML:
                overview_html_file = HTML_DIR / f"overview_{lecture_id}_{safe_filename(row.get('course_name'))}.html"
                overview_html_file.write_text(overview_html, encoding="utf-8")
            detail_data = parse_lecture_overview_page(overview_html, lecture_id=lecture_id, source_url=lecture_url_overview)
            summary = detail_data["lecture_summary"]
            summary["target_course_name"] = row.get("course_name")
            summary["target_raw_course_name"] = row.get("raw_course_name")
            summary["target_professor_raw"] = row.get("professor_raw")
            summary["lecture_card_rating"] = row.get("lecture_card_rating")
            summary["lecture_card_rating_width_percent"] = row.get("lecture_card_rating_width_percent")
            summary["lecture_final_rating"] = summary.get("avg_rating") if summary.get("avg_rating") is not None else row.get("lecture_card_rating")
            summary["search_keyword"] = row.get("search_keyword")
            summary["review_count_from_span"] = total_review_count_from_span
            summary["review_count_span_selector"] = total_data.get("selector")
            summary["review_count_span_text"] = total_data.get("text")
            all_lecture_summaries.append(pd.DataFrame([summary]))
            if not detail_data["rating_distribution"].empty:
                all_rating_distributions.append(detail_data["rating_distribution"])
            if not detail_data["assessment_subjective"].empty:
                all_assessment_subjective.append(detail_data["assessment_subjective"])
            if not detail_data["assessment_objective"].empty:
                all_assessment_objective.append(detail_data["assessment_objective"])
            if not detail_data["preview_reviews"].empty:
                all_preview_reviews.append(detail_data["preview_reviews"])
            if not detail_data["books"].empty:
                all_books.append(detail_data["books"])
            if not detail_data["exam_info"].empty:
                all_exam_info.append(detail_data["exam_info"])
            entered = enter_review_page(page, lecture_url_article)
            if entered:
                scroll_logs_df = scroll_until_count_match(page, lecture_id=lecture_id, total_count=total_review_count_from_span, max_rounds=REVIEW_MAX_SCROLL_ROUNDS)
                if not scroll_logs_df.empty:
                    all_scroll_logs.append(scroll_logs_df)
                article_html = page.content()
                if SAVE_LECTURE_HTML:
                    article_html_file = HTML_DIR / f"article_{lecture_id}_{safe_filename(row.get('course_name'))}.html"
                    article_html_file.write_text(article_html, encoding="utf-8")
                full_reviews_df = parse_reviews_from_lecture_page(
                    article_html,
                    lecture_id=lecture_id,
                    source_url=page.url,
                    default_course_name=summary.get("course_name"),
                    default_professor_raw=summary.get("professor_raw"),
                    source_tab="article"
                )
                if not full_reviews_df.empty:
                    full_reviews_df["lecture_avg_rating"] = summary.get("avg_rating")
                    full_reviews_df["lecture_review_count_total"] = summary.get("review_count_total")
                    full_reviews_df["lecture_review_count_from_span"] = total_review_count_from_span
                    full_reviews_df["lecture_card_rating"] = summary.get("lecture_card_rating")
                    full_reviews_df["lecture_final_rating"] = summary.get("lecture_final_rating")
                    full_reviews_df["target_course_name"] = row.get("course_name")
                    full_reviews_df["target_raw_course_name"] = row.get("raw_course_name")
                    full_reviews_df["target_professor_raw"] = row.get("professor_raw")
                    all_full_reviews.append(full_reviews_df)
            else:
                print("강의평 페이지 진입 실패")
                save_debug_page(page, f"failed_enter_review_{lecture_id}")
            ok = safe_goto(page, lecture_url_exam, timeout=30000)
            if ok:
                page.wait_for_timeout(random.randint(2000, 4000))
                exam_html = page.content()
                if SAVE_LECTURE_HTML:
                    exam_html_file = HTML_DIR / f"exam_{lecture_id}_{safe_filename(row.get('course_name'))}.html"
                    exam_html_file.write_text(exam_html, encoding="utf-8")
                exam_detail_data = parse_lecture_overview_page(exam_html, lecture_id=lecture_id, source_url=lecture_url_exam)
                if not exam_detail_data["exam_info"].empty:
                    exam_df = exam_detail_data["exam_info"].copy()
                    exam_df["source_tab"] = "exam"
                    all_exam_info.append(exam_df)
            lecture_dir = save_lecture_detail_outputs(
                lecture_id=lecture_id,
                course_name=summary.get("course_name") or row.get("course_name"),
                professor_raw=summary.get("professor_raw") or row.get("professor_raw"),
                detail_data=detail_data,
                full_reviews_df=full_reviews_df,
                scroll_logs_df=scroll_logs_df
            )
            print("강의별 저장 완료:", lecture_dir)
            print("전체 강의평 수(span.count):", total_review_count_from_span)
            print("최종 수집 강의평 수:", len(full_reviews_df))
        except Exception as e:
            print("강의 전체 정보 수집 실패:", e)
            save_debug_page(page, f"failed_full_collect_{lecture_id}")
        random_sleep()
    def concat_or_empty(dfs):
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()
    df_lecture_summary = concat_or_empty(all_lecture_summaries)
    df_rating_distribution = concat_or_empty(all_rating_distributions)
    df_assessment_subjective = concat_or_empty(all_assessment_subjective)
    df_assessment_objective = concat_or_empty(all_assessment_objective)
    df_preview_reviews = concat_or_empty(all_preview_reviews)
    df_full_reviews = concat_or_empty(all_full_reviews)
    df_books = concat_or_empty(all_books)
    df_exam_info = concat_or_empty(all_exam_info)
    df_scroll_logs = concat_or_empty(all_scroll_logs)
    if not df_full_reviews.empty:
        df_full_reviews = (
            df_full_reviews
            .drop_duplicates(subset=["lecture_id", "review_semester", "review_rating", "review_text"])
            .reset_index(drop=True)
        )
    if not df_exam_info.empty:
        df_exam_info = df_exam_info.drop_duplicates().reset_index(drop=True)
    df_lecture_summary.to_csv(OUTPUT_DIR / "lecture_summary_all.csv", index=False, encoding="utf-8-sig")
    df_rating_distribution.to_csv(OUTPUT_DIR / "rating_distribution_all.csv", index=False, encoding="utf-8-sig")
    df_assessment_subjective.to_csv(OUTPUT_DIR / "assessment_subjective_all.csv", index=False, encoding="utf-8-sig")
    df_assessment_objective.to_csv(OUTPUT_DIR / "assessment_objective_all.csv", index=False, encoding="utf-8-sig")
    df_preview_reviews.to_csv(OUTPUT_DIR / "preview_reviews_all.csv", index=False, encoding="utf-8-sig")
    df_full_reviews.to_csv(OUTPUT_DIR / "practical_english_reviews_raw.csv", index=False, encoding="utf-8-sig")
    df_books.to_csv(OUTPUT_DIR / "books_all.csv", index=False, encoding="utf-8-sig")
    df_exam_info.to_csv(OUTPUT_DIR / "exam_info_all.csv", index=False, encoding="utf-8-sig")
    df_scroll_logs.to_csv(OUTPUT_DIR / "review_scroll_logs_all.csv", index=False, encoding="utf-8-sig")
    if not df_full_reviews.empty:
        anonymize_reviews(df_full_reviews)
    print("\n통합 저장 완료")
    print("-", OUTPUT_DIR / "lecture_summary_all.csv")
    print("-", OUTPUT_DIR / "rating_distribution_all.csv")
    print("-", OUTPUT_DIR / "assessment_subjective_all.csv")
    print("-", OUTPUT_DIR / "assessment_objective_all.csv")
    print("-", OUTPUT_DIR / "practical_english_reviews_raw.csv")
    print("-", OUTPUT_DIR / "books_all.csv")
    print("-", OUTPUT_DIR / "exam_info_all.csv")
    print("-", OUTPUT_DIR / "review_scroll_logs_all.csv")
    return df_full_reviews


# =========================================================
# 9. 실행
# =========================================================

def main():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=HEADLESS,
            viewport={"width": 1400, "height": 1000},
            slow_mo=80,
        )
        page = context.new_page()
        open_lecture_page(page)
        print("\n브라우저가 열렸습니다.")
        print("에브리타임에 직접 로그인하세요.")
        print("강의실 페이지가 보이면 PowerShell로 돌아와 Enter를 누르세요.")
        input("준비 완료 후 Enter: ")
        page.wait_for_timeout(3000)
        if "/lecture" not in page.url:
            open_lecture_page(page)
        df_search_results, df_summary, df_targets = collect_target_lecture_ids(page)
        if df_targets.empty:
            print("실용영어 lecture_id를 찾지 못했습니다.")
            print("디버그 폴더:", DEBUG_DIR)
            context.close()
            return
        df_reviews = collect_full_details_for_targets(page, df_targets)
        if df_reviews.empty:
            print("수집된 강의평이 없습니다.")
            print("디버그 폴더:", DEBUG_DIR)
        print("\n전체 작업 완료")
        print("결과 폴더:", OUTPUT_DIR)
        context.close()


if __name__ == "__main__":
    main()
