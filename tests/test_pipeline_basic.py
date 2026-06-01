import pandas as pd

from src.course_grouping import normalize_course_group
from src.rating_signals import add_rating_satisfaction_signals, rating_to_satisfaction_signal
from src.segmentation import split_review_to_segments
from src.text_cleaning import clean_review_text, remove_private_patterns, split_korean_sentences


def test_remove_private_patterns_removes_email_phone_and_url():
    text = "문의는 test@example.com 또는 010-1234-5678, https://example.com 으로 주세요."
    cleaned = remove_private_patterns(text)
    assert "test@example.com" not in cleaned
    assert "010-1234-5678" not in cleaned
    assert "https://example.com" not in cleaned


def test_clean_review_text_normalizes_repeated_chars():
    assert "좋아" in clean_review_text("좋아아아!!!")


def test_split_korean_sentences_basic():
    sentences = split_korean_sentences("설명이 좋았습니다. 과제는 많았습니다.")
    assert len(sentences) >= 2
    assert sentences[0].startswith("설명")


def test_split_review_to_segments_contrast_marker():
    segments = split_review_to_segments("교수님 설명은 좋았습니다. 하지만 과제가 많았습니다.")
    texts = [row["segment_text"] for row in segments]
    assert any("설명" in text for text in texts)
    assert any("과제" in text for text in texts)


def test_rating_to_satisfaction_signal_rules():
    assert rating_to_satisfaction_signal(4.5) == "VERY_HIGH_SATISFACTION"
    assert rating_to_satisfaction_signal(4.0) == "HIGH_SATISFACTION"
    assert rating_to_satisfaction_signal(3.5) == "MID_SATISFACTION"
    assert rating_to_satisfaction_signal(2.5) == "LOW_SATISFACTION"
    assert rating_to_satisfaction_signal(1.5) == "VERY_LOW_SATISFACTION"
    assert rating_to_satisfaction_signal(0) == "RATING_UNKNOWN"


def test_add_rating_signals_does_not_create_sentiment_label():
    df = pd.DataFrame({"review_rating": [5.0, 3.0, 1.5]})
    labeled = add_rating_satisfaction_signals(df)
    assert labeled["rating_satisfaction_signal"].tolist() == [
        "VERY_HIGH_SATISFACTION",
        "MID_SATISFACTION",
        "VERY_LOW_SATISFACTION",
    ]
    assert "weak_sentiment_label" not in labeled.columns
    assert "sentiment_label" not in labeled.columns


def test_normalize_course_group():
    assert normalize_course_group("실용영어(Practical English)") == "실용영어"
    assert normalize_course_group("Practical English") == "실용영어"
    assert normalize_course_group("대학글쓰기") == "글쓰기"
