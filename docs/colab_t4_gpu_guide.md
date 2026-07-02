# Colab T4 GPU 실행 가이드

## GPU 설정
Colab에서 노트북을 연 뒤 `런타임 → 런타임 유형 변경 → 하드웨어 가속기 GPU 선택`을 설정한다. 권장 GPU는 T4다. 첫 셀에서 `nvidia-smi`로 GPU가 잡혔는지 확인한다.

## 입력 CSV 생성
로컬에서 먼저 실행한다.

```powershell
python scripts/run_segment_absa_pipeline.py --pre-colab-only
```

업로드할 파일:
- `outputs/colab_input/segments_for_embedding_colab.csv`
- `outputs/colab_input/segments_for_sentiment_colab.csv`
- `outputs/colab_input/colab_model_config.json`

## 노트북 실행 순서
1. `notebooks/01_colab_t4_embedding_aspect_discovery.ipynb`
2. `notebooks/02_colab_t4_sentiment_inference.ipynb`
3. 선택: `notebooks/03_colab_t4_optional_domain_finetuning.ipynb`

## 결과 CSV 다운로드
다운로드한 결과 CSV는 로컬의 다음 폴더에 넣는다.

```text
outputs/colab_results
```

필수 결과:
- `segment_embedding_clusters.csv`
- `aspect_cluster_keywords.csv`
- `aspect_representative_segments.csv`
- `segment_sentiment_predictions_all_models.csv`
- `segment_sentiment_binary_primary.csv`
- `segment_emotion_extension.csv`

## 로컬 결과 병합
```powershell
python scripts/run_segment_absa_pipeline.py --post-colab-only
```

## T4 메모리 부족 시
- embedding batch size를 `128 → 64 → 32` 순서로 낮춘다.
- sentiment batch size를 `32 → 16 → 8` 순서로 낮춘다.
- 모델 하나 실행 후 `del model`, `del tokenizer`, `torch.cuda.empty_cache()`를 실행한다.
- embedding cache가 있으면 재사용한다.

## 주의
Colab 노트북은 `review_rating` 또는 `rating_satisfaction_signal`을 감정 정답으로 두고 accuracy를 계산하지 않는다. 만족도 신호는 모델 예측과의 관계 분석에만 사용한다.
