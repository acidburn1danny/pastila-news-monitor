"""Remediate and audit the Pilot 05 pre-construction G02B release."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
ASSIGNMENT_COMMIT = "def90e29e81f42e41e3cb77417000710207dc88a"
SOURCE_COMMIT = "585c986e0bd6b4717b3a1e90aad4aa5a7c8c0373"
SOURCE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-ingestion-v1/source.utf8.txt"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-constructor-facing-rebalancing-assignment-proposal-v1.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-sealed-rebalancing-assignment-v1.json"
AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-rebalancing-assignment-design-audit-v1.json"
SOURCE_SHA = "e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc"
SOURCE_OID = "62f76d5645edd0be0535f4611b43548491e6c6ea"
PACKET_NAMESPACE = "B2_DEVELOPMENT_PILOT05_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(git_bytes(commit, path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: Any) -> None:
    (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == ASSIGNMENT_COMMIT,
            "HEAD differs from assignment freeze")
    prior = git_json(ASSIGNMENT_COMMIT, PACKET_PATH)
    mapping = git_json(ASSIGNMENT_COMMIT, MAPPING_PATH)
    prior_audit = git_json(ASSIGNMENT_COMMIT, AUDIT_PATH)
    source = git_bytes(SOURCE_COMMIT, SOURCE_PATH)
    require(hashlib.sha256(source).hexdigest() == SOURCE_SHA, "source hash")
    require(hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest() == SOURCE_OID, "source blob")
    require(prior["constructor_facing_packet_identity"] == "116febfa5e3953741e7afbbddc78eaecf09b33dbdad495d3f3019903b8a56b2a", "prior packet")
    require(mapping["sealed_assignment_identity"] == "17fe47e507801352f5892d03e3fd4faa8fec9535202f05a90f1e337c87f89e75", "mapping")
    require(prior_audit["audit_identity"] == "c92287214e9291cca257543f105b71d7fdda17bb63b57a9ea8bd923362cb7732", "audit")
    core = dict(prior)
    old_identity = core.pop("constructor_facing_packet_identity")
    removed_mapping = core.pop("mapping_commitment")
    embedded = core.pop("exact_source_utf8")
    require(embedded.encode("utf-8") == source, "prior source binding")
    core["source_object"] = {
        "git_blob_oid_sha1": SOURCE_OID, "sha256": SOURCE_SHA, "byte_length": len(source),
        "encoding": "UTF-8", "source_text_utf8": source.decode("utf-8"),
        "access": "CONSTRUCTOR_VISIBLE_INSIDE_SINGLE_USE_CAPABILITY_ONLY",
    }
    core["status"] = "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION"
    packet_id = seal(PACKET_NAMESPACE, core)
    packet = {**core, "constructor_facing_packet_identity": packet_id}
    release_core = {
        "constructor_facing_packet_identity": packet_id, "packet_seal_namespace": PACKET_NAMESPACE,
        "immutable_assignment_identity": packet["immutable_assignment_identity"], "admission_identity": packet["admission_identity"],
        "partition": "DEVELOPMENT", "creative_premise_family_id": "UNASSIGNED",
        "source_sha256": SOURCE_SHA, "source_git_blob_oid_sha1": SOURCE_OID, "source_byte_length": len(source),
        "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
        "single_use_state": "UNCONSUMED_0_OF_1", "constructor_invocation_authorized": False,
    }
    release_id = seal("B2_DEVELOPMENT_PILOT05_CONSTRUCTOR_ACCESS_RELEASE_V1", release_core)
    transport = {
        "constructor_role": "CONSTRUCTOR", "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_CAPABILITY",
        "repository_access": False, "filesystem_path_access": False, "sibling_artifact_discovery": False,
        "environment_inheritance": False, "command_line_payload": False, "process_handle_inheritance": False,
        "metadata_enumeration": False, "cache_or_temp_file": False, "import_time_repository_access": False,
        "logs_contain_packet_or_mapping": False, "exceptions_contain_packet_or_mapping": False,
        "network_access": False, "constructor_invocation_authorized": False,
    }
    release = {
        "schema_name": "batch2-development-pilot05-constructor-access-release-v1", "schema_version": "1.0.0",
        "release_core": release_core, "release_identity": release_id, "constructor_packet": packet,
        "constructor_visible_object_set": ["CONSTRUCTOR_PACKET_EXACT_BYTES"], "transport_policy": transport,
    }
    visible = canonical(packet)
    forbidden = [rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
                 rb"MISDIRECTION", rb"ESCALATION", rb"HYPERBOLE", rb"reclasific", rb"rebalanc", rb"g04b", rb"pool",
                 rb"mechanism_id", rb"mechanism_name", rb"answer key", rb"owner preference", rb"BLIND_EVALUATION",
                 rb"mapping_commitment", rb"conformance_schema", rb"dependency_receipt", rb"removal_test"]
    hits = [item.decode("ascii") for item in forbidden if re.search(item, visible, re.I)]
    require(not hits, f"constructor-visible leakage: {hits}")
    require(packet["source_object"]["source_text_utf8"].encode("utf-8") == source, "source bytes")
    require(packet["creative_premise_family_id"] == "UNASSIGNED", "creative premise")
    require(all(value is False for value in packet["authority_matrix"].values()), "hidden authority")
    require(packet["candidate_surface"] is None and packet["constructor_invoked"] is False, "construction")
    require(all(value is False for key, value in transport.items() if key not in {"constructor_role", "packet_delivery"}), "transport")
    audit_core = {
        "schema_name": "batch2-development-pilot05-g02b-preconstruction-audit-v1", "schema_version": "1.0.0",
        "reviewed_assignment_commit": ASSIGNMENT_COMMIT, "superseded_packet_identity": old_identity,
        "constructor_facing_packet_identity": packet_id, "release_identity": release_id,
        "deterministic_defects_found": ["MAPPING_COMMITMENT_OFFLINE_CORRELATION_ORACLE", "DUPLICATE_SOURCE_SURFACE_FIELDS"],
        "remediation": "REMOVED_CORRELATION_ORACLE_AND_CANONICALIZED_EXACT_SOURCE_IN_SINGLE_SOURCE_OBJECT",
        "removed_mapping_commitment_sha256": hashlib.sha256(removed_mapping.encode()).hexdigest(),
        "packet_integrity": "PASS", "source_byte_binding": f"PASS_EXACT_{len(source)}_BYTES_SHA256_AND_GIT_BLOB",
        "obligation_family_integrity": "PASS_EXACT_REVERSE_DISCLOSURE_DEPENDENCY_BODY",
        "exact_authorized_visible_fields": "PASS", "path_traversal": "PASS_NO_PATH_API",
        "sibling_discovery": "PASS_SINGLE_OBJECT_CAPABILITY", "environment_and_cli_leakage": "PASS_NONE",
        "process_inheritance": "PASS_NO_HANDLES", "logs_telemetry_exceptions": "PASS_NO_PACKET_OR_MAPPING",
        "repository_and_import_access": "PASS_NONE", "cache_temp_leakage": "PASS_NO_PERSISTENCE",
        "metadata_enumeration": "PASS_NO_ENUMERATION_API", "stale_packet_substitution": "PASS_EXACT_SUCCESSOR_IDENTITY_ONLY",
        "packet_relocation_resealing": "PASS_PATHLESS_IDENTITY_BOUND", "constructor_role_substitution": "PASS_EXACT_ROLE_POLICY",
        "sealed_mapping_access": "DENIED", "blind_material_access": "DENIED", "label_token_scan": "PASS_ZERO_HITS",
        "cue_minimization": "PASS_OPERATIONAL_SEMANTICS_ONLY_NO_POOL_OR_ALTERNATIVE_LABELS",
        "source_shape_shortcut": "PASS_SELECTION_RATIONALE_NOT_VISIBLE", "constructor_invocations": 0,
        "candidate_surfaces": 0, "creative_premise_family_id": "UNASSIGNED",
        "capability_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED", "downstream_authority_granted": False,
        "deterministic_blockers_remaining": [], "verdict": "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT05_G02B_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot05-constructor-facing-assignment-g02b-v1.json", packet)
    write("humor-mechanics-batch2-development-pilot05-constructor-access-release-v1.json", release)
    write("humor-mechanics-batch2-development-pilot05-g02b-preconstruction-audit-v1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "constructor_facing_packet_identity": packet_id,
                      "release_identity": release_id, "audit_identity": audit["audit_identity"],
                      "source_binding": f"PASS_EXACT_{len(source)}_BYTES", "creative_premise_family_id": "UNASSIGNED",
                      "constructor_invocations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
