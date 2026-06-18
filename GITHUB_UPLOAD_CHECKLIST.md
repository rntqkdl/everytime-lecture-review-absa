# GitHub 업로드 체크리스트

## 1. GitHub에 올릴 파일 목록
- `README.md`
- `requirements.txt`
- `.gitignore`
- `config/project_config.example.yaml`
- `src/`
- `scripts/`
- `tests/`
- `docs/`
- `notebooks/README.md`
- 출력이 제거된 `notebooks/*.ipynb`
- `collect_writing_lectures_final.py`
- `collect_practical_english_lectures_final.py`
- `collect_practical_english_variants_final.py`
- `make_submission_pack.py`
- `GITHUB_UPLOAD_CHECKLIST.md`
- `DATA_EXCLUSION_CHECKLIST.md`

## 2. GitHub에 올리면 안 되는 파일 목록
- `.venv/`, `.pytest_cache/`, `__pycache__/`
- `.tmp.drivedownload/`, `.tmp.driveupload/`
- `browser_profile/`, `colab_upload/`
- `data/`, `outputs/`, `sample_data/`
- `submission_pack_안성민/`
- `appendix_안성민.zip`, `submission_pack_안성민.zip`
- `evidence_verification_data_안성민/`, `evidence_verification_data_안성민.zip`
- 원본 리뷰 CSV, 분석 결과 CSV/XLSX/PNG, HTML 원본, 로그, 임시 파일
- `config/project_config.yaml`, `.env`, `.env.*`

## 3. git status 확인 방법
```powershell
git status --short
```

## 4. 데이터 파일 포함 여부 확인 명령어
```powershell
git status --short
git ls-files data outputs sample_data colab_upload browser_profile
git status --short | Select-String -Pattern '\.csv|\.xlsx|\.png|\.html|\.log|project_config\.yaml|submission_pack|appendix_|evidence_verification_data'
```

## 5. 커밋 전 확인 체크리스트
- [ ] `git add .`를 사용하지 않았다.
- [ ] `data/`, `outputs/`, `sample_data/`, `browser_profile/`가 staged 상태가 아니다.
- [ ] CSV/XLSX/PNG/HTML/LOG 파일이 staged 상태가 아니다.
- [ ] `config/project_config.yaml` 대신 `config/project_config.example.yaml`만 staged 상태다.
- [ ] 로컬 산출물 zip은 공개 코드 저장소에 포함하지 않는다.
- [ ] tracked notebook에 저장된 실행 output이 없는지 확인했다.

## 6. 권장 커밋 메시지
```powershell
git commit -m "Prepare Everytime lecture review analysis code for submission"
```
