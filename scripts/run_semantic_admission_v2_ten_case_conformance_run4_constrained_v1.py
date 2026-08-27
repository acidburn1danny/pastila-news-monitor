"""One-shot SAV2 Run 4 using the frozen Run 3 constrained implementation."""
from __future__ import annotations

from pathlib import Path

try:
    import scripts.run_semantic_admission_v2_ten_case_conformance_run3_constrained_v1 as implementation
except ModuleNotFoundError:
    import run_semantic_admission_v2_ten_case_conformance_run3_constrained_v1 as implementation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".semantic-admission-v2-ten-case-conformance-run-v4-evidence"
implementation.OUT = OUT
implementation.AUTHORITY = OUT / "run4-execution-authority.json"
implementation.PLAN = ROOT / "docs/artifacts/semantic-admission-v2-run4-constrained-plan.json"


if __name__ == "__main__":
    implementation.run()
