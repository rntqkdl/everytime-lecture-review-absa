# 이후 방향성

## 현재 위치
현재 파이프라인은 수집 데이터 병합, 전처리, 교수명 익명화, 별점 기반 weak label 생성, `글쓰기`/`실용영어` 그룹 정규화, 평가 요인 키워드 태깅, LDA 토픽 모델링, 그룹별 데이터 프로파일 시각화까지 완료한 상태다.

아직 Colab GPU 모델 결과는 들어오지 않았으므로 현재 감정 분석은 `review_rating` 기반 weak label 중심이다. 따라서 지금 결과는 "별점 기준 감정 경향"으로 해석해야 하며, 문장 텍스트 자체의 모델 예측 감정과는 구분해야 한다.

## 1단계: 현재 데이터 품질 점검
먼저 수집 데이터의 규모와 균형을 확정한다.

- `outputs/summary/course_group_data_counts.csv`
- `outputs/summary/course_group_weak_label_counts.csv`
- `outputs/summary/course_group_aspect_counts.csv`
- `outputs/figures/course_group_data_counts.png`
- `outputs/figures/course_group_data_ratios.png`

확인할 질문:

- `글쓰기`와 `실용영어`의 리뷰 수와 문장 수가 비교 가능한 수준인가
- 강의 수 차이가 분석 결과 해석에 영향을 주는가
- 특정 강의나 교수의 리뷰가 과도하게 많은가
- aspect 태그가 과제, 시험, 조모임 등 특정 요인에 과도하게 쏠려 있는가

## 2단계: weak label 기반 1차 결과 정리
Colab 모델 없이도 다음 결과는 바로 보고서 초안에 쓸 수 있다.

- 그룹별 긍정/중립/부정 비율
- 그룹별 평가 요인 언급량
- 그룹별 평가 요인별 weak label 감정 비율
- 강의별 평가 요인 감정 분포

주의할 점:

- weak label은 별점 기반 기준 신호이며 정답 라벨이 아니다.
- 한 리뷰 안의 모든 문장에 같은 weak label이 붙으므로, 문장별 실제 감정을 완전히 반영하지 못한다.
- "과제는 많지만 설명은 좋다" 같은 혼합 평가는 Colab 문장 모델 결과가 들어와야 더 잘 볼 수 있다.

## 3단계: Colab GPU 모델 추론
다음 파일을 Colab에 올린다.

```text
outputs/colab_input/sentences_for_sentiment_colab.csv
```

Colab에서 실행할 노트북:

```text
notebooks/07_colab_finetuned_sentiment_inference.ipynb
```

다운로드 후 로컬에 넣을 위치:

```text
outputs/colab_results
```

그 다음 실행:

```powershell
python scripts/run_current_data_analysis.py --fast --from-step 08
```

## 4단계: 모델 결과와 weak label 비교
Colab 결과가 들어오면 다음을 확인한다.

- weak label 기준 accuracy
- macro F1
- weighted F1
- confusion matrix
- `글쓰기`/`실용영어` 그룹별 모델 일치율
- 별점 구간별 모델 일치율

해석 방향:

- weak label과 모델이 일치하는 영역은 별점과 텍스트 감정이 같은 방향인 구간이다.
- 불일치 영역은 혼합 감정, 반어적 표현, 도메인 차이, 별점과 문장 감정의 단위 차이를 보여줄 수 있다.

## 5단계: 혼합 감정 분석 강화
문장 단위 모델 결과가 들어오면 리뷰별로 긍정/부정이 섞인 정도를 계산한다.

추가하면 좋은 산출물:

- 리뷰별 긍정 문장 수, 부정 문장 수, 중립 문장 수
- 긍정/부정이 모두 있는 리뷰 비율
- 평가 요인별 긍정/부정 혼합 비율
- `글쓰기`와 `실용영어`의 혼합 감정 리뷰 비율 비교

이 단계가 들어가야 "한 강의평 안에서 장점과 단점이 동시에 언급되는가"를 더 설득력 있게 말할 수 있다.

## 6단계: 보고서 구성
권장 보고서 흐름:

1. 연구 배경과 데이터 수집 범위
2. 데이터 규모와 `글쓰기`/`실용영어` 그룹 구성
3. 별점 기반 weak label 방법과 한계
4. 평가 요인 키워드 사전과 토픽 모델링 결과
5. weak label 기반 감정 경향
6. Colab 모델 결과와 weak label 비교
7. 혼합 감정 및 평가 요인별 해석
8. 한계와 향후 수작업 검증 계획

## 우선순위
가장 먼저 할 일은 Colab 모델 결과를 생성하는 것이다. 현재 로컬 결과만으로도 데이터 규모와 별점 기반 경향은 충분히 볼 수 있지만, 강의평 내부의 긍정/부정 혼합과 텍스트 기반 감정 판별은 Colab 모델 결과가 있어야 본격적으로 분석할 수 있다.
