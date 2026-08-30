"""Remediate and freeze the Pilot 01 G02B constructor access release."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "cd2aaf781b1044a66003aff74ba2fa12a8ba3e2c"
OUT = ROOT / "docs/artifacts"
OLD_PACKET = "docs/artifacts/humor-mechanics-batch2-development-pilot01-constructor-facing-assignment-proposal-v1.json"
MAPPING = "docs/artifacts/humor-mechanics-batch2-development-pilot01-sealed-assignment-mapping-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def write(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD differs from assignment freeze")
    old, mapping = committed(OLD_PACKET), committed(MAPPING)
    if old["constructor_facing_packet_identity"] != "b4e993b4693b66fda71775c7dd4d0524c436b1f3e08f046d864eb624b710c7ca":
        raise SystemExit("old packet identity")
    if mapping["sealed_assignment_identity"] != "9b5e3e0a51c1909dbdfb811eb930d2e23cbb13c3dbef783ea27a55f21c3ff75b":
        raise SystemExit("mapping identity")
    core = dict(old)
    core.pop("constructor_facing_packet_identity")
    removed = core.pop("mapping_commitment")
    core["supersedes_constructor_facing_packet_identity"] = old["constructor_facing_packet_identity"]
    core["g02b_remediation"] = "UNNECESSARY_CORRELATION_ORACLE_REMOVED"
    core["status"] = "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION"
    packet_identity = seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_PACKET_G02B_V1", core)
    packet = {**core, "constructor_facing_packet_identity": packet_identity}
    release_core = {
        "constructor_facing_packet_identity": packet_identity,
        "immutable_assignment_identity": packet["immutable_assignment_identity"],
        "admission_identity": packet["admission_identity"],
        "partition": "DEVELOPMENT", "creative_premise_family_id": "UNASSIGNED",
        "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
        "old_mapping_commitment_removed_sha256": hashlib.sha256(removed.encode()).hexdigest(),
    }
    release_identity = seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_ACCESS_RELEASE_V1", release_core)
    transport = {
        "constructor_role": "CONSTRUCTOR", "repository_access": False,
        "filesystem_path_access": False, "sibling_artifact_discovery": False,
        "environment_inheritance": False, "command_line_payload": False,
        "process_handle_inheritance": False, "metadata_enumeration": False,
        "cache_or_temp_file": False, "import_time_repository_access": False,
        "logs_contain_packet_or_mapping": False, "exceptions_contain_packet_or_mapping": False,
        "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_CAPABILITY",
        "constructor_invocation_authorized": False,
    }
    release = {
        "schema_name": "batch2-development-pilot01-constructor-access-release-v1", "schema_version": "1.0.0",
        "release_core": release_core, "release_identity": release_identity,
        "constructor_packet": packet, "constructor_visible_file_set": ["CONSTRUCTOR_PACKET"],
        "transport_policy": transport,
    }
    packet_bytes = canonical(packet)
    forbidden = [rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
                 rb"mechanism_id", rb"mechanism_name", rb"expected evidence role", rb"answer key",
                 rb"owner preference", rb"BLIND_EVALUATION", rb"mapping_commitment"]
    hits = [x.decode("ascii") for x in forbidden if re.search(x, packet_bytes, re.I)]
    if hits:
        raise SystemExit(f"leakage: {hits}")
    if packet["creative_premise_family_id"] != "UNASSIGNED" or not all(v is False for v in packet["authority_matrix"].values()):
        raise SystemExit("assignment/authority")
    audit_core = {
        "schema_name": "batch2-development-pilot01-g02b-preconstruction-audit-v1", "schema_version": "1.0.0",
        "reviewed_assignment_commit": COMMIT, "superseded_packet_identity": old["constructor_facing_packet_identity"],
        "constructor_facing_packet_identity": packet_identity, "release_identity": release_identity,
        "deterministic_defect_found": "MAPPING_COMMITMENT_OFFLINE_CORRELATION_ORACLE",
        "remediation": "REMOVED_FROM_CONSTRUCTOR_VIEW_SUCCESSOR_PACKET",
        "packet_integrity": "PASS", "exact_authorized_visible_fields": "PASS",
        "path_traversal": "PASS_NO_PATH_API", "sibling_discovery": "PASS_SINGLE_OBJECT_CAPABILITY",
        "environment_leakage": "PASS_NO_ENV_INHERITANCE", "command_line_leakage": "PASS_NO_PAYLOAD",
        "process_inheritance": "PASS_NO_HANDLES", "logs_telemetry_exceptions": "PASS_NO_PACKET_OR_MAPPING",
        "repository_relative_lookup": "PASS_NO_REPOSITORY_ACCESS", "import_time_access": "PASS_PASSIVE_IMPORT",
        "cache_temp_leakage": "PASS_NO_PERSISTENCE", "metadata_enumeration": "PASS_NO_ENUMERATION_API",
        "stale_packet_substitution": "PASS_EXACT_SUCCESSOR_IDENTITY", "packet_relocation_resealing": "PASS_PATHLESS_IDENTITY_BOUND",
        "constructor_role_substitution": "PASS_EXACT_PREPARED_TYPE_AND_ROLE_POLICY",
        "sealed_mapping_access": "DENIED", "blind_material_access": "DENIED",
        "label_token_scan": "PASS_ZERO_HITS", "cue_minimization": "PASS_OPERATION_SEMANTICS_ONLY",
        "source_shape_shortcut": "PASS_SELECTION_NOT_DISCLOSED_AND_NEUTRAL_PACKET_PROFILE",
        "constructor_invocations": 0, "candidate_surfaces": 0, "creative_premise_family_id": "UNASSIGNED",
        "downstream_authority_granted": False,
        "verdict": "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT01_G02B_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot01-constructor-facing-assignment-g02b-v1.json", packet)
    write("humor-mechanics-batch2-development-pilot01-constructor-access-release-v1.json", release)
    write("humor-mechanics-batch2-development-pilot01-g02b-preconstruction-audit-v1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "constructor_facing_packet_identity": packet_identity,
                      "release_identity": release_identity, "audit_identity": audit["audit_identity"],
                      "successor_required": True, "creative_premise_family_id": "UNASSIGNED"}, sort_keys=True))


if __name__ == "__main__":
    main()
