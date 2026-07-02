from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print(
        "This command runs final analysis evidence verification only.\n"
        "It does not regenerate the report document or local analysis archive.\n"
    )
    subprocess.run([sys.executable, "scripts/verify_report_evidence.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
