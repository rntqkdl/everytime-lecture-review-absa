# Codex 작업 로그

## 2026-06-01
- 기존 스크래핑 스크립트는 보존했다.
- 별점 기반 weak label 파이프라인을 추가했다.
- 로컬 CPU 단계와 Colab GPU 추론 단계를 분리했다.
- `course_group` 기준으로 글쓰기와 실용영어를 정규화했다.
- 현재 수집 데이터의 규모와 비율을 요약하는 `scripts/12_profile_course_group_data.py`를 추가했다.
- 이후 분석 방향을 `docs/next_steps_roadmap.md`에 정리했다.

## 2026-06-01 segment ABSA 확장
- 첨부 프롬프트 `codex_prompt_optimized_cpu_colab_t4_everytime_absa.md` 기준으로 segment 기반 ABSA 파이프라인을 추가했다.
- 리뷰를 문장/절 단위 `segment`로 나누는 `scripts/02_preprocess_and_segment_reviews.py`와 `src/segmentation.py`를 추가했다.
- 로컬 CPU는 전처리, weak label, Colab 입력 생성, 선택적 TF-IDF/NMF baseline까지만 수행하도록 분리했다.
- Colab T4용 노트북 3개를 추가했다: 임베딩 기반 aspect discovery, 감정 추론, 선택적 도메인 파인튜닝 템플릿.
- Colab 결과가 없어도 CPU baseline fallback으로 `segment_aspect_sentiment_merged.csv`, 혼합 감정 리뷰, 인사이트, 시각화가 생성되도록 구성했다.
- 실행 편의를 위해 `scripts/run_segment_absa_pipeline.py`를 추가했다.

## 2026-06-01 rating satisfaction signal 전환
- 별점을 segment 감정 라벨로 쓰는 weak label 구조를 제거하고, `rating_satisfaction_signal` 구조로 전환했다.
- `scripts/03_create_rating_satisfaction_signals.py`와 `src/rating_signals.py`를 추가했다.
- Colab 입력에서 감정 정답 라벨을 제거하고 `rating_satisfaction_signal`, `rating_group`, `rating_value`만 보조 변수로 포함했다.
- CPU baseline은 TF-IDF/NMF topic baseline만 수행하고, 별점 기반 sentiment 학습은 수행하지 않도록 변경했다.
- 높은 별점 리뷰 안의 부정 segment와 낮은 별점 리뷰 안의 긍정 segment를 별도 산출물로 저장하도록 확장했다.
