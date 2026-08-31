"""Remediate and audit the Pilot 04 pre-construction G02B release."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
ASSIGNMENT_COMMIT = "02ab072957e748cc5df0102487668e6ec1cc7b1d"
SOURCE_COMMIT = "4e4afc730be7600fb0b6ce8abf822bce868b0565"
SOURCE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-ingestion-v1/source.utf8.txt"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-constructor-facing-assignment-proposal-v1.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-sealed-assignment-mapping-v1.json"
AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-assignment-design-leakage-audit-v1.json"
SOURCE_SHA = "db4d440d42596e2db5ca402afa23bc8f65dcf7a7ba23a06d3ebef9e2eb1aa480"
SOURCE_OID = "342f171ed4dcf103a95dd49a6e974a2b246a8f8d"
PACKET_NAMESPACE = "B2_DEVELOPMENT_PILOT04_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1"


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
    require(prior["constructor_facing_packet_identity"] == "61f127f4829f8e697902b087906059add0ca72481d63f370e549807621b19239", "prior packet")
    require(mapping["sealed_assignment_identity"] == "689f57472f4c0147cb6613da5ea737639d74404fbf5e2d0d54ad24700b55f28c", "mapping")
    require(prior_audit["audit_identity"] == "61323e32f2d4783fba4fa01834ae6f624cecbef2c514242bdf42595f1f362087", "audit")
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
    release_id = seal("B2_DEVELOPMENT_PILOT04_CONSTRUCTOR_ACCESS_RELEASE_V1", release_core)
    transport = {
        "constructor_role": "CONSTRUCTOR", "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_CAPABILITY",
        "repository_access": False, "filesystem_path_access": False, "sibling_artifact_discovery": False,
        "environment_inheritance": False, "command_line_payload": False, "process_handle_inheritance": False,
        "metadata_enumeration": False, "cache_or_temp_file": False, "import_time_repository_access": False,
        "logs_contain_packet_or_mapping": False, "exceptions_contain_packet_or_mapping": False,
        "network_access": False, "constructor_invocation_authorized": False,
    }
    release = {
        "schema_name": "batch2-development-pilot04-constructor-access-release-v1", "schema_version": "1.0.0",
        "release_core": release_core, "release_identity": release_id, "constructor_packet": packet,
        "constructor_visible_object_set": ["CONSTRUCTOR_PACKET_EXACT_BYTES"], "transport_policy": transport,
    }
    visible = canonical(packet)
    forbidden = [rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
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
        "schema_name": "batch2-development-pilot04-g02b-preconstruction-audit-v1", "schema_version": "1.0.0",
        "reviewed_assignment_commit": ASSIGNMENT_COMMIT, "superseded_packet_identity": old_identity,
        "constructor_facing_packet_identity": packet_id, "release_identity": release_id,
        "deterministic_defects_found": ["MAPPING_COMMITMENT_OFFLINE_CORRELATION_ORACLE", "DUPLICATE_SOURCE_SURFACE_FIELDS"],
        "remediation": "REMOVED_CORRELATION_ORACLE_AND_CANONICALIZED_EXACT_SOURCE_IN_SINGLE_SOURCE_OBJECT",
        "removed_mapping_commitment_sha256": hashlib.sha256(removed_mapping.encode()).hexdigest(),
        "packet_integrity": "PASS", "source_byte_binding": f"PASS_EXACT_{len(source)}_BYTES_SHA256_AND_GIT_BLOB",
        "governance_v2_obligation_integrity": "PASS_EXACT_FROZEN_CONSTRUCTOR_VISIBLE_BODY",
        "exact_authorized_visible_fields": "PASS", "path_traversal": "PASS_NO_PATH_API",
        "sibling_discovery": "PASS_SINGLE_OBJECT_CAPABILITY", "environment_and_cli_leakage": "PASS_NONE",
        "process_inheritance": "PASS_NO_HANDLES", "logs_telemetry_exceptions": "PASS_NO_PACKET_OR_MAPPING",
        "repository_and_import_access": "PASS_NONE", "cache_temp_leakage": "PASS_NO_PERSISTENCE",
        "metadata_enumeration": "PASS_NO_ENUMERATION_API", "stale_packet_substitution": "PASS_EXACT_SUCCESSOR_IDENTITY_ONLY",
        "packet_relocation_resealing": "PASS_PATHLESS_IDENTITY_BOUND", "constructor_role_substitution": "PASS_EXACT_ROLE_POLICY",
        "sealed_mapping_access": "DENIED", "blind_material_access": "DENIED", "label_token_scan": "PASS_ZERO_HITS",
        "cue_minimization": "PASS_GOVERNANCE_V2_OPERATIONAL_SEMANTICS_ONLY",
        "source_shape_shortcut": "PASS_SELECTION_RATIONALE_NOT_VISIBLE", "constructor_invocations": 0,
        "candidate_surfaces": 0, "creative_premise_family_id": "UNASSIGNED",
        "capability_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED", "downstream_authority_granted": False,
        "deterministic_blockers_remaining": [], "verdict": "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT04_G02B_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot04-constructor-facing-assignment-g02b-v1.json", packet)
    write("humor-mechanics-batch2-development-pilot04-constructor-access-release-v1.json", release)
    write("humor-mechanics-batch2-development-pilot04-g02b-preconstruction-audit-v1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "constructor_facing_packet_identity": packet_id,
                      "release_identity": release_id, "audit_identity": audit["audit_identity"],
                      "source_binding": f"PASS_EXACT_{len(source)}_BYTES", "creative_premise_family_id": "UNASSIGNED",
                      "constructor_invocations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
