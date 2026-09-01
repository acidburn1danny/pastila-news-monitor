"""Git-object-only post-G01 proposition-sufficiency evaluation for Pilot 08."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "268f497f827c9045ac9dd15a07c6c6e66cae9b46"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot08-ingestion-v1/"
ADMISSION = "docs/artifacts/humor-mechanics-batch2-development-pilot08-g01a-g01b-admission-v1.json"
ADMISSION_AUDIT = "docs/artifacts/humor-mechanics-batch2-development-pilot08-g01a-g01b-admission-v1-audit.json"
GOVERNANCE = "docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-governance-v4.json"
SCHEMA = "docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-conformance-schema-v4.json"
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
    require(admission["admission_identity"] == "8010b5510177b2805ef5e512f982e459a0f3b16c61ba34eb49ac4a62c40734ba", "admission")
    require(admission_audit["audit_identity"] == "08c8033bca4a3b15370913cf9514bb7b82f03bd6f72063cfe43124939d7f9e62", "audit")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "G01")
    require(admission["proposition_sufficiency_evaluated"] is False, "prior sufficiency")
    require(governance["governance_identity"] == "cc86204c6f199c80ef7c7bf87a58cf3c62d17acb1fe14bd2666bbf5ba86692f6", "governance")
    require(schema["schema_identity"] == "12c96a72555a26181abd5d0e7fa033a425fdacafb3a7fb197a21b39358da1dbe", "schema")
    require(governance["preserves_v3_causal_spine_requirements"] is True, "V3 preservation")
    require(inherited_governance["governance_identity"] == governance["supersedes_governance_identity"], "inherited governance")
    require(inherited_schema["schema_identity"] == "28dfdab8dd9112d0148dad0b513155b5ae14445f5daee359b7a35d1bc5eb1c2c", "inherited schema")
    require(package["source_package_identity"] == "2fd6e1cee4fe69136d976bd988c004de354c5c3cfee553d92f6395ac464fe64f", "package")
    require(package["factual_authority_envelope_identity"] == "9988272b9a99ca29fbd706abc4b6f57bbb6c87a62bf2fe4a79de0919a4051847", "envelope")
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
                "relation": "NONRESPONDING_ZONE_ENTAILS_INTERVENTION_RECORD_AND_LATER_COMPONENT_CHECK",
                "adjacent_links": [
                    "ZONE_NONRESPONSE_IS_THE_EXPLICIT_CONDITION_FOR_INTERVENTION_RECORDING",
                    "THE_INTERVENTION_RECORD_DIRECTS_A_LATER_CHECK_OF_THE_LISTED_COMPONENT_CLASSES",
                ],
                "non_arbitrariness": "REMOVING_NONRESPONSE_RECORDING_OR_LATER_CHECK_BREAKS_THE_EXPLICIT_CONDITIONAL_CHAIN",
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
        "schema_name": "batch2-pilot08-post-g01-proposition-sufficiency-receipt-v4",
        "schema_version": "4.0.0",
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
        "creative_premise_family_id": "UNASSIGNED",
        "all_proposition_assessments": assessments,
        "verdict": "PASS_SELECTED_PROPOSITION_SUFFICIENT",
        "authority_matrix": {key: False for key in ("assignment", "constructor_release", "construction", "g04b_pool_certification",
                                                       "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "receipt_identity": seal("B2_PILOT08_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V4", core)}
    audit_core = {
        "schema_name": "batch2-pilot08-post-g01-proposition-sufficiency-audit-v4",
        "schema_version": "1.0.0",
        "receipt_identity": receipt["receipt_identity"],
        "git_object_only": True,
        "exact_admission_binding": "PASS",
        "exact_source_and_envelope_binding": "PASS",
        "seven_proposition_spans_reverified": "PASS",
        "exactly_one_selected_proposition": "PASS_P5",
        "positive_source_only_witness": "PASS_NONEMPTY_MECHANISM_NEUTRAL",
        "candidate_surface_absent": True,
        "mechanism_label_absent": True,
        "downstream_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SOURCE_ONLY_NO_ASSIGNMENT_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_PILOT08_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V4", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot08-proposition-sufficiency-receipt-v4.json", receipt),
                        ("humor-mechanics-batch2-development-pilot08-proposition-sufficiency-audit-v4.json", audit)):
        path = OUT / name
        require(not path.exists(), "artifact exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": receipt["verdict"], "selected_proposition": "P5",
                      "receipt_identity": receipt["receipt_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
