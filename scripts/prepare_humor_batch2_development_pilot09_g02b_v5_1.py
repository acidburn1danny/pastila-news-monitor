"""Prepare and audit Pilot 09's uninvoked pathless G02B release decision."""

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
COMMIT = "93549976a469312e8c177e01a2a89ad819b36672"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def words(surface: str) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", surface).casefold(), flags=re.UNICODE)


def build_denyset() -> dict[str, Any]:
    sources, hashes = [], set()
    for pilot in range(1, 9):
        path = f"docs/artifacts/humor-mechanics-batch2-development-pilot{pilot:02d}-candidate01-v1.txt"
        raw = git_bytes(path)
        tokens = words(raw.decode("utf-8"))
        local = set()
        for size in range(3, 9):
            for index in range(len(tokens) - size + 1):
                local.add(hashlib.sha256(" ".join(tokens[index:index + size]).encode()).hexdigest())
        hashes.update(local)
        oid = subprocess.check_output(["git", "rev-parse", f"{COMMIT}:{path}"], cwd=ROOT, text=True).strip()
        sources.append({"path": path, "partition": "DEVELOPMENT_NONBLIND", "surface_sha256": hashlib.sha256(raw).hexdigest(),
                        "git_blob_oid_sha1": oid, "normalized_word_count": len(tokens), "normalized_ngram_hash_count": len(local)})
    core = {"schema_name": "batch2-nonblind-development-fragment-denyset-v5-1", "schema_version": "5.1.0",
            "source_commit": COMMIT, "eligible_corpus": "NONBLIND_DEVELOPMENT_ONLY", "blind_reserve_accessed": False,
            "candidate_sources": sources, "ngram_word_lengths": [3, 4, 5, 6, 7, 8],
            "normalization": "UNICODE_NFKC_CASEFOLD_ALPHANUMERIC_WORDS", "normalized_ngram_sha256": sorted(hashes),
            "complete_surface_text_included": False, "model_or_semantic_similarity_used": False}
    return {**core, "fragment_denyset_identity": seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_1", core)}


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    prior = load("docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-facing-rebalancing-assignment-proposal-v5.json")
    mapping = load("docs/artifacts/humor-mechanics-batch2-development-pilot09-sealed-rebalancing-assignment-v5.json")
    assignment_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot09-rebalancing-assignment-design-audit-v5.json")
    contract = load("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-1.json")
    implementation = load("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-1.json")
    static_audit = load("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-1-static-audit-v1.json")
    compatibility = load("docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-v5-1-source-compatibility-v1.json")
    compatibility_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-v5-1-source-compatibility-audit-v1.json")
    require(prior["constructor_facing_packet_identity"] == "2fc8967cb7fba1667524a8683c4d837afbb21dd6c7d6ae61b244ff8b9e6cb5c1", "proposal")
    require(mapping["sealed_assignment_identity"] == "735814216b914a8c3f86150261cff19efb77536126c3c4d13b2f38bd3c0590e1", "mapping")
    require(assignment_audit["audit_identity"] == "071c07ab33d3a1cc373c311381758eab7f3126031a244b51ec33abd8d16e5acd", "assignment audit")
    require(contract["constructor_contract_identity"] == "9b647d33dfa40171040fe6acf08b8b6dca6081c41c0f1f4428f910bfdfaa8a6b", "contract")
    require(implementation["constructor_implementation_identity"] == "c7134743e6b0e7c3ed7637bff3203f774159f192fef7a7b712e15d4d44a6f419", "implementation")
    require(static_audit["audit_identity"] == "7c304534fbe2ee6b526a4cc4582a243b685ab97f5694ef5524abdeb3e150de47", "static audit")
    require(compatibility["compatibility_identity"] == "6554798852137176e9d0b860523b1110da5ac279c9ceae456a99acc09f70a50d", "compatibility")
    require(compatibility_audit["audit_identity"] == "de9c7240fc19cda27c9b893e2ad6ab2151102078e9708f3f76af777a5041de62", "compatibility audit")
    require(static_audit["constructor_invocations"] == static_audit["candidate_surfaces_created"] == 0, "zero construction")
    require(prior["selected_proposition_id"] == "P5" and len(prior["closed_factual_authority_envelope"]["propositions"]) == 1, "P5")
    context = prior["exact_authorized_visible_context_utf8"].encode()
    require(hashlib.sha256(context).hexdigest() == prior["authorized_visible_context_sha256"] == prior["selected_supporting_span_sha256"], "span")
    denyset = build_denyset()
    require(len(denyset["candidate_sources"]) == 8 and denyset["blind_reserve_accessed"] is False, "denyset")
    core = dict(prior)
    superseded = core.pop("constructor_facing_packet_identity")
    mapping_commitment = core.pop("mapping_commitment")
    require(core["authority_matrix"].pop("g04b_pool_certification") is False, "pool")
    require(core.pop("constructor_implementation_identity").startswith("UNASSIGNED_"), "placeholder")
    require(core.pop("fragment_denyset_identity").startswith("UNASSIGNED_"), "denyset placeholder")
    require(core.pop("constructor_v5_source_compatibility_evaluated") is False, "compatibility placeholder")
    core.update({"constructor_contract_identity": contract["constructor_contract_identity"],
                 "constructor_implementation_identity": implementation["constructor_implementation_identity"],
                 "constructor_implementation_generation": "5.1",
                 "constructor_source_compatibility_identity": compatibility["compatibility_identity"],
                 "typed_plan_commitment": seal("B2_PILOT09_P5_TYPED_PLAN_COMMITMENT_V5_1", compatibility["proposition_derived_abstract_plan"]),
                 "fragment_denyset_identity": denyset["fragment_denyset_identity"],
                 "status": "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION"})
    packet_id = seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_PACKET_G02B_V5_1", core)
    packet = {**core, "constructor_facing_packet_identity": packet_id}
    transport = {"constructor_role": "CONSTRUCTOR", "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_PATHLESS_CAPABILITY",
                 "repository_access": False, "filesystem_path_access": False, "sibling_artifact_discovery": False,
                 "environment_inheritance": False, "command_line_payload": False, "process_handle_inheritance": False,
                 "metadata_enumeration": False, "cache_or_temp_file": False, "import_time_repository_access": False,
                 "logs_contain_packet_or_mapping": False, "exceptions_contain_packet_or_mapping": False, "network_access": False,
                 "constructor_invocation_authorized": False}
    release_core = {"constructor_facing_packet_identity": packet_id,
                    "packet_seal_namespace": "B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_PACKET_G02B_V5_1",
                    "immutable_assignment_identity": packet["immutable_assignment_identity"],
                    "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"], "selected_proposition_id": "P5",
                    "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
                    "authorized_visible_context_sha256": packet["authorized_visible_context_sha256"], "partition": "DEVELOPMENT",
                    "creative_premise_family_id": "UNASSIGNED", "constructor_contract_identity": contract["constructor_contract_identity"],
                    "constructor_implementation_identity": implementation["constructor_implementation_identity"],
                    "constructor_implementation_generation": "5.1", "constructor_source_compatibility_identity": compatibility["compatibility_identity"],
                    "typed_plan_commitment": packet["typed_plan_commitment"], "fragment_denyset_identity": denyset["fragment_denyset_identity"],
                    "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
                    "single_use_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED", "constructor_invocation_authorized": False}
    release_id = seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_ACCESS_RELEASE_V5_1", release_core)
    release = {"schema_name": "batch2-development-pilot09-constructor-access-release-v5-1", "schema_version": "5.1.0",
               "release_core": release_core, "release_identity": release_id, "constructor_packet": packet,
               "constructor_visible_object_set": ["CONSTRUCTOR_PACKET_EXACT_BYTES"], "transport_policy": transport}
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension", rb"LITERALIZATION", rb"MISDIRECTION", rb"ESCALATION", rb"PERSONIFICATION",
                 rb"mechanism_id", rb"mechanism_name", rb"close_alternative", rb"mapping_commitment", rb"BLIND_EVALUATION", rb"owner.preference", rb"G04B", rb"pool"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"leakage {hits}")
    require(packet["candidate_surface"] is None and packet["constructor_invoked"] is False, "construction")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    require(all(value is False for key, value in transport.items() if key not in {"constructor_role", "packet_delivery"}), "transport")
    audit_core = {"schema_name": "batch2-development-pilot09-g02b-preconstruction-audit-v5-1", "schema_version": "5.1.0",
                  "reviewed_commit": COMMIT, "superseded_packet_identity": superseded, "constructor_facing_packet_identity": packet_id,
                  "release_identity": release_id, "contract_implementation_compatibility_binding": "PASS_EXACT_V5_1",
                  "selected_proposition_and_span_binding": "PASS_EXACT_P5_ONLY", "typed_plan_binding": "PASS_EXACT_COMPATIBILITY_COMMITMENT",
                  "fragment_denyset_binding": f"PASS_EXACT_{len(denyset['candidate_sources'])}_NONBLIND_DEVELOPMENT_FAMILIES_{len(denyset['normalized_ngram_sha256'])}_HASHES",
                  "blind_reserve_access": "NONE", "packet_integrity": "PASS", "pathless_single_object_isolation": "PASS",
                  "environment_cli_process_log_cache_temp_repository_network_access": "PASS_NONE", "sealed_mapping_access": "DENIED",
                  "label_and_pool_token_scan": "PASS_ZERO_HITS", "removed_mapping_commitment_sha256": hashlib.sha256(mapping_commitment.encode()).hexdigest(),
                  "constructor_invocations": 0, "candidate_surfaces": 0, "creative_premise_family_id": "UNASSIGNED",
                  "capability_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED", "downstream_authority_granted": False,
                  "deterministic_blockers_remaining": [], "verdict": "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT09_G02B_AUDIT_V5_1", audit_core)}
    write("humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-1.json", denyset)
    write("humor-mechanics-batch2-development-pilot09-constructor-facing-assignment-g02b-v5-1.json", packet)
    write("humor-mechanics-batch2-development-pilot09-constructor-access-release-v5-1.json", release)
    write("humor-mechanics-batch2-development-pilot09-g02b-preconstruction-audit-v5-1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "constructor_facing_packet_identity": packet_id,
                      "release_identity": release_id, "audit_identity": audit["audit_identity"],
                      "fragment_denyset_identity": denyset["fragment_denyset_identity"], "constructor_invocations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
