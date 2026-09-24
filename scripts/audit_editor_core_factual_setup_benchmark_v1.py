"""Fail-closed audit for EDITOR factual setup contract and benchmark v1."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-factual-setup-benchmark-v1"
CONTRACT = ART / "editor-core-factual-setup-contract-v1.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sentences(text: str) -> int:
    return len(re.findall(r'[.!?](?=(?:[\"”»)]*)\s|$)', text.strip())) or 1


def audit() -> dict[str, object]:
    contract = json.loads(CONTRACT.read_bytes())
    contract_core = {key: value for key, value in contract.items() if key != "contract_identity"}
    if contract["contract_identity"] != sha(canonical(contract_core)):
        raise ValueError("contract identity")
    requests_path = ART / f"{PREFIX}-requests.jsonl"
    key_path = ART / f"{PREFIX}-answer-key.jsonl"
    manifest_path = ART / f"{PREFIX}-manifest.json"
    requests = [json.loads(line) for line in requests_path.read_bytes().splitlines()]
    keys = [json.loads(line) for line in key_path.read_bytes().splitlines()]
    manifest = json.loads(manifest_path.read_bytes())
    manifest_core = {key: value for key, value in manifest.items() if key != "manifest_identity"}
    if manifest["manifest_identity"] != sha(canonical(manifest_core)):
        raise ValueError("manifest identity")
    if manifest["requests_sha256"] != sha(requests_path.read_bytes()) or manifest["answer_key_sha256"] != sha(key_path.read_bytes()):
        raise ValueError("artifact identity")
    if len(requests) != 24 or len(keys) != 24:
        raise ValueError("case count")
    request_ids = {row["example_id"] for row in requests}
    key_ids = {row["example_id"] for row in keys}
    if len(request_ids) != 24 or request_ids != key_ids:
        raise ValueError("case identity closure")
    operators: Counter[str] = Counter()
    all_spans: set[str] = set()
    forbidden_words = re.compile(r"(?i)\b(?:sarcasm|ironi|roast|glum|punchline)\b")
    for request_row in requests:
        if request_row["split"] != "INDEPENDENT_SELECTION_BENCHMARK" or len(request_row["messages"]) != 2:
            raise ValueError("request split")
        if any(message["role"] == "assistant" for message in request_row["messages"]):
            raise ValueError("target leakage")
        payload = json.loads(request_row["messages"][1]["content"].split("\nINPUT=", 1)[1])
        identity = payload.pop("request_identity")
        if identity != "sha256:" + sha(canonical(payload)):
            raise ValueError("request identity")
        spans = payload["authority_spans"]
        if len(spans) != 3 or len({span["source_id"] for span in spans}) != 3:
            raise ValueError("multisource closure")
        if payload["sentence_budget"] != {"minimum": 2, "maximum": 3}:
            raise ValueError("sentence budget")
        for span in spans:
            if span["span_id"] in all_spans:
                raise ValueError("span replay")
            all_spans.add(span["span_id"])
        operators[request_row["operator"]] += 1
    for key in keys:
        target = json.loads(key["assistant_target"])
        if not 2 <= sentences(target["text"]) <= 3:
            raise ValueError("target sentence budget")
        if forbidden_words.search(target["text"]):
            raise ValueError("voice/style leakage")
        if not key["required_evidence"] or not key["forbidden_inferences"]:
            raise ValueError("rubric closure")
    if len(operators) != 8 or set(operators.values()) != {3}:
        raise ValueError("operator balance")
    # Exact bytes from prior training inputs are forbidden; historical holdouts are never read.
    prior = []
    for round_name in ("v1", "r2", "r3", "r4", "r5", "r6"):
        path = ART / f"editor-core-v10-v12-targeted-continuation-{round_name}-new-train.jsonl"
        prior.extend(json.loads(line) for line in path.read_bytes().splitlines())
    old_text = {message["content"] for row in prior for message in row["messages"]}
    new_text = {message["content"] for row in requests for message in row["messages"]}
    if old_text & new_text:
        raise ValueError("historical train exact reuse")
    core = {
        "schema": "editor-core-factual-setup-benchmark-audit", "schema_version": 1,
        "status": "PASS", "contract_identity": contract["contract_identity"],
        "manifest_identity": manifest["manifest_identity"], "cases": 24,
        "operators": dict(sorted(operators.items())), "unique_spans": len(all_spans),
        "multisource_cases": 24, "sentence_budget_closed": True,
        "target_leakage": False, "voice_comedy_polish_objective": False,
        "historical_training_exact_reuse": False, "historical_holdouts_read": False,
    }
    return {**core, "audit_identity": sha(canonical(core))}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
