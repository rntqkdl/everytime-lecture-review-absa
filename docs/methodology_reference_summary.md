# 방법론 근거 요약

## 직접 사용
- **Python**: Python 기반 분석 파이프라인으로 강의평 수집부터 결과 표와 그래프 생성까지 수행했다. 근거: `requirements.txt; scripts/run_segment_absa_pipeline.py`
- **pandas**: pandas를 사용해 리뷰와 세그먼트 단위 데이터를 집계하고 검증표를 생성했다. 근거: `requirements.txt; scripts/*.py; make_submission_pack.py`
- **정규표현식과 텍스트 정제**: 정규표현식과 텍스트 정제 함수를 이용해 원문 리뷰를 분석 가능한 형태로 정리했다. 근거: `src/text_cleaning.py; src/anonymize.py; src/io_utils.py`
- **문장과 절 단위 세그먼트 분리**: 리뷰 전체가 아니라 문장과 절 단위 세그먼트를 분석 단위로 삼아 복합 감정을 분리했다. 근거: `src/segmentation.py; scripts/02_preprocess_and_segment_reviews.py`
- **jhgan/ko-sroberta-multitask**: 한국어 문장 임베딩 모델인 jhgan/ko-sroberta-multitask를 적용해 세그먼트 의미 벡터를 생성했다. 근거: `outputs/colab_results/embedding_run_log.csv; notebooks/01_colab_t4_embedding_aspect_discovery.ipynb`
- **UMAP**: UMAP으로 문장 임베딩의 차원을 축소한 뒤 군집화를 수행했다. 근거: `outputs/colab_results/embedding_run_log.csv; notebooks/01_colab_t4_embedding_aspect_discovery.ipynb`
- **HDBSCAN**: HDBSCAN을 이용해 유사한 평가 표현을 군집화하고 111개 평가 요인 후보를 얻었다. 근거: `outputs/colab_results/embedding_run_log.csv; notebooks/01_colab_t4_embedding_aspect_discovery.ipynb`
- **BERTopic**: 최종본에서는 BERTopic 라이브러리를 직접 실행해 세그먼트 topic을 추출하고, topic별 키워드와 대표 문장을 바탕으로 평가 요인을 해석했다. 근거: `scripts/18_run_bertopic_report_analysis.py; outputs/bertopic_analysis/bertopic_run_log.json; outputs/bertopic_analysis/bertopic_topic_info.csv`
- **TF-IDF / CountVectorizer 계열 키워드 추출**: 군집 해석을 위해 TF-IDF 또는 CountVectorizer 계열 방식으로 대표 키워드를 추출했다. 근거: `notebooks/01_colab_t4_embedding_aspect_discovery.ipynb; src/topic_utils.py; src/cpu_baseline.py`
- **monologg/koelectra-base-finetuned-nsmc**: 공개 KoELECTRA 기반 NSMC 감정분석 모델을 적용해 세그먼트별 긍정/부정을 추론했다. 근거: `outputs/colab_results/sentiment_model_run_log.csv; notebooks/02_colab_t4_sentiment_inference.ipynb`
- **별점 신호 분석**: 별점은 감정 정답 라벨이 아니라 전체 만족도 신호로만 사용했다. 근거: `src/rating_signals.py; scripts/07_detect_mixed_sentiment.py; report_validation_summary.md`
- **mixed review, 높은 별점 속 부정, 낮은 별점 속 긍정**: mixed review와 별점-텍스트 불일치를 통해 별점만으로 포착되지 않는 평가 내용을 확인했다. 근거: `outputs/report_analysis/review_level_summary.csv; report_validation_summary.md`
- **글쓰기와 실용영어 과목군 비교**: 글쓰기와 실용영어를 구분해 과목군별 부담 요인과 공통 요인을 비교했다. 근거: `outputs/report_analysis/groupwise_report_pack/groupwise_comparison_summary.csv; cross_group_aspect_comparison.csv`
- **대표 문장 수동 검증**: 대표 문장 7개를 수동 검토해 모델 판단과 연구자 해석의 방향을 확인했다. 근거: `outputs/report_analysis/groupwise_report_pack/ALL/manual_validation_7_samples.csv`

## 이론적 참고
- **Sentence-BERT**: Sentence-BERT 계열 문장 임베딩 방법론에 기반해 세그먼트 의미 표현을 비교했다. 근거: `README.md; notebooks/01_colab_t4_embedding_aspect_discovery.ipynb`
- **CARBD-Ko**: CARBD-Ko와 같은 한국어 리뷰 ABSA 연구의 문제의식을 참고했다. 근거: `README.md`

## 보조 실험
- **cringepnh/koelectra-korean-sentiment**: 보조 감정분석 모델도 실행했으나 본문 집계는 monologg KoELECTRA 결과를 중심으로 제시했다. 근거: `outputs/colab_results/sentiment_model_run_log.csv`
- **tobykim/koelectra-44emotions**: 44개 감정 분류 모델은 확장 실험으로 실행했으며 본문 핵심 수치에는 사용하지 않았다. 근거: `outputs/colab_results/sentiment_model_run_log.csv`
- **dlckdfuf141/korean-emotion-kluebert-v2**: KLUE-BERT 기반 감정 모델은 보조 실험으로 실행했으며 본문 핵심 수치에는 사용하지 않았다. 근거: `outputs/colab_results/sentiment_model_run_log.csv`

## 사용하지 않음 또는 확인 불가
- **EduRABSA**: 필요할 경우 교육 리뷰 ABSA의 선택 참고문헌으로만 다룬다. 근거: `코드와 로그에서 직접 사용 근거 미확인`
