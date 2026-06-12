# 교수님 검증용 실행 안내

이 저장소에서 교수님이 직접 실행하실 범위는 보고서나 제출 패키지를 다시 만드는 것이 아니라, 보고서에 적은 분석 근거가 최종 데이터에서 재계산되는지 확인하는 것입니다.

## 1. 필요한 파일

GitHub 저장소에는 코드와 안내 문서만 올립니다. 데이터는 별도로 전달합니다.

별도 전달 파일:

- `professor_verification_data_안성민.zip`

압축을 풀면 다음 경로의 검증용 데이터가 생깁니다.

- `outputs/bertopic_analysis/...`
- `outputs/report_analysis/...`
- `outputs/colab_results/...`

## 2. 실행 방법

```powershell
git clone https://github.com/rntqkdl/everytime-lecture-review-absa.git
cd everytime-lecture-review-absa
```

`professor_verification_data_안성민.zip`을 이 폴더에 풉니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\verify_report_evidence.py
```

## 3. 실행 결과

검증 결과는 다음 폴더에 생성됩니다.

```text
outputs/professor_verification/
```

주요 결과 파일:

- `verification_summary.md`: 핵심 검증 요약
- `report_claim_validation.csv`: 보고서 핵심 수치 재계산표
- `groupwise_recalculated.csv`: 글쓰기/실용영어/전체 과목군 비교 재계산
- `top_factors_recalculated.csv`: 좋은 강의 요인과 부정 요인 상위 항목
- `pipeline_evidence_checks.csv`: BERTopic 외 기존 기획서 분석 산출물 확인
- `evidence_file_inventory.csv`: 검증 데이터 파일 목록, 행 수, sha256

## 4. 검증되는 내용

- 전체 리뷰 수, 전체 세그먼트 수
- 글쓰기/실용영어 세그먼트 수
- 긍정/부정 세그먼트 수와 비율
- mixed review 수
- 높은 별점의 부정 세그먼트/리뷰 수
- 낮은 별점의 긍정 세그먼트/리뷰 수
- BERTopic topic 수와 outlier 세그먼트 수
- 좋은 강의 요인과 부정/불만 요인 상위 항목
- 글쓰기와 실용영어 과목군 비교
- Colab T4 KoELECTRA 감정분석 결과와 최종 분석 데이터의 segment_id 일치 여부
- Colab T4 문장 임베딩 클러스터 결과와 최종 분석 데이터의 segment_id 일치 여부
- BERTopic 이전 직접 병합 분석 결과의 행 수 일치 여부

## 5. 교수님이 실행하지 않아도 되는 작업

- 에브리타임 재수집
- raw HTML/debug 파일 확인
- Colab 노트북 재실행
- BERTopic 재학습
- 보고서 DOCX 재생성
- 제출 패키지 zip 재생성

## 6. 데이터 제외 원칙

GitHub에는 원본 강의평 데이터, HTML 원본, 브라우저 프로필, `.venv`, `outputs`, 제출 zip을 올리지 않습니다. 검증에 필요한 최종 분석 CSV만 `professor_verification_data_안성민.zip`으로 별도 전달합니다.
