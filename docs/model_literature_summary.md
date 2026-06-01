# 모델 및 관련 연구 요약

## KoELECTRA NSMC baseline
`monologg/koelectra-base-finetuned-nsmc`와 `cringepnh/koelectra-korean-sentiment`는 한국어 긍정/부정 baseline으로 사용한다. NSMC는 영화 리뷰 기반이므로 강의평 도메인과 차이가 있다. 따라서 이 모델의 출력은 최종 정답이 아니라 별점 weak label과 비교할 외부 감정 신호로 해석한다.

## KOTE 기반 댓글 감정 모델
`tobykim/koelectra-44emotions`는 온라인 댓글체 감정 표현을 더 세분화해 볼 수 있는 확장 모델이다. 강의평도 구어체와 짧은 평가 문장이 많기 때문에 NSMC보다 표현 양식이 가까울 수 있다. 다만 44감정을 강의평의 긍정/부정/중립으로 환원할 때는 별도 라벨 매핑이 필요하다.

## KLUE-BERT 7감정 모델
`dlckdfuf141/korean-emotion-kluebert-v2`는 공포, 놀람, 분노, 슬픔, 중립, 행복, 혐오 같은 다중 감정 출력을 비교용으로 사용한다. 강의평에서는 특히 중립, 행복, 분노, 슬픔 계열이 평가 문맥과 연결될 수 있다.

## KcBERT/KcELECTRA 계열
KcBERT/KcELECTRA 계열은 한국어 온라인 댓글체와 비정형 텍스트에 상대적으로 강한 후보 모델이다. 향후 strong weak label 또는 소량 수작업 검증셋을 이용한 도메인 적응 후보로 남긴다.

## CARBD-Ko와 측면 기반 감정분석
CARBD-Ko의 핵심 문제의식은 문장 전체 감정과 측면별 감정이 다를 수 있다는 점이다. 본 프로젝트도 “과제는 많지만 설명은 좋다”처럼 한 리뷰 안에서 평가 요인별 감정이 갈라지는 사례를 분리하기 위해 segment 단위 aspect sentiment analysis를 사용한다.

## EduRABSA와 교육 리뷰 ABSA
교육 리뷰 도메인에서는 교수 설명, 과제, 시험, 성적, 출석, 수업 운영 같은 aspect가 반복적으로 등장한다. EduRABSA류 접근은 교육 리뷰에서 aspect와 sentiment를 함께 봐야 한다는 방향성을 제공한다. 본 프로젝트는 수작업 aspect 주석 대신 임베딩 cluster와 weak label을 결합해 자동화된 후보 aspect를 만든다.

## 도메인 차이와 한계
외부 공개 모델은 영화 리뷰, 댓글, 일반 감정 데이터에서 학습되었기 때문에 강의평의 평가 맥락과 완전히 일치하지 않는다. 최종 분석에서는 weak label, 모델 예측, cluster keyword, 대표 세그먼트를 함께 검토해야 한다.
