"""Two-process synthetic smoke for V6 save/restart/resume semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from pastila_scout.production_core_checkpoint_resume_v6 import build_receipt, validate_chain, write_receipt

ATTEMPT = "a" * 64
AUTHORITY = "b" * 64
GENERATION = "c" * 64


def batches():
    return [
        {"materialization": "A" if n <= 6 else "B", "repetition": ((n - 1) % 6) // 2 + 1,
         "candidate_alias": "CANDIDATE-A" if n % 2 else "CANDIDATE-B", "batch_sha256": f"{n:064x}",
         "batch": [{"synthetic_row": i} for i in range(1, 201)],
         "first_global_ordinal": (n - 1) * 200 + 1, "last_global_ordinal": n * 200}
        for n in range(1, 13)
    ]


def save(root: Path, items, ordinal: int, previous):
    directory = root / f"synthetic-batch-{ordinal:02d}"
    directory.mkdir()
    (directory / "observation.json").write_bytes(json.dumps({"checkpoint": ordinal}, separators=(",", ":")).encode())
    receipt = build_receipt(attempt_identity=ATTEMPT, execution_authority_identity=AUTHORITY,
                            generation_identity=GENERATION, checkpoint_ordinal=ordinal,
                            previous_checkpoint_identity=previous, batch=items[ordinal - 1], directory=directory)
    write_receipt(root / f"checkpoint-{ordinal:02d}.json", receipt)
    return receipt["checkpoint_identity"]


def phase(root: Path, start: int, stop: int) -> None:
    items = batches()
    accepted, previous = validate_chain(root, attempt_identity=ATTEMPT,
                                        execution_authority_identity=AUTHORITY,
                                        generation_identity=GENERATION, batches=items)
    if accepted != start - 1:
        raise SystemExit("smoke restart boundary mismatch")
    for ordinal in range(start, stop + 1):
        previous = save(root, items, ordinal, previous)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("one", "two"))
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    if args.phase:
        if args.root is None:
            raise SystemExit("root required")
        phase(args.root, 1, 6) if args.phase == "one" else phase(args.root, 7, 12)
        return 0
    with tempfile.TemporaryDirectory(prefix="pastila-v6-smoke-") as temporary:
        root = Path(temporary)
        for name in ("one", "two"):
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--phase", name, "--root", str(root)], check=True)
        accepted, terminal = validate_chain(root, attempt_identity=ATTEMPT,
                                            execution_authority_identity=AUTHORITY,
                                            generation_identity=GENERATION, batches=batches())
        core = {"schema": "pastila-production-core-checkpoint-resume-smoke", "schema_version": 6,
                "processes": 2, "checkpoints": accepted, "terminal_checkpoint_identity": terminal,
                "qualification_rows_used": 0, "candidate_execution_performed": False,
                "attempt_consumed": False, "retry_or_redraw": False, "status": "PASS"}
        print(json.dumps({**core, "smoke_identity": hashlib.sha256(json.dumps(core, separators=(",", ":")).encode()).hexdigest()}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
