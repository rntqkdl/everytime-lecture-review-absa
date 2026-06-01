# 별점은 전체 만족도 신호로만 사용

## 왜 별점을 감정 라벨로 쓰지 않는가
별점은 리뷰 전체에 대한 만족도다. 하나의 리뷰 안에서도 교수 설명, 과제, 시험, 성적 평가, 수업 운영에 대한 감정이 서로 다를 수 있다. 따라서 `review_rating >= 4`를 모든 segment의 긍정 라벨로 쓰거나, `review_rating <= 2.5`를 모든 segment의 부정 라벨로 쓰면 측면 감정분석의 목적과 충돌한다.

## 예시
5점 리뷰:

```text
교수님은 너무 친절하고 설명도 좋아요. 근데 과제가 너무 많아서 힘들었어요.
```

해석:
- 교수 태도/설명 segment: positive
- 과제 부담 segment: negative
- 리뷰 전체 만족도: `VERY_HIGH_SATISFACTION`
- `high_rating_negative_segment_flag = true`

1점 리뷰:

```text
시험과 성적 평가는 너무 힘들었지만 자료는 정리가 잘 되어 있었어요.
```

해석:
- 시험/성적 평가 segment: negative
- 수업 자료 segment: positive
- 리뷰 전체 만족도: `VERY_LOW_SATISFACTION`
- `low_rating_positive_segment_flag = true`

## 변환 규칙
| review_rating | rating_satisfaction_signal |
| --- | --- |
| `>= 4.5` | `VERY_HIGH_SATISFACTION` |
| `4.0 <= rating < 4.5` | `HIGH_SATISFACTION` |
| `3.0 <= rating < 4.0` | `MID_SATISFACTION` |
| `2.0 <= rating < 3.0` | `LOW_SATISFACTION` |
| `0 < rating < 2.0` | `VERY_LOW_SATISFACTION` |
| `0` 또는 결측 | `RATING_UNKNOWN` |

## 함께 해석하는 방식
별점 만족도 신호는 다음 분석에만 사용한다.

- 높은 별점 리뷰 안의 부정 segment 탐지
- 낮은 별점 리뷰 안의 긍정 segment 탐지
- 만족도 그룹별 aspect/sentiment 비율 비교
- 좋은 강의 요인과 불만 요인의 맥락 보강

감정 예측은 Colab T4에서 한국어 감정분석 모델이 segment 단위로 수행한다.
