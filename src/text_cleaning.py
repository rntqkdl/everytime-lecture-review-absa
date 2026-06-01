from __future__ import annotations

import re


URL_PATTERN = re.compile(r"(?:https?://\S+|www\.\S+)", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?82[-.\s]?)?(?:0?10|011|016|017|018|019)[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)"
)
LOCAL_PHONE_PATTERN = re.compile(r"(?<!\d)0(?:2|3[1-3]|4[1-4]|5[1-5]|6[1-4])[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)")
STUDENT_ID_PATTERN = re.compile(r"(?<!\d)(?:19|20)\d{2}[-.\s]?\d{4,7}(?!\d)")
LONG_NUMBER_PATTERN = re.compile(r"(?<!\d)\d{8,13}(?!\d)")
RRN_PATTERN = re.compile(r"(?<!\d)\d{6}[-\s]?[1-4]\d{6}(?!\d)")
MESSENGER_PATTERN = re.compile(
    r"(?:\uce74\ud1a1|\uce74\uce74\uc624\ud1a1|\uc624\ud508\ucc44\ud305|\ub77c\uc778|\ud154\ub808\uadf8\ub7a8|\uc544\uc774\ub514|id)\s*[:=\-]?\s*[A-Za-z0-9_.-]{3,}",
    re.IGNORECASE,
)


def normalize_repeated_chars(text: str) -> str:
    if text is None:
        return ""
    normalized = str(text)
    normalized = re.sub(r"(.)\1{2,}", r"\1\1", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def remove_private_patterns(text: str) -> str:
    if text is None:
        return ""
    cleaned = str(text)
    for pattern in (
        URL_PATTERN,
        EMAIL_PATTERN,
        RRN_PATTERN,
        PHONE_PATTERN,
        LOCAL_PHONE_PATTERN,
        STUDENT_ID_PATTERN,
        LONG_NUMBER_PATTERN,
        MESSENGER_PATTERN,
    ):
        cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def clean_review_text(text: str) -> str:
    if text is None:
        return ""
    cleaned = str(text)
    cleaned = cleaned.replace("\u200b", " ").replace("\ufeff", " ")
    cleaned = remove_private_patterns(cleaned)
    cleaned = normalize_repeated_chars(cleaned)
    cleaned = re.sub(r"[^0-9A-Za-z\uAC00-\uD7A3\s.,!?~%&()/+\-:;]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def split_korean_sentences(text: str) -> list[str]:
    cleaned = clean_review_text(text)
    if not cleaned:
        return []

    protected = re.sub(r"([.!?]+)\s*", r"\1\n", cleaned)
    ending_pattern = (
        r"((?:\uc2b5\ub2c8\ub2e4|\uc2b5\ub2c8\uae4c|\uc608\uc694|\uc5d0\uc694|\uc544\uc694|\uc5b4\uc694|"
        r"\uc9c0\uc694|\ub124\uc694|\ud574\uc694|\ud569\ub2c8\ub2e4|\ud588\ub2e4|\ub2e4|\uc694))\s+"
    )
    protected = re.sub(ending_pattern, r"\1\n", protected)
    pieces = re.split(r"[\r\n]+", protected)
    sentences: list[str] = []
    for piece in pieces:
        sentence = piece.strip(" \t\r\n,;")
        if sentence:
            sentences.append(sentence)
    return sentences
