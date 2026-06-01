from __future__ import annotations

from collections import Counter


ASPECT_KEYWORDS: dict[str, list[str]] = {
    "과제 부담": ["과제", "레포트", "보고서", "제출", "분량", "매주", "숙제"],
    "시험 난이도": ["시험", "중간", "기말", "퀴즈", "족보", "문제", "난이도"],
    "교수 설명": ["설명", "이해", "강의력", "전달", "수업력", "쉽게"],
    "교수 태도": ["친절", "불친절", "열정", "성의", "피드백", "소통"],
    "성적 평가": ["성적", "학점", "A+", "비율", "채점", "평가", "너그러움", "깐깐"],
    "출석": ["출석", "출결", "지각", "결석", "전자출결", "호명"],
    "조모임": ["팀플", "조모임", "조별", "발표", "팀원", "조별과제"],
    "수업 자료": ["자료", "교재", "ppt", "피피티", "프린트", "강의자료"],
    "강의 운영": ["운영", "진도", "공지", "과정", "방식", "온라인", "오프라인"],
    "수업 이해도": ["이해", "쉽다", "어렵다", "기초", "입문", "따라가기"],
}


def tag_aspects_by_keywords(sentence: str) -> list[dict]:
    text = "" if sentence is None else str(sentence)
    lowered = text.lower()
    tags: list[dict] = []
    for aspect, keywords in ASPECT_KEYWORDS.items():
        matched = []
        for keyword in keywords:
            if keyword.lower() in lowered:
                matched.append(keyword)
        if matched:
            counts = Counter(matched)
            tags.append(
                {
                    "aspect": aspect,
                    "matched_keywords": sorted(counts),
                    "match_count": int(sum(counts.values())),
                }
            )
    return tags
