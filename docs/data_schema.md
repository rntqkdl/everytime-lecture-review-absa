# 데이터 스키마

## reviews_merged_raw_private.csv
수집 CSV를 병합한 리뷰 원본 테이블이다.

주요 컬럼:
- `review_id`
- `lecture_id`
- `course_name`
- `course_group`
- `professor_raw`
- `review_semester`
- `review_rating`
- `review_text`
- `source_file`

## reviews_preprocessed_private.csv
개인정보 패턴을 제거하고 교수명을 익명화한 리뷰 단위 테이블이다.

주요 컬럼:
- `review_id`
- `lecture_id`
- `course_name`
- `course_group`
- `professor_id`
- `review_rating`
- `review_text_clean`

## review_segments_private.csv
리뷰를 문장/절 수준으로 나눈 세그먼트 테이블이다.

주요 컬럼:
- `review_id`
- `sentence_id`
- `segment_id`
- `lecture_id`
- `course_name`
- `professor_raw`
- `professor_id`
- `review_rating`
- `review_text_clean`
- `sentence_text`
- `segment_text`
- `segment_order`

## reviews_with_rating_signals_private.csv
리뷰 단위 별점을 전체 만족도 신호로 변환한 테이블이다.

추가 컬럼:
- `rating_satisfaction_signal`
- `rating_group`
- `rating_value`
- `rating_signal_source`

## segments_with_rating_signals_private.csv
세그먼트에 리뷰 단위 만족도 신호를 참고 변수로 연결한 테이블이다. 이 신호는 감정 정답 라벨이 아니다.

추가 컬럼:
- `rating_satisfaction_signal`
- `rating_group`
- `rating_value`
- `rating_signal_source`

## Colab 입력
`segments_for_embedding_colab.csv`와 `segments_for_sentiment_colab.csv`의 주요 컬럼:

- `segment_id`
- `review_id`
- `lecture_id`
- `course_name`
- `professor_id`
- `review_rating`
- `rating_satisfaction_signal`
- `rating_group`
- `segment_text`
- `segment_text_for_model`

## Aspect 산출물
- `segment_aspect_clusters.csv`: 세그먼트별 자동 발견 aspect cluster
- `aspect_cluster_keywords.csv`: cluster별 키워드
- `aspect_representative_segments.csv`: cluster 대표 세그먼트
- `cpu_baseline_topic_keywords.csv`: CPU baseline 키워드
- `cpu_baseline_segment_topic_assignments.csv`: CPU baseline 세그먼트 topic 할당

## Sentiment 산출물
- `segment_sentiment_predictions_all_models.csv`: 모든 Colab 모델 예측
- `segment_sentiment_binary_primary.csv`: primary binary sentiment 결과
- `segment_emotion_extension.csv`: 확장 감정 결과
- `segment_aspect_sentiment_merged.csv`: aspect cluster와 model sentiment를 결합한 핵심 테이블
- `mixed_sentiment_reviews.csv`: 한 리뷰 안에서 긍정/부정 segment가 함께 발견된 사례
- `mixed_aspect_sentiment_cases.csv`: 혼합 감정 리뷰의 세그먼트 상세
- `high_rating_negative_segments.csv`: 높은 만족도 리뷰 안의 부정 segment
- `low_rating_positive_segments.csv`: 낮은 만족도 리뷰 안의 긍정 segment

## Insight 산출물
- `good_lecture_factors.csv`
- `dissatisfaction_factors.csv`
- `rating_signal_sentiment_crosstab.csv`
- `high_rating_negative_factor_summary.csv`
- `low_rating_positive_factor_summary.csv`
- `rating_group_mixed_review_summary.csv`
- `aspect_cluster_avg_rating.csv`
