# GitHub 업로드 체크리스트

## 1. GitHub에 올릴 파일

- `README.md`
- `PROFESSOR_VERIFICATION_GUIDE.md`
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

## 2. GitHub에 올리지 않을 파일

- `.venv/`, `.pytest_cache/`, `__pycache__/`
- `.tmp.drivedownload/`, `.tmp.driveupload/`
- `browser_profile/`, `colab_upload/`
- `data/`, `outputs/`, `sample_data/`
- `submission_pack_안성민/`
- `appendix_안성민.zip`, `submission_pack_안성민.zip`
- `professor_verification_data_안성민/`, `professor_verification_data_안성민.zip`
- `gpt_attachment_pack_안성민/`
- 원본 리뷰 CSV, 분석 결과 CSV/XLSX/PNG, HTML 원본, 로그, 임시 파일
- `config/project_config.yaml`, `.env`, `.env.*`

## 3. 상태 확인 명령

```powershell
git status --short
git ls-files data outputs sample_data colab_upload browser_profile
git status --short | Select-String -Pattern '\.csv|\.xlsx|\.png|\.html|\.log|project_config\.yaml|submission_pack|appendix_|professor_verification_data'
```

## 4. 커밋 전 확인

- [ ] `git add .`를 사용하지 않고 필요한 코드/문서만 선택적으로 stage했다.
- [ ] `data/`, `outputs/`, `sample_data/`, `browser_profile/`가 staged 상태가 아니다.
- [ ] CSV/XLSX/PNG/HTML/LOG 결과 파일이 staged 상태가 아니다.
- [ ] `config/project_config.yaml` 대신 `config/project_config.example.yaml`만 staged 상태다.
- [ ] 제출용 zip은 GitHub가 아니라 교수님 제출물로만 보관한다.
- [ ] 교수님 검증용 데이터 zip인 `professor_verification_data_안성민.zip`은 GitHub에 올리지 않고 별도 전달한다.
- [ ] tracked notebook에 저장된 실행 output이 없는지 확인했다.

## 5. 권장 커밋 메시지

```powershell
git commit -m "Prepare Everytime lecture review analysis verification package"
```
