"""Consume exactly one Pilot 11 V5.3 capability and freeze the observed result."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_constructor_access_v1 import ConstructorPacketCapabilityV1, prepare_development_constructor_access_v1
from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_3_runtime import (
    SemanticNodeLexicalization, emit_semantic_candidate_utf8, realize_semantic_typed_plan,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness, OperandSemanticSpec, PredicateSemanticSignature,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE_COMMIT = "766a59c9a4abd89cedffc401e62c7a9f347c32ca"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot11-constructor-access-release-v5-3.json"
RUNNER_PATH = "scripts/run_humor_batch2_development_pilot11_construction_once_v5_3.py"
CANDIDATE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot11-candidate01-v1.txt"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot11-construction-attempt01-v1.json"
SOURCE_HASHES = {
    "src/pastila_scout/humor_batch2_constructor_access_v1.py": "4f555bab5961055a2db3ffd6c61d8a2a337e32b4f205d50f5ed56f21a54cd7a8",
    "src/pastila_scout/humor_batch2_development_constructor_v5_3_runtime.py": "400997eea183e7d9cab1d57fc899a0f13a96453bc417cb4da4771a86779ffabf",
    "src/pastila_scout/humor_batch2_development_constructor_v5_3_semantic_enforcement.py": "a72eea6961d4ee47cfbce284a5c7bf794e11bab979c8c835b8e0dcd25d966709",
    "src/pastila_scout/humor_batch2_development_constructor_v5_2.py": "ec8ddecb00d64f96d5d8742befd270305f9a16be5d907eae19e33ecbdee280e1",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def lexicalizations() -> tuple[SemanticNodeLexicalization, ...]:
    return (
        SemanticNodeLexicalization(
            node_id="L1",
            clause=("Într-o fabrică imaginară, acceptarea și trimiterea recipientului pun în mișcare, "
                    "numai datorită ambelor verificări conforme, un ecou mecanic prins de recipient."),
            actor_surface="acceptarea și trimiterea recipientului", predicate_surface="pun în mișcare",
            patient_surface="ambele verificări conforme",
            produced_operand_surfaces=(("INVENTED_RELATION_1", "un ecou mecanic prins de recipient"),),
            terminal_result=False,
            actor_semantic_roles=("CONDITIONED_DISPOSITION_RELATION",),
            actor_affordances=("LICENSE_LOCAL_NONFACTUAL_EXTENSION",),
            patient_semantic_roles=("CONDITION_STATE",), patient_affordances=("QUALIFY_DISPOSITION",),
            predecessor_causal_rule_ids=(),
        ),
        SemanticNodeLexicalization(
            node_id="L2",
            clause=("Un ecou mecanic prins de recipient ajunge odată cu el la linia de umplere și "
                    "declanșează în linia de umplere o copie a semnalului de expediere."),
            actor_surface="un ecou mecanic prins de recipient", predicate_surface="declanșează",
            patient_surface="linia de umplere",
            produced_operand_surfaces=(("INVENTED_RELATION_2", "o copie a semnalului de expediere"),),
            terminal_result=False,
            actor_semantic_roles=("LICENSED_PROCESS_STATE",),
            actor_affordances=("PROPAGATE_TO_AUTHORIZED_DESTINATION",),
            patient_semantic_roles=("TRANSFER_DESTINATION",), patient_affordances=("RECEIVE_CONTAINER",),
            predecessor_causal_rule_ids=("RULE_L1_OUTPUT_IS_REQUIRED_ACTOR_OF_L2",),
        ),
        SemanticNodeLexicalization(
            node_id="RESULT",
            clause=("O copie a semnalului de expediere reactivează acceptarea și trimiterea recipientului; "
                    "recipientul pornește din nou spre linia la care se află deja și rămâne prins într-o "
                    "navetă între expediere și sosire."),
            actor_surface="o copie a semnalului de expediere", predicate_surface="reactivează",
            patient_surface="acceptarea și trimiterea recipientului", produced_operand_surfaces=(),
            terminal_result=True,
            actor_semantic_roles=("DESTINATION_BOUND_PROCESS_STATE",),
            actor_affordances=("RESOLVE_AGAINST_SOURCE_RELATION",),
            patient_semantic_roles=("CONDITIONED_DISPOSITION_RELATION",),
            patient_affordances=("LICENSE_LOCAL_NONFACTUAL_EXTENSION",),
            predecessor_causal_rule_ids=("RULE_L2_OUTPUT_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT",),
        ),
    )


def main() -> None:
    if CANDIDATE.exists() or EVIDENCE.exists():
        raise SystemExit("Pilot 11 construction attempt already consumed")
    execution_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", RELEASE_COMMIT, execution_commit], cwd=ROOT).returncode:
        raise SystemExit("release commit is not an ancestor")
    runner = (ROOT / RUNNER_PATH).read_bytes()
    if committed(execution_commit, RUNNER_PATH) != runner:
        raise SystemExit("runner is not exact committed execution source")
    for path, expected in SOURCE_HASHES.items():
        raw = (ROOT / path).read_bytes()
        if committed(execution_commit, path) != raw or hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit(f"execution source identity: {path}")

    prepared = prepare_development_constructor_access_v1(release_bytes=committed(RELEASE_COMMIT, RELEASE_PATH))
    if prepared.release_identity != "377357f3e5dc85e044fc7a479d893c9643838cf599135cc52ea9c69467ae3fac":
        raise SystemExit("release identity")
    if prepared.packet_identity != "0a594d3b19b0c386e6dbe5a8d87d1a983524656c504d832826b20f16c93545b9":
        raise SystemExit("packet identity")
    capability = ConstructorPacketCapabilityV1(prepared)
    packet_bytes = capability.read_constructor_packet()
    packet = json.loads(packet_bytes)
    plan = tuple(TypedPlanNode(n["node_id"], n["bound_actor_id"], n["actor_role"], n["predicate_id"],
                               n["bound_patient_id"], tuple(n["predecessor_node_ids"]), tuple(n["introduces_ids"]),
                               n["source_provenance"], n["nonfactual_scope"])
                 for n in packet["proposition_derived_typed_plan"])
    specs = tuple(OperandSemanticSpec(s["operand_id"], s["entity_identity"], tuple(s["semantic_roles"]),
                                      tuple(s["affordances"]), tuple(s["provenance_operand_ids"]), s["reclassification_only"])
                  for s in packet["operand_semantic_specs"])
    signatures = tuple(PredicateSemanticSignature(s["predicate_id"], tuple(s["required_actor_roles"]),
                                                   tuple(s["required_patient_roles"]), tuple(s["required_actor_affordances"]),
                                                   tuple(s["required_patient_affordances"]))
                       for s in packet["predicate_semantic_signatures"])
    edges = tuple(EdgeNecessityWitness(e["predecessor_node_id"], e["successor_node_id"], e["produced_operand_id"],
                                       e["consumed_position"], e["explicit_licensing_rule"],
                                       e["counterfactual_dependency"], e["non_arbitrary"])
                  for e in packet["edge_necessity_witnesses"])

    provider_invocations = emitter_invocations = 0
    candidate_bytes = None
    failure_code = None
    try:
        provider_invocations = 1
        draft = realize_semantic_typed_plan(exact_source=packet["exact_authorized_visible_context_utf8"],
                                            typed_plan=plan, operand_specs=specs,
                                            predicate_signatures=signatures, edge_witnesses=edges,
                                            lexicalizations=lexicalizations())
        emitter_invocations = 1
        candidate_bytes = emit_semantic_candidate_utf8(typed_plan=plan, operand_specs=specs,
                                                        predicate_signatures=signatures, edge_witnesses=edges,
                                                        draft=draft)
        terminal = "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY_FRAGMENT_COLLISION_PENDING"
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        terminal = "FAIL_CLOSED_PRE_EMISSION_SEMANTIC_CONFORMANCE_NO_CANDIDATE"
        failure_code = f"{type(exc).__name__}: {exc}"

    hidden_tokens = (b"HMCV1-", b"mechanism_id", b"mechanism_name", b"answer_key", b"witness", b"operand",
                     b"predecessor", b"governance", b"conformance", b"semantic plan")
    hidden = candidate_bytes is not None and any(token.lower() in candidate_bytes.lower() for token in hidden_tokens)
    conformance_pass = candidate_bytes is not None and not hidden
    if candidate_bytes is not None:
        candidate_bytes.decode("utf-8")
        candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
        candidate_id = seal("B2_DEVELOPMENT_PILOT11_CANDIDATE_V1", {
            "constructor_packet_identity": prepared.packet_identity, "raw_surface_sha256": candidate_sha,
            "attempt_ordinal": 1, "partition": "DEVELOPMENT"})
        creative_family = seal("B2_CREATIVE_PREMISE_FAMILY_V1", {
            "sealed_assignment_identity": packet["immutable_assignment_identity"],
            "source_commitment": packet["closed_factual_authority_envelope"]["source_commitment"],
            "candidate_identity": candidate_id})
        creative_marker = seal("B2_CREATIVE_MARKER_FAMILY_V5_3", {
            "candidate_identity": candidate_id, "construction_revision_family_id": packet["construction_revision_family_id"]})
        CANDIDATE.write_bytes(candidate_bytes)
    else:
        candidate_sha = candidate_id = None
        creative_family = creative_marker = "UNASSIGNED"

    core = {
        "schema_name": "batch2-development-pilot11-construction-attempt01-v1", "schema_version": "1.0.0",
        "execution_source_commit": execution_commit, "execution_source_sha256": {key: value for key, value in SOURCE_HASHES.items()},
        "release_commit": RELEASE_COMMIT, "release_identity": prepared.release_identity,
        "constructor_facing_packet_identity": prepared.packet_identity,
        "constructor_contract_identity": packet["constructor_contract_identity"],
        "constructor_implementation_identity": packet["constructor_implementation_identity"],
        "realization_provider_identity": packet["realization_provider_identity"],
        "candidate_emitter_identity": packet["candidate_emitter_identity"],
        "constructor_source_compatibility_identity": packet["constructor_source_compatibility_identity"],
        "constructor_source_compatibility_audit_identity": packet["constructor_source_compatibility_audit_identity"],
        "semantic_plan_commitment": packet["semantic_plan_commitment"],
        "pre_emission_governance_identity": packet["pre_emission_governance_identity"],
        "pre_emission_conformance_schema_identity": packet["pre_emission_conformance_schema_identity"],
        "pre_emission_enforcement_identity": packet["pre_emission_enforcement_identity"],
        "fragment_denyset_identity": packet["fragment_denyset_identity"], "selected_proposition_id": "P3",
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "attempt": {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1,
                    "provider_invocations": provider_invocations, "emitter_invocations": emitter_invocations},
        "terminal_classification": terminal, "failure_code": failure_code,
        "pre_emission_semantic_conformance": {
            "verdict": "PASS_PRE_EMISSION_V5_3_SEMANTIC_CONFORMANCE" if conformance_pass else "FAIL_CLOSED_NO_EMISSION",
            "causal_nodes_realized": 3 if conformance_pass else None, "causal_nodes_required": 3,
            "causal_edges_realized": 2 if conformance_pass else None, "causal_edges_required": 2,
            "typed_operand_continuity": "PASS_EXACT" if conformance_pass else "NOT_ESTABLISHED",
            "predicate_argument_role_compatibility": "PASS_3_OF_3" if conformance_pass else "NOT_ESTABLISHED",
            "action_and_affordance_compatibility": "PASS" if conformance_pass else "NOT_ESTABLISHED",
            "entity_identity_preservation": "PASS_NO_RECLASSIFICATION_USED" if conformance_pass else "NOT_ESTABLISHED",
            "privileged_role_or_affordance_from_reclassification": "ABSENT" if conformance_pass else "NOT_ESTABLISHED",
            "counterfactual_dependency_and_non_arbitrariness": "PASS_2_OF_2" if conformance_pass else "NOT_ESTABLISHED",
            "terminal_edge_equal_semantic_strength": "PASS" if conformance_pass else "NOT_ESTABLISHED",
            "terminal_result_witnesses": 1 if conformance_pass else 0,
            "omitted_collapsed_summarized_placeholder_or_asserted_relations": "ABSENT" if conformance_pass else "NOT_ESTABLISHED",
            "instruction_governance_plan_meta_language_transfer": "ABSENT" if conformance_pass else "NOT_ESTABLISHED",
            "validation_preceded_candidate_persistence_and_emission": True},
        "candidate_identity": candidate_id, "candidate_surface_sha256": candidate_sha,
        "candidate_surface_byte_length": len(candidate_bytes) if candidate_bytes else None,
        "candidate_surface_present": candidate_bytes is not None, "candidate_partition": "DEVELOPMENT" if candidate_id else None,
        "creative_premise_family_id": creative_family, "creative_marker_family_id": creative_marker,
        "capability": {"state": "CONSUMED_1_OF_1", "single_use": True, "reads": 1, "remaining": 0,
                       "constructor_visible_sha256": hashlib.sha256(packet_bytes).hexdigest()},
        "constructor_exposure_reconciliation": {"authorized_packet_only": True, "exact_selected_source_span_only": True,
            "sealed_mapping_exposed": False, "blind_material_exposed": False, "repository_or_filesystem_access_by_constructor": False,
            "environment_or_cli_access": False, "logs_cache_temp_process_or_network_access": False,
            "hidden_mechanism_or_governance_metadata_introduced": bool(hidden)},
        "post_construction_g02b_verdict": "PASS" if not hidden else "FAIL_HIDDEN_METADATA",
        "fragment_collision_evaluation": "NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02",
        "g02_eligibility": False, "retry_authority": False, "repair_authority": False, "selection_authority": False,
        "authority_matrix": {key: False for key in ("fragment_collision_evaluation", "g02", "g02c", "g03",
            "romanian_naturalness", "voice", "owner_review", "g04b_pool_certification", "model_exposure", "training",
            "runtime_integration", "production_routing")},
    }
    evidence = {**core, "evidence_identity": seal("B2_DEVELOPMENT_PILOT11_CONSTRUCTION_ATTEMPT01_V1", core)}
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"terminal_classification": terminal, "candidate_identity": candidate_id,
                      "candidate_surface_sha256": candidate_sha, "candidate_bytes": len(candidate_bytes) if candidate_bytes else None,
                      "creative_premise_family_id": creative_family, "creative_marker_family_id": creative_marker,
                      "pre_emission_conformance": evidence["pre_emission_semantic_conformance"]["verdict"],
                      "capability_state": "CONSUMED_1_OF_1", "constructor_invocations": 1,
                      "provider_invocations": provider_invocations, "emitter_invocations": emitter_invocations,
                      "evidence_identity": evidence["evidence_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
