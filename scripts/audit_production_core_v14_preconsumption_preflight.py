"""Fresh executable audit of both V14 pre-consumption gates, with zero writes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import audit_production_core_v14_launcher_boundary as signed_boundary
import preflight_production_core_candidate_qualification_v14 as gate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pastila_scout import production_core_candidate_execution_authority_v14 as validator  # noqa: E402


def audit(recovery_root: Path, private_root: Path, backup_root: Path, terminal_root: Path, unicode_root: Path, output: Path) -> dict[str, str]:
    boundary = signed_boundary.audit()
    outer = gate.preflight(recovery_root, private_root, backup_root, terminal_root, unicode_root, output)
    command = [
        sys.executable, str(ROOT / "scripts/execute_production_core_candidate_qualification_v14.py"),
        "--preflight-only",
        "--resolution", str(recovery_root / "v12-executor-resolution.json"),
        "--secret", str(private_root / "candidate-alias-secret-v13.json"),
        "--unicode-authority-root", str(unicode_root),
        "--output", str(output),
    ]
    completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    receipt = json.loads(completed.stdout)
    validator.validate_preflight_receipt(receipt)
    if (receipt["execution_authority_identity"] != outer["authority_identity"]
            or receipt["qualification_generation_identity"] != validator.GENERATION_IDENTITY
            or receipt["alias_secret_commitment"] != validator.ALIAS_SECRET_COMMITMENT
            or receipt["attempt_consumed"] is not False
            or receipt["candidate_execution_performed"] is not False
            or any(output.iterdir())):
        raise ValueError("V14 executable preflight or output state mismatch")
    stale = dict(receipt)
    stale["qualification_generation_identity"] = "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7"
    try:
        validator.validate_preflight_receipt(stale)
    except validator.ExecutionAuthorityError:
        pass
    else:
        raise ValueError("historical V10 generation was accepted")
    return {
        "verdict": "PASS + 0 BLOCKERS",
        "launcher_boundary_identity": boundary["boundary_identity"],
        "v14_authority_identity": outer["authority_identity"],
        "outer_preflight_identity": outer["preflight_identity"],
        "executor_preflight_identity": receipt["preflight_identity"],
        "ed25519_verification": boundary["ed25519_verification"],
        "source_closure": outer["source_closure"],
        "runtime_object_closure": outer["runtime_object_closure"],
        "qualification_schedule_closure": outer["qualification_schedule_closure"],
        "historical_v10_transfer": "REJECTED",
        "output": "EMPTY_NATIVE_EXT4",
        "candidate_execution": "0",
        "successor_attempt_consumption": "0",
        "adjudication": "false",
        "promotion": "false",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--terminal-root", type=Path, required=True)
    parser.add_argument("--unicode-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.recovery_root, args.private_root, args.backup_root, args.terminal_root, args.unicode_root, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
