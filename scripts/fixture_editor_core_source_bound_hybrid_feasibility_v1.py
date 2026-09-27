"""Fixture-only executable boundary for the source-bound hybrid diagnostic."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-source-bound-hybrid-feasibility-v1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def load_jsonl(name: str) -> list[dict]:
    return [json.loads(line) for line in (ART / name).read_text(encoding="utf-8").splitlines() if line]


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]+", text.casefold(), re.UNICODE))


def numbers(text: str) -> set[str]:
    return set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", text))


def repeated(text: str, width: int = 6) -> bool:
    words = re.findall(r"[^\W_]+", text.casefold(), re.UNICODE)
    seen = set()
    for index in range(max(0, len(words) - width + 1)):
        gram = tuple(words[index : index + width])
        if gram in seen:
            return True
        seen.add(gram)
    return False


def verify_identity(value: dict, key: str) -> None:
    core = {field: item for field, item in value.items() if field != key}
    if value[key] != sha(canonical(core)):
        raise ValueError(f"identity mismatch: {key}")


def validate_ledger(ledger: dict) -> None:
    verify_identity(ledger, "ledger_identity")
    spans = {span["span_id"]: span for span in ledger["source_spans"]}
    atom_ids = {atom["atom_id"] for atom in ledger["atoms"]}
    if len(spans) != len(ledger["source_spans"]) or len(atom_ids) != len(ledger["atoms"]):
        raise ValueError("duplicate source or atom identity")
    for span in spans.values():
        if sha(span["text"].encode("utf-8")) != span["sha256"]:
            raise ValueError("source hash mismatch")
    for atom in ledger["atoms"]:
        source = spans[atom["source_span_id"]]["text"].encode("utf-8")
        quote = atom["quote"].encode("utf-8")
        if source[atom["byte_start"] : atom["byte_end"]] != quote:
            raise ValueError("atom byte binding mismatch")
        if sha(quote) != atom["source_sha256"]:
            raise ValueError("atom hash mismatch")
    contract = ledger["realization_contract"]
    required = set(contract["required_atom_ids"])
    allowed = set(contract["allowed_atom_ids"])
    excluded = set(contract["excluded_atom_ids"])
    if not required or not required <= allowed or allowed & excluded or not (allowed | excluded) <= atom_ids:
        raise ValueError("selection partition mismatch")
    for obligation in ledger["obligations"]:
        support = set(obligation["support_atom_ids"])
        if not support or not support <= required:
            raise ValueError("obligation not bound to required atoms")
    fallback = ledger["extractive_fallback"]["atom_ids"]
    if not (2 <= len(fallback) <= 3) or not set(fallback) <= required:
        raise ValueError("fallback cannot meet sentence contract")


def extractive_proposal(ledger: dict) -> dict:
    atoms = {atom["atom_id"]: atom for atom in ledger["atoms"]}
    return {
        "case_id": ledger["case_id"],
        "sentences": [
            {"text": atoms[atom_id]["quote"], "atom_ids": [atom_id]}
            for atom_id in ledger["extractive_fallback"]["atom_ids"]
        ],
    }


def verify_proposal(ledger: dict, proposal: dict) -> dict:
    reasons = []
    contract = ledger["realization_contract"]
    if proposal.get("case_id") != ledger["case_id"]:
        reasons.append("CASE_ID_MISMATCH")
    sentences = proposal.get("sentences")
    if not isinstance(sentences, list) or not contract["minimum_sentences"] <= len(sentences) <= contract["maximum_sentences"]:
        return {"accepted": False, "reasons": reasons + ["SENTENCE_BUDGET"], "text": None}
    allowed = set(contract["allowed_atom_ids"])
    required = set(contract["required_atom_ids"])
    excluded = set(contract["excluded_atom_ids"])
    bound = set()
    texts = []
    for sentence in sentences:
        text = sentence.get("text")
        atom_ids = sentence.get("atom_ids")
        if not isinstance(text, str) or not text.strip() or not isinstance(atom_ids, list) or not atom_ids:
            reasons.append("MALFORMED_SENTENCE_BINDING")
            continue
        ids = set(atom_ids)
        bound |= ids
        if not ids <= allowed:
            reasons.append("UNAUTHORIZED_ATOM_BINDING")
        if ids & excluded:
            reasons.append("EXCLUDED_ATOM_BINDING")
        texts.append(text.strip())
    if not required <= bound:
        reasons.append("MISSING_REQUIRED_ATOM")
    text = " ".join(texts)
    allowed_words = set(contract["allowed_content_tokens"]) | set(contract["function_words"])
    unauthorized_words = sorted(token for token in tokens(text) if len(token) > 2 and token not in allowed_words)
    if unauthorized_words:
        reasons.append("UNAUTHORIZED_CONTENT_TOKEN")
    output_numbers = numbers(text)
    allowed_numbers = set(contract["allowed_numbers"])
    if output_numbers - allowed_numbers:
        reasons.append("UNAUTHORIZED_NUMBER")
    if allowed_numbers - output_numbers:
        reasons.append("MISSING_REQUIRED_NUMBER")
    low = text.casefold()
    if any(marker not in low for marker in contract["required_epistemic_markers"]):
        reasons.append("MISSING_EPISTEMIC_MARKER")
    if any(marker not in low for marker in contract["required_procedural_markers"]):
        reasons.append("MISSING_PROCEDURAL_MARKER")
    if repeated(text):
        reasons.append("REPETITIVE_CLAUSE")
    return {
        "accepted": not reasons,
        "reasons": sorted(set(reasons)),
        "text": text if not reasons else None,
        "unauthorized_content_tokens": unauthorized_words,
    }


def execute_with_fallback(ledger: dict, proposal: dict) -> dict:
    primary = verify_proposal(ledger, proposal)
    if primary["accepted"]:
        return {"route": "HYBRID_ACCEPTED", "text": primary["text"], "primary": primary}
    fallback_proposal = extractive_proposal(ledger)
    fallback = verify_proposal(ledger, fallback_proposal)
    if not fallback["accepted"]:
        raise ValueError("fail-closed fallback invalid")
    return {
        "route": "EXTRACTIVE_FALLBACK",
        "text": fallback["text"],
        "primary": primary,
        "fallback": fallback,
    }


def run() -> dict:
    manifest = load_json(f"{PREFIX}-manifest.json")
    protocol = load_json(f"{PREFIX}-protocol.json")
    schema = load_json(f"{PREFIX}-ledger-schema.json")
    reconciliation = load_json(f"{PREFIX}-reconciliation-rules.json")
    realization = load_json(f"{PREFIX}-realization-schema.json")
    comparison = load_json(f"{PREFIX}-comparison.json")
    terminal = load_json(f"{PREFIX}-terminal-rules.json")
    ledgers = load_jsonl(f"{PREFIX}-ledgers.jsonl")
    verify_identity(manifest, "pack_identity")
    verify_identity(protocol, "protocol_identity")
    verify_identity(schema, "ledger_schema_identity")
    verify_identity(reconciliation, "reconciliation_identity")
    verify_identity(realization, "realization_schema_identity")
    verify_identity(comparison, "comparison_identity")
    verify_identity(terminal, "decision_identity")
    for name, expected in manifest["files"].items():
        if sha((ART / name).read_bytes()) != expected:
            raise ValueError(f"manifest mismatch: {name}")
    if len(ledgers) != 48 or {row["partition"] for row in ledgers} != {"DEVELOPMENT", "REPLAY_RETENTION"}:
        raise ValueError("ledger inventory mismatch")
    if protocol["parent"] != "R2_STEP_9" or protocol["successor_training"] != "SUSPENDED":
        raise ValueError("parent/training boundary drift")
    if protocol["reconciliation_identity"] != reconciliation["reconciliation_identity"] or not reconciliation["deterministic"]:
        raise ValueError("reconciliation binding drift")
    if any(protocol[key] for key in (
        "model_load_authorized", "inference_authorized", "optimizer_creation_authorized",
        "training_authorized", "successor_candidate_authorized", "parent_selection_authority",
        "promotion_authorized", "release_authorized", "voice_or_chief_editor_objective",
    )):
        raise ValueError("forbidden authority enabled")
    adversarial_rejections = 0
    fallback_closures = 0
    for ledger in ledgers:
        validate_ledger(ledger)
        valid = extractive_proposal(ledger)
        if not verify_proposal(ledger, valid)["accepted"]:
            raise ValueError("valid fixture rejected")
        mutations = []
        novel = json.loads(json.dumps(valid))
        novel["sentences"][0]["text"] += " Birocrația confirmă cazul."
        mutations.append(novel)
        wrong_number = json.loads(json.dumps(valid))
        wrong_number["sentences"][0]["text"] += " 999999."
        mutations.append(wrong_number)
        missing = json.loads(json.dumps(valid))
        missing["sentences"] = missing["sentences"][:-1]
        mutations.append(missing)
        excluded = json.loads(json.dumps(valid))
        excluded_ids = ledger["realization_contract"]["excluded_atom_ids"]
        if excluded_ids:
            excluded["sentences"][0]["atom_ids"].append(excluded_ids[0])
            mutations.append(excluded)
        for mutation in mutations:
            result = execute_with_fallback(ledger, mutation)
            if result["route"] != "EXTRACTIVE_FALLBACK" or not result["fallback"]["accepted"]:
                raise ValueError("adversarial proposal escaped verifier")
            adversarial_rejections += 1
            fallback_closures += 1
    return {
        "status": "PASS_FIXTURE_ONLY",
        "pack_identity": manifest["pack_identity"],
        "protocol_identity": protocol["protocol_identity"],
        "ledgers": len(ledgers),
        "atoms": sum(len(row["atoms"]) for row in ledgers),
        "obligations": sum(len(row["obligations"]) for row in ledgers),
        "valid_extractive_proposals": len(ledgers),
        "adversarial_rejections": adversarial_rejections,
        "fallback_closures": fallback_closures,
        "model_loaded": False,
        "inference_performed": False,
        "optimizer_created": False,
        "training_performed": False,
        "historical_holdouts_read": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
