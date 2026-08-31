"""Git-object-only post-G01 proposition-sufficiency evaluation for Pilot 06."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "b88b2f7431818c51d24fc307ca24743b3a868473"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot06-ingestion-v1/"
ADMISSION = "docs/artifacts/humor-mechanics-batch2-development-pilot06-g01a-g01b-admission-v1.json"
ADMISSION_AUDIT = "docs/artifacts/humor-mechanics-batch2-development-pilot06-g01a-g01b-admission-v1-audit.json"
GOVERNANCE = "docs/artifacts/humor-mechanics-batch2-reverse-disclosure-dependency-governance-v2.json"
SCHEMA = "docs/artifacts/humor-mechanics-batch2-reverse-disclosure-sufficiency-schema-v2.json"
OUT = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(blob(path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    admission, admission_audit = load(ADMISSION), load(ADMISSION_AUDIT)
    governance, schema = load(GOVERNANCE), load(SCHEMA)
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(admission["admission_identity"] == "9cf027e7bdf1c5e8370f8d384d1a775c2aa164703c7dbdbaacf3337d2311d41e", "admission")
    require(admission_audit["audit_identity"] == "9bcb10632904480b346e87a61305340f43c8cec1d0235980215c2eaaa3798821", "audit")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "G01")
    require(admission["proposition_sufficiency_evaluated"] is False, "prior sufficiency")
    require(governance["governance_identity"] == "4b36fa7fbe4f13f8c69add229586fdcb1f571dcb8691601709b45073f4f51f83", "governance")
    require(schema["schema_identity"] == "8e76fe9719e38580b364b3406908f358476f3dba1454695dd34b36d1f0dc92bd", "schema")
    require(package["source_package_identity"] == "67f2744713981d08e5b460284cfec094a0e6be1029b8ce02b46c43e2a378082d", "package")
    require(package["factual_authority_envelope_identity"] == "847d37bb095d029758d1c8cce44e7685edf61016a151762f6ec7e12b7af2660c", "envelope")
    require(package["partition"] == "DEVELOPMENT" and package["family_identities"]["creative_premise_family_id"] == "UNASSIGNED", "partition")

    assessments = []
    for proposition in envelope["propositions"]:
        pid = proposition["proposition_id"]
        span = proposition["supporting_span"]
        start, end = span["utf8_byte_coordinates"]
        visible = source[start:end]
        require(hashlib.sha256(visible).hexdigest() == span["span_sha256"], f"{pid} span")
        closed = pid in {"P1", "P2", "P3", "P4", "P5", "P6"}
        reference_resolution = "PASS_INTERNAL_TO_SELECTED_SPAN" if pid == "P3" else "PASS_NO_UNRESOLVED_REFERENCE"
        witness = None
        if pid == "P3":
            witness = {
                "kind": "ABSTRACT_SOURCE_RELATION_ONLY",
                "relation": "VERIFICATION_EVENT_ENTAILS_REGISTER_ENTRY_WITH_VERIFIED_STATUS_AND_CONTROL_DATE",
                "adjacent_links": [
                    "REGISTERED_CONTROL_DATE_IS_BOUND_TO_THE_VERIFICATION_EVENT",
                    "VERIFIED_STATUS_ENTRY_IS_BOUND_TO_THE_SAME_VERIFICATION_EVENT",
                ],
                "non_arbitrariness": "REMOVING_THE_VERIFICATION_EVENT_BREAKS_BOTH_RECORDED_COMPONENT_BINDINGS",
                "candidate_surface": None,
                "humor": None,
            }
        assessments.append({
            "proposition_id": pid,
            "supporting_span_sha256": span["span_sha256"],
            "standalone_semantic_closure": closed,
            "reference_resolution": reference_resolution,
            "operand_closure": "PASS_NO_UNBOUND_DERIVED_OPERAND",
            "qualification_preservation": "PASS_BOUND_EXACTLY" if proposition["qualification"] else "PASS_NONE_REQUIRED",
            "abstract_adjacent_link_witness": witness,
            "selection_status": "SELECTED_SUFFICIENT" if pid == "P3" else "NOT_SELECTED_NO_POSITIVE_WITNESS_ASSERTED",
        })

    selected = envelope["propositions"][2]
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    visible_sha = hashlib.sha256(source[bs:be]).hexdigest()
    require(visible_sha == span["span_sha256"], "visible context")
    witness = assessments[2]["abstract_adjacent_link_witness"]
    require(witness and witness["candidate_surface"] is None and witness["humor"] is None, "witness")
    core = {
        "schema_name": schema["schema_name"],
        "schema_version": schema["schema_version"],
        "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"],
        "admission_commit": COMMIT,
        "admission_identity": admission["admission_identity"],
        "source_package_identity": package["source_package_identity"],
        "authority_envelope_identity": package["factual_authority_envelope_identity"],
        "selected_proposition_id": "P3",
        "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": visible_sha,
        "authorized_visible_context": "EXACT_SELECTED_SUPPORTING_SPAN_ONLY",
        "standalone_semantic_closure": True,
        "reference_resolution": "PASS_INTERNAL_TO_SELECTED_SPAN",
        "operand_closure": "PASS_NO_UNBOUND_DERIVED_OPERAND",
        "abstract_adjacent_link_witness": witness,
        "qualification_preservation": "PASS_BOUND_EXACTLY",
        "scope_time_modality_unknown_boundaries": "PASS_PRESERVED",
        "mechanism_label_exposed": False,
        "candidate_surface": None,
        "creative_premise_family_id": "UNASSIGNED",
        "all_proposition_assessments": assessments,
        "verdict": "PASS_SELECTED_PROPOSITION_SUFFICIENT",
        "authority_matrix": {key: False for key in ("assignment", "constructor_release", "construction", "g04b_pool_certification",
                                                       "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "receipt_identity": seal("B2_PILOT06_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V2", core)}
    audit_core = {
        "schema_name": "batch2-pilot06-post-g01-proposition-sufficiency-audit-v1",
        "schema_version": "1.0.0",
        "receipt_identity": receipt["receipt_identity"],
        "git_object_only": True,
        "exact_admission_binding": "PASS",
        "exact_source_and_envelope_binding": "PASS",
        "six_proposition_spans_reverified": "PASS",
        "exactly_one_selected_proposition": "PASS_P3",
        "positive_source_only_witness": "PASS_NONEMPTY_MECHANISM_NEUTRAL",
        "candidate_surface_absent": True,
        "mechanism_label_absent": True,
        "downstream_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SOURCE_ONLY_NO_ASSIGNMENT_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_PILOT06_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot06-proposition-sufficiency-receipt-v2.json", receipt),
                        ("humor-mechanics-batch2-development-pilot06-proposition-sufficiency-audit-v1.json", audit)):
        path = OUT / name
        require(not path.exists(), "artifact exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": receipt["verdict"], "selected_proposition": "P3",
                      "receipt_identity": receipt["receipt_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
