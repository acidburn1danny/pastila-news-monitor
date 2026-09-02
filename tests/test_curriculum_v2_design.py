from pastila_scout.curriculum_v2_design import BATCHES,MAX_ADMITTED,MAX_CANDIDATES,PER_CLASS_BUDGET,STOP_CONDITIONS,audit_structure,dry_qualify
from pastila_scout.relation_contract_v2 import SPECS

def test_exact_17_classes_assigned_once_by_semantic_rationale():
 flat=[x for batch in BATCHES.values() for x in batch]
 assert len(BATCHES)==5 and len(flat)==17 and set(flat)==set(SPECS) and len(flat)==len(set(flat))

def test_budgets_are_bounded_and_not_combinatorial():
 assert MAX_CANDIDATES==68 and MAX_ADMITTED==48 and set(PER_CLASS_BUDGET)==set(SPECS)
 assert max(PER_CLASS_BUDGET.values())==4

def test_dry_positive_17_of_17_and_negative_17_of_17():
 positive,negative=dry_qualify()
 assert all(v["verdict"]=="PASS_ZERO_FAMILY_DIAGNOSTIC" for v in positive.values())
 assert all(v["verdict"]=="FAIL_CLOSED" for v in negative.values())

def test_no_chain_slot_or_repeated_template_identity():
 a=audit_structure();assert a["distinct_identities"]==17 and a["distinct_primitives"]==17 and a["chain_slot_fields"]==0

def test_evidence_type_does_not_collapse():
 assert audit_structure()["evidence_types"]>=10

def test_diagnostic_stops_cover_suspicious_extremes_and_leakage():
 assert {"FIRST_SUBSTANTIAL_BATCH_ZERO_PERCENT_ADMISSION","UNIVERSAL_PASS","UNIVERSAL_IDENTICAL_REJECTION_REASON","AUTHOR_ADJUDICATOR_LEAKAGE"}<=set(STOP_CONDITIONS)
