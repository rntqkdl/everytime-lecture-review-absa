from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print(
        "This project does not ask the professor to regenerate the report or submission package.\n"
        "Running the professor-facing final analysis verification instead.\n"
    )
    subprocess.run([sys.executable, "scripts/verify_report_evidence.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
