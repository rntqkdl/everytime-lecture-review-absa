# 에브리타임 강의평 기반 ML/DL 측면 감정분석 파이프라인

## 최종 분석 근거 검증 실행

이 저장소의 검증 실행 범위는 전체 수집/전처리/Colab/보고서 생성을 반복하는 것이 아니라, 보고서에 작성한 핵심 수치와 분석 근거가 최종 분석 데이터에서 다시 계산되는지 확인하는 것이다.

1. GitHub 저장소를 내려받습니다.
2. 검증 데이터 파일 `evidence_verification_data_안성민.zip`을 저장소 루트에 풉니다.
3. 의존성을 설치한 뒤 검증 스크립트를 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\verify_report_evidence.py
```

검증 결과는 `outputs/evidence_verification/`에 생성됩니다. 자세한 안내는 `VERIFICATION_GUIDE.md`를 확인하면 됩니다.

검증되는 범위는 BERTopic 결과뿐 아니라 KoELECTRA 감정분석 결과, Colab 문장 임베딩 클러스터 결과, BERTopic 이전 직접 병합 분석 결과, 과목군 비교, 좋은 강의 요인과 부정/불만 요인까지 포함합니다.

## 연구 목적
이 프로젝트는 에브리타임 강의평을 문장/절 단위로 나누고, Colab T4 GPU 기반 문장 임베딩 클러스터링과 한국어 감정분석 모델을 활용해 한 리뷰 안에 섞여 있는 여러 평가 요인과 감정을 분리한다.

본 프로젝트는 별점을 문장/절 단위 감정 라벨로 사용하지 않는다. 별점은 리뷰 전체 만족도를 나타내는 보조 신호로만 사용하며, 실제 감정분석은 문장/절 단위에서 기존 한국어 감정분석 모델을 통해 수행한다.

본 프로젝트는 TF-IDF 기반 키워드 매칭을 최종 분류 방식으로 사용하지 않는다. TF-IDF는 선택적 baseline이나 topic representation 보조로만 사용하며, 최종 평가 요인 발견은 BERTopic 라이브러리 기반 문장 임베딩, UMAP/HDBSCAN 클러스터링, c-TF-IDF topic representation, 연구자 해석을 중심으로 수행한다.

본 프로젝트는 CARBD-Ko처럼 문장 전체 감정과 측면별 감정을 구분해야 한다는 문제의식을 따른다. 다만 별도의 수작업 aspect 주석 데이터셋을 구축하지 않고, 에브리타임 강의평의 별점 기반 만족도 신호와 문장 임베딩 기반 aspect discovery를 결합하여 자동화된 측면 감정분석 파이프라인을 구현한다.

## 기존 수집 코드와 분석 코드
기존 스크래핑 코드는 보존한다.

- `collect_writing_lectures_final.py`
- `collect_practical_english_lectures_final.py`
- `collect_practical_english_variants_final.py`

분석 코드는 이미 수집된 `data/*_output` CSV를 읽어 처리한다.

## 분석 대상
- 글쓰기: `글쓰기`, `대학글쓰기`
- 실용영어: `실용영어`, `Practical English`, `실용영어(Practical English)`

원본 강의명은 `course_group` 컬럼에서 `글쓰기`와 `실용영어`로 정규화한다.

## CPU/GPU 분리 구조
로컬 CPU:
1. CSV 병합
2. 개인정보 제거와 교수명 익명화
3. 문장/절 segment 분리
4. 별점 기반 `rating_satisfaction_signal` 생성
5. Colab 입력 CSV 생성
6. 선택적 TF-IDF/NMF topic baseline 생성
7. Colab 결과 병합, mixed sentiment 탐지, 인사이트 추출, 시각화

Colab T4 GPU:
1. SentenceTransformer 임베딩
2. UMAP 차원 축소
3. HDBSCAN 또는 KMeans 클러스터링
4. BERTopic 기반 c-TF-IDF topic representation
5. KoELECTRA/KOTE/KLUE-BERT 감정 추론

## 별점 만족도 신호
별점은 다음처럼 전체 만족도 신호로만 변환한다.

| review_rating | rating_satisfaction_signal |
| --- | --- |
| `>= 4.5` | `VERY_HIGH_SATISFACTION` |
| `4.0 <= rating < 4.5` | `HIGH_SATISFACTION` |
| `3.0 <= rating < 4.0` | `MID_SATISFACTION` |
| `2.0 <= rating < 3.0` | `LOW_SATISFACTION` |
| `0 < rating < 2.0` | `VERY_LOW_SATISFACTION` |
| `0` 또는 결측 | `RATING_UNKNOWN` |

5점 리뷰에도 부정 segment가 있을 수 있고, 1점 리뷰에도 긍정 segment가 있을 수 있다. 따라서 별점은 segment 감정 정답이나 학습 라벨로 사용하지 않는다.

## 로컬 CPU 1차 실행
```powershell
cd <프로젝트_폴더>
.\.venv\Scripts\Activate.ps1
python scripts\run_segment_absa_pipeline.py --pre-colab-only
```

생성되는 Colab 업로드 파일:
- `outputs/colab_input/segments_for_embedding_colab.csv`
- `outputs/colab_input/segments_for_sentiment_colab.csv`
- `outputs/colab_input/colab_model_config.json`

## Colab T4 실행
Colab에서 `런타임 → 런타임 유형 변경 → 하드웨어 가속기 GPU 선택`을 설정한다. 권장 GPU는 T4다.

실행 순서:
1. `notebooks/01_colab_t4_embedding_aspect_discovery.ipynb`
2. `notebooks/02_colab_t4_sentiment_inference.ipynb`
3. 선택: `notebooks/03_colab_t4_optional_domain_finetuning.ipynb`

Colab 결과 CSV를 `outputs/colab_results`에 넣는다.

## 로컬 CPU 2차 실행
```powershell
python scripts\run_segment_absa_pipeline.py --post-colab-only
```

개별 실행이 필요하면 `docs/current_pipeline_process.md`를 확인한다.

## BERTopic 최종 분석
기존 Colab 결과와 감정분석 결과를 바탕으로 최종 보고서용 평가 요인은 BERTopic 라이브러리로 재분석한다.

```powershell
python scripts\18_run_bertopic_report_analysis.py
python make_submission_pack.py
python scripts\build_final_report_docx.py
```

BERTopic 최종 산출물은 `outputs/bertopic_analysis/` 아래에 생성된다. `outputs/`는 GitHub 업로드 대상이 아니며, 최종 문서와 분석 산출물 압축본은 로컬 산출물로 별도 관리한다.

## 최종 산출물
- `outputs/aspects/aspect_cluster_keywords.csv`
- `outputs/aspects/aspect_representative_segments.csv`
- `outputs/sentiment/segment_aspect_sentiment_merged.csv`
- `outputs/bertopic_analysis/report_analysis/segment_aspect_sentiment_merged_DIRECT_CHECK.csv`
- `outputs/bertopic_analysis/bertopic_topic_info.csv`
- `outputs/sentiment/mixed_sentiment_reviews.csv`
- `outputs/sentiment/high_rating_negative_segments.csv`
- `outputs/sentiment/low_rating_positive_segments.csv`
- `outputs/insights/good_lecture_factors.csv`
- `outputs/insights/dissatisfaction_factors.csv`
- `outputs/insights/rating_signal_sentiment_crosstab.csv`
- `outputs/figures/rating_signal_vs_negative_ratio.png`
- `sample_data/sample_reviews_anonymized.csv`

## GitHub 업로드 금지
다음은 업로드하지 않는다.

- `.venv/`
- `browser_profile/`
- `data/`
- `outputs/`
- `sample_data/`
- 로컬 분석 산출물 폴더
- 최종 문서 파일
- 분석 산출물 압축본
- 실제 강의평 원문
- HTML 원본
- debug 파일
- 교수명 매핑 파일
- Colab 모델 가중치
- 분석 결과 CSV/XLSX/PNG/PDF

업로드 가능:
- 분석 코드
- `README.md`
- `docs/`
- `requirements.txt`
- `config/project_config.example.yaml`
- 출력이 제거된 `notebooks/*.ipynb`와 `notebooks/README.md`
- `GITHUB_UPLOAD_CHECKLIST.md`
- `DATA_EXCLUSION_CHECKLIST.md`

## 분석 산출물 패키지 생성
보고서에 사용할 표, 그림, 검증 파일은 GitHub에 올리지 않고 로컬 산출물 패키지로 생성한다.

```powershell
cd <프로젝트_폴더>
python make_submission_pack.py
```

생성 결과:
- `submission_pack_안성민/`
- `appendix_안성민.zip`
- `submission_pack_안성민.zip`
- `submission_pack_안성민/report_validation_summary.md`
- `submission_pack_안성민/report_assets/tables/claim_validation_table.csv`

최종 보고서의 핵심 수치는 실제 `outputs` 데이터 기준으로 다시 계산한다. 현재 데이터 기준으로 전체 리뷰 수 13,751건, 전체 세그먼트 수 37,808건, 긍정 22,263건, 부정 15,545건, mixed review 5,984건이 재계산된다. 별점과 텍스트 불일치 항목은 기준 단위에 따라 값이 달라지므로, 높은 별점의 부정 사례는 세그먼트 기준 9,694건과 리뷰 기준 5,698건, 낮은 별점의 긍정 사례는 세그먼트 기준 975건과 리뷰 기준 602건으로 구분한다.

## 한계
외부 감정분석 모델은 강의평 도메인에 최적화된 모델이 아니다. 자동 발견 cluster도 사람이 최종 이름을 검토해야 한다. 별점 만족도 신호는 해석 보조 변수이며, segment 감정 정답이 아니다.
