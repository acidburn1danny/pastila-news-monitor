"""Fail-closed audit for the prepared Editor Core continuation round."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from pastila_scout.production_core_execution_contract_v10 import (
    EDITORIAL_PROMPT_SHA256,
    OUTPUT_PROTOCOL,
    canonical,
    render_training_messages,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-v1"
EXPECTED_PARENT = "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f"
EXPECTED_CHECKPOINT = "6925fca8c5b6c9e94e96255cb21ec9442aff5d0ac2f7bd0f2038ce45475a7dd1"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rows(name: str) -> list[dict]:
    return [json.loads(x) for x in (ART / f"{PREFIX}-{name}.jsonl").read_bytes().splitlines()]


def input_value(row: dict) -> dict:
    raw = row["messages"][1]["content"]
    return json.loads(raw.split("\nINPUT=", 1)[1])


def semantic_text(row: dict) -> str:
    try:
        value = input_value(row)
    except (KeyError, IndexError, json.JSONDecodeError):
        return row["messages"][1]["content"]
    return " ".join([value["request"], *(x["text"] for x in value["authority_spans"])])


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9ăâîșț]+", unicodedata.normalize("NFC", text).casefold())


def shingles(text: str, width: int = 5) -> set[tuple[str, ...]]:
    t = tokens(text)
    return {tuple(t[i:i + width]) for i in range(max(0, len(t) - width + 1))}


def similarity(a: str, b: str) -> float:
    aa, bb = shingles(a), shingles(b)
    return len(aa & bb) / len(aa | bb) if aa or bb else 1.0


def reference_rows() -> list[tuple[str, dict]]:
    found = []
    for path in sorted(ART.glob("*.jsonl")):
        if path.name.startswith(PREFIX):
            continue
        for raw in path.read_bytes().splitlines():
            value = json.loads(raw)
            if isinstance(value, dict) and isinstance(value.get("messages"), list) and len(value["messages"]) >= 2:
                found.append((path.name, value))
    manifest = json.loads((ART / "production-core-candidate-request-manifest-v2.json").read_bytes())
    for value in manifest["requests"]:
        found.append(("production-core-candidate-request-manifest-v2.json", {
            "example_id": value["case_id"],
            "messages": [{"role": "system", "content": ""}, {"role": "user", "content": value["candidate_visible_request"]}],
        }))
    return found


def audit() -> dict:
    manifest_path = ART / f"{PREFIX}-manifest.json"
    config_path = ART / f"{PREFIX}-training-config.json"
    manifest = json.loads(manifest_path.read_bytes())
    config = json.loads(config_path.read_bytes())
    if manifest["manifest_identity"] != sha(canonical({k: v for k, v in manifest.items() if k != "manifest_identity"})):
        raise ValueError("manifest identity mismatch")
    if config["training_config_identity"] != sha(canonical({k: v for k, v in config.items() if k != "training_config_identity"})):
        raise ValueError("config identity mismatch")
    if config["parent_adapter_content_identity"] != EXPECTED_PARENT or config["parent_checkpoint_identity"] != EXPECTED_CHECKPOINT:
        raise ValueError("parent identity mismatch")
    new, replay, training, holdout, keys = (rows(n) for n in ("new-train", "replay-anchors", "training", "holdout-requests", "holdout-answer-key"))
    if tuple(map(len, (new, replay, training, holdout, keys))) != (64, 64, 128, 32, 32):
        raise ValueError("cardinality mismatch")
    if training != new + replay:
        raise ValueError("combined training projection mismatch")
    expected_families = set(manifest["failure_classes"])
    if Counter(x["failure_class"] for x in new) != Counter({x: 8 for x in expected_families}):
        raise ValueError("new family balance mismatch")
    if Counter(x["failure_class"] for x in holdout) != Counter({x: 4 for x in expected_families}):
        raise ValueError("holdout family balance mismatch")
    source_v10 = rows_from_path(ART / "pastila-editor-core-v1.2-json-successor-v10-train.jsonl")
    combined_system = source_v10[0]["messages"][0]["content"]
    suffix = "\n\n" + OUTPUT_PROTOCOL
    if not combined_system.endswith(suffix):
        raise ValueError("V10 source system projection mismatch")
    editorial = combined_system[:-len(suffix)].encode("utf-8")
    if sha(editorial) != EDITORIAL_PROMPT_SHA256["pastila-editor-core-v1.2-json-successor"]:
        raise ValueError("V10 editorial authority mismatch")
    for row in new:
        if len(row["messages"]) != 3:
            raise ValueError("training message shape mismatch")
        projected = list(render_training_messages(candidate="pastila-editor-core-v1.2-json-successor", editorial_prompt=editorial, user_prompt=row["messages"][1]["content"]))
        if row["messages"][:2] != projected:
            raise ValueError("training renderer mismatch")
        target = row["messages"][2]["content"]
        target_value = json.loads(target)
        if canonical(target_value).decode() != target:
            raise ValueError("noncanonical target")
        inp = input_value(row)
        expected_keys = ("schema", "schema_version", "case_id", "request_identity", "output_type", "outcome", "text", "claim_bindings", "abstention_code")
        if tuple(target_value) != expected_keys:
            raise ValueError("target key order mismatch")
        if target_value["case_id"] != inp["case_id"] or target_value["request_identity"] != inp["request_identity"] or target_value["output_type"] != inp["output_type"]:
            raise ValueError("target request binding mismatch")
        span_order = [value["span_id"] for value in inp["authority_spans"]]
        bindings = target_value["claim_bindings"]
        if len(bindings) != inp["expected_material_proposition_count"]:
            raise ValueError("material proposition count mismatch")
        for index, binding in enumerate(bindings, 1):
            ids = binding["source_span_ids"]
            if binding["claim_index"] != index or not ids or any(value not in span_order for value in ids):
                raise ValueError("claim binding mismatch")
            if ids != sorted(ids, key=span_order.index):
                raise ValueError("claim source ordering mismatch")
        if target_value["outcome"] == "ABSTAIN":
            if target_value["text"] is not None or bindings or target_value["abstention_code"] is None:
                raise ValueError("abstention target mismatch")
        elif target_value["outcome"] == "ANSWER":
            if not target_value["text"] or target_value["abstention_code"] is not None:
                raise ValueError("answer target mismatch")
        else:
            raise ValueError("target outcome mismatch")
    for row in holdout:
        if len(row["messages"]) != 2:
            raise ValueError("holdout leaks answer")
    if {x["example_id"] for x in new} & {x["example_id"] for x in holdout}:
        raise ValueError("new/holdout id overlap")
    if {sha(canonical(x)) for x in new} & {sha(canonical(x)) for x in holdout}:
        raise ValueError("new/holdout row overlap")
    refs = reference_rows()
    ref_inputs = []
    for source, row in refs:
        try:
            try:
                raw = canonical(input_value(row))
            except (KeyError, IndexError, json.JSONDecodeError):
                raw = None
            ref_inputs.append((source, row["example_id"], semantic_text(row), raw))
        except (KeyError, IndexError, json.JSONDecodeError, TypeError):
            continue
    maximum = (0.0, "", "", "")
    exact = []
    for candidate in new + holdout:
        text, raw = semantic_text(candidate), canonical(input_value(candidate))
        for source, ref_id, ref_text, ref_raw in ref_inputs:
            if ref_raw is not None and raw == ref_raw:
                exact.append((candidate["example_id"], source, ref_id))
            score = similarity(text, ref_text)
            if score > maximum[0]:
                maximum = (score, candidate["example_id"], source, ref_id)
    if exact:
        raise ValueError(f"exact contamination: {exact[:3]}")
    if maximum[0] >= 0.72:
        raise ValueError(f"lexical contamination threshold: {maximum}")
    internal_maximum = (0.0, "", "")
    for left in new:
        for right in holdout:
            score = similarity(semantic_text(left), semantic_text(right))
            if score > internal_maximum[0]:
                internal_maximum = (score, left["example_id"], right["example_id"])
    if internal_maximum[0] >= 0.72:
        raise ValueError(f"new/holdout lexical contamination threshold: {internal_maximum}")
    source_hashes = {sha(canonical(x)) for x in source_v10}
    replay_hashes = {sha(canonical(x)) for x in replay}
    if len(replay_hashes) != 64 or not replay_hashes <= source_hashes:
        raise ValueError("replay provenance mismatch")
    source_canonical_raw = b"".join(canonical(row) + b"\n" for row in source_v10)
    replay_source = manifest["replay_source"]
    if sha(source_canonical_raw) != replay_source["canonical_sha256"]:
        raise ValueError("canonical replay source mismatch")
    published_config = json.loads((ART / "pastila-editor-core-v1.2-json-successor-v10-training-config-v10.json").read_bytes())
    if replay_source["canonical_sha256"] != published_config["training_corpus_sha256"]:
        raise ValueError("replay source/public V10 identity mismatch")
    artifacts = manifest["artifacts"]
    for name, record in artifacts.items():
        path = ROOT / record["path"]
        if sha(path.read_bytes()) != record["sha256"]:
            raise ValueError(f"artifact hash mismatch: {name}")
    if config["training_corpus_sha256"] != artifacts["training"]["sha256"]:
        raise ValueError("training/config closure mismatch")
    token_path = ART / f"{PREFIX}-token-audit.json"
    token_audit = json.loads(token_path.read_bytes())
    token_core = {k: v for k, v in token_audit.items() if k != "audit_identity"}
    if token_audit["audit_identity"] != sha(canonical(token_core)):
        raise ValueError("token audit identity mismatch")
    if token_audit["dataset_manifest_identity"] != manifest["manifest_identity"]:
        raise ValueError("token audit manifest binding mismatch")
    expected_token_bindings = {
        "training_corpus_sha256": artifacts["training"]["sha256"],
        "holdout_requests_sha256": artifacts["holdout-requests"]["sha256"],
        "holdout_answer_key_sha256": artifacts["holdout-answer-key"]["sha256"],
    }
    if any(token_audit[key] != value for key, value in expected_token_bindings.items()):
        raise ValueError("token audit artifact binding mismatch")
    if not token_audit["all_sequences_within_ceiling"] or not token_audit["terminal_eos_verified"] or token_audit["training_performed"]:
        raise ValueError("token audit verdict mismatch")
    return {
        "verdict": "PASS",
        "blockers": 0,
        "manifest_identity": manifest["manifest_identity"],
        "training_config_identity": config["training_config_identity"],
        "new_rows": len(new),
        "replay_rows": len(replay),
        "holdout_rows": len(holdout),
        "reference_rows_checked": len(ref_inputs),
        "exact_contamination_matches": len(exact),
        "maximum_lexical_jaccard_5gram": maximum,
        "maximum_new_holdout_jaccard_5gram": internal_maximum,
        "replay_exact_source_matches": len(replay_hashes),
        "token_audit_identity": token_audit["audit_identity"],
        "maximum_training_sequence_tokens": token_audit["maximum_training_sequence_tokens"],
        "training_performed": False,
    }


def rows_from_path(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_bytes().splitlines()]


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
