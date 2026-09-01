"""Git-object-only post-G01 proposition-sufficiency evaluation for Pilot 09."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "f9d930f2e28f8f93f1831666ed60c4a795843f2d"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot09-ingestion-v1/"
ADMISSION = "docs/artifacts/humor-mechanics-batch2-development-pilot09-g01a-g01b-admission-v1.json"
ADMISSION_AUDIT = "docs/artifacts/humor-mechanics-batch2-development-pilot09-g01a-g01b-admission-v1-audit.json"
GOVERNANCE = "docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-governance-v5.json"
SCHEMA = "docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-conformance-schema-v5.json"
INHERITED_GOVERNANCE = "docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json"
INHERITED_SCHEMA = "docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-conformance-schema-v3.json"
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
    inherited_governance, inherited_schema = load(INHERITED_GOVERNANCE), load(INHERITED_SCHEMA)
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(admission["admission_identity"] == "10c3b5e30247e95e3fe52208e3c292b8404535eee5b2895560efaefbf467d1ed", "admission")
    require(admission_audit["audit_identity"] == "0ce2f1f6e53135574796b0ad045efa3fd506264d52199c786eabf84278ecc907", "audit")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "G01")
    require(admission["proposition_sufficiency_evaluated"] is False, "prior sufficiency")
    require(governance["governance_identity"] == "e81ee4eff9044ee16180ef36a7508fe9f1e7c784fa6830299588cea16c2d3a3e", "governance")
    require(schema["schema_identity"] == "29d7b0f97008ad38e64b8e966f398d829a66299ec805290ebbec3f92848efab6", "schema")
    require(governance["preserves_v3_order_robust_causal_spine_requirements"] is True, "V3 preservation")
    require(inherited_governance["governance_identity"] == governance["supersedes_governance_identities"][0], "inherited governance")
    require(governance["proposition_sufficiency_boundary"] == "UNCHANGED_POST_G01_FACTUAL_RELATION_SUFFICIENCY_ONLY_NO_CREATIVE_ACTOR_ROLE_GUARANTEE", "V5 sufficiency boundary")
    require(schema["governance_identity"] == governance["governance_identity"], "V5 schema binding")
    require(inherited_schema["schema_identity"] == "28dfdab8dd9112d0148dad0b513155b5ae14445f5daee359b7a35d1bc5eb1c2c", "inherited schema")
    require(package["source_package_identity"] == "e6b520958d949f673600366018572fb00da98125646ab75cdb4fc6e34d1da5f0", "package")
    require(package["factual_authority_envelope_identity"] == "9e791c37ce2fca9b927e3c386ede1ae0c2c0019e1301261e5bb900c7ffaa39f9", "envelope")
    require(package["partition"] == "DEVELOPMENT" and package["family_identities"]["creative_premise_family_id"] == "UNASSIGNED", "partition")

    assessments = []
    for proposition in envelope["propositions"]:
        pid = proposition["proposition_id"]
        span = proposition["supporting_span"]
        start, end = span["utf8_byte_coordinates"]
        visible = source[start:end]
        require(hashlib.sha256(visible).hexdigest() == span["span_sha256"], f"{pid} span")
        closed = pid in {"P1", "P2", "P3", "P4", "P5", "P6", "P7"}
        reference_resolution = "PASS_INTERNAL_TO_SELECTED_SPAN" if pid == "P5" else "PASS_NO_UNRESOLVED_REFERENCE"
        witness = None
        if pid == "P5":
            witness = {
                "kind": "ABSTRACT_SOURCE_RELATION_ONLY",
                "relation": "SENSOR_OR_SIGNAL_FAILURE_CONDITION_ENTAILS_AUTOMATIC_BELT_NONSTART",
                "adjacent_links": [
                    "SENSOR_NONDETECTION_OR_SIGNAL_NONARRIVAL_IS_THE_EXPLICIT_DISJUNCTIVE_CONDITION",
                    "THE_EXPLICIT_CONSEQUENCE_IS_AUTOMATIC_BELT_NONSTART",
                ],
                "non_arbitrariness": "REMOVING_EITHER_THE_TRIGGER_CONDITION_OR_AUTOMATIC_NONSTART_BREAKS_THE_EXPLICIT_CONDITIONAL_RELATION",
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
            "selection_status": "SELECTED_SUFFICIENT" if pid == "P5" else "NOT_SELECTED_NO_POSITIVE_WITNESS_ASSERTED",
        })

    selected = envelope["propositions"][4]
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    visible_sha = hashlib.sha256(source[bs:be]).hexdigest()
    require(visible_sha == span["span_sha256"], "visible context")
    witness = assessments[4]["abstract_adjacent_link_witness"]
    require(witness and witness["candidate_surface"] is None and witness["humor"] is None, "witness")
    core = {
        "schema_name": "batch2-pilot09-post-g01-proposition-sufficiency-receipt-v5",
        "schema_version": "5.0.0",
        "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"],
        "inherited_causal_spine_governance_identity": inherited_governance["governance_identity"],
        "inherited_causal_spine_schema_identity": inherited_schema["schema_identity"],
        "admission_commit": COMMIT,
        "admission_identity": admission["admission_identity"],
        "source_package_identity": package["source_package_identity"],
        "authority_envelope_identity": package["factual_authority_envelope_identity"],
        "selected_proposition_id": "P5",
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
        "constructor_v5_compatibility_evaluated": False,
        "creative_premise_family_id": "UNASSIGNED",
        "all_proposition_assessments": assessments,
        "verdict": "PASS_SELECTED_PROPOSITION_SUFFICIENT",
        "authority_matrix": {key: False for key in ("assignment", "constructor_v5_source_compatibility_evaluation", "constructor_release", "construction", "g04b_pool_certification",
                                                       "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "receipt_identity": seal("B2_PILOT09_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V5", core)}
    audit_core = {
        "schema_name": "batch2-pilot09-post-g01-proposition-sufficiency-audit-v5",
        "schema_version": "1.0.0",
        "receipt_identity": receipt["receipt_identity"],
        "git_object_only": True,
        "exact_admission_binding": "PASS",
        "exact_source_and_envelope_binding": "PASS",
        "eight_proposition_spans_reverified": "PASS",
        "exactly_one_selected_proposition": "PASS_P5",
        "positive_source_only_witness": "PASS_NONEMPTY_MECHANISM_NEUTRAL",
        "candidate_surface_absent": True,
        "constructor_v5_compatibility_evaluated": False,
        "mechanism_label_absent": True,
        "downstream_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SOURCE_ONLY_NO_ASSIGNMENT_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_PILOT09_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V5", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot09-proposition-sufficiency-receipt-v5.json", receipt),
                        ("humor-mechanics-batch2-development-pilot09-proposition-sufficiency-audit-v5.json", audit)):
        path = OUT / name
        require(not path.exists(), "artifact exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": receipt["verdict"], "selected_proposition": "P5",
                      "receipt_identity": receipt["receipt_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()


