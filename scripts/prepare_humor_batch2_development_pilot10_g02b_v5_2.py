"""Freeze Pilot 10's uninvoked, pathless Governance V5.2 G02B release."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "da164d884821f1da6a66244d62b2dc96fe641294"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name: str) -> dict[str, Any]:
    raw = subprocess.check_output(["git", "show", f"{COMMIT}:docs/artifacts/{name}"], cwd=ROOT)
    return json.loads(raw)


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), f"artifact already exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def normalized_words(surface: str) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", surface).casefold(), flags=re.UNICODE)


def build_denyset() -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    hashes: set[str] = set()
    for pilot in range(1, 10):
        path = f"docs/artifacts/humor-mechanics-batch2-development-pilot{pilot:02d}-candidate01-v1.txt"
        raw = git_bytes(path)
        tokens = normalized_words(raw.decode("utf-8"))
        local: set[str] = set()
        for size in range(3, 9):
            for index in range(len(tokens) - size + 1):
                local.add(hashlib.sha256(" ".join(tokens[index:index + size]).encode()).hexdigest())
        hashes.update(local)
        oid = subprocess.check_output(["git", "rev-parse", f"{COMMIT}:{path}"], cwd=ROOT, text=True).strip()
        sources.append({"path": path, "partition": "DEVELOPMENT_NONBLIND", "surface_sha256": hashlib.sha256(raw).hexdigest(),
                        "git_blob_oid_sha1": oid, "normalized_word_count": len(tokens), "normalized_ngram_hash_count": len(local)})
    core = {"schema_name": "batch2-nonblind-development-fragment-denyset-v5-2", "schema_version": "5.2.0",
            "source_commit": COMMIT, "eligible_corpus": "NONBLIND_DEVELOPMENT_ONLY", "blind_reserve_accessed": False,
            "candidate_sources": sources, "ngram_word_lengths": [3, 4, 5, 6, 7, 8],
            "normalization": "UNICODE_NFKC_CASEFOLD_ALPHANUMERIC_WORDS", "normalized_ngram_sha256": sorted(hashes),
            "complete_surface_text_included": False, "model_or_semantic_similarity_used": False}
    return {**core, "fragment_denyset_identity": seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_2", core)}


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "unexpected HEAD")
    proposal = load("humor-mechanics-batch2-development-pilot10-constructor-facing-assignment-proposal-v5-2.json")
    mapping = load("humor-mechanics-batch2-development-pilot10-sealed-assignment-v5-2.json")
    assignment_audit = load("humor-mechanics-batch2-development-pilot10-assignment-design-audit-v5-2.json")
    contract = load("humor-mechanics-batch2-development-constructor-contract-v5-2.json")
    implementation = load("humor-mechanics-batch2-development-constructor-implementation-v5-2.json")
    provider = load("humor-mechanics-batch2-development-constructor-v5-2-realization-provider-implementation.json")
    emitter = load("humor-mechanics-batch2-development-constructor-v5-2-candidate-emitter-implementation.json")
    static_audit = load("humor-mechanics-batch2-development-constructor-v5-2-runtime-static-audit-v1.json")
    enforcement = load("humor-mechanics-batch2-development-constructor-plan-to-surface-enforcement-v5-2.json")
    governance = load("humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json")
    schema = load("humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json")
    compatibility = load("humor-mechanics-batch2-development-pilot10-constructor-v5-2-source-compatibility-v1.json")
    compatibility_audit = load("humor-mechanics-batch2-development-pilot10-constructor-v5-2-source-compatibility-audit-v1.json")

    require(proposal["constructor_facing_packet_identity"] == "cf93852215e2214cf9a67eaf82aba747e4b88dc082d0fe935583d9d7af12a807", "proposal")
    require(mapping["sealed_assignment_identity"] == "c4677b0b8d148163d339cf72590078564f5a462a571d6272cbc8800d90ad4aab", "mapping")
    require(assignment_audit["audit_identity"] == "56b1f93daaf9286bcb703d9864575ca424cf2f9e4542b5f95261864aafcd5e6d", "assignment audit")
    require(contract["constructor_contract_identity"] == "69138467540b37cbfb8444596d9a37119f8b74d002e0c491c8ff599ce77cec77", "contract")
    require(implementation["constructor_implementation_identity"] == "bdf48e9942f097f0259831c0f2f611e50644cdbe7179a2dc7d990bf9ab2b5493", "implementation")
    require(provider["realization_provider_implementation_identity"] == "36b3669acb5e7d2b772ad6d8a912f4cdbfea8f58e3c45e72cafcd206336afce8", "provider")
    require(emitter["candidate_emitter_implementation_identity"] == "e325bd20ba1f58bbc48a6e749dc7a505e5522e4ff11c798855e8d530dae113d4", "emitter")
    require(compatibility["compatibility_identity"] == "fda3e7f2bea30b8429fb4f93415c85b81a3322595be6eae7542a367d5f0ad9ee", "compatibility")
    require(compatibility_audit["audit_identity"] == "178b880eb29d58b5ce93145e160d4cb122c191cbe813f9da85c255e0dd1e42d8", "compatibility audit")
    require(compatibility["verdict"] == "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_2_NO_RELEASE", "compatibility verdict")
    require(proposal["selected_proposition_id"] == "P3" and len(proposal["closed_factual_authority_envelope"]["propositions"]) == 1, "P3 only")
    context = proposal["exact_authorized_visible_context_utf8"].encode()
    require(hashlib.sha256(context).hexdigest() == proposal["selected_supporting_span_sha256"], "span")
    plan = compatibility["proposition_derived_abstract_plan_compatibility"]
    require(len(plan) == 3 and sum(len(n["predecessor_node_ids"]) for n in plan) == 2, "three-node/two-edge plan")
    require(all(not n["introduces_ids"] or n["node_id"] != "RESULT" for n in plan), "terminal")
    require(static_audit["constructor_invocations"] == static_audit["realizer_invocations"] == static_audit["emitter_invocations"] == 0, "zero invocation")
    require(static_audit["candidate_surfaces_created_or_persisted"] == 0, "zero candidates")

    denyset = build_denyset()
    require(len(denyset["candidate_sources"]) == 9 and denyset["blind_reserve_accessed"] is False, "denyset scope")
    core = dict(proposal)
    superseded = core.pop("constructor_facing_packet_identity")
    mapping_commitment = core.pop("mapping_commitment")
    core["authority_matrix"].pop("g04b_pool_certification")
    require(core.pop("constructor_implementation_identity").startswith("UNASSIGNED_"), "implementation placeholder")
    require(core.pop("fragment_denyset_identity").startswith("UNASSIGNED_"), "denyset placeholder")
    require(core.pop("constructor_v5_2_source_compatibility_evaluated") is False, "compatibility placeholder")
    core.pop("realization_plan")
    core.pop("witness_topology")
    typed_plan_commitment = seal("B2_PILOT10_P3_PROPOSITION_DERIVED_TYPED_PLAN_V5_2", plan)
    core.update({"constructor_contract_identity": contract["constructor_contract_identity"],
                 "constructor_implementation_identity": implementation["constructor_implementation_identity"],
                 "realization_provider_identity": provider["realization_provider_implementation_identity"],
                 "candidate_emitter_identity": emitter["candidate_emitter_implementation_identity"],
                 "constructor_static_audit_identity": static_audit["static_audit_identity"],
                 "constructor_source_compatibility_identity": compatibility["compatibility_identity"],
                 "proposition_derived_typed_plan": plan, "typed_plan_commitment": typed_plan_commitment,
                 "pre_emission_governance_identity": governance["governance_identity"],
                 "pre_emission_conformance_schema_identity": schema["schema_identity"],
                 "pre_emission_enforcement_identity": enforcement["enforcement_implementation_identity"],
                 "fragment_denyset_identity": denyset["fragment_denyset_identity"],
                 "status": "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION"})
    packet_id = seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_PACKET_G02B_V5_2", core)
    packet = {**core, "constructor_facing_packet_identity": packet_id}
    transport = {"constructor_role": "CONSTRUCTOR", "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_PATHLESS_CAPABILITY",
                 "repository_access": False, "filesystem_path_access": False, "sibling_artifact_discovery": False,
                 "environment_inheritance": False, "command_line_payload": False, "process_handle_inheritance": False,
                 "metadata_enumeration": False, "cache_or_temp_file": False, "import_time_repository_access": False,
                 "logs_contain_packet_or_mapping": False, "exceptions_contain_packet_or_mapping": False, "network_access": False,
                 "constructor_invocation_authorized": False, "provider_invocation_authorized": False,
                 "emitter_invocation_authorized": False}
    release_core = {"constructor_facing_packet_identity": packet_id,
                    "packet_seal_namespace": "B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_PACKET_G02B_V5_2",
                    "immutable_assignment_identity": packet["immutable_assignment_identity"],
                    "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"], "selected_proposition_id": "P3",
                    "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
                    "authorized_visible_context_sha256": packet["authorized_visible_context_sha256"], "partition": "DEVELOPMENT",
                    "creative_premise_family_id": "UNASSIGNED", "constructor_contract_identity": contract["constructor_contract_identity"],
                    "constructor_implementation_identity": implementation["constructor_implementation_identity"],
                    "realization_provider_identity": provider["realization_provider_implementation_identity"],
                    "candidate_emitter_identity": emitter["candidate_emitter_implementation_identity"],
                    "constructor_source_compatibility_identity": compatibility["compatibility_identity"],
                    "typed_plan_commitment": typed_plan_commitment, "fragment_denyset_identity": denyset["fragment_denyset_identity"],
                    "pre_emission_governance_identity": governance["governance_identity"],
                    "pre_emission_conformance_schema_identity": schema["schema_identity"],
                    "pre_emission_enforcement_identity": enforcement["enforcement_implementation_identity"],
                    "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
                    "single_use_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED", "constructor_invocation_authorized": False}
    release_id = seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_ACCESS_RELEASE_V5_2", release_core)
    release = {"schema_name": "batch2-development-pilot10-constructor-access-release-v5-2", "schema_version": "5.2.0",
               "release_core": release_core, "release_identity": release_id, "constructor_packet": packet,
               "constructor_visible_object_set": ["CONSTRUCTOR_PACKET_EXACT_BYTES"], "transport_policy": transport}
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"LITERALIZATION", rb"MISDIRECTION", rb"ESCALATION",
                 rb"PERSONIFICATION", rb"mechanism_id", rb"mechanism_name", rb"close_alternative", rb"mapping_commitment",
                 rb"BLIND_EVALUATION", rb"owner.preference", rb"G04B", rb"pool"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"leakage: {hits}")
    require(packet["candidate_surface"] is None and packet["constructor_invoked"] is False, "construction")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    require(all(value is False for key, value in transport.items() if key not in {"constructor_role", "packet_delivery"}), "transport")
    audit_core = {"schema_name": "batch2-development-pilot10-g02b-preconstruction-audit-v5-2", "schema_version": "5.2.0",
                  "reviewed_commit": COMMIT, "superseded_packet_identity": superseded, "constructor_facing_packet_identity": packet_id,
                  "release_identity": release_id, "contract_implementation_provider_emitter_binding": "PASS_EXACT_V5_2",
                  "source_compatibility_binding": "PASS_EXACT", "selected_proposition_and_span_binding": "PASS_EXACT_P3_ONLY",
                  "typed_plan_binding": "PASS_EXACT_THREE_NODES_TWO_EDGES_NO_UNBOUND_OPERANDS",
                  "pre_emission_conformance_enforcement_binding": "PASS_EXACT_MANDATORY_BEFORE_EMISSION",
                  "fragment_denyset_binding": f"PASS_EXACT_{len(denyset['candidate_sources'])}_NONBLIND_DEVELOPMENT_FAMILIES_{len(denyset['normalized_ngram_sha256'])}_HASHES",
                  "blind_reserve_access": "NONE", "packet_integrity": "PASS", "pathless_single_object_isolation": "PASS",
                  "environment_cli_process_log_cache_temp_repository_network_access": "PASS_NONE", "sealed_mapping_access": "DENIED",
                  "label_and_pool_token_scan": "PASS_ZERO_HITS", "removed_mapping_commitment_sha256": hashlib.sha256(mapping_commitment.encode()).hexdigest(),
                  "constructor_invocations": 0, "provider_invocations": 0, "emitter_invocations": 0, "candidate_surfaces": 0,
                  "creative_premise_family_id": "UNASSIGNED", "capability_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED",
                  "downstream_authority_granted": False, "deterministic_blockers_remaining": [],
                  "verdict": "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT10_G02B_AUDIT_V5_2", audit_core)}
    write("humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-2.json", denyset)
    write("humor-mechanics-batch2-development-pilot10-constructor-facing-assignment-g02b-v5-2.json", packet)
    write("humor-mechanics-batch2-development-pilot10-constructor-access-release-v5-2.json", release)
    write("humor-mechanics-batch2-development-pilot10-g02b-preconstruction-audit-v5-2.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "constructor_facing_packet_identity": packet_id,
                      "release_identity": release_id, "audit_identity": audit["audit_identity"],
                      "fragment_denyset_identity": denyset["fragment_denyset_identity"],
                      "fragment_hashes": len(denyset["normalized_ngram_sha256"]), "constructor_invocations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
