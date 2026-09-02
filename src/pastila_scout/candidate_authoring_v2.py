"""Canonical evidence-first candidate authoring for frozen Curriculum V2.

The same functions serve dry qualification and later governed execution.  They
perform no persistence, admission, activation, or family access.
"""
from __future__ import annotations
import hashlib,json
from typing import Any,Iterable,Mapping
from .relation_contract_v2 import SPECS,candidate_identity,evidence_identity

EPHEMERAL=frozenset({"candidate_identity","batch","sequence","nonce","timestamp","label","author_identity","adjudicator_identity","filename"})

def _canonical(value:Any)->Any:
    if isinstance(value,Mapping):return {k:_canonical(v) for k,v in sorted(value.items()) if k not in EPHEMERAL}
    if isinstance(value,(list,tuple)):return [_canonical(v) for v in value]
    return value

def semantic_primitive_identity(candidate:Mapping[str,Any])->str:
    """Identity over substantive semantics only, excluding ephemeral metadata."""
    payload=_canonical(candidate)
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def evidence_basis_identity(basis:Mapping[str,Any])->str:
    return hashlib.sha256(json.dumps(_canonical(basis),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def author_from_basis(basis:Mapping[str,Any],*,author_identity:str,adjudicator_identity:str,metadata:Mapping[str,Any]|None=None):
    """Create evidence authority content first, then candidate and final bindings."""
    rc=str(basis.get("relation_class"));spec=SPECS.get(rc)
    if not spec:raise ValueError("unknown relation class")
    required={"semantic_basis","actor_class","patient_class","operands","claimed_result","scope","authority_provenance"}
    if required-set(basis):raise ValueError("incomplete independent semantic basis")
    if basis.get("origin_order")!="INDEPENDENT_BASIS_BEFORE_EVIDENCE_BEFORE_CANDIDATE":raise ValueError("evidence-first protocol bypass")
    if basis.get("chain_slot") is not None:raise ValueError("V1 chain-slot recurrence")
    if basis.get("generic_produced_state") is True:raise ValueError("unlicensed generic produced-state manufacturing")
    authority={"basis_identity":evidence_basis_identity(basis),"provenance_identity":basis["authority_provenance"],"canonical_semantic_content":_canonical(basis)}
    c={"relation_class":rc,"actor_class":basis["actor_class"],"patient_class":basis["patient_class"],"operands":list(basis["operands"]),"affordances":list(basis.get("affordances",spec.required_affordances)),"continuity":{"kind":spec.continuity,"binding":basis.get("continuity_binding")},"dependency_test":spec.dependency,"claimed_result":basis["claimed_result"],"scope":basis["scope"],"claimed_result_licensed":True,"arbitrary_substitution_rejected":True,"alternative_results_allowed":spec.alternatives_allowed,"terminal":{"enabled":False},"semantic_basis_identity":authority["basis_identity"],"author_identity":author_identity,"adjudicator_identity":adjudicator_identity,"candidate_identity":""}
    if metadata:c.update(metadata)
    c["candidate_identity"]=candidate_identity(c)
    evidence=[]
    for kind in {spec.evidence_kind,"contrast_alternatives","semantic_authority"}:
        e={"kind":kind,"relation_class":rc,"candidate_identity":c["candidate_identity"],"provenance_identity":authority["provenance_identity"],"trust_domain_owner":"INDEPENDENT_GENERAL_SEMANTIC_AUTHORITY","independent":True,"operands":c["operands"],"canonical_content":{"basis_identity":authority["basis_identity"],"kind":kind},"evidence_identity":""};e["evidence_identity"]=evidence_identity(e);evidence.append(e)
    return c,evidence,authority

def duplicate_report(candidates:Iterable[Mapping[str,Any]])->dict[str,Any]:
    ids=[semantic_primitive_identity(c) for c in candidates];total=len(ids);unique=len(set(ids))
    return {"total":total,"unique":unique,"duplicate_count":total-unique,"duplicate_rate":0 if not total else (total-unique)/total,"identities":ids}

def paths_conform(dry_callable,execution_callable,bases):
    dry=[dry_callable(b) for b in bases];execution=[execution_callable(b) for b in bases]
    return [semantic_primitive_identity(x[0]) for x in dry]==[semantic_primitive_identity(x[0]) for x in execution]
