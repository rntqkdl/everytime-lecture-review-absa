# Segment 기반 ABSA 파이프라인

## 목표
리뷰 전체 별점만 보는 방식에서 벗어나, 한 리뷰 안의 문장/절 단위 평가 요인과 감정 방향을 분리한다. 별점은 감정 라벨이 아니라 리뷰 전체 만족도 신호로만 사용한다.

## 처리 단위
기본 분석 단위는 `segment`다. 하나의 리뷰는 먼저 문장으로 분리되고, `근데`, `하지만`, `다만`, `그래도`, `반면`, `장점은`, `단점은` 같은 대비 표현을 기준으로 다시 나뉜다.

## 로컬 CPU 단계
1. 수집 CSV 병합
2. 개인정보 패턴 제거
3. 교수명 익명화
4. `course_group` 생성
5. 리뷰 세그먼트 분리
6. `rating_satisfaction_signal` 생성
7. Colab 업로드용 입력 CSV 생성
8. 선택적 TF-IDF/NMF topic baseline 실행
9. Colab 결과 병합
10. 혼합 감정 리뷰와 높은 별점의 부정 segment, 낮은 별점의 긍정 segment 추출
11. 좋은 강의 요인과 불만 요인 인사이트 추출

## Colab T4 단계
1. SentenceTransformer 기반 세그먼트 임베딩
2. UMAP 차원 축소
3. HDBSCAN 클러스터링, 실패 시 KMeans fallback
4. BERTopic 또는 c-TF-IDF 방식의 cluster keyword 추출
5. KoELECTRA/KOTE/KLUE-BERT 기반 감정 추론

## 핵심 산출물
- `segments_with_rating_signals_private.csv`
- `segment_aspect_clusters.csv`
- `segment_aspect_sentiment_merged.csv`
- `mixed_sentiment_reviews.csv`
- `high_rating_negative_segments.csv`
- `low_rating_positive_segments.csv`
- `good_lecture_factors.csv`
- `dissatisfaction_factors.csv`
