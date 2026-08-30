"""Bind exact admitted source bytes into a successor pathless G02B release."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HEAD = "b6f74bb91dc0c8dd68a7d65aeefdcd9e956d3077"
G02B_COMMIT = "81b6e690843b29139f6b199f3be8904a5e613b93"
SOURCE_COMMIT = "601ee4812d864301cb55620e3d239515163e9ef8"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1/"
PRIOR_PACKET = "docs/artifacts/humor-mechanics-batch2-development-pilot01-constructor-facing-assignment-g02b-v1.json"
ATTEMPT = "docs/artifacts/humor-mechanics-batch2-development-pilot01-construction-attempt01-v1.json"
OUT = ROOT / "docs/artifacts"
NAMESPACE = "B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(git_bytes(commit, path))


def write(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != HEAD:
        raise SystemExit("HEAD differs from consumed-attempt commit")
    prior = git_json(G02B_COMMIT, PRIOR_PACKET)
    attempt = git_json(HEAD, ATTEMPT)
    source = git_bytes(SOURCE_COMMIT, PREFIX + "source.utf8.txt")
    source_sha = hashlib.sha256(source).hexdigest()
    source_oid = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    if source_sha != "84261f1a6b97f951f70a1b86d42114da9703996607d43d2fc3779bffd7a97cb2":
        raise SystemExit("source hash")
    if source_oid != "c3a3316a2fc6be4befa40c1f777c09ecc2b48b6f":
        raise SystemExit("source Git object")
    if attempt["attempt"] != {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}:
        raise SystemExit("prior attempt state")
    if attempt["failure_code"] != "CONSTRUCTOR_SOURCE_SURFACE_UNAVAILABLE" or attempt["candidate_surface_present"] is not False:
        raise SystemExit("prior failure evidence")
    core = dict(prior)
    old_identity = core.pop("constructor_facing_packet_identity")
    if old_identity != "c41a80dc3d6461a4c1bcc68c138aa64da5a3c3074e7768e1d3e8d31cb4367821":
        raise SystemExit("prior packet identity")
    core["supersedes_constructor_facing_packet_identity"] = old_identity
    core["g02b_remediation"] = "EXACT_ADMITTED_SOURCE_BYTES_BOUND"
    core["source_object"] = {
        "commit": SOURCE_COMMIT, "git_blob_oid_sha1": source_oid, "sha256": source_sha,
        "byte_length": len(source), "encoding": "UTF-8", "source_text_utf8": source.decode("utf-8"),
        "access": "CONSTRUCTOR_VISIBLE_INSIDE_SINGLE_USE_CAPABILITY_ONLY",
    }
    core["status"] = "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION"
    packet_identity = seal(NAMESPACE, core)
    packet = {**core, "constructor_facing_packet_identity": packet_identity}
    release_core = {
        "constructor_facing_packet_identity": packet_identity,
        "immutable_assignment_identity": packet["immutable_assignment_identity"],
        "admission_identity": packet["admission_identity"], "partition": "DEVELOPMENT",
        "creative_premise_family_id": "UNASSIGNED", "packet_seal_namespace": NAMESPACE,
        "source_sha256": source_sha, "source_git_blob_oid_sha1": source_oid,
        "source_byte_length": len(source),
        "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
        "prior_attempt_evidence_identity": attempt["evidence_identity"],
    }
    release_identity = seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_ACCESS_RELEASE_V1", release_core)
    release = {
        "schema_name": "batch2-development-pilot01-constructor-access-release-v1", "schema_version": "1.0.0",
        "release_core": release_core, "release_identity": release_identity,
        "constructor_packet": packet, "constructor_visible_file_set": ["CONSTRUCTOR_PACKET"],
        "transport_policy": {
            "constructor_role": "CONSTRUCTOR", "repository_access": False,
            "filesystem_path_access": False, "sibling_artifact_discovery": False,
            "environment_inheritance": False, "command_line_payload": False,
            "process_handle_inheritance": False, "metadata_enumeration": False,
            "cache_or_temp_file": False, "import_time_repository_access": False,
            "logs_contain_packet_or_mapping": False, "exceptions_contain_packet_or_mapping": False,
            "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_CAPABILITY",
            "constructor_invocation_authorized": False,
        },
    }
    packet_bytes = canonical(packet)
    forbidden = [rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
                 rb"mechanism_id", rb"mechanism_name", rb"expected evidence role", rb"answer key",
                 rb"owner preference", rb"BLIND_EVALUATION", rb"mapping_commitment"]
    hits = [x.decode("ascii") for x in forbidden if re.search(x, packet_bytes, re.I)]
    if hits:
        raise SystemExit(f"leakage: {hits}")
    if packet["source_object"]["source_text_utf8"].encode("utf-8") != source:
        raise SystemExit("source byte disagreement")
    if packet["creative_premise_family_id"] != "UNASSIGNED" or not all(v is False for v in packet["authority_matrix"].values()):
        raise SystemExit("authority state")
    decision_core = {
        "schema_name": "batch2-development-pilot01-g02b-source-bound-construction-decision-v1", "schema_version": "1.0.0",
        "prior_consumed_attempt_evidence_identity": attempt["evidence_identity"],
        "prior_attempt_reusable": False, "constructor_facing_packet_identity": packet_identity,
        "release_identity": release_identity, "source_binding": {"sha256": source_sha, "git_blob_oid_sha1": source_oid,
                                                                  "byte_length": len(source), "encoding": "UTF-8"},
        "exact_source_binding": "PASS", "packet_integrity": "PASS", "label_and_taxonomy_scan": "PASS_ZERO_HITS",
        "operational_cue_minimization": "PASS_NO_NEW_OPERATIONAL_WORDING",
        "source_shape_leakage": "PASS_SOURCE_IS_AUTHORITY_INPUT_NOT_SELECTION_RATIONALE",
        "path_and_sibling_isolation": "PASS_SINGLE_OBJECT_CAPABILITY",
        "mapping_and_blind_access": "DENIED", "stale_prior_packet": "REJECTED",
        "mutation_relocation_reseal": "REJECTED", "creative_premise_family_id": "UNASSIGNED",
        "constructor_invocations_after_remediation": 0, "candidate_surfaces_after_remediation": 0,
        "fresh_attempt_state": "UNAUTHORIZED_0_OF_1_PENDING_SEPARATE_OWNER_DECISION",
        "downstream_authority_granted": False,
        "verdict": "READY_FOR_FRESH_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION",
    }
    decision = {**decision_core, "decision_identity": seal("B2_DEVELOPMENT_PILOT01_G02B_SOURCE_BOUND_DECISION_V1", decision_core)}
    write("humor-mechanics-batch2-development-pilot01-constructor-facing-assignment-source-bound-v1.json", packet)
    write("humor-mechanics-batch2-development-pilot01-constructor-access-release-source-bound-v1.json", release)
    write("humor-mechanics-batch2-development-pilot01-g02b-source-bound-construction-decision-v1.json", decision)
    print(json.dumps({"verdict": decision["verdict"], "constructor_facing_packet_identity": packet_identity,
                      "release_identity": release_identity, "decision_identity": decision["decision_identity"],
                      "prior_attempt_consumed": "1/1_NOT_REUSABLE", "fresh_attempt_authorized": False,
                      "creative_premise_family_id": "UNASSIGNED"}, sort_keys=True))


if __name__ == "__main__":
    main()
