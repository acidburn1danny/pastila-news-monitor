"""Fail-closed closure and contamination audit for targeted R6."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r6"
PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"
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
    tokens = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold(), flags=re.UNICODE)
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
    if (manifest["parent_adapter_content_identity"], manifest["parent_checkpoint_identity"]) != (PARENT, CHECKPOINT):
        raise ValueError("parent identity mismatch")
    if (config["parent_adapter_content_identity"], config["parent_checkpoint_identity"]) != (PARENT, CHECKPOINT):
        raise ValueError("config parent mismatch")
    if (config["new_training_rows"], config["replay_rows"], config["independent_holdout_rows"],
        config["learning_rate"], config["gradient_accumulation_steps"], config["expected_optimizer_steps"],
        config["max_sequence_tokens"], config["training_authorized"], config["training_performed"]) != \
       (18, 18, 12, "0.0000005", 6, 6, 3072, False, False):
        raise ValueError("training recipe mismatch")
    if manifest["rows"] != {"new_train": 18, "replay": 18, "holdout": 12} or manifest["replay_sources"] != {"v10_v1_2": 6, "targeted_r1": 6, "targeted_r2": 6}:
        raise ValueError("manifest projection mismatch")
    new, replay, training, holdout, keys = (load(name) for name in ("new-train", "replay-anchors", "training", "holdout-requests", "holdout-answer-key"))
    if tuple(map(len, (new, replay, training, holdout, keys))) != (18, 18, 36, 12, 12) or training != new + replay:
        raise ValueError("cardinality/projection mismatch")
    if (len({row["example_id"] for row in new}) != 18 or
        len({row["example_id"] for row in holdout}) != 12 or
        len({row["example_id"] for row in training}) != 36 or
        {row["example_id"] for row in training} & {row["example_id"] for row in holdout}):
        raise ValueError("train/replay/holdout case identity collision")
    if config["r2_r3_r4_r5_holdout_training_use"] or config["rejected_r3_r4_r5_adapter_training_use"]:
        raise ValueError("historical holdout or rejected adapter enabled")
    if set(row["failure_class"] for row in new + holdout) != {"ATTRIBUTION_GRAMMAR"}:
        raise ValueError("failure-class scope mismatch")
    if Counter(row["diagnostic_pattern"] for row in new) != Counter({"PETITION_ATTRIBUTION": 6, "DRAFT_REPORT_CONTEST": 6, "WITNESS_ATTRIBUTION": 6}):
        raise ValueError("training pattern balance mismatch")
    if Counter(row["diagnostic_pattern"] for row in holdout) != Counter({"PETITION_ATTRIBUTION": 4, "DRAFT_REPORT_CONTEST": 4, "WITNESS_ATTRIBUTION": 4}):
        raise ValueError("holdout pattern balance mismatch")
    if any(len(row["messages"]) != 2 for row in holdout) or any(len(row["messages"]) != 3 for row in new):
        raise ValueError("target leakage/shape mismatch")
    key_map = {row["example_id"]: row for row in keys}
    if len(key_map) != 12 or {row["example_id"] for row in new} & set(key_map):
        raise ValueError("holdout identity closure mismatch")
    for row in holdout:
        key = key_map[row["example_id"]]
        if key["request_identity"] != inp(row)["request_identity"] or key["diagnostic_pattern"] != row["diagnostic_pattern"]:
            raise ValueError("holdout key/request binding mismatch")
    for row in new:
        value, target = inp(row), json.loads(row["messages"][2]["content"])
        if tuple(target) != KEY_ORDER or target["case_id"] != value["case_id"] or target["request_identity"] != value["request_identity"]:
            raise ValueError("target binding mismatch")
        if len(target["claim_bindings"]) != 3:
            raise ValueError("epistemic component binding mismatch")
    frozen_holdout_ids: set[str] = set()
    frozen_targets: set[str] = set()
    for version in ("v1", "r2", "r3", "r4", "r5"):
        frozen_holdout_ids |= {row["example_id"] for row in [json.loads(line) for line in (ART / f"editor-core-v10-v12-targeted-continuation-{version}-holdout-requests.jsonl").read_bytes().splitlines()]}
        frozen_targets |= {row["assistant_target"] for row in [json.loads(line) for line in (ART / f"editor-core-v10-v12-targeted-continuation-{version}-holdout-answer-key.jsonl").read_bytes().splitlines()]}
    if frozen_holdout_ids & {row["example_id"] for row in training}:
        raise ValueError("frozen holdout used for training")
    if frozen_targets & {row["messages"][2]["content"] for row in training if len(row["messages"]) == 3}:
        raise ValueError("frozen holdout target reuse")
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
    maximum = (0.0, "", "", ""); exact = []
    for candidate in new + holdout:
        raw, text = canonical(inp(candidate)), semantic(candidate)
        for source, ref_id, ref_text, ref_raw in references:
            if raw == ref_raw: exact.append((candidate["example_id"], source, ref_id))
            score = similarity(text, ref_text)
            if score > maximum[0]: maximum = (score, candidate["example_id"], source, ref_id)
    internal = max((similarity(semantic(a), semantic(b)), a["example_id"], b["example_id"]) for a in new for b in holdout)
    if exact or maximum[0] >= 0.72 or internal[0] >= 0.72:
        raise ValueError(f"contamination closure mismatch: exact={exact[:2]} external={maximum} internal={internal}")
    replay_hashes = [sha(canonical(row)) for row in replay]
    if len(set(replay_hashes)) != 18:
        raise ValueError("replay duplication")
    source_paths = {
        "v10_v1_2": "pastila-editor-core-v1.2-json-successor-v10-train.jsonl",
        "targeted_r1": "editor-core-v10-v12-targeted-continuation-v1-new-train.jsonl",
        "targeted_r2": "editor-core-v10-v12-targeted-continuation-r2-training.jsonl",
    }
    used: set[str] = set(); expected_replay: list[dict] = []; replay_provenance: dict[str, int] = {}
    for name, path in source_paths.items():
        selected = []
        rows = [json.loads(line) for line in (ART / path).read_bytes().splitlines()]
        for row in sorted(rows, key=lambda item: sha(canonical(item))):
            identity = sha(canonical(row))
            if identity not in used:
                used.add(identity); selected.append(row)
                if len(selected) == 6: break
        if len(selected) != 6:
            raise ValueError(f"insufficient replay source rows: {name}")
        replay_provenance[name] = len(selected); expected_replay.extend(selected)
    if replay != expected_replay:
        raise ValueError("deterministic replay source projection mismatch")
    for record in manifest["artifacts"].values():
        if sha((ROOT / record["path"]).read_bytes()) != record["sha256"]:
            raise ValueError("artifact hash mismatch")
    token = json.loads((ART / f"{PREFIX}-token-audit.json").read_bytes())
    if token["audit_identity"] != sha(json.dumps({k: v for k, v in token.items() if k != "audit_identity"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()):
        raise ValueError("token audit identity mismatch")
    if token["dataset_manifest_identity"] != manifest["manifest_identity"] or not token["all_sequences_within_ceiling"] or token["training_performed"]:
        raise ValueError("token audit binding mismatch")
    return {"verdict": "PASS", "blockers": 0, "manifest_identity": manifest["manifest_identity"], "training_config_identity": config["training_config_identity"], "new_rows": 18, "replay_rows": 18, "holdout_rows": 12, "replay_provenance": replay_provenance, "reference_rows_checked": len(references), "exact_contamination_matches": len(exact), "maximum_external_jaccard_5gram": maximum, "maximum_train_holdout_jaccard_5gram": internal, "frozen_holdout_training_use": False, "frozen_holdout_targets_reused": False, "rejected_r3_r4_r5_adapter_training_use": False, "r5_diagnostics_used_for_design_only": True, "token_audit_identity": token["audit_identity"], "maximum_training_sequence_tokens": token["maximum_training_sequence_tokens"], "training_performed": False}


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
