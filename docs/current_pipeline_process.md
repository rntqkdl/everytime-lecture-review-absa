# 현재 최종 분석 과정

## 로컬 CPU 1차
```powershell
cd <프로젝트_폴더>
.\.venv\Scripts\Activate.ps1

python scripts/01_merge_scraped_outputs.py
python scripts/02_preprocess_and_segment_reviews.py
python scripts/03_create_rating_satisfaction_signals.py
python scripts/04_prepare_colab_inputs.py
python scripts/05_optional_cpu_baseline.py
```

한 번에 실행:

```powershell
python scripts/run_segment_absa_pipeline.py --pre-colab-only
```

## Colab T4
1. `notebooks/01_colab_t4_embedding_aspect_discovery.ipynb`
2. `notebooks/02_colab_t4_sentiment_inference.ipynb`
3. 선택: `notebooks/03_colab_t4_optional_domain_finetuning.ipynb`

Colab 결과 CSV는 `outputs/colab_results`에 넣는다.

## 로컬 CPU 2차
```powershell
python scripts/06_merge_colab_results.py
python scripts/07_detect_mixed_sentiment.py
python scripts/08_extract_good_lecture_factors.py
python scripts/09_analyze_rating_signal_relationships.py
python scripts/10_visualize_results.py
python scripts/11_make_public_sample.py
```

한 번에 실행:

```powershell
python scripts/run_segment_absa_pipeline.py --post-colab-only
```

## 정책
- 별점은 `rating_satisfaction_signal`로만 변환한다.
- 별점은 segment 감정 라벨이나 학습 라벨로 사용하지 않는다.
- TF-IDF/NMF는 CPU baseline이며 최종 aspect discovery 방식이 아니다.
