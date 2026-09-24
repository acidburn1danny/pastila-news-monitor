"""Close the blinded R1 checkpoint-8 versus R2 step-9 factual-setup comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def verify_bundle(root: Path, expected_adapter: str, requests_sha: str) -> tuple[dict, list[dict]]:
    receipt = json.loads((root / "inference-receipt.json").read_text(encoding="utf-8"))
    responses_raw = (root / "responses.jsonl").read_bytes()
    observations_raw = (root / "observations.jsonl").read_bytes()
    core = {key: value for key, value in receipt.items() if key != "receipt_identity"}
    assert receipt["receipt_identity"] == sha(canonical(core))
    assert receipt["adapter_sha256"] == expected_adapter
    assert receipt["requests_sha256"] == requests_sha
    assert receipt["responses_sha256"] == sha(responses_raw)
    assert receipt["observations_sha256"] == sha(observations_raw)
    assert receipt["rows"] == receipt["terminal_eos"] == 24
    assert receipt["answer_key_accessed"] is receipt["holdout_accessed"] is False
    assert receipt["training_performed"] is False and receipt["optimizer_steps"] == 0
    rows = read_jsonl(root / "responses.jsonl")
    assert len(rows) == len({row["case_id"] for row in rows}) == 24
    return receipt, rows


def sign_test(wins: int, losses: int) -> float:
    n = wins + losses
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / (2**n) if n else 1.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r1", type=Path, required=True)
    parser.add_argument("--r2", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    r1_receipt, r1_rows = verify_bundle(
        args.r1, "50b292f9cfdfb2f44dcc8bb9ef811ea367c78db505e4adc2c62e851e6060d3a4",
        manifest["requests_sha256"],
    )
    r2_receipt, r2_rows = verify_bundle(
        args.r2, "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
        manifest["requests_sha256"],
    )
    judgments = read_jsonl(args.judgments)
    assert len(judgments) == len({row["case_id"] for row in judgments}) == 24
    allowed = {"R1", "R2", "TIE"}
    assert all(row["winner"] in allowed for row in judgments)
    assert {row["case_id"] for row in judgments} == {row["case_id"] for row in r1_rows} == {row["case_id"] for row in r2_rows}

    wins = {name: sum(row["winner"] == name for row in judgments) for name in allowed}
    r2_safety_regressions = sum(row["r2_safety_regression"] for row in judgments)
    p_value = sign_test(wins["R2"], wins["R1"])
    selection_pass = r2_safety_regressions == 0 and wins["R2"] > wins["R1"] and p_value <= 0.05
    core = {
        "schema": "editor-core-factual-setup-comparison-result",
        "schema_version": 1,
        "contract_identity": "67a5cd5813d422c513795dd88b561db3f74a55ee2a932d8bcb2d0d1035eb0b37",
        "benchmark_manifest_identity": manifest["manifest_identity"],
        "r1_receipt_identity": r1_receipt["receipt_identity"],
        "r2_receipt_identity": r2_receipt["receipt_identity"],
        "judgments_sha256": sha(args.judgments.read_bytes()),
        "cases": 24,
        "r1_wins": wins["R1"],
        "r2_wins": wins["R2"],
        "ties": wins["TIE"],
        "r2_safety_regressions": r2_safety_regressions,
        "one_sided_sign_test_p": p_value,
        "selection_rule_pass": selection_pass,
        "development_parent_conclusion": "R2_STEP_9_RETAINS" if selection_pass else "R2_STEP_9_RETAINS_OPERATIONALLY_NO_SUPERIORITY_CLAIM",
        "historical_holdouts_opened": False,
        "training_performed": False,
        "voice_comedy_final_polish_scored": False,
        "claim_limit": manifest["allowed_claim"],
    }
    result = {**core, "result_identity": sha(canonical(core))}
    args.output.write_bytes(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
