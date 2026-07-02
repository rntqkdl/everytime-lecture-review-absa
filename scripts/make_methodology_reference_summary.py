from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"


ROWS = [
    {
        "구분": "개발 환경",
        "방법론 또는 모델명": "Python",
        "프로젝트에서의 역할": "데이터 수집, 전처리, 세그먼트 구성, 분석 결과 생성의 실행 환경",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "requirements.txt; scripts/run_segment_absa_pipeline.py",
        "레포트에 넣을 표현": "Python 기반 분석 파이프라인으로 강의평 수집부터 결과 표와 그래프 생성까지 수행했다.",
        "주의할 표현": "Python만으로 모델을 직접 학습했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "아니오",
    },
    {
        "구분": "데이터 처리",
        "방법론 또는 모델명": "pandas",
        "프로젝트에서의 역할": "CSV 병합, 집계, 교차표, 보고서용 표 생성",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "requirements.txt; scripts/*.py; make_submission_pack.py",
        "레포트에 넣을 표현": "pandas를 사용해 리뷰와 세그먼트 단위 데이터를 집계하고 검증표를 생성했다.",
        "주의할 표현": "통계적 유의성 검정까지 수행했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "선택",
    },
    {
        "구분": "전처리",
        "방법론 또는 모델명": "정규표현식과 텍스트 정제",
        "프로젝트에서의 역할": "불필요 문자 정리, 개인정보 가능 정보 제거, 분석 가능한 텍스트 생성",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "src/text_cleaning.py; src/anonymize.py; src/io_utils.py",
        "레포트에 넣을 표현": "정규표현식과 텍스트 정제 함수를 이용해 원문 리뷰를 분석 가능한 형태로 정리했다.",
        "주의할 표현": "모든 개인정보가 완벽히 제거되었다고 단정하지 않는다.",
        "참고문헌 필요 여부": "아니오",
    },
    {
        "구분": "분석 단위",
        "방법론 또는 모델명": "문장과 절 단위 세그먼트 분리",
        "프로젝트에서의 역할": "한 리뷰 안의 복합 평가와 감정을 세그먼트 단위로 분리",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "src/segmentation.py; scripts/02_preprocess_and_segment_reviews.py",
        "레포트에 넣을 표현": "리뷰 전체가 아니라 문장과 절 단위 세그먼트를 분석 단위로 삼아 복합 감정을 분리했다.",
        "주의할 표현": "수작업 형태소 주석 데이터셋을 구축했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "아니오",
    },
    {
        "구분": "임베딩",
        "방법론 또는 모델명": "jhgan/ko-sroberta-multitask",
        "프로젝트에서의 역할": "세그먼트를 의미 벡터로 변환",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "outputs/colab_results/embedding_run_log.csv; notebooks/01_colab_t4_embedding_aspect_discovery.ipynb",
        "레포트에 넣을 표현": "한국어 문장 임베딩 모델인 jhgan/ko-sroberta-multitask를 적용해 세그먼트 의미 벡터를 생성했다.",
        "주의할 표현": "직접 사전학습했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "임베딩 방법론",
        "방법론 또는 모델명": "Sentence-BERT",
        "프로젝트에서의 역할": "문장 임베딩 기반 유사도 비교의 이론적 기반",
        "직접 사용 여부": "이론적 참고",
        "근거 파일": "README.md; notebooks/01_colab_t4_embedding_aspect_discovery.ipynb",
        "레포트에 넣을 표현": "Sentence-BERT 계열 문장 임베딩 방법론에 기반해 세그먼트 의미 표현을 비교했다.",
        "주의할 표현": "Sentence-BERT 논문 모델 자체를 새로 구현했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "차원 축소",
        "방법론 또는 모델명": "UMAP",
        "프로젝트에서의 역할": "고차원 임베딩을 군집화 가능한 저차원 표현으로 변환",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "outputs/colab_results/embedding_run_log.csv; notebooks/01_colab_t4_embedding_aspect_discovery.ipynb",
        "레포트에 넣을 표현": "UMAP으로 문장 임베딩의 차원을 축소한 뒤 군집화를 수행했다.",
        "주의할 표현": "UMAP 결과를 인과적 구조로 해석하지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "군집화",
        "방법론 또는 모델명": "HDBSCAN",
        "프로젝트에서의 역할": "유사한 평가 표현을 밀도 기반 군집으로 묶음",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "outputs/colab_results/embedding_run_log.csv; notebooks/01_colab_t4_embedding_aspect_discovery.ipynb",
        "레포트에 넣을 표현": "HDBSCAN을 이용해 유사한 평가 표현을 군집화하고 111개 평가 요인 후보를 얻었다.",
        "주의할 표현": "군집 이름이 완전 자동으로 확정되었다고 쓰지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "주제 모델링 참고",
        "방법론 또는 모델명": "BERTopic",
        "프로젝트에서의 역할": "문장 임베딩, UMAP, HDBSCAN, c-TF-IDF 기반 topic representation을 통합한 최종 평가 요인 추출",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "scripts/18_run_bertopic_report_analysis.py; outputs/bertopic_analysis/bertopic_run_log.json; outputs/bertopic_analysis/bertopic_topic_info.csv",
        "레포트에 넣을 표현": "최종본에서는 BERTopic 라이브러리를 직접 실행해 세그먼트 topic을 추출하고, topic별 키워드와 대표 문장을 바탕으로 평가 요인을 해석했다.",
        "주의할 표현": "BERTopic topic 이름을 완전 자동 결론으로 쓰지 않고 연구자 해석을 거쳤다고 쓴다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "키워드 추출",
        "방법론 또는 모델명": "TF-IDF / CountVectorizer 계열 키워드 추출",
        "프로젝트에서의 역할": "군집별 대표 키워드와 선택적 baseline 생성",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "notebooks/01_colab_t4_embedding_aspect_discovery.ipynb; src/topic_utils.py; src/cpu_baseline.py",
        "레포트에 넣을 표현": "군집 해석을 위해 TF-IDF 또는 CountVectorizer 계열 방식으로 대표 키워드를 추출했다.",
        "주의할 표현": "키워드 매칭만으로 최종 요인을 분류했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "선택",
    },
    {
        "구분": "감정분석",
        "방법론 또는 모델명": "monologg/koelectra-base-finetuned-nsmc",
        "프로젝트에서의 역할": "본문 분석의 중심이 되는 긍정/부정 이진 감정분석",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "outputs/colab_results/sentiment_model_run_log.csv; notebooks/02_colab_t4_sentiment_inference.ipynb",
        "레포트에 넣을 표현": "공개 KoELECTRA 기반 NSMC 감정분석 모델을 적용해 세그먼트별 긍정/부정을 추론했다.",
        "주의할 표현": "감정분석 모델을 직접 학습했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "감정분석 보조 실험",
        "방법론 또는 모델명": "cringepnh/koelectra-korean-sentiment",
        "프로젝트에서의 역할": "보조 이진 감정분석 모델",
        "직접 사용 여부": "보조 실험",
        "근거 파일": "outputs/colab_results/sentiment_model_run_log.csv",
        "레포트에 넣을 표현": "보조 감정분석 모델도 실행했으나 본문 집계는 monologg KoELECTRA 결과를 중심으로 제시했다.",
        "주의할 표현": "여러 모델의 앙상블 결과라고 쓰지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "감정분석 보조 실험",
        "방법론 또는 모델명": "tobykim/koelectra-44emotions",
        "프로젝트에서의 역할": "감정 확장 보조 실험",
        "직접 사용 여부": "보조 실험",
        "근거 파일": "outputs/colab_results/sentiment_model_run_log.csv",
        "레포트에 넣을 표현": "44개 감정 분류 모델은 확장 실험으로 실행했으며 본문 핵심 수치에는 사용하지 않았다.",
        "주의할 표현": "본문의 긍정/부정 수치가 이 모델에서 나온 것처럼 쓰지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "감정분석 보조 실험",
        "방법론 또는 모델명": "dlckdfuf141/korean-emotion-kluebert-v2",
        "프로젝트에서의 역할": "감정 확장 보조 실험",
        "직접 사용 여부": "보조 실험",
        "근거 파일": "outputs/colab_results/sentiment_model_run_log.csv",
        "레포트에 넣을 표현": "KLUE-BERT 기반 감정 모델은 보조 실험으로 실행했으며 본문 핵심 수치에는 사용하지 않았다.",
        "주의할 표현": "본문의 긍정/부정 수치가 이 모델에서 나온 것처럼 쓰지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "별점 신호",
        "방법론 또는 모델명": "별점 신호 분석",
        "프로젝트에서의 역할": "별점을 전체 만족도 신호로 변환하고 감정 결과와 비교",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "src/rating_signals.py; scripts/07_detect_mixed_sentiment.py; report_validation_summary.md",
        "레포트에 넣을 표현": "별점은 감정 정답 라벨이 아니라 전체 만족도 신호로만 사용했다.",
        "주의할 표현": "별점으로 감정 라벨을 만들었다고 쓰지 않는다.",
        "참고문헌 필요 여부": "아니오",
    },
    {
        "구분": "별점-텍스트 불일치",
        "방법론 또는 모델명": "mixed review, 높은 별점 속 부정, 낮은 별점 속 긍정",
        "프로젝트에서의 역할": "하나의 리뷰 안의 복합 감정과 별점-텍스트 불일치를 측정",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "outputs/report_analysis/review_level_summary.csv; report_validation_summary.md",
        "레포트에 넣을 표현": "mixed review와 별점-텍스트 불일치를 통해 별점만으로 포착되지 않는 평가 내용을 확인했다.",
        "주의할 표현": "리뷰 기준 수치와 세그먼트 기준 수치를 혼용하지 않는다.",
        "참고문헌 필요 여부": "아니오",
    },
    {
        "구분": "과목군 비교",
        "방법론 또는 모델명": "글쓰기와 실용영어 과목군 비교",
        "프로젝트에서의 역할": "과목군별 세그먼트 수, 감정 비율, 주요 요인 비교",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "outputs/report_analysis/groupwise_report_pack/groupwise_comparison_summary.csv; cross_group_aspect_comparison.csv",
        "레포트에 넣을 표현": "글쓰기와 실용영어를 구분해 과목군별 부담 요인과 공통 요인을 비교했다.",
        "주의할 표현": "모든 교양 과목으로 일반화하지 않는다.",
        "참고문헌 필요 여부": "아니오",
    },
    {
        "구분": "검증",
        "방법론 또는 모델명": "대표 문장 수동 검증",
        "프로젝트에서의 역할": "대표 문장 일부에 대해 모델 감정과 연구자 해석을 비교",
        "직접 사용 여부": "직접 사용",
        "근거 파일": "outputs/report_analysis/groupwise_report_pack/ALL/manual_validation_7_samples.csv",
        "레포트에 넣을 표현": "대표 문장 7개를 수동 검토해 모델 판단과 연구자 해석의 방향을 확인했다.",
        "주의할 표현": "전체 데이터셋을 사람이 전수 검증했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "아니오",
    },
    {
        "구분": "ABSA 배경",
        "방법론 또는 모델명": "CARBD-Ko",
        "프로젝트에서의 역할": "한국어 리뷰에서 문장 전체 감정과 측면별 감정을 구분해야 한다는 문제의식 참고",
        "직접 사용 여부": "이론적 참고",
        "근거 파일": "README.md",
        "레포트에 넣을 표현": "CARBD-Ko와 같은 한국어 리뷰 ABSA 연구의 문제의식을 참고했다.",
        "주의할 표현": "CARBD-Ko 데이터셋을 직접 사용했다고 쓰지 않는다.",
        "참고문헌 필요 여부": "예",
    },
    {
        "구분": "교육 리뷰 ABSA",
        "방법론 또는 모델명": "EduRABSA",
        "프로젝트에서의 역할": "교육 리뷰 ABSA 배경으로 검토 가능하나 실제 파일 근거는 확인되지 않음",
        "직접 사용 여부": "사용하지 않음 또는 확인 불가",
        "근거 파일": "코드와 로그에서 직접 사용 근거 미확인",
        "레포트에 넣을 표현": "필요할 경우 교육 리뷰 ABSA의 선택 참고문헌으로만 다룬다.",
        "주의할 표현": "실제 사용 방법론이나 직접 비교 대상으로 쓰지 않는다.",
        "참고문헌 필요 여부": "선택",
    },
]


APA_REFERENCES = """# APA 참고문헌 초안

Campello, R. J. G. B., Moulavi, D., & Sander, J. (2013). Density-based clustering based on hierarchical density estimates. In *Advances in Knowledge Discovery and Data Mining* (pp. 160-172). Springer.

Grootendorst, M. (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure. *arXiv*. https://arxiv.org/abs/2203.05794

Ham, J., Choe, Y. J., Park, K., Choi, I., & Soh, H. (2020). KorNLI and KorSTS: New benchmark datasets for Korean natural language understanding. *Findings of EMNLP 2020*. https://aclanthology.org/2020.findings-emnlp.261/

Jang, D., Seo, J., Byun, S., Kim, T., Kim, M., & Shin, H. (2024). CARBD-Ko: A contextually annotated review benchmark dataset for aspect-level sentiment classification in Korean.

McInnes, L., Healy, J., & Melville, J. (2018). UMAP: Uniform manifold approximation and projection for dimension reduction. *arXiv*. https://arxiv.org/abs/1802.03426

Park, J. (2020). KoELECTRA: Pretrained ELECTRA model for Korean. GitHub repository. https://github.com/monologg/KoELECTRA

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. *Proceedings of EMNLP-IJCNLP 2019*, 3982-3992. https://doi.org/10.18653/v1/D19-1410

Hugging Face model repositories used or tested:

- jhgan/ko-sroberta-multitask. https://huggingface.co/jhgan/ko-sroberta-multitask
- monologg/koelectra-base-finetuned-nsmc. https://huggingface.co/monologg/koelectra-base-finetuned-nsmc
- cringepnh/koelectra-korean-sentiment. https://huggingface.co/cringepnh/koelectra-korean-sentiment
- tobykim/koelectra-44emotions. https://huggingface.co/tobykim/koelectra-44emotions
- dlckdfuf141/korean-emotion-kluebert-v2. https://huggingface.co/dlckdfuf141/korean-emotion-kluebert-v2

Libraries:

- pandas, NumPy, scikit-learn, matplotlib, transformers, PyTorch, BeautifulSoup4, Playwright, kiwipiepy, openpyxl.
"""


WRITEUP = """# 레포트 방법론 서술 초안

## 1. 연구 설계 및 수행 과정에 넣을 문단
본 연구는 에브리타임 강의평을 수집한 뒤 원문을 정제하고, 리뷰를 문장과 절 단위 세그먼트로 나누어 분석했다. 최종본에서는 BERTopic 라이브러리를 직접 실행해 각 세그먼트를 한국어 문장 임베딩 모델로 벡터화하고, UMAP 차원 축소와 HDBSCAN 군집화, c-TF-IDF 기반 topic representation을 거쳐 평가 요인 topic을 추출했다. 이후 topic별 대표 키워드와 대표 문장을 검토하여 평가 요인을 해석했으며, 공개 KoELECTRA 기반 감정분석 모델을 적용해 세그먼트별 긍정/부정 감정을 추론했다.

## 2. 분석 방법에 넣을 문단
분석 단위는 리뷰 전체가 아니라 세그먼트이다. 이는 하나의 리뷰 안에 장점과 단점이 함께 나타나는 경우가 많기 때문이다. 별점은 감정 정답 라벨로 사용하지 않고, 리뷰 전체 만족도를 나타내는 보조 신호로만 사용했다.

## 3. 감정분석 방법에 넣을 문단
본문의 긍정/부정 수치는 monologg/koelectra-base-finetuned-nsmc 모델의 결과를 중심으로 계산했다. cringepnh/koelectra-korean-sentiment, tobykim/koelectra-44emotions, dlckdfuf141/korean-emotion-kluebert-v2는 보조 실험으로 실행했으나 본문 핵심 집계에는 사용하지 않았다.

## 4. 별점과 텍스트 불일치 분석 방법에 넣을 문단
높은 별점이지만 부정 세그먼트를 포함한 경우와 낮은 별점이지만 긍정 세그먼트를 포함한 경우를 별점-텍스트 불일치로 보았다. mixed review는 하나의 review_id 안에 긍정 세그먼트와 부정 세그먼트가 모두 있는 경우로 정의했다.

## 5. 과목군 비교 방법에 넣을 문단
강의명을 글쓰기 계열과 실용영어 계열로 정규화한 뒤 과목군별 세그먼트 수, 긍정/부정 비율, mixed review 수, 주요 평가 요인을 비교했다.

## 6. 방법론의 한계에 넣을 문단
이 분석은 공개 감정분석 모델을 적용한 것이며, 강의평 도메인에 맞춰 모델을 직접 학습한 것은 아니다. 또한 BERTopic topic 이름은 자동 결과를 그대로 확정한 것이 아니라 키워드와 대표 문장을 바탕으로 연구자가 해석한 결과이다. 따라서 수치는 경향을 보여주는 자료로 해석해야 하며, 모든 강의평의 실제 의도를 완전하게 대변한다고 보기 어렵다.

## 7. 부록에 넣을 코드와 데이터 설명
부록에는 최종 분석 데이터셋, 요인 요약표, 과목군 비교표, 검증표, 보고서용 그림, 표, 분석 코드, 수동 검증 예시를 포함한다. 원본 리뷰 데이터와 HTML 원본, 브라우저 프로필, 환경 파일은 개인정보와 재현 환경 보호를 위해 GitHub와 보고서 본문에서 제외한다.
"""


CAUTIONS = """# 방법론 표현 주의사항

- 최종본에서는 BERTopic 라이브러리를 직접 실행했으므로 "BERTopic을 사용했다"라고 쓸 수 있다. 다만 topic 이름은 자동 확정값이 아니라 키워드와 대표 문장을 바탕으로 연구자가 해석한 결과라고 쓴다.
- ABSA 모델을 직접 학습하지 않았으므로 "ABSA 모델을 학습했다"가 아니라 "측면 기반 감정분석 관점에서 평가 요인과 감정을 분리해 해석했다"라고 쓴다.
- 감정분석 모델을 직접 학습하지 않았으므로 "모델을 학습했다"가 아니라 "공개 KoELECTRA 기반 감정분석 모델을 적용했다"라고 쓴다.
- 별점은 감정 정답 라벨이 아니라 전체 만족도 신호로만 사용했다.
- 군집 이름은 자동 확정값이 아니라 대표 키워드와 대표 문장을 바탕으로 연구자가 해석한 이름이다.
- 높은 별점 속 부정, 낮은 별점 속 긍정은 세그먼트 기준과 리뷰 기준 수치를 구분해서 쓴다.
"""


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(ROWS)

    csv_path = DOCS_DIR / "methodology_reference_table.csv"
    xlsx_path = DOCS_DIR / "methodology_reference_table.xlsx"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)

    summary = ["# 방법론 근거 요약", ""]
    for status, group in df.groupby("직접 사용 여부", sort=False):
        summary.append(f"## {status}")
        for _, row in group.iterrows():
            summary.append(f"- **{row['방법론 또는 모델명']}**: {row['레포트에 넣을 표현']} 근거: `{row['근거 파일']}`")
        summary.append("")

    (DOCS_DIR / "methodology_reference_summary.md").write_text("\n".join(summary), encoding="utf-8")
    (DOCS_DIR / "apa_references_for_report.md").write_text(APA_REFERENCES, encoding="utf-8")
    (DOCS_DIR / "methodology_writeup_for_report.md").write_text(WRITEUP, encoding="utf-8")
    (DOCS_DIR / "methodology_caution_notes.md").write_text(CAUTIONS, encoding="utf-8")

    print("생성 완료")
    print(f"- {csv_path}")
    print(f"- {xlsx_path}")
    print(f"- {DOCS_DIR / 'methodology_reference_summary.md'}")
    print(f"- {DOCS_DIR / 'apa_references_for_report.md'}")
    print(f"- {DOCS_DIR / 'methodology_writeup_for_report.md'}")
    print(f"- {DOCS_DIR / 'methodology_caution_notes.md'}")


if __name__ == "__main__":
    main()
