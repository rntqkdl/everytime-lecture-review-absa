# Scripts

현재 루트 `scripts` 폴더는 별점을 감정 라벨로 쓰지 않는 segment 기반 ABSA 파이프라인이다.

로컬 CPU 1차 실행:

```powershell
python scripts/run_segment_absa_pipeline.py --pre-colab-only
```

Colab 결과 병합 이후 실행:

```powershell
python scripts/run_segment_absa_pipeline.py --post-colab-only
```

전체 흐름 확인:

```powershell
python scripts/run_segment_absa_pipeline.py
```

주의: `review_rating`은 `rating_satisfaction_signal`로만 변환하며, segment 감정 정답이나 학습 라벨로 사용하지 않는다.
