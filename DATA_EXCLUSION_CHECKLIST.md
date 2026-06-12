# 데이터 제외 체크리스트

## 1. 개인정보 포함 가능 파일 제외

- [ ] 원본 강의평, 교수명 매핑, 브라우저 프로필을 GitHub에 올리지 않는다.
- [ ] `browser_profile/`, `colab_upload/`, `.tmp.drivedownload/`, `.tmp.driveupload/`가 staged 상태가 아니다.
- [ ] `.env`, `.env.*`, `credentials.*`, `secrets.*`가 staged 상태가 아니다.

## 2. 원본 리뷰 데이터 제외

- [ ] `data/` 폴더가 `.gitignore`에 포함되어 있다.
- [ ] `*_reviews_raw*.csv`, HTML 원본, debug screenshot이 staged 상태가 아니다.
- [ ] `professor_mapping_private.csv`가 staged 상태가 아니다.

## 3. 분석 결과 파일 제외

- [ ] `outputs/` 폴더가 `.gitignore`에 포함되어 있다.
- [ ] 분석 결과 `*.csv`, `*.xlsx`, `*.png`, `*.pdf`가 staged 상태가 아니다.
- [ ] `sample_data/`가 staged 상태가 아니다.

## 4. 제출물과 검증 데이터 zip 제외

- [ ] `submission_pack_안성민/`이 staged 상태가 아니다.
- [ ] `appendix_안성민.zip`, `submission_pack_안성민.zip`이 staged 상태가 아니다.
- [ ] `final_report_안성민.docx`가 staged 상태가 아니다.
- [ ] `professor_verification_data_안성민/`, `professor_verification_data_안성민.zip`이 staged 상태가 아니다.
- [ ] `gpt_attachment_pack_안성민/`이 staged 상태가 아니다.

## 5. 교수님께 별도 전달할 파일

GitHub에는 올리지 않고 별도로 전달한다.

- `final_report_안성민.docx`
- `appendix_안성민.zip`
- `submission_pack_안성민.zip`
- `professor_verification_data_안성민.zip`

## 6. 교수님 검증용 데이터 범위

`professor_verification_data_안성민.zip`에는 원본 수집 데이터가 아니라 최종 분석 검증에 필요한 CSV만 포함한다.

- BERTopic 최종 분석 세그먼트 데이터
- BERTopic topic 정보와 실행 로그
- 보고서에 사용한 요인별/과목군별 요약 CSV
- BERTopic 이전 직접 병합 분석 결과
- Colab T4 KoELECTRA 감정분석 결과
- Colab T4 문장 임베딩 클러스터 결과

다음은 포함하지 않는다.

- 에브리타임 원본 스크래핑 데이터
- HTML 원본과 debug screenshot
- 브라우저 프로필과 로그인 세션
- 가상환경과 캐시
- BERTopic 임베딩 캐시 `.npy`
