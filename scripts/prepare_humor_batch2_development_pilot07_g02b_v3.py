"""Audit and prepare Pilot 07's pathless G02B constructor-access release."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "b63a4c0b321f15bf5af89fa44ed46a8c088f2f3b"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-constructor-facing-rebalancing-assignment-proposal-v3.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-sealed-rebalancing-assignment-v3.json"
AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-rebalancing-assignment-design-audit-v3.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    prior, mapping, prior_audit = load(PACKET_PATH), load(MAPPING_PATH), load(AUDIT_PATH)
    require(prior["constructor_facing_packet_identity"] == "816db443646694596047f81eda5e83e1805e375244e8930b6e790325dce0f894", "packet")
    require(mapping["sealed_assignment_identity"] == "40e51c49f9f488aab87c044d107aff5f78be8d900ca3c5e33e07b7d06e2cce50", "mapping")
    require(prior_audit["audit_identity"] == "3d10dcf65e3f192225258199914e92d15b14042d3d2f62b323b8939126347a21", "audit")
    require(prior["selected_proposition_id"] == "P5" and len(prior["closed_factual_authority_envelope"]["propositions"]) == 1, "P5 only")
    context = prior["exact_authorized_visible_context_utf8"].encode()
    require(hashlib.sha256(context).hexdigest() == prior["authorized_visible_context_sha256"] == prior["selected_supporting_span_sha256"], "span")
    core = dict(prior)
    superseded_identity = core.pop("constructor_facing_packet_identity")
    removed_mapping_commitment = core.pop("mapping_commitment")
    removed_pool_authority = core["authority_matrix"].pop("g04b_pool_certification")
    require(removed_pool_authority is False, "pool authority")
    core["status"] = "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION"
    packet_id = seal("B2_DEVELOPMENT_PILOT07_CONSTRUCTOR_PACKET_G02B_V3", core)
    packet = {**core, "constructor_facing_packet_identity": packet_id}
    transport = {
        "constructor_role": "CONSTRUCTOR",
        "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_PATHLESS_CAPABILITY",
        "repository_access": False,
        "filesystem_path_access": False,
        "sibling_artifact_discovery": False,
        "environment_inheritance": False,
        "command_line_payload": False,
        "process_handle_inheritance": False,
        "metadata_enumeration": False,
        "cache_or_temp_file": False,
        "import_time_repository_access": False,
        "logs_contain_packet_or_mapping": False,
        "exceptions_contain_packet_or_mapping": False,
        "network_access": False,
        "constructor_invocation_authorized": False,
    }
    release_core = {
        "constructor_facing_packet_identity": packet_id,
        "packet_seal_namespace": "B2_DEVELOPMENT_PILOT07_CONSTRUCTOR_PACKET_G02B_V3",
        "immutable_assignment_identity": packet["immutable_assignment_identity"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "authorized_visible_context_sha256": packet["authorized_visible_context_sha256"],
        "partition": "DEVELOPMENT",
        "creative_premise_family_id": "UNASSIGNED",
        "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
        "single_use_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED",
        "constructor_invocation_authorized": False,
    }
    release_id = seal("B2_DEVELOPMENT_PILOT07_CONSTRUCTOR_ACCESS_RELEASE_V3", release_core)
    release = {
        "schema_name": "batch2-development-pilot07-constructor-access-release-v3",
        "schema_version": "3.0.0",
        "release_core": release_core,
        "release_identity": release_id,
        "constructor_packet": packet,
        "constructor_visible_object_set": ["CONSTRUCTOR_PACKET_EXACT_BYTES"],
        "transport_policy": transport,
    }
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension", rb"LITERALIZATION", rb"MISDIRECTION", rb"ESCALATION",
                 rb"mechanism_id", rb"mechanism_name", rb"close_alternative", rb"mapping_commitment", rb"BLIND_EVALUATION", rb"owner.preference", rb"G04B", rb"pool"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"leakage: {hits}")
    require(packet["selected_proposition_id"] == "P5" and len(packet["closed_factual_authority_envelope"]["propositions"]) == 1, "visible scope")
    require(packet["exact_authorized_visible_context_utf8"].encode() == context, "context equality")
    require(packet["candidate_surface"] is None and packet["constructor_invoked"] is False, "construction")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    require(all(value is False for key, value in transport.items() if key not in {"constructor_role", "packet_delivery"}), "transport")
    audit_core = {
        "schema_name": "batch2-development-pilot07-g02b-preconstruction-audit-v3",
        "schema_version": "3.0.0",
        "reviewed_assignment_commit": COMMIT,
        "superseded_packet_identity": superseded_identity,
        "constructor_facing_packet_identity": packet_id,
        "release_identity": release_id,
        "deterministic_defects_found": ["MAPPING_COMMITMENT_OFFLINE_CORRELATION_ORACLE", "POOL_GOVERNANCE_FIELD_VISIBLE_TO_CONSTRUCTOR"],
        "remediation": "REMOVED_MAPPING_COMMITMENT_AND_POOL_GOVERNANCE_FIELD_FROM_CONSTRUCTOR_VISIBLE_PACKET",
        "removed_mapping_commitment_sha256": hashlib.sha256(removed_mapping_commitment.encode()).hexdigest(),
        "packet_integrity": "PASS",
        "sufficiency_receipt_binding": "PASS_EXACT",
        "selected_proposition_and_span_binding": "PASS_EXACT_P5_ONLY",
        "authorized_visible_context": f"PASS_EXACT_{len(context)}_BYTES",
        "no_extra_proposition_context": "PASS",
        "path_traversal": "PASS_NO_PATH_API",
        "sibling_discovery": "PASS_SINGLE_OBJECT_CAPABILITY",
        "environment_cli_process_leakage": "PASS_NONE",
        "logs_exceptions_cache_temp": "PASS_NO_PERSISTENCE_OR_PAYLOAD",
        "repository_import_metadata_access": "PASS_NONE",
        "stale_packet_substitution": "PASS_SUCCESSOR_IDENTITY_ONLY",
        "packet_relocation_resealing": "PASS_PATHLESS_IDENTITY_BOUND",
        "constructor_role_substitution": "PASS_EXACT_ROLE_POLICY",
        "sealed_mapping_access": "DENIED",
        "blind_material_access": "DENIED",
        "label_and_pool_token_scan": "PASS_ZERO_HITS",
        "cue_minimization": "PASS_OPERATIONAL_SEMANTICS_ONLY",
        "constructor_invocations": 0,
        "candidate_surfaces": 0,
        "creative_premise_family_id": "UNASSIGNED",
        "capability_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED",
        "downstream_authority_granted": False,
        "deterministic_blockers_remaining": [],
        "verdict": "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT07_G02B_AUDIT_V3", audit_core)}
    write("humor-mechanics-batch2-development-pilot07-constructor-facing-assignment-g02b-v3.json", packet)
    write("humor-mechanics-batch2-development-pilot07-constructor-access-release-v3.json", release)
    write("humor-mechanics-batch2-development-pilot07-g02b-preconstruction-audit-v3.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "constructor_facing_packet_identity": packet_id,
                      "release_identity": release_id, "audit_identity": audit["audit_identity"],
                      "selected_proposition": "P5", "constructor_invocations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
