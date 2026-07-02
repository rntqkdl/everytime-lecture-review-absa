from __future__ import annotations

import os
import shutil
import stat
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK_NAME = "evidence_verification_data_안성민"
PACK_DIR = ROOT / PACK_NAME
ZIP_PATH = ROOT / f"{PACK_NAME}.zip"


INCLUDE_FILES = [
    # Final BERTopic-based analysis evidence.
    "outputs/bertopic_analysis/report_analysis/segment_aspect_sentiment_merged_DIRECT_CHECK.csv",
    "outputs/bertopic_analysis/bertopic_topic_info.csv",
    "outputs/bertopic_analysis/bertopic_run_log.json",
    "outputs/bertopic_analysis/report_analysis/overall_summary.csv",
    "outputs/bertopic_analysis/report_analysis/aspect_summary.csv",
    "outputs/bertopic_analysis/report_analysis/course_group_summary.csv",
    "outputs/bertopic_analysis/report_analysis/review_level_summary.csv",
    "outputs/bertopic_analysis/report_analysis/groupwise_report_pack/groupwise_comparison_summary.csv",
    "outputs/bertopic_analysis/report_analysis/groupwise_report_pack/ALL/overall_summary.csv",
    "outputs/bertopic_analysis/report_analysis/groupwise_report_pack/ALL/aspect_summary.csv",
    "outputs/bertopic_analysis/report_analysis/groupwise_report_pack/ALL/good_factors.csv",
    "outputs/bertopic_analysis/report_analysis/groupwise_report_pack/ALL/bad_factors.csv",
    "outputs/bertopic_analysis/report_analysis/groupwise_report_pack/ALL/manual_validation_7_samples.csv",
    "outputs/bertopic_analysis/report_analysis/groupwise_report_pack/ALL/rating_sentiment_crosstab.csv",
    # BERTopic 이전 기획서 흐름에서 사용한 직접 병합/분석 산출물.
    "outputs/report_analysis/segment_aspect_sentiment_merged_DIRECT_CHECK.csv",
    "outputs/report_analysis/overall_summary.csv",
    "outputs/report_analysis/aspect_summary.csv",
    "outputs/report_analysis/course_group_summary.csv",
    "outputs/report_analysis/review_level_summary.csv",
    "outputs/report_analysis/rating_signal_sentiment_crosstab_report.csv",
    # Colab T4 단계 산출물. 원본 스크래핑 데이터 없이도 모델 결과 근거를 확인할 수 있게 포함한다.
    "outputs/colab_results/segment_sentiment_binary_primary.csv",
    "outputs/colab_results/segment_embedding_clusters.csv",
    "outputs/colab_results/aspect_cluster_keywords.csv",
    "outputs/colab_results/aspect_representative_segments.csv",
    "outputs/colab_results/embedding_run_log.csv",
    "outputs/colab_results/sentiment_model_run_log.csv",
    "outputs/colab_results/rating_signal_model_sentiment_relation.csv",
]


README = """# 최종 분석 근거 검증 데이터

이 압축 파일은 최종 분석 근거 검증에 필요한 데이터만 모아 둔 파일입니다.

## 목적

보고서에 적힌 주요 수치와 분석 근거가 실제 최종 데이터에서 다시 계산되는지 확인할 수 있도록 구성했습니다.
보고서 DOCX 재생성, 분석 산출물 압축본 생성, 에브리타임 재수집, Colab 재실행은 이 검증 실행 범위에 포함하지 않습니다.

## 사용 방법

1. GitHub 저장소를 내려받습니다.
2. 이 zip 파일을 저장소 루트에 풉니다.
   - 압축을 풀면 `outputs/...` 폴더 구조가 생깁니다.
3. 필요한 패키지를 설치합니다.

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

4. 검증 스크립트를 실행합니다.

```powershell
python scripts\\verify_report_evidence.py
```

5. 결과는 `outputs/evidence_verification/`에 생성됩니다.

## 생성되는 검증 결과

- `verification_summary.md`: 핵심 검증 요약
- `report_claim_validation.csv`: 보고서 핵심 수치 재계산표
- `groupwise_recalculated.csv`: 글쓰기/실용영어/전체 과목군 비교 재계산
- `top_factors_recalculated.csv`: 좋은 강의 요인과 부정 요인 상위 항목
- `pipeline_evidence_checks.csv`: BERTopic 외 기존 기획서 분석 산출물 확인
- `evidence_file_inventory.csv`: 검증 데이터 파일 목록, 행 수, sha256

## 포함한 데이터 범위

- BERTopic 최종 분석 세그먼트 데이터와 topic 정보
- 보고서에 사용한 요인별/과목군별 요약 CSV
- BERTopic 이전 직접 병합 분석 결과
- Colab T4에서 생성한 KoELECTRA 감정분석 결과
- Colab T4에서 생성한 문장 임베딩 클러스터 결과

## 제외한 데이터 범위

- 에브리타임 원본 스크래핑 폴더 `data/`
- HTML 원본과 debug screenshot
- 브라우저 프로필과 로그인 세션
- 가상환경과 캐시
- BERTopic 임베딩 캐시 `.npy`
- 보고서 DOCX와 분석 산출물 압축본

생성 시각: {created_at}
"""


def copy_file(rel_path: str, missing: list[str]) -> None:
    src = ROOT / rel_path
    if not src.exists():
        missing.append(rel_path)
        return
    dst = PACK_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def make_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(PACK_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(PACK_DIR))


def remove_tree(path: Path) -> None:
    def handle_remove_error(func, failed_path, _exc_info):
        os.chmod(failed_path, stat.S_IWRITE)
        func(failed_path)

    shutil.rmtree(path, onerror=handle_remove_error)


def main() -> None:
    if PACK_DIR.exists():
        remove_tree(PACK_DIR)
    PACK_DIR.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    for rel_path in INCLUDE_FILES:
        copy_file(rel_path, missing)

    readme = README.format(created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    (PACK_DIR / "README_EVIDENCE_VERIFICATION_DATA.md").write_text(readme, encoding="utf-8")

    if missing:
        missing_text = "\n".join(f"- {item}" for item in missing)
        (PACK_DIR / "MISSING_FILES.txt").write_text(missing_text + "\n", encoding="utf-8")

    make_zip()

    print(f"created: {PACK_DIR}")
    print(f"created: {ZIP_PATH}")
    if missing:
        print("missing files:")
        for item in missing:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
