from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


LOCAL_PRE_COLAB_STEPS = [
    "scripts/01_merge_scraped_outputs.py",
    "scripts/02_preprocess_and_segment_reviews.py",
    "scripts/03_create_rating_satisfaction_signals.py",
    "scripts/04_prepare_colab_inputs.py",
    "scripts/05_optional_cpu_baseline.py",
]

LOCAL_POST_COLAB_STEPS = [
    "scripts/06_merge_colab_results.py",
    "scripts/07_detect_mixed_sentiment.py",
    "scripts/08_extract_good_lecture_factors.py",
    "scripts/09_analyze_rating_signal_relationships.py",
    "scripts/10_visualize_results.py",
    "scripts/11_make_public_sample.py",
]


def run_step(script: str) -> None:
    print(f"\n=== {script} ===", flush=True)
    subprocess.run([sys.executable, script], cwd=ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CPU side of the rating-signal segment ABSA pipeline.")
    parser.add_argument(
        "--pre-colab-only",
        action="store_true",
        help="Run local merge/preprocess/rating-signal/Colab-input/CPU-topic-baseline steps only.",
    )
    parser.add_argument(
        "--post-colab-only",
        action="store_true",
        help="Run only Colab-result merge, mixed sentiment, insight, visualization, and public sample steps.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.post_colab_only:
        for script in LOCAL_PRE_COLAB_STEPS:
            run_step(script)
        if args.pre_colab_only:
            print("\nPre-Colab CPU files are ready in outputs/colab_input.")
            return

    for script in LOCAL_POST_COLAB_STEPS:
        run_step(script)

    print("\nRating-signal segment ABSA pipeline finished.")


if __name__ == "__main__":
    main()
