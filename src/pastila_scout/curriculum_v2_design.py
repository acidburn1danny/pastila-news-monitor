"""Design-only Curriculum V2 dry qualification; creates no operational rules."""
from __future__ import annotations
from copy import deepcopy
from .relation_contract_v2 import SPECS, adjudicate, candidate_identity, evidence_identity
from .relation_contract_v2_qualification import candidate, evidence, reviews

BATCHES={
1:("PHYSICAL_ACTION","MOVEMENT_LOCATION","OBSERVATION_PERCEPTION","MEASUREMENT"),
2:("RECORDING_EVIDENTIARY","REPRESENTATIONAL","INFORMATION_TRANSFER","COMPARISON_VERIFICATION"),
3:("CLASSIFICATION_CONSTITUTIVE","LOGICAL_INFERENCE","TEMPORAL"),
4:("PROCEDURAL","NORMATIVE_AUTHORIZATION","NORMATIVE_OBLIGATION"),
5:("CAUSAL","TRIGGER","STATE_TRANSITION"),
}
PER_CLASS_BUDGET={name:4 for name in SPECS}
MAX_CANDIDATES=sum(PER_CLASS_BUDGET.values())
MAX_ADMITTED=48

STOP_CONDITIONS=(
"FIRST_SUBSTANTIAL_BATCH_ZERO_PERCENT_ADMISSION","UNIVERSAL_IDENTICAL_REJECTION_REASON",
"UNIVERSAL_PASS","EVIDENCE_TYPE_COLLAPSE","REPEATED_TEMPLATE_IDENTITY",
"SEMANTIC_DUPLICATE_RATE_GT_0_10","OVERLAP_CONFLICT_COUNT_GT_0",
"THREE_CONSECUTIVE_CANDIDATES_WITHOUT_SEMANTIC_NOVELTY","AUTHOR_ADJUDICATOR_LEAKAGE",
)

def positive_fixture(rc:str,ordinal:int=1):
 c=candidate(rc);c["operands"]=[f"{rc}_ACTOR_{ordinal}",f"{rc}_PATIENT_{ordinal}"];c["semantic_primitive"]=f"{rc}_GENERAL_PRIMITIVE_{ordinal}";c["candidate_identity"]=candidate_identity(c)
 es=evidence(c)
 return c,es,reviews(c,es)

def negative_fixture(rc:str):
 c,es,rs=positive_fixture(rc,99);es[0]["candidate_identity"]="0"*64;es[0]["evidence_identity"]=evidence_identity(es[0]);return c,es,rs

def dry_qualify():
 pos={};neg={}
 for rc in SPECS:
  c,e,r=positive_fixture(rc);pos[rc]=adjudicate(c,e,r)
  c,e,r=negative_fixture(rc);neg[rc]=adjudicate(c,e,r)
 return pos,neg

def audit_structure():
 fixtures=[positive_fixture(rc)[0] for rc in SPECS]
 identities={c["candidate_identity"] for c in fixtures}
 primitives={c["semantic_primitive"] for c in fixtures}
 evidence_types={SPECS[c["relation_class"]].evidence_kind for c in fixtures}
 return {"distinct_identities":len(identities),"distinct_primitives":len(primitives),"evidence_types":len(evidence_types),"chain_slot_fields":sum(any(k in c for k in ("anchor","intermediate","terminal_slot")) for c in fixtures)}
