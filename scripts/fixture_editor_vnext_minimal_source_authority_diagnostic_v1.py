"""Fixture-only validator for the self-contained VNext diagnostic."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-vnext-minimal-source-authority-diagnostic-v1"


def enc(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_identity(value: dict, key: str) -> None:
    core = {name: item for name, item in value.items() if name != key}
    if value[key] != digest(enc(core)):
        raise ValueError(f"identity mismatch: {key}")


def validate_manifest(manifest: dict) -> None:
    verify_identity(manifest, "manifest_identity")
    if manifest["legacy_runtime_dependencies"]:
        raise ValueError("legacy runtime dependency injected")
    for name, expected in manifest["diagnostic_tooling"].items():
        path = ROOT / name
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError(f"diagnostic tooling drift: {name}")


def load() -> tuple[dict, dict]:
    bundle_path = ART / f"{PREFIX}-bundle.json"
    manifest = json.loads((ART / f"{PREFIX}-manifest.json").read_text(encoding="utf-8"))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    verify_identity(bundle, "bundle_identity")
    validate_manifest(manifest)
    if digest(bundle_path.read_bytes()) != manifest["bundle_sha256"] or bundle["bundle_identity"] != manifest["bundle_identity"]:
        raise ValueError("bundle/manifest mismatch")
    return bundle, manifest


def validate_fixture(fixture: dict) -> None:
    verify_identity(fixture, "fixture_identity")
    packet = fixture["source_packet"]
    verify_identity(packet, "packet_identity")
    ids = set()
    for span in packet["spans"]:
        if span["span_id"] in ids:
            raise ValueError("duplicate span")
        ids.add(span["span_id"])
        raw = span["text"].encode()
        if digest(raw) != span["sha256"] or raw[span["byte_start"]:span["byte_end"]] != raw:
            raise ValueError("source byte binding failure")
    arms = fixture["arms"]
    for name in ("V0_FULL_SOURCE", "V1_DETERMINISTIC_EVIDENCE", "V2_DETERMINISTIC_PLUS_BOUNDED_SELECTOR", "ORACLE_UPPER_BOUND"):
        if not set(arms[name]) <= ids:
            raise ValueError("arm references unknown span")
    if set(arms["V0_FULL_SOURCE"]) != ids:
        raise ValueError("full-source arm is incomplete")
    if not set(arms["V1_DETERMINISTIC_EVIDENCE"]) <= set(arms["V2_DETERMINISTIC_PLUS_BOUNDED_SELECTOR"]):
        raise ValueError("selector removed deterministic evidence")
    selector = fixture["bounded_selector_fixture"]
    if selector["free_text_facts_allowed"] or selector["operation"] != "ADD_EXISTING_SPAN_IDS_ONLY":
        raise ValueError("selector authority expanded")
    if set(selector["add_span_ids"]) - ids:
        raise ValueError("selector invented span")


def run() -> dict:
    bundle, manifest = load()
    if len(bundle["fixtures"]) != 48 or {x["partition"] for x in bundle["fixtures"]} != {"DEVELOPMENT", "REPLAY_RETENTION"}:
        raise ValueError("fixture inventory mismatch")
    for fixture in bundle["fixtures"]:
        validate_fixture(fixture)
    if any(bundle["authorities"].values()) or manifest["legacy_runtime_dependencies"]:
        raise ValueError("forbidden authority or legacy dependency")
    required = sum(len(x["arms"]["ORACLE_UPPER_BOUND"]) for x in bundle["fixtures"])
    v1_hit = sum(len(set(x["arms"]["V1_DETERMINISTIC_EVIDENCE"]) & set(x["arms"]["ORACLE_UPPER_BOUND"])) for x in bundle["fixtures"])
    selector_cases = sum(bool(x["bounded_selector_fixture"]["add_span_ids"]) for x in bundle["fixtures"])
    return {
        "status": "PASS_FIXTURE_ONLY", "bundle_identity": bundle["bundle_identity"], "manifest_identity": manifest["manifest_identity"],
        "cases": 48, "source_spans": sum(len(x["source_packet"]["spans"]) for x in bundle["fixtures"]),
        "v1_required_span_recall": v1_hit / required, "selector_case_rate": selector_cases / 48,
        "legacy_runtime_dependencies": 0, "persistent_artifacts": 3,
        "model_loaded": False, "inference_performed": False, "training_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
