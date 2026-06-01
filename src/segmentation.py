from __future__ import annotations

import re

from src.text_cleaning import clean_review_text, split_korean_sentences


DEFAULT_CONTRAST_MARKERS = [
    "\uadfc\ub370",  # 근데
    "\uadf8\ub7f0\ub370",  # 그런데
    "\ud558\uc9c0\ub9cc",  # 하지만
    "\ub2e4\ub9cc",  # 다만
    "\uadf8\ub798\ub3c4",  # 그래도
    "\ubc18\uba74",  # 반면
    "\uc544\uc26c\uc6b4 \uc810\uc740",  # 아쉬운 점은
    "\ub2e8\uc810\uc740",  # 단점은
    "\uc7a5\uc810\uc740",  # 장점은
]


def split_by_contrast_markers(text: str, markers: list[str] | None = None) -> list[str]:
    value = clean_review_text(text)
    if not value:
        return []
    marker_values = markers or DEFAULT_CONTRAST_MARKERS
    marker_pattern = "|".join(re.escape(marker) for marker in sorted(marker_values, key=len, reverse=True))
    if not marker_pattern:
        return [value]
    pieces = re.split(rf"\s*(?:{marker_pattern})\s*", value)
    return [piece.strip(" ,.;") for piece in pieces if piece.strip(" ,.;")]


def split_review_to_segments(
    text: str,
    contrast_markers: list[str] | None = None,
    min_segment_length: int = 5,
    split_sentence: bool = True,
    split_contrast_markers: bool = True,
) -> list[dict]:
    cleaned = clean_review_text(text)
    if not cleaned:
        return []

    sentences = split_korean_sentences(cleaned) if split_sentence else [cleaned]
    rows: list[dict] = []
    segment_order = 1
    for sentence_order, sentence in enumerate(sentences, start=1):
        segment_texts = split_by_contrast_markers(sentence, contrast_markers) if split_contrast_markers else [sentence]
        for segment_text in segment_texts:
            segment_text = clean_review_text(segment_text)
            if len(segment_text.replace(" ", "")) < min_segment_length:
                continue
            rows.append(
                {
                    "sentence_order": sentence_order,
                    "segment_order": segment_order,
                    "sentence_text": sentence,
                    "segment_text": segment_text,
                    "segment_text_clean": segment_text,
                }
            )
            segment_order += 1
    return rows
