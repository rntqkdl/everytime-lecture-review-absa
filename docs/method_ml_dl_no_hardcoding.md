# ML/DL 기반 평가 요인 발견 원칙

## 하드코딩 키워드 방식을 쓰지 않는 이유
`if "과제" in segment_text`처럼 aspect를 고정 키워드로 결정하면 표현 변형과 문맥을 놓친다. 강의평에서는 “레포트”, “매주 제출”, “분량”, “보고서”처럼 같은 요인이 다양한 표현으로 나타난다.

## 최종 방식
최종 평가 요인 발견은 다음 흐름을 따른다.

```text
문장/절 임베딩
↓
UMAP 차원 축소
↓
HDBSCAN 또는 KMeans 클러스터링
↓
BERTopic 또는 c-TF-IDF 키워드 추출
↓
대표 segment 추출
↓
aspect cluster 자동 생성
```

## TF-IDF의 역할
TF-IDF/NMF는 로컬 CPU에서 빠르게 실행할 수 있는 선택적 baseline이다. Colab 결과가 아직 없을 때 구조를 확인하는 용도로 사용하며, 최종 분류 방식으로 간주하지 않는다.

## BERTopic/UMAP/HDBSCAN의 역할
- SentenceTransformer: 의미가 비슷한 segment를 가까운 벡터로 표현한다.
- UMAP: 고차원 임베딩을 clustering에 적합한 차원으로 줄인다.
- HDBSCAN: cluster 수를 미리 고정하지 않고 밀도 기반으로 평가 요인을 찾는다.
- KMeans: HDBSCAN이 부적합할 때 fallback으로 사용한다.
- BERTopic 또는 c-TF-IDF: cluster를 사람이 해석할 수 있도록 키워드를 추출한다.
