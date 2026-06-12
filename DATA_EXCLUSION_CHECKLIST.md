# 데이터 제외 체크리스트

## 1. 개인정보 포함 가능 파일 제외 여부
- [ ] 원본 강의평, 교수명 매핑, 브라우저 프로필을 GitHub에 올리지 않는다.

## 2. 원본 리뷰 데이터 제외 여부
- [ ] `data/` 폴더가 `.gitignore`에 포함되어 있다.
- [ ] `*_reviews_raw*.csv`와 HTML 원본이 staged 상태가 아니다.

## 3. 분석 결과 CSV 제외 여부
- [ ] `outputs/` 폴더가 `.gitignore`에 포함되어 있다.
- [ ] 모든 `*.csv` 분석 결과가 staged 상태가 아니다.

## 4. 그래프 PNG 제외 여부
- [ ] 모든 `*.png`, `*.jpg`, `*.jpeg`, `*.pdf` 결과물이 staged 상태가 아니다.

## 5. 브라우저 프로필 제외 여부
- [ ] `browser_profile/`과 `colab_upload/`가 staged 상태가 아니다.

## 6. 환경 파일 제외 여부
- [ ] `.venv/`, `.env`, `.env.*`, 캐시, 로그, 임시 파일이 staged 상태가 아니다.

## 7. config/project_config.yaml 제외 여부
- [ ] `config/project_config.yaml`은 제외하고 `config/project_config.example.yaml`만 올린다.

## 8. 교수님 제출용 appendix 안내
- [ ] `submission_pack_안성민/`, `appendix_안성민.zip`, `submission_pack_안성민.zip`은 GitHub에 올리지 않는다.
- [ ] 교수님 제출용 최종 파일은 GitHub가 아니라 `appendix_안성민.zip`과 `final_report_안성민.docx`다.
