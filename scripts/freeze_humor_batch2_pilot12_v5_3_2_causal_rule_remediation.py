"""Freeze the source-only Pilot 12 causal-rule root cause and narrow V5.3.2 guard."""
import hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"docs/artifacts"
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def seal(n,v): return hashlib.sha256(canonical({"namespace":n,"value":v})).hexdigest()
def write(name,value):
    path=ART/name; path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n"); return path

def main():
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    trace={"validated_plan":"RESULT predecessor L2 requires RULE_L2_DESTINATION_BOUND_STATE_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT",
      "realized_surface_relation":"Statutul de transport confirmat closes the transport rule; actor/predicate/patient topology preserved",
      "witness_extraction":"RESULT roles and affordances preserved; provider supplied RULE_L2_OUTPUT_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT",
      "semantic_comparison":"exact tuple comparison against frozen edge-derived rule",
      "first_failed_predicate":"RESULT.predecessor_causal_rule_ids == expected_rules"}
    analysis_core={"schema_name":"pilot12-v5-3-1-causal-rule-root-cause-v1","pilot":12,
      "verdict":"ROOT_CAUSE_CONFIRMED_AT_PROVIDER_CAUSAL_RULE_WITNESS_BINDING_BOUNDARY",
      "exact_causal_boundary":"V5_3_1_PROVIDER_LEXICALIZATION_TO_SURFACE_SEMANTIC_WITNESS_CAUSAL_RULE_METADATA",
      "first_divergence_trace":trace,"planned_rule":"RULE_L2_DESTINATION_BOUND_STATE_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT",
      "realized_rule":"RULE_L2_OUTPUT_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT","first_divergent_node":"RESULT","edge":"L2_TO_RESULT",
      "actor_patient_predicate_roles_affordances":"PRESERVED","surface_semantic_role":"NOT_CAUSAL",
      "coordinate_alignment":"NOT_REACHED_AND_NON_CAUSAL","romanian_syntax_or_morphology":"NON_CAUSAL",
      "static_semantic_plan":"CORRECT_AND_NON_CAUSAL","classification":"GENUINE_PROVIDER_METADATA_DRIFT_NOT_EQUIVALENCE_ERROR",
      "pilot12_evidence_identity":"a08ffd997e6304e4d405cc8a3a74d2210fcd46327e923b18ecbf0c8a8164727b"}
    analysis={**analysis_core,"analysis_identity":seal("B2_PILOT12_V5_3_1_CAUSAL_RULE_ROOT_CAUSE_V1",analysis_core)}
    write("humor-mechanics-batch2-development-pilot12-v5-3-1-causal-rule-root-cause-v1.json",analysis)
    contract_core={"schema_name":"constructor-v5-3-2-frozen-causal-rule-binding-contract","requirements":["derive predecessor causal-rule IDs only from frozen edge witnesses","reject nonempty provider rule aliases that differ","preserve V5.3.1 coordinate and semantic enforcement","no fuzzy or semantic equivalence substitution"],"base_contract":"c4af75cd962802d0035d9de39e6d014f715d5b5f5b60fd690ea3761f289d99fc"}
    contract={**contract_core,"contract_identity":seal("B2_CONSTRUCTOR_V5_3_2_CAUSAL_RULE_BINDING_CONTRACT",contract_core)}; write("humor-mechanics-batch2-constructor-v5-3-2-causal-rule-binding-contract.json",contract)
    impl_raw=(ROOT/"src/pastila_scout/humor_batch2_development_constructor_v5_3_2_runtime.py").read_bytes()
    impl=seal("B2_CONSTRUCTOR_V5_3_2_IMPLEMENTATION",{"contract_identity":contract["contract_identity"],"source_sha256":hashlib.sha256(impl_raw).hexdigest()})
    regression_core={"schema_name":"pilot12-v5-3-2-causal-rule-regression","cases":{"REALIZED_RELATION_GENUINELY_DIFFERS_FROM_VALIDATED_PLAN":"FAIL_CLOSED","REALIZED_RELATION_SEMANTICALLY_EQUIVALENT_WITH_DETERMINISTIC_SURFACE_VARIATION":"ACCEPT_ONLY_COORDINATE_BOUND_EXPLICITLY_LICENSED_EQUIVALENCE","PILOT12_WRONG_CAUSAL_RULE_ALIAS":"FAIL_CLOSED_BEFORE_REALIZATION"}}
    regression={**regression_core,"regression_identity":seal("B2_PILOT12_V5_3_2_CAUSAL_RULE_REGRESSION",regression_core)}; write("humor-mechanics-batch2-development-pilot12-v5-3-2-causal-rule-regression.json",regression)
    audit_core={"schema_name":"pilot12-v5-3-2-causal-rule-remediation-audit","verdict":"PASS_SOURCE_ONLY_FROZEN_EDGE_DERIVED_CAUSAL_RULE_BINDING_ZERO_CONSTRUCTION_NO_RELEASE","analysis_identity":analysis["analysis_identity"],"contract_identity":contract["contract_identity"],"implementation_identity":impl,"regression_identity":regression["regression_identity"],"candidate_created":False,"capability_restored":False,"constructor_invocations":0}
    audit={**audit_core,"audit_identity":seal("B2_PILOT12_V5_3_2_CAUSAL_RULE_REMEDIATION_AUDIT",audit_core)}; write("humor-mechanics-batch2-development-pilot12-v5-3-2-causal-rule-remediation-audit.json",audit)
    print(json.dumps({"analysis_identity":analysis["analysis_identity"],"contract_identity":contract["contract_identity"],"implementation_identity":impl,"regression_identity":regression["regression_identity"],"audit_identity":audit["audit_identity"],"execution_commit":head},sort_keys=True))
if __name__=="__main__": main()
