"""Mechanism-neutral V5.3.3 G02C review for Pilot 13 candidate 01."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "96c5503c21309754596868bc0e652b5b191174b3"
PACKET_COMMIT = "42d9d2baf75ebf5bdd2287d20cbff6d90f8ea73a"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-g02-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-constructor-facing-assignment-g02b-v5-3-3.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_json(commit, path):
    return json.loads(git_bytes(commit, path))


def require(value, message):
    if not value:
        raise SystemExit(message)


def surface_span(text, value):
    start = text.index(value)
    end = start + len(value)
    return {"character_coordinates": [start, end],
            "utf8_byte_coordinates": [len(text[:start].encode()), len(text[:end].encode())],
            "sha256": hashlib.sha256(value.encode()).hexdigest()}


def main():
    receipt_path = ART / "humor-mechanics-batch2-development-pilot13-candidate01-g02c-conformance-receipt-v5-3-3.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot13-candidate01-g02c-review-v5-3-3.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C already frozen")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", G02_COMMIT, "HEAD"], cwd=ROOT).returncode == 0, "G02 commit")
    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    text = candidate.decode("utf-8")
    g02, packet = git_json(G02_COMMIT, G02_PATH), git_json(PACKET_COMMIT, PACKET_PATH)
    obligation = packet["unlabeled_operational_obligation"]
    require(g02["g02_verdict"] == "PASS" and g02["g02_receipt_identity"] == "885e62fadc3f2a4d2bd3e7e090a697c0f390cbf54d21b486d9b58afdffc7965f", "G02")
    require(g02["candidate_git_blob_oid_sha1"] == "9a643cff281455ee0b4c9772f9740175ab27753b", "candidate blob")
    require(hashlib.sha256(candidate).hexdigest() == "907392cd76554340b09ef27145256b45f3c1ae013f41f4e4503ea156dc546759", "candidate")
    require(packet["constructor_facing_packet_identity"] == "5824366b1f2f917b986574a9bcb184dc0d00cdcf457c594d8a00d3c694223f3e", "packet")
    require(packet["selected_proposition_id"] == "P5" and packet["unselected_proposition_or_fallback_authority"] == "ABSENT", "authority")
    require(obligation["obligation_instance_identity"] == "85b142a8988b99981d7a44c2c2665fce1b303a441663d3dc1b383e03ca773d3d", "obligation")

    anchor = "faptul că, după montare, poziția efectivă a fiecărui senzor și ora instalării au fost consemnate în jurnalul campaniei"
    node1 = "faptul că, după montare, poziția efectivă a fiecărui senzor și ora instalării au fost consemnate în jurnalul campaniei activează momentul ulterior montării și produce eligibilitatea locală a înregistrării"
    node2 = "Eligibilitatea locală a înregistrării propagă poziția și ora către jurnalul campaniei și produce starea de înregistrare legată de jurnal"
    terminal = "Starea de înregistrare legată de jurnal rezolvă relația factuală inițială și obligă jurnalul să ceară senzorilor pontaj pentru fiecare centimetru ocupat"
    for value in (anchor, node1, node2, terminal):
        require(value in text, "surface component")
    spans = {"selected_fact": surface_span(text, anchor), "node_L1": surface_span(text, node1),
             "node_L2": surface_span(text, node2), "node_RESULT": surface_span(text, terminal)}
    nodes = {
        "L1": {"material_presence": "PASS_MATERIALLY_INSTANTIATED", "actor": "exact P5 factual proposition",
            "predicate": "activates", "patient": "the post-installation moment", "produced_operand": "local recording eligibility",
            "semantic_role_compatibility": "FAIL_FACT_HAS_NO_ACTIVATION_AFFORDANCE_AND_TEMPORAL_MOMENT_IS_NOT_ACTIVATABLE_PATIENT",
            "causal_necessity": "FAIL_NO_LOCAL_RULE_MAKES_P5_PRODUCE_RECORDING_ELIGIBILITY"},
        "L2": {"material_presence": "PASS_MATERIALLY_INSTANTIATED", "actor": "local recording eligibility",
            "predicate": "propagates", "patient": "campaign log", "produced_operand": "log-bound recording state",
            "semantic_role_compatibility": "FAIL_ELIGIBILITY_STATE_HAS_NO_POSITION_TIME_PROPAGATION_CAPABILITY",
            "causal_necessity": "FAIL_L1_OUTPUT_DOES_NOT_ENTAIL_PROPAGATION_OR_LOG_BOUND_STATE"},
        "RESULT": {"material_presence": "PASS_MATERIALLY_INSTANTIATED", "actor": "log-bound recording state",
            "predicate": "resolves and obliges", "patient": "initial factual relation and campaign log",
            "produced_operand": "log demands sensor timesheets for occupied centimeters",
            "semantic_role_compatibility": "FAIL_STATE_LACKS_RESOLUTION_AUTHORITY_AND_CANNOT_OBLIGATE_LOG_OR_SENSORS",
            "causal_necessity": "FAIL_TERMINAL_RESULT_IS_LEXICALLY_ATTACHED_NOT_ENTAILED_BY_L2"},
    }
    edges = {
        "P5_TO_L1": {"material_presence": "PASS", "semantic_role_compatibility": "FAIL",
            "causal_necessity": "FAIL", "non_arbitrariness": "FAIL",
            "counterfactual": "Removing P5 wording removes the named actor but no stated rule makes that fact causally necessary for eligibility."},
        "L1_TO_L2": {"material_presence": "PASS", "semantic_role_compatibility": "FAIL",
            "causal_necessity": "FAIL", "non_arbitrariness": "FAIL",
            "counterfactual": "Eligibility is repeated as actor, but removing L1's production does not expose a rule licensing propagation."},
        "L2_TO_RESULT": {"material_presence": "PASS", "semantic_role_compatibility": "FAIL",
            "causal_necessity": "FAIL", "non_arbitrariness": "FAIL",
            "counterfactual": "The timesheet demand can be removed or replaced without contradicting the log-bound state."},
    }
    predicates = {
        "SELECTED_FACTUAL_ANCHOR_RECOVERABLE": True, "EVERY_REQUIRED_NODE_MATERIALLY_INSTANTIATED": True,
        "EVERY_REQUIRED_EDGE_MATERIALLY_INSTANTIATED": True, "EVERY_ACTOR_PATIENT_AND_PRODUCED_OPERAND_ROLE_COMPATIBLE": False,
        "EVERY_ACTING_OPERAND_HAS_REQUIRED_AFFORDANCE": False, "ENTITY_IDENTITY_LEXICALLY_CONTINUOUS": True,
        "NO_RECLASSIFICATION_DERIVES_PRIVILEGED_AFFORDANCE": False, "EVERY_EDGE_NECESSARY_AND_NON_ARBITRARY": False,
        "EXACTLY_ONE_TERMINAL_RESULT_RECOVERABLE": True, "TERMINAL_RELATION_CAUSALLY_SUPPORTED": False,
        "NO_PLACEHOLDER_SUMMARY_META_OR_INSTRUCTION_SUBSTITUTION": True, "QUALIFICATION_AND_FICTIONAL_SCOPE_CONTINUITY": True,
    }
    failure = {
        "classification": "FIRST_INVENTED_LINK_ROLE_AFFORDANCE_AND_CAUSAL_NECESSITY_FAILURE",
        "earliest_failed_link": "P5_TO_L1",
        "observed_gap": "The surface explicitly states the link but supplies no local rule under which the factual recording proposition can activate a temporal moment or produce eligibility.",
        "downstream_failures": ["L1_TO_L2_ROLE_AND_NECESSITY", "L2_TO_TERMINAL_ROLE_AUTHORITY_AND_NECESSITY"],
        "candidate_level_failure_not_infrastructure_defect": True, "candidate_repair_performed": False,
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot13-g02c-conformance-receipt-v5-3-3", "schema_version": "5.3.3",
        "candidate_identity": g02["candidate_identity"], "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": g02["candidate_git_blob_oid_sha1"],
        "constructor_facing_packet_identity": packet["constructor_facing_packet_identity"],
        "qualified_executable_implementation_identity": packet["qualified_executable_implementation_identity"],
        "semantic_plan_commitment": packet["semantic_plan_commitment"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "obligation_instance_identity": obligation["obligation_instance_identity"], "obligation_version": obligation["obligation_version"],
        "selected_proposition_id": "P5", "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "fragment_collision_receipt_identity": g02["fragment_collision_binding"]["receipt_identity"],
        "pre_emission_conformance_provenance": "PASS_PRESERVED_NOT_USED_AS_SUFFICIENT_G02C_EVIDENCE",
        "surface_components": spans, "independently_recovered_nodes": nodes, "independently_recovered_edges": edges,
        "required_predicates": predicates, "failure": failure, "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False, "candidate_bytes_unchanged": True,
        "verdict": "FAIL_FIRST_INVENTED_LINK_ROLE_AFFORDANCE_AND_CAUSAL_NECESSITY",
    }
    receipt_id = seal("B2_DEVELOPMENT_PILOT13_G02C_CONFORMANCE_RECEIPT_V5_3_3", receipt_core)
    receipt = {**receipt_core, "conformance_receipt_identity": receipt_id}
    review_core = {
        "schema_name": "batch2-development-pilot13-candidate-g02c-review-v5-3-3", "schema_version": "5.3.3",
        "candidate_identity": g02["candidate_identity"], "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "g02_commit": G02_COMMIT, "g02_receipt_identity": g02["g02_receipt_identity"],
        "conformance_receipt_identity": receipt_id, "predicate_verification": "FAIL_SEMANTIC_ROLE_AFFORDANCE_AND_CAUSAL_NECESSITY",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED", "sealed_mapping_accessed": False,
        "g03_performed": False, "candidate_modified": False, "g02c_verdict": receipt_core["verdict"],
        "disposition": "G02C_REJECTED_STOP_NO_REPAIR", "g03_eligibility": False,
        "POST_REQUALIFICATION_DETERMINISTIC_INFRASTRUCTURE_DEFECT": "NONE_CANDIDATE_LEVEL_FAILURE",
        "authority_matrix": {key: False for key in ("g03_mechanism_recovery", "g03b", "g03c",
            "romanian_naturalness", "voice_review", "repair", "rewrite", "regeneration", "additional_construction",
            "owner_review", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT13_G02C_REVIEW_V5_3_3", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02c_verdict": review["g02c_verdict"], "conformance_receipt_identity": receipt_id,
                      "g02c_review_identity": review["g02c_review_identity"], "g03_eligibility": False,
                      "next_action": "FREEZE_NONPOSITIVE_G02C_REJECTION_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
