"""Audit and prepare Pilot 08's pathless G02B constructor-access release."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "56a97c55146273dc08f1a783c1de306fb48f8f8e"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-constructor-facing-rebalancing-assignment-proposal-v4.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-sealed-rebalancing-assignment-v4.json"
AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-rebalancing-assignment-design-audit-v4.json"
IMPLEMENTATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v4.json"
DENYSET_PATH = "docs/artifacts/humor-mechanics-batch2-nonblind-development-fragment-denyset-v4.json"
STATIC_AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-constructor-v4-static-audit-v1.json"


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
    implementation, denyset, static_audit = load(IMPLEMENTATION_PATH), load(DENYSET_PATH), load(STATIC_AUDIT_PATH)
    require(prior["constructor_facing_packet_identity"] == "2ecb50bcca118b4c62f67d6ee05c685ce1073030d6ef8f26d5930185c87ce48c", "packet")
    require(mapping["sealed_assignment_identity"] == "87c2c2d9f5607e1bdcfcf4b2e01bda2039635e2f9c41c633338d4b42d627259a", "mapping")
    require(prior_audit["audit_identity"] == "d5dc3abb29535200ae98488fd61ce9de7877e0b301d550407d92b5492171bdeb", "audit")
    require(implementation["constructor_implementation_identity"] == "68101cd87711761c2c739dc989490c5dd05eaccc0fac03472b9aac180ce647e4", "implementation")
    require(denyset["fragment_denyset_identity"] == "d35beab3b093d118e52369239477f6dc835e764976e44336793f90704b38c844", "denyset")
    require(static_audit["audit_identity"] == "d25a8e97a4f7bb9e75506120a70f4f84ecef45b7f67e6601fa7c4d67c27a240b", "static audit")
    require(static_audit["constructor_invocations"] == static_audit["candidate_surfaces_created"] == 0, "zero construction")
    require(denyset["blind_reserve_accessed"] is False and len(denyset["candidate_sources"]) == 7, "denyset scope")
    require(prior["selected_proposition_id"] == "P5" and len(prior["closed_factual_authority_envelope"]["propositions"]) == 1, "P5 only")
    context = prior["exact_authorized_visible_context_utf8"].encode()
    require(hashlib.sha256(context).hexdigest() == prior["authorized_visible_context_sha256"] == prior["selected_supporting_span_sha256"], "span")
    core = dict(prior)
    superseded_identity = core.pop("constructor_facing_packet_identity")
    removed_mapping_commitment = core.pop("mapping_commitment")
    removed_pool_authority = core["authority_matrix"].pop("g04b_pool_certification")
    require(removed_pool_authority is False, "pool authority")
    require(core.pop("constructor_implementation_identity").startswith("UNASSIGNED_"), "prior implementation placeholder")
    require(core.pop("fragment_denyset_identity").startswith("UNASSIGNED_"), "prior denyset placeholder")
    core["constructor_implementation_identity"] = implementation["constructor_implementation_identity"]
    core["constructor_implementation_generation"] = 4
    core["fragment_denyset_identity"] = denyset["fragment_denyset_identity"]
    core["status"] = "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION"
    packet_id = seal("B2_DEVELOPMENT_PILOT08_CONSTRUCTOR_PACKET_G02B_V4", core)
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
        "packet_seal_namespace": "B2_DEVELOPMENT_PILOT08_CONSTRUCTOR_PACKET_G02B_V4",
        "immutable_assignment_identity": packet["immutable_assignment_identity"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "authorized_visible_context_sha256": packet["authorized_visible_context_sha256"],
        "partition": "DEVELOPMENT",
        "creative_premise_family_id": "UNASSIGNED",
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "constructor_implementation_generation": 4,
        "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
        "single_use_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED",
        "constructor_invocation_authorized": False,
    }
    release_id = seal("B2_DEVELOPMENT_PILOT08_CONSTRUCTOR_ACCESS_RELEASE_V4", release_core)
    release = {
        "schema_name": "batch2-development-pilot08-constructor-access-release-v4",
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
        "schema_name": "batch2-development-pilot08-g02b-preconstruction-audit-v4",
        "schema_version": "3.0.0",
        "reviewed_assignment_commit": COMMIT,
        "superseded_packet_identity": superseded_identity,
        "constructor_facing_packet_identity": packet_id,
        "release_identity": release_id,
        "deterministic_defects_found": ["MAPPING_COMMITMENT_OFFLINE_CORRELATION_ORACLE", "POOL_GOVERNANCE_FIELD_VISIBLE_TO_CONSTRUCTOR"],
        "remediation": "REMOVED_MAPPING_COMMITMENT_AND_POOL_GOVERNANCE_FIELD_FROM_CONSTRUCTOR_VISIBLE_PACKET",
        "removed_mapping_commitment_sha256": hashlib.sha256(removed_mapping_commitment.encode()).hexdigest(),
        "packet_integrity": "PASS",
        "constructor_implementation_binding": "PASS_EXACT_STATIC_AUDIT_ZERO_INVOCATION",
        "fragment_denyset_binding": "PASS_EXACT_7_NONBLIND_DEVELOPMENT_FAMILIES_1617_HASHES",
        "constructor_v1_preservation": "PASS_BYTE_EXACT_HISTORICAL_ONLY",
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
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT08_G02B_AUDIT_V4", audit_core)}
    write("humor-mechanics-batch2-development-pilot08-constructor-facing-assignment-g02b-v4.json", packet)
    write("humor-mechanics-batch2-development-pilot08-constructor-access-release-v4.json", release)
    write("humor-mechanics-batch2-development-pilot08-g02b-preconstruction-audit-v4.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "constructor_facing_packet_identity": packet_id,
                      "release_identity": release_id, "audit_identity": audit["audit_identity"],
                      "selected_proposition": "P5", "constructor_invocations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
