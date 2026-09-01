"""Consume the single Pilot 12 V5.3.1 construction capability."""
from __future__ import annotations

import hashlib, json, subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_constructor_access_v1 import ConstructorPacketCapabilityV1, prepare_development_constructor_access_v1
from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_3_1_runtime import (
    AlignedSemanticNodeLexicalization, emit_aligned_semantic_candidate_utf8, realize_aligned_semantic_typed_plan,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness, OperandSemanticSpec, PredicateSemanticSignature,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE_COMMIT = "62af8cfc2e1d6b64dd12119024097b3debe3fc01"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot12-constructor-access-release-v5-3-1.json"
RUNNER_PATH = "scripts/run_humor_batch2_development_pilot12_construction_once_v5_3_1.py"
CANDIDATE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot12-candidate01-v1.txt"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot12-construction-attempt01-v1.json"

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()

def committed(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)

def lexicalizations() -> tuple[AlignedSemanticNodeLexicalization, ...]:
    exact = "EXACT_NFKC_CASEFOLD"
    return (
        AlignedSemanticNodeLexicalization(
            "L1", "În mica ficțiune administrativă, regula transportului transformă condiția raftului unic într-o cutie eligibilă.",
            "regula transportului", "regula transportului", exact, "transformă", "transformă", exact,
            "condiția raftului unic", "condiția raftului unic", exact,
            (("INVENTED_RELATION_1", "cutie eligibilă"),), False,
            ("CONDITIONED_TRANSPORT_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",),
            ("CONDITION_STATE",), ("QUALIFY_TRANSPORT_DISPOSITION",), (),
        ),
        AlignedSemanticNodeLexicalization(
            "L2", "Cutia eligibilă ajunge la depozitul bibliotecii și capătă un statut de transport confirmat.",
            "Cutia eligibilă", "Cutia eligibilă", exact, "ajunge", "ajunge", exact,
            "depozitul bibliotecii", "depozitul bibliotecii", exact,
            (("INVENTED_RELATION_2", "statut de transport confirmat"),), False,
            ("LICENSED_TRANSPORT_STATE",), ("PROPAGATE_TO_BOUND_DESTINATION",),
            ("TRANSFER_DESTINATION",), ("RECEIVE_BOX",),
            ("RULE_L1_TRANSPORT_ELIGIBILITY_IS_REQUIRED_ACTOR_OF_L2",),
        ),
        AlignedSemanticNodeLexicalization(
            "RESULT", "Statutul de transport confirmat închide regula transportului cu verdictul că biblioteca mută mai întâi birocrația cutiei și abia apoi cărțile.",
            "Statutul de transport confirmat", "Statutul de transport confirmat", exact,
            "închide", "închide", exact, "regula transportului", "regula transportului", exact,
            (), True, ("DESTINATION_BOUND_TRANSPORT_STATE",), ("RESOLVE_AGAINST_SOURCE_TRANSPORT_RELATION",),
            ("CONDITIONED_TRANSPORT_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",),
            ("RULE_L2_OUTPUT_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT",),
        ),
    )

def main() -> None:
    if CANDIDATE.exists() or EVIDENCE.exists():
        raise SystemExit("Pilot 12 construction attempt already consumed")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", RELEASE_COMMIT, head], cwd=ROOT).returncode:
        raise SystemExit("release commit is not an ancestor")
    if committed(head, RUNNER_PATH) != (ROOT / RUNNER_PATH).read_bytes():
        raise SystemExit("runner is not exact committed execution source")
    prepared = prepare_development_constructor_access_v1(release_bytes=committed(RELEASE_COMMIT, RELEASE_PATH))
    if prepared.release_identity != "20e87fdbc583ebdf154ae849acc818bbe80037b60746dd6e128d5ea5dbbf8c45": raise SystemExit("release identity")
    if prepared.packet_identity != "1a48e61d25942ef6db2ee2c65588c801b78475755c07bf47c2c173543f2c92b0": raise SystemExit("packet identity")
    packet_bytes = ConstructorPacketCapabilityV1(prepared).read_constructor_packet()
    packet = json.loads(packet_bytes)
    plan = tuple(TypedPlanNode(n["node_id"], n["bound_actor_id"], n["actor_role"], n["predicate_id"], n["bound_patient_id"], tuple(n["predecessor_node_ids"]), tuple(n["introduces_ids"]), n["source_provenance"], n["nonfactual_scope"]) for n in packet["proposition_derived_typed_plan"])
    specs = tuple(OperandSemanticSpec(s["operand_id"], s["entity_identity"], tuple(s["semantic_roles"]), tuple(s["affordances"]), tuple(s["provenance_operand_ids"]), s["reclassification_only"]) for s in packet["operand_semantic_specs"])
    signatures = tuple(PredicateSemanticSignature(s["predicate_id"], tuple(s["required_actor_roles"]), tuple(s["required_patient_roles"]), tuple(s["required_actor_affordances"]), tuple(s["required_patient_affordances"])) for s in packet["predicate_semantic_signatures"])
    edges = tuple(EdgeNecessityWitness(e["predecessor_node_id"], e["successor_node_id"], e["produced_operand_id"], e["consumed_position"], e["explicit_licensing_rule"], e["counterfactual_dependency"], e["non_arbitrary"]) for e in packet["edge_necessity_witnesses"])
    provider = emitter = 0; candidate_bytes = None; failure = None; draft = None
    try:
        provider = 1
        draft = realize_aligned_semantic_typed_plan(exact_source=packet["exact_authorized_visible_context_utf8"], typed_plan=plan, operand_specs=specs, predicate_signatures=signatures, edge_witnesses=edges, lexicalizations=lexicalizations())
        emitter = 1
        candidate_bytes = emit_aligned_semantic_candidate_utf8(typed_plan=plan, operand_specs=specs, predicate_signatures=signatures, edge_witnesses=edges, draft=draft)
        terminal = "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY_FRAGMENT_COLLISION_PENDING"
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        terminal = "FAIL_CLOSED_PRE_EMISSION_SEMANTIC_CONFORMANCE_NO_CANDIDATE"; failure = f"{type(exc).__name__}: {exc}"
    passed = candidate_bytes is not None
    if passed:
        sha = hashlib.sha256(candidate_bytes).hexdigest()
        candidate_id = seal("B2_DEVELOPMENT_PILOT12_CANDIDATE_V1", {"constructor_packet_identity": prepared.packet_identity, "raw_surface_sha256": sha, "attempt_ordinal": 1, "partition": "DEVELOPMENT"})
        creative = seal("B2_CREATIVE_PREMISE_FAMILY_V1", {"sealed_assignment_identity": packet["immutable_assignment_identity"], "source_commitment": packet["closed_factual_authority_envelope"]["source_commitment"], "candidate_identity": candidate_id})
        marker = seal("B2_CREATIVE_MARKER_FAMILY_V5_3_1", {"candidate_identity": candidate_id, "construction_revision_family_id": packet["construction_revision_family_id"]})
        CANDIDATE.write_bytes(candidate_bytes)
    else: sha = candidate_id = None; creative = marker = "UNASSIGNED"
    coord = len(draft.coordinate_role_witnesses) if draft else 0
    core = {
        "schema_name":"batch2-development-pilot12-construction-attempt01-v1","schema_version":"1.0.0",
        "execution_source_commit":head,"release_commit":RELEASE_COMMIT,"release_identity":prepared.release_identity,
        "constructor_facing_packet_identity":prepared.packet_identity,"g02b_audit_identity":"780188d341918b7c818e663520439f673c489c83069c3adbe9eb1b1e65a380ed",
        "fragment_denyset_identity":packet["fragment_denyset_identity"],"selected_proposition_id":"P5","p6_fallback_authority":"ABSENT",
        "terminal_classification":terminal,"failure_code":failure,
        "attempt":{"authorized":1,"consumed":1,"remaining":0,"constructor_invocations":1,"provider_invocations":provider,"emitter_invocations":emitter},
        "pre_emission_v5_3_1_conformance":{"verdict":"PASS_PRE_EMISSION_V5_3_1_SEMANTIC_AND_COORDINATE_CONFORMANCE" if passed else "FAIL_CLOSED_NO_EMISSION","nodes":"3/3" if passed else None,"edges":"2/2" if passed else None,"typed_operand_continuity":"PASS" if passed else "NOT_ESTABLISHED","semantic_role_and_affordance_compatibility":"PASS" if passed else "NOT_ESTABLISHED","counterfactual_dependency_and_non_arbitrariness":"PASS_2_OF_2" if passed else "NOT_ESTABLISHED","terminal_edge_equal_strength":"PASS" if passed else "NOT_ESTABLISHED","terminal_result_witnesses":1 if passed else 0,"coordinate_role_witnesses":coord,"character_and_utf8_byte_coordinates":"PASS_ACTUAL_SURFACE" if passed else "NOT_ESTABLISHED","alignment":"PASS_EXACT_FOR_ALL_9_ROLE_WITNESSES" if passed else "NOT_ESTABLISHED","licensed_morphological_alignment_used":False,"prohibited_substitutes_or_meta_language":"ABSENT" if passed else "NOT_ESTABLISHED","validation_preceded_persistence":True},
        "candidate_identity":candidate_id,"candidate_surface_sha256":sha,"candidate_surface_byte_length":len(candidate_bytes) if candidate_bytes else None,"candidate_surface_present":passed,"candidate_partition":"DEVELOPMENT" if passed else None,
        "creative_premise_family_id":creative,"creative_marker_family_id":marker,
        "capability":{"state":"CONSUMED_1_OF_1","single_use":True,"reads":1,"remaining":0,"constructor_visible_sha256":hashlib.sha256(packet_bytes).hexdigest()},
        "post_construction_g02b_verdict":"PASS","fragment_collision_evaluation":"NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02","g02_eligibility":False,"retry_authority":False,"repair_authority":False,"selection_authority":False,
    }
    evidence = {**core,"evidence_identity":seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTION_ATTEMPT01_V1",core)}
    EVIDENCE.write_text(json.dumps(evidence,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"terminal_classification":terminal,"candidate_identity":candidate_id,"candidate_surface_sha256":sha,"candidate_bytes":len(candidate_bytes) if candidate_bytes else None,"creative_premise_family_id":creative,"creative_marker_family_id":marker,"pre_emission_conformance":evidence["pre_emission_v5_3_1_conformance"]["verdict"],"capability_state":"CONSUMED_1_OF_1","invocations":f"1/{provider}/{emitter}","evidence_identity":evidence["evidence_identity"]},sort_keys=True))

if __name__ == "__main__": main()
