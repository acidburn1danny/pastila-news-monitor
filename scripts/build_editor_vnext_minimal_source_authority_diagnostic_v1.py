"""Build the self-contained VNext minimal source-authority diagnostic bundle."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-vnext-minimal-source-authority-diagnostic-v1"
LEGACY_FIXTURE = ART / "editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl"


def enc(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identified(value: dict, key: str) -> dict:
    value = dict(value)
    value[key] = digest(enc(value))
    return value


def literals(text: str) -> dict:
    return {
        "numbers_dates_amounts": re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?:\s*%)?(?!\w)", text),
        "attribution_modality": [x for x in ("potrivit", "afirma", "sustine", "estimeaza", "ar fi", "preliminar") if x in text.casefold()],
        "procedural": [x for x in ("propus", "propunere", "vot", "aprobat", "in curs", "conditionat", "semnat") if x in text.casefold()],
    }


legacy = [json.loads(line) for line in LEGACY_FIXTURE.read_text(encoding="utf-8").splitlines() if line]
if len(legacy) != 48:
    raise ValueError("expected closed 48-case fixture source")

fixtures = []
for row in legacy:
    spans = []
    required_atoms = set(row["realization_contract"]["required_atom_ids"])
    required_spans = {atom["source_span_id"] for atom in row["atoms"] if atom["atom_id"] in required_atoms}
    for position, source in enumerate(row["source_spans"]):
        raw = source["text"].encode()
        spans.append({
            "span_id": source["span_id"], "source_id": source["source_id"], "position": position,
            "text": source["text"], "sha256": digest(raw), "byte_start": 0, "byte_end": len(raw),
            "critical_literals": literals(source["text"]),
        })
    deterministic_ids = []
    for span in spans:
        features = span["critical_literals"]
        if span["position"] == 0 or any(features.values()):
            deterministic_ids.append(span["span_id"])
    selector_additions = sorted(required_spans - set(deterministic_ids))
    fixtures.append(identified({
        "case_id": row["case_id"], "partition": row["partition"], "failure_class": row["failure_class"],
        "source_packet": identified({
            "schema": "editor-vnext-source-packet", "schema_version": 1, "event_id": row["case_id"],
            "completeness": "FIXTURE_EXCERPTS_COMPLETE_FOR_CASE", "spans": spans,
        }, "packet_identity"),
        "measurement_only": {"oracle_required_span_ids": sorted(required_spans)},
        "arms": {
            "V0_FULL_SOURCE": [span["span_id"] for span in spans],
            "V1_DETERMINISTIC_EVIDENCE": deterministic_ids,
            "V2_DETERMINISTIC_PLUS_BOUNDED_SELECTOR": sorted(set(deterministic_ids) | set(selector_additions)),
            "ORACLE_UPPER_BOUND": sorted(required_spans),
        },
        "bounded_selector_fixture": {
            "operation": "ADD_EXISTING_SPAN_IDS_ONLY", "add_span_ids": selector_additions,
            "free_text_facts_allowed": False, "oracle_measurement_proxy": True,
        },
    }, "fixture_identity"))

contracts = {
    "SourcePacket": {
        "required": ["event_id", "completeness", "spans", "packet_identity"],
        "span_required": ["span_id", "source_id", "text", "sha256", "byte_start", "byte_end"],
        "authority": "SOURCE_TEXT_BYTES_ONLY",
    },
    "EvidencePacket": {
        "required": ["source_packet_identity", "selected_span_ids", "critical_literals", "unresolved_flags"],
        "prohibits": ["FREE_TEXT_FACTS", "NEW_ACTORS", "NEW_NUMBERS", "SILENT_CONFLICT_RESOLUTION"],
    },
    "EditorSetup": {
        "required": ["text", "sentence_span_citations", "verifier_status"],
        "usual_sentence_target": "TWO_TO_THREE_EXTENSIBLE_FOR_FACTUAL_SUFFICIENCY",
        "creative_content_allowed": False,
    },
}

bundle = identified({
    "schema": "editor-vnext-minimal-source-authority-diagnostic", "schema_version": 1,
    "status": "DESIGN_FIXTURE_ONLY", "product_pipeline": ["SCOUT", "FACTUAL_AUTHORITY", "EDITOR", "VOICE", "CHIEF_EDITOR", "FINAL"],
    "contracts": contracts,
    "arms": {
        "V0_FULL_SOURCE": "ALL_SOURCE_SPANS_TO_R2_REFERENCE_REALIZER",
        "V1_DETERMINISTIC_EVIDENCE": "CANONICAL_FIRST_SPAN_PLUS_SPANS_WITH_EXPLICIT_CRITICAL_LITERALS",
        "V2_DETERMINISTIC_PLUS_BOUNDED_SELECTOR": "V1_PLUS_ID_ONLY_SELECTOR_FOR_MISSING_REQUIRED_SPANS",
        "ORACLE_UPPER_BOUND": "MEASUREMENT_ONLY",
    },
    "selector_contract": {
        "input": "SOURCE_PACKET_AND_DETERMINISTIC_SPAN_FEATURES", "output": "EXISTING_SPAN_IDS_OR_ABSTAIN",
        "free_text_facts": False, "may_change_source_bytes": False, "unresolved_conflicts_must_be_flagged": True,
    },
    "verifier": {
        "checks": ["PACKET_IDENTITY", "CITATIONS_EXIST", "NUMBER_DATE_AMOUNT_IN_CITED_SPANS", "REQUIRED_MODALITY_AND_PROCEDURE", "NO_VOICE_CONTENT"],
        "failure": "DISCARD_DRAFT_THEN_EXTRACTIVE_FALLBACK_OR_ABSTAIN",
    },
    "metrics": ["FACTUAL_SAFETY", "FACTUAL_SUFFICIENCY", "SPAN_RECALL", "SELECTOR_RATE", "FALLBACK_RATE", "CONTEXT_BYTES", "FUNCTIONAL_ROMANIAN", "OPERATIONAL_COMPONENT_COUNT"],
    "terminal_rules": {
        "STOP": ["ANY_UNBOUND_ACCEPTED_FACT", "ANY_CRITICAL_LITERAL_MUTATION", "V2_CANNOT_ABSTAIN", "NO_SAFETY_OR_SUFFICIENCY_ADVANTAGE_OVER_V0"],
        "REVISE": ["V1_REQUIRED_SPAN_RECALL_BELOW_90_PERCENT", "V2_SELECTOR_RATE_ABOVE_50_PERCENT", "FALLBACK_RATE_ABOVE_25_PERCENT"],
        "CONTINUE": ["ZERO_ACCEPTED_DRIFT", "V2_PRESERVES_ORACLE_SUFFICIENCY", "V2_REDUCES_CONTEXT_WITH_STABLE_SAFETY", "SELECTOR_OUTPUT_IS_ID_ONLY"],
        "precedence": "STOP_THEN_REVISE_THEN_CONTINUE",
    },
    "fixtures": fixtures,
    "claim_limits": ["NO_REAL_INFERENCE", "NO_AUTONOMOUS_SELECTOR_CLAIM", "NO_PARENT_SELECTION", "NO_NATURALISTIC_TRANSFER"],
    "r2_reference": {
        "role": "FROZEN_REFERENCE_REALIZER_NOT_LOADED", "adapter_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
        "checkpoint_identity": "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be",
        "tokenizer_identity": "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135",
    },
    "authorities": {"model_load": False, "inference": False, "optimizer": False, "training": False, "parent_selection": False, "promotion": False, "release": False},
}, "bundle_identity")

bundle_path = ART / f"{PREFIX}-bundle.json"
bundle_path.write_bytes((json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())

manifest = identified({
    "schema": "editor-vnext-minimal-complete-dependency-manifest", "schema_version": 1,
    "bundle_file": bundle_path.name, "bundle_sha256": digest(bundle_path.read_bytes()), "bundle_identity": bundle["bundle_identity"],
    "self_contained_fixture_source_bytes": True, "legacy_runtime_dependencies": [],
    "required_real_runtime_objects": bundle["r2_reference"],
    "real_runtime_preflight": "FAIL_CLOSED_UNLESS_EACH_REQUIRED_OBJECT_IS_LOCALLY_MATERIALIZED_AND_CONTENT_VERIFIED",
    "python": ">=3.14", "third_party_runtime_dependencies": [],
    "diagnostic_tooling": {
        name: digest((ROOT / name).read_bytes()) for name in (
            "scripts/build_editor_vnext_minimal_source_authority_diagnostic_v1.py",
            "scripts/fixture_editor_vnext_minimal_source_authority_diagnostic_v1.py",
            "tests/test_editor_vnext_minimal_source_authority_diagnostic_v1.py",
        )
    },
    "persistent_outputs": [bundle_path.name, f"{PREFIX}-manifest.json", f"../editor-vnext-minimal-source-authority-diagnostic-v1.md"],
    "ephemeral_by_default": ["GENERATIONS", "CACHES", "INTERMEDIATE_PACKETS", "REJECTED_OUTPUTS", "PER_CASE_DEBUG_TRACES"],
    "model_loaded": False, "inference_performed": False, "training_performed": False, "historical_holdouts_read": False,
}, "manifest_identity")
manifest_path = ART / f"{PREFIX}-manifest.json"
manifest_path.write_bytes((json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())

required = sum(len(x["measurement_only"]["oracle_required_span_ids"]) for x in fixtures)
v1_hit = sum(len(set(x["arms"]["V1_DETERMINISTIC_EVIDENCE"]) & set(x["measurement_only"]["oracle_required_span_ids"])) for x in fixtures)
selector_cases = sum(bool(x["bounded_selector_fixture"]["add_span_ids"]) for x in fixtures)
print(json.dumps({"status": "PASS_BUILD", "bundle_identity": bundle["bundle_identity"], "manifest_identity": manifest["manifest_identity"], "cases": len(fixtures), "v1_required_span_recall": v1_hit / required, "selector_case_rate": selector_cases / len(fixtures)}, sort_keys=True))
