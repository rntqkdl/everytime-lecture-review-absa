from __future__ import annotations

import json
from typing import Any

import pandas as pd


BINARY_BASELINE_MODELS: list[dict[str, Any]] = [
    {
        "name": "koelectra_nsmc_monologg",
        "hf_model": "monologg/koelectra-base-finetuned-nsmc",
        "task": "binary_sentiment",
        "expected_labels": ["NEGATIVE", "POSITIVE"],
        "note": "KoELECTRA NSMC 파인튜닝 baseline. 영화 리뷰 기반이라 강의평과 도메인 차이를 명시한다.",
    },
    {
        "name": "koelectra_nsmc_documented",
        "hf_model": "cringepnh/koelectra-korean-sentiment",
        "task": "binary_sentiment",
        "expected_labels": ["NEGATIVE", "POSITIVE"],
        "note": "NSMC 기반 KoELECTRA 비교 baseline.",
    },
]

EMOTION_EXTENSION_MODELS: list[dict[str, Any]] = [
    {
        "name": "koelectra_kote_44emotion",
        "hf_model": "tobykim/koelectra-44emotions",
        "task": "multi_label_emotion",
        "note": "KOTE 기반 한국어 온라인 댓글 44감정 분석 모델.",
    },
    {
        "name": "kluebert_aihub_7emotion",
        "hf_model": "dlckdfuf141/korean-emotion-kluebert-v2",
        "task": "multi_class_emotion",
        "expected_labels": ["공포", "놀람", "분노", "슬픔", "중립", "행복", "혐오"],
        "note": "KLUE-BERT 기반 7감정 비교 모델.",
    },
]


BINARY_LABEL_MAP = {
    "LABEL_0": "NEGATIVE",
    "0": "NEGATIVE",
    "NEGATIVE": "NEGATIVE",
    "NEG": "NEGATIVE",
    "negative": "NEGATIVE",
    "neg": "NEGATIVE",
    "부정": "NEGATIVE",
    "LABEL_1": "POSITIVE",
    "1": "POSITIVE",
    "POSITIVE": "POSITIVE",
    "POS": "POSITIVE",
    "positive": "POSITIVE",
    "pos": "POSITIVE",
    "긍정": "POSITIVE",
}


def standardize_binary_label(label: str) -> str:
    if label is None:
        return "UNKNOWN"
    raw = str(label).strip()
    return BINARY_LABEL_MAP.get(raw, BINARY_LABEL_MAP.get(raw.upper(), "UNKNOWN"))


def safe_json_dumps(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except TypeError:
        return json.dumps(str(obj), ensure_ascii=False)


def _device_id(device: str = "cuda") -> int:
    if device == "cpu":
        return -1
    try:
        import torch

        return 0 if torch.cuda.is_available() else -1
    except Exception:
        return -1


def _normalize_pipeline_outputs(outputs: Any) -> list[list[dict[str, Any]]]:
    if outputs is None:
        return []
    if isinstance(outputs, dict):
        return [[outputs]]
    if isinstance(outputs, list):
        if not outputs:
            return []
        if all(isinstance(item, dict) for item in outputs):
            return [[item] for item in outputs]
        normalized: list[list[dict[str, Any]]] = []
        for item in outputs:
            if isinstance(item, dict):
                normalized.append([item])
            elif isinstance(item, list):
                normalized.append([score for score in item if isinstance(score, dict)])
            else:
                normalized.append([])
        return normalized
    return []


def _run_pipeline(classifier, batch: list[str], max_length: int):
    try:
        return classifier(batch, truncation=True, max_length=max_length, top_k=None)
    except TypeError:
        return classifier(batch, truncation=True, max_length=max_length, return_all_scores=True)


def predict_with_hf_model(
    texts,
    model_name,
    batch_size,
    max_length,
    device: str = "cuda",
    run_transformer_locally: bool = True,
) -> pd.DataFrame:
    if not run_transformer_locally and _device_id(device) == -1:
        print("run_transformer_locally=false이며 CUDA GPU가 없어 로컬 Transformer 전체 추론을 건너뜁니다.")
        return pd.DataFrame()

    clean_texts = ["" if text is None else str(text) for text in texts]
    if not clean_texts:
        return pd.DataFrame()

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError("transformers 패키지가 필요합니다.") from exc

    classifier = pipeline("text-classification", model=model_name, tokenizer=model_name, device=_device_id(device))
    rows: list[dict[str, Any]] = []
    for start in range(0, len(clean_texts), int(batch_size)):
        batch = clean_texts[start : start + int(batch_size)]
        outputs = _run_pipeline(classifier, batch, int(max_length))
        normalized = _normalize_pipeline_outputs(outputs)
        if len(normalized) != len(batch):
            normalized = normalized[: len(batch)] + [[] for _ in range(max(0, len(batch) - len(normalized)))]

        for offset, (text, score_list) in enumerate(zip(batch, normalized)):
            score_list = score_list or []
            top = max(score_list, key=lambda item: float(item.get("score", 0.0)), default={})
            original_label = str(top.get("label", "UNKNOWN"))
            rows.append(
                {
                    "text_index": start + offset,
                    "sentence_for_model": text,
                    "hf_model": model_name,
                    "predicted_label_original": original_label,
                    "predicted_label_standard": standardize_binary_label(original_label),
                    "predicted_score": float(top.get("score", 0.0)),
                    "all_scores_json": safe_json_dumps(score_list),
                }
            )
    return pd.DataFrame(rows)
