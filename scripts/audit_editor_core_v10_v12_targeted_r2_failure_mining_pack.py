"""Fail-closed closure and contamination audit for targeted R2."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r2"
PARENT = "50b292f9cfdfb2f44dcc8bb9ef811ea367c78db505e4adc2c62e851e6060d3a4"
CHECKPOINT = "00ee968941f8cba8ea47534d441c272c7a3120f9076953aa552f67e302a0ceef"
FAMILIES = {"UNSUPPORTED_MATERIAL_CLAIMS", "EPISTEMIC_CALIBRATION", "TRANSITION_NO_NEW_FACTS"}
KEY_ORDER = ("schema", "schema_version", "case_id", "request_identity", "output_type", "outcome", "text", "claim_bindings", "abstention_code")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (ART / f"{PREFIX}-{name}.jsonl").read_bytes().splitlines()]


def inp(row: dict) -> dict:
    return json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])


def semantic(row: dict) -> str:
    value = inp(row)
    return " ".join([value["request"], *(span["text"] for span in value["authority_spans"])])


def shingles(text: str) -> set[tuple[str, ...]]:
    tokens = re.findall(r"[a-z0-9ăâîșț]+", unicodedata.normalize("NFC", text).casefold())
    return {tuple(tokens[index:index + 5]) for index in range(max(0, len(tokens) - 4))}


def similarity(left: str, right: str) -> float:
    a, b = shingles(left), shingles(right)
    return len(a & b) / len(a | b) if a or b else 1.0


def audit() -> dict:
    manifest = json.loads((ART / f"{PREFIX}-manifest.json").read_bytes())
    config = json.loads((ART / f"{PREFIX}-training-config.json").read_bytes())
    if manifest["manifest_identity"] != sha(canonical({k: v for k, v in manifest.items() if k != "manifest_identity"})):
        raise ValueError("manifest identity mismatch")
    if config["training_config_identity"] != sha(canonical({k: v for k, v in config.items() if k != "training_config_identity"})):
        raise ValueError("config identity mismatch")
    if manifest["parent_adapter_content_identity"] != PARENT or manifest["parent_checkpoint_identity"] != CHECKPOINT:
        raise ValueError("parent identity mismatch")
    new, replay, training, holdout, keys = (load(name) for name in ("new-train", "replay-anchors", "training", "holdout-requests", "holdout-answer-key"))
    if tuple(map(len, (new, replay, training, holdout, keys))) != (36, 36, 72, 18, 18) or training != new + replay:
        raise ValueError("cardinality/projection mismatch")
    if Counter(row["failure_class"] for row in new) != Counter({family: 12 for family in FAMILIES}):
        raise ValueError("new family balance mismatch")
    if Counter(row["failure_class"] for row in holdout) != Counter({family: 6 for family in FAMILIES}):
        raise ValueError("holdout family balance mismatch")
    key_map = {row["example_id"]: row for row in keys}
    if len(key_map) != 18 or any(len(row["messages"]) != 2 for row in holdout):
        raise ValueError("holdout closure/leakage mismatch")
    for row in new:
        if len(row["messages"]) != 3:
            raise ValueError("training shape mismatch")
        value, target = inp(row), json.loads(row["messages"][2]["content"])
        if tuple(target) != KEY_ORDER or json.dumps(target, ensure_ascii=False, allow_nan=False, separators=(",", ":")) != row["messages"][2]["content"]:
            raise ValueError("target canonical/order mismatch")
        if (target["case_id"], target["request_identity"], target["output_type"]) != (value["case_id"], value["request_identity"], value["output_type"]):
            raise ValueError("target binding mismatch")
    if {row["example_id"] for row in new} & {row["example_id"] for row in holdout}:
        raise ValueError("train/holdout identity overlap")
    prior_targets = {row["assistant_target"] for row in [json.loads(line) for line in (ART / "editor-core-v10-v12-targeted-continuation-v1-holdout-answer-key.jsonl").read_bytes().splitlines()]}
    if prior_targets & {row["assistant_target"] for row in keys}:
        raise ValueError("prior holdout target reuse")

    references = []
    for path in sorted(ART.glob("*.jsonl")):
        if path.name.startswith(PREFIX):
            continue
        for raw in path.read_bytes().splitlines():
            try:
                row = json.loads(raw)
                if isinstance(row.get("messages"), list) and len(row["messages"]) >= 2 and "\nINPUT=" in row["messages"][1].get("content", ""):
                    references.append((path.name, row.get("example_id", ""), semantic(row), canonical(inp(row))))
            except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
    maximum = (0.0, "", "", "")
    exact = []
    for candidate in new + holdout:
        raw, text = canonical(inp(candidate)), semantic(candidate)
        for source, ref_id, ref_text, ref_raw in references:
            if raw == ref_raw:
                exact.append((candidate["example_id"], source, ref_id))
            score = similarity(text, ref_text)
            if score > maximum[0]:
                maximum = (score, candidate["example_id"], source, ref_id)
    if exact or maximum[0] >= 0.72:
        raise ValueError(f"external contamination: exact={exact[:2]} max={maximum}")
    internal = max((similarity(semantic(a), semantic(b)), a["example_id"], b["example_id"]) for a in new for b in holdout)
    if internal[0] >= 0.72:
        raise ValueError(f"train/holdout lexical contamination: {internal}")

    v10 = [json.loads(line) for line in (ART / "pastila-editor-core-v1.2-json-successor-v10-train.jsonl").read_bytes().splitlines()]
    r1 = [json.loads(line) for line in (ART / "editor-core-v10-v12-targeted-continuation-v1-new-train.jsonl").read_bytes().splitlines()]
    v10_hashes, r1_hashes = {sha(canonical(row)) for row in v10}, {sha(canonical(row)) for row in r1}
    replay_hashes = [sha(canonical(row)) for row in replay]
    if len(set(replay_hashes)) != 36 or sum(value in v10_hashes for value in replay_hashes) != 18 or sum(value in r1_hashes for value in replay_hashes) != 18:
        raise ValueError("replay provenance mismatch")
    for record in manifest["artifacts"].values():
        if sha((ROOT / record["path"]).read_bytes()) != record["sha256"]:
            raise ValueError("artifact hash mismatch")
    token = json.loads((ART / f"{PREFIX}-token-audit.json").read_bytes())
    if token["audit_identity"] != sha(json.dumps({k: v for k, v in token.items() if k != "audit_identity"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()):
        raise ValueError("token audit identity mismatch")
    if token["dataset_manifest_identity"] != manifest["manifest_identity"] or token["training_corpus_sha256"] != manifest["artifacts"]["training"]["sha256"]:
        raise ValueError("token audit binding mismatch")
    if not token["all_sequences_within_ceiling"] or not token["terminal_eos_verified"] or token["model_loaded"] or token["training_performed"]:
        raise ValueError("token audit verdict mismatch")
    return {
        "verdict": "PASS",
        "blockers": 0,
        "manifest_identity": manifest["manifest_identity"],
        "training_config_identity": config["training_config_identity"],
        "new_rows": 36,
        "replay_rows": 36,
        "holdout_rows": 18,
        "reference_rows_checked": len(references),
        "exact_contamination_matches": len(exact),
        "maximum_external_jaccard_5gram": maximum,
        "maximum_train_holdout_jaccard_5gram": internal,
        "prior_holdout_targets_reused": False,
        "r4_evidence_used": False,
        "token_audit_identity": token["audit_identity"],
        "maximum_training_sequence_tokens": token["maximum_training_sequence_tokens"],
        "training_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
