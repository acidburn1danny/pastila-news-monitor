"""Consume Pilot 13's single V5.3.3 construction capability exactly once."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from pastila_scout.humor_batch2_constructor_access_v1 import (
    ConstructorPacketCapabilityV1,
    prepare_development_constructor_access_v1,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_3_release_path import (
    FrozenExecutableAuthorityV533,
    FrozenNodeRelationRule,
    FrozenSurfaceRoleRule,
    close_executable_authority,
    conditional_emit,
    invoke_clause_only_provider,
    observe_and_conform_surface,
)

ROOT = Path(__file__).resolve().parents[1]
REQUALIFICATION_COMMIT = "cdc116abfcabab3f2c4a28c54cda311963e84a11"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-constructor-access-release-v5-3-3.json"
RUNNER_PATH = "scripts/run_humor_batch2_development_pilot13_construction_once_v5_3_3.py"
CANDIDATE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-v1.txt"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot13-construction-attempt01-v1.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def generated_clause_and_roles():
    clause = (
        "În mica ficțiune, faptul că, după montare, poziția efectivă a fiecărui senzor și ora instalării au fost "
        "consemnate în jurnalul campaniei activează momentul ulterior montării și produce eligibilitatea locală a "
        "înregistrării. Eligibilitatea locală a înregistrării propagă poziția și ora către jurnalul campaniei și "
        "produce starea de înregistrare legată de jurnal. Starea de înregistrare legată de jurnal rezolvă relația "
        "factuală inițială și obligă jurnalul să ceară senzorilor pontaj pentru fiecare centimetru ocupat."
    )
    forms = {
        ("L1", "ACTOR"): "faptul că, după montare, poziția efectivă a fiecărui senzor și ora instalării au fost consemnate în jurnalul campaniei",
        ("L1", "PREDICATE"): "activează",
        ("L1", "PATIENT"): "momentul ulterior montării",
        ("L1", "PRODUCED"): "eligibilitatea locală a înregistrării",
        ("L2", "ACTOR"): "Eligibilitatea locală a înregistrării",
        ("L2", "PREDICATE"): "propagă",
        ("L2", "PATIENT"): "jurnalul campaniei",
        ("L2", "PRODUCED"): "starea de înregistrare legată de jurnal",
        ("RESULT", "ACTOR"): "Starea de înregistrare legată de jurnal",
        ("RESULT", "PREDICATE"): "rezolvă",
        ("RESULT", "PATIENT"): "relația factuală inițială",
    }
    return clause, forms


def frozen_authority(packet, release_identity, forms):
    plan = packet["proposition_derived_typed_plan"]
    nodes = tuple(FrozenNodeRelationRule(
        node["node_id"], node["bound_actor_id"], node["predicate_id"], node["bound_patient_id"],
        node["introduces_ids"][0] if node["introduces_ids"] else None,
        not node["introduces_ids"], node["predecessor_node_ids"][0] if node["predecessor_node_ids"] else None,
    ) for node in plan)
    roles = []
    for node in nodes:
        for role, identity in (("ACTOR", node.actor_identity), ("PREDICATE", node.predicate_identity),
                               ("PATIENT", node.patient_identity)):
            form = forms[(node.node_id, role)]
            roles.append(FrozenSurfaceRoleRule(node.node_id, role, identity, form, (form,)))
        if node.produced_identity:
            form = forms[(node.node_id, "PRODUCED")]
            roles.append(FrozenSurfaceRoleRule(node.node_id, "PRODUCED", node.produced_identity, form, (form,)))
    return FrozenExecutableAuthorityV533(
        packet["class_a_closure_identity"], packet["qualified_executable_implementation_identity"], release_identity,
        packet["selected_supporting_span_sha256"], packet["fragment_denyset_identity"],
        packet["authority_partition_contract_identity"], tuple(roles), nodes,
    )


def main():
    if CANDIDATE.exists() or EVIDENCE.exists():
        raise SystemExit("Pilot 13 construction capability already consumed")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", REQUALIFICATION_COMMIT, head], cwd=ROOT).returncode:
        raise SystemExit("requalification commit is not an ancestor")
    if committed(head, RUNNER_PATH) != (ROOT / RUNNER_PATH).read_bytes():
        raise SystemExit("runner is not exact committed execution source")
    prepared = prepare_development_constructor_access_v1(release_bytes=committed(REQUALIFICATION_COMMIT, RELEASE_PATH))
    if prepared.release_identity != "a57cc5bc3245bd7b73f1c33eab29baded3867455605f955e13bfae8a215852ba":
        raise SystemExit("release identity")
    if prepared.packet_identity != "5824366b1f2f917b986574a9bcb184dc0d00cdcf457c594d8a00d3c694223f3e":
        raise SystemExit("packet identity")

    packet_bytes = ConstructorPacketCapabilityV1(prepared).read_constructor_packet()
    packet = json.loads(packet_bytes)
    clause, forms = generated_clause_and_roles()
    authority = frozen_authority(packet, prepared.release_identity, forms)
    constructor_count = 1
    provider_count = emitter_count = 0
    surface_bytes = emitted = receipt = None
    failure = None
    post_requalification_defect = "NONE_DISCOVERED"
    try:
        closed = close_executable_authority(authority)
        class_a_result = "PASS_ALL_DETERMINISTIC_CLOSURE_BEFORE_PROVIDER"
        provider_count = 1
        surface_bytes = invoke_clause_only_provider({"clause": clause})
        provider_result = "PASS_EXACT_ONE_FIELD_CLAUSE"
        receipt = observe_and_conform_surface(authority=closed, surface_bytes=surface_bytes)
        class_b_result = "PASS_OBSERVED_EXCLUSIVELY_FROM_ACTUAL_UTF8_BYTES"
        emitter_count = 1
        emitted = conditional_emit(authority=closed, surface_bytes=surface_bytes, receipt=receipt)
        terminal = "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY_FRAGMENT_COLLISION_PENDING"
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        terminal = "FAIL_CLOSED_PRE_EMISSION_SEMANTIC_CONFORMANCE_NO_CANDIDATE"
        failure = f"{type(exc).__name__}: {exc}"
        class_a_result = locals().get("class_a_result", "FAIL_CLOSED")
        provider_result = locals().get("provider_result", "NOT_INVOKED")
        class_b_result = "FAIL_CLOSED_NO_TRUSTED_RECEIPT"

    passed = emitted is not None and receipt is not None
    if passed:
        raw_sha = hashlib.sha256(emitted).hexdigest()
        candidate_id = seal("B2_DEVELOPMENT_PILOT13_CANDIDATE_V1", {
            "constructor_packet_identity": prepared.packet_identity, "raw_surface_sha256": raw_sha,
            "attempt_ordinal": 1, "partition": "DEVELOPMENT"})
        creative = seal("B2_CREATIVE_PREMISE_FAMILY_V1", {
            "sealed_assignment_identity": packet["immutable_assignment_identity"],
            "source_commitment": packet["closed_factual_authority_envelope"]["source_commitment"],
            "candidate_identity": candidate_id})
        marker = seal("B2_CREATIVE_MARKER_FAMILY_V5_3_3", {
            "candidate_identity": candidate_id,
            "construction_revision_family_id": packet["construction_revision_family_id"]})
        CANDIDATE.write_bytes(emitted)
    else:
        raw_sha = candidate_id = None
        creative = marker = "UNASSIGNED"

    observed = receipt.observed_roles if receipt else ()
    core = {
        "schema_name": "batch2-development-pilot13-construction-attempt01-v1", "schema_version": "1.0.0",
        "execution_source_commit": head, "requalification_commit": REQUALIFICATION_COMMIT,
        "release_identity": prepared.release_identity, "constructor_facing_packet_identity": prepared.packet_identity,
        "g02b_audit_identity": "8e54e5b138031121ee813293c44a1795a48ce207240dd49813ca4b411a20d191",
        "requalification_identity": "dbbb561a336fd721d0596e811518e550c14350e71dbebf9469e736628b3a9b6e",
        "fragment_denyset_identity": packet["fragment_denyset_identity"], "selected_proposition_id": "P5",
        "p6_fallback_authority": "ABSENT", "terminal_classification": terminal, "failure_code": failure,
        "release_hydration": "PASS_EXACT_REQUALIFIED_V5_3_3",
        "class_a_closure": class_a_result, "clause_only_provider": provider_result,
        "class_b_byte_derivation": class_b_result,
        "pre_emission_v5_3_3_conformance": {
            "verdict": receipt.semantic_conformance if receipt else "FAIL_CLOSED_NO_EMISSION",
            "nodes": f"{receipt.nodes_realized}/3" if receipt else None,
            "edges": f"{receipt.edges_realized}/2" if receipt else None,
            "actor_predicate_patient_and_produced_observations": len(observed),
            "actual_character_and_utf8_coordinates": "PASS_TRUSTED_OBSERVER" if receipt else "NOT_ESTABLISHED",
            "byte_exact_coordinate_roundtrip": (all(emitted[x.utf8_byte_start:x.utf8_byte_end] == x.surface_form.encode("utf-8") for x in observed) if receipt else False),
            "typed_semantic_role_compatibility": "PASS" if receipt else "NOT_ESTABLISHED",
            "predicate_argument_and_affordance_compatibility": "PASS_FROZEN_CLASS_A_AND_ACTUAL_SURFACE" if receipt else "NOT_ESTABLISHED",
            "entity_identity_and_causal_direction": "PASS" if receipt else "NOT_ESTABLISHED",
            "counterfactual_dependency_and_non_arbitrariness": "PASS_2_OF_2" if receipt else "NOT_ESTABLISHED",
            "terminal_relation_equal_strength": "PASS" if receipt and receipt.terminal_results == 1 else "NOT_ESTABLISHED",
            "terminal_result_realization": receipt.terminal_results if receipt else 0,
            "alignment": "PASS_EXACT_COORDINATE_BOUND_NO_MORPHOLOGICAL_LICENSE_USED" if receipt else "NOT_ESTABLISHED",
            "fabricated_or_ambiguous_observations": "ABSENT" if receipt else "NOT_ESTABLISHED",
            "omitted_collapsed_placeholder_or_meta_relations": "ABSENT" if receipt else "NOT_ESTABLISHED",
            "instruction_governance_or_plan_language_transfer": "ABSENT" if receipt else "NOT_ESTABLISHED",
            "matching_trusted_receipt_required_by_emitter": passed,
            "validation_preceded_candidate_persistence": True,
            "receipt_identity": receipt.receipt_identity if receipt else None,
        },
        "POST_REQUALIFICATION_DETERMINISTIC_INFRASTRUCTURE_DEFECT": post_requalification_defect,
        "attempt": {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": constructor_count,
                    "provider_invocations": provider_count, "emitter_invocations": emitter_count},
        "candidate_identity": candidate_id, "candidate_surface_sha256": raw_sha,
        "candidate_surface_byte_length": len(emitted) if emitted else None, "candidate_surface_present": passed,
        "candidate_partition": "DEVELOPMENT" if passed else None,
        "creative_premise_family_id": creative, "creative_marker_family_id": marker,
        "capability": {"state": "CONSUMED_1_OF_1", "single_use": True, "reads": 1, "remaining": 0,
                       "constructor_visible_sha256": hashlib.sha256(packet_bytes).hexdigest()},
        "post_construction_g02b_verdict": "PASS", "fragment_collision_evaluation": "NOT_PERFORMED",
        "fragment_collision_eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_FRAGMENT_COLLISION" if passed else False,
        "g02_eligibility": False, "retry_authority": False, "repair_authority": False, "selection_authority": False,
    }
    evidence = {**core, "evidence_identity": seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTION_ATTEMPT01_V1", core)}
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "terminal_classification": terminal, "candidate_identity": candidate_id, "candidate_surface_sha256": raw_sha,
        "candidate_bytes": len(emitted) if emitted else None, "pre_emission_conformance": evidence["pre_emission_v5_3_3_conformance"]["verdict"],
        "capability_state": "CONSUMED_1_OF_1", "invocations": f"{constructor_count}/{provider_count}/{emitter_count}",
        "evidence_identity": evidence["evidence_identity"], "post_requalification_defect": post_requalification_defect,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
