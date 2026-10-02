from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/root/vnext-voice-chief-slice")
RUN = Path("/root/vnext-voice-bakeoff-run-v1")
ART = REPO / "docs/artifacts"
CANDIDATES = {
    "V0_R2_MINISTRAL_CONTROL": {"revision": "BOUND_BY_VNEXT_R2_LOCK_53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"},
    "V1_QWEN3_8B_NON_THINKING": {"revision": "b968826d9c46dd6066d109eabc6255188de91218", "snapshot_identity": "be259728abcc2c864bdf4d035267a8fcf8ccc57e4e277f8bd5d0934f1963fbc7"},
    "V2_QWEN25_7B_INSTRUCT": {"revision": "a09a35458c702b33eeacc393d103063234e8bc28", "snapshot_identity": "5fe636f259ab71443c94837b3c19420e0b796c3d9edcd371332b8ff88577e8fd"},
}

def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()

def identity(value, field):
    body = {k: v for k, v in value.items() if k != field}
    return hashlib.sha256(canonical(body)).hexdigest()

def norm(text):
    return " ".join(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))

cases = {x["case_id"]: x for x in (json.loads(line) for line in (ART / "editor-vnext-voice-bakeoff-boundary-v1-cases.jsonl").read_text().splitlines())}
answer = json.loads((ART / "editor-vnext-voice-bakeoff-boundary-v1-answer-key.json").read_text())
slot_candidate = {x["slot_identity"]: x["candidate_id"] for x in answer["mappings"]}
rows = []
for path in sorted(RUN.glob("*/outputs/**/*.json")):
    row = json.loads(path.read_text())
    assert identity(row, "receipt_identity") == row["receipt_identity"]
    assert slot_candidate[row["slot_identity"]] == row["candidate_receipt"]["candidate_id"]
    case_id = path.parts[-3]
    case = cases[case_id]
    blind_id = hashlib.sha256(canonical({"slot_identity": row["slot_identity"], "receipt_identity": row["receipt_identity"]})).hexdigest()
    setup_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", case["factual_setup"]))
    output_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", row["commentary"]))
    rows.append({**row, "case_id": case_id, "case_identity": case["case_identity"], "factual_setup": case["factual_setup"], "blind_output_identity": blind_id, "unsupported_numbers": sorted(output_numbers - setup_numbers)})
assert len(rows) == 216

per_candidate = {}
for candidate in CANDIDATES:
    selected = [r for r in rows if r["candidate_receipt"]["candidate_id"] == candidate]
    normalized = [norm(r["commentary"]) for r in selected]
    by_case = defaultdict(list)
    for r in selected:
        by_case[r["case_id"]].append(norm(r["commentary"]))
    cross_case = defaultdict(set)
    for r in selected:
        if not r["abstained"] and norm(r["commentary"]):
            cross_case[norm(r["commentary"])].add(r["case_id"])
    factual_case_findings = sorted({r["case_id"] for r in selected if r["unsupported_numbers"]})
    abstentions = sum(bool(r["abstained"]) for r in selected)
    terminal = "STOP_FACTUAL_DRIFT" if factual_case_findings else ("REVISE_ABSTENTION" if abstentions / len(selected) > 0.20 else "CONTINUE")
    per_candidate[candidate] = {
        "outputs": len(selected),
        "abstentions": abstentions,
        "abstention_rate": round(abstentions / len(selected), 6),
        "unsupported_number_findings": len(factual_case_findings),
        "unsupported_number_cases": factual_case_findings,
        "exact_duplicate_outputs": sum(v - 1 for v in Counter(normalized).values() if v > 1),
        "cross_case_reused_phrases": sum(len(case_ids) > 1 for case_ids in cross_case.values()),
        "seed_stable_cases": sum(len(set(values)) == 1 for values in by_case.values()),
        "seed_cases": len(by_case),
        "mean_commentary_chars": round(sum(len(r["commentary"]) for r in selected) / len(selected), 3),
        "terminal": terminal,
    }

blind_rows = []
for row in sorted(rows, key=lambda r: r["blind_output_identity"]):
    blind_rows.append({
        "schema": "vnext-voice-commentary-blind-review-item",
        "schema_version": 1,
        "blind_output_identity": row["blind_output_identity"],
        "case_id": row["case_id"],
        "case_identity": row["case_identity"],
        "factual_setup": row["factual_setup"],
        "commentary": row["commentary"],
        "abstained": row["abstained"],
    })
blind_payload = b"".join(canonical(x) + b"\n" for x in blind_rows)
(ART / "vnext-voice-candidate-bakeoff-v1-blind-review.jsonl").write_bytes(blind_payload)

materialization = {
    "schema": "vnext-voice-candidate-materialization",
    "schema_version": 1,
    "status": "PASS",
    "candidates": CANDIDATES,
    "inference_outputs": 216,
    "network_runtime_dependency": False,
    "legacy_dependency_count": 0,
}
materialization["materialization_identity"] = identity(materialization, "materialization_identity")
(ART / "vnext-voice-candidate-materialization-v1.json").write_bytes(json.dumps(materialization, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")

result = {
    "schema": "vnext-voice-candidate-commentary-bakeoff-result",
    "schema_version": 1,
    "status": "PASS_BAKEOFF_CLOSED_NO_PROMOTABLE_CANDIDATE",
    "outputs": 216,
    "per_candidate": per_candidate,
    "blind_review_items": 216,
    "blind_review_sha256": hashlib.sha256(blind_payload).hexdigest(),
    "factual_safety_automated_scope": "UNSUPPORTED_NUMERIC_CLAIMS_ONLY",
    "human_semantic_review_completed": False,
    "human_commentary_review_materialized": True,
    "human_review_required_for_current_terminal": False,
    "selected_candidate": None,
    "promotion_prerequisites_closed": False,
    "promotion": False,
    "active_integration": False,
    "voice_state": "DISABLED_UNTIL_PROMOTION",
    "legacy_dependency_count": 0,
}
result["result_identity"] = identity(result, "result_identity")
(ART / "vnext-voice-candidate-commentary-bakeoff-result-v1.json").write_bytes(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
