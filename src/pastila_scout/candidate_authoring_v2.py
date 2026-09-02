"""Canonical evidence-first candidate authoring for frozen Curriculum V2.

The same functions serve dry qualification and later governed execution.  They
perform no persistence, admission, activation, or family access.
"""
from __future__ import annotations
import hashlib,json
from typing import Any,Iterable,Mapping
from .relation_contract_v2 import SPECS,candidate_identity,evidence_identity

EPHEMERAL=frozenset({"candidate_identity","batch","sequence","nonce","timestamp","label","author_identity","adjudicator_identity","filename"})
SUBSTANTIVE_FIELDS=("relation_class","actor_class","patient_class","roles","operands","affordances","continuity","dependency_test","claimed_result","scope","claimed_result_licensed","arbitrary_substitution_rejected","alternative_results_allowed","terminal","semantic_basis_identity")

def _canonical(value:Any)->Any:
    if isinstance(value,Mapping):return {k:_canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,(list,tuple)):return [_canonical(v) for v in value]
    return value

def semantic_primitive_identity(candidate:Mapping[str,Any])->str:
    """Identity over substantive semantics only, excluding ephemeral metadata."""
    payload=_canonical({k:candidate[k] for k in SUBSTANTIVE_FIELDS if k in candidate})
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def evidence_basis_identity(basis:Mapping[str,Any])->str:
    payload={k:v for k,v in basis.items() if k not in EPHEMERAL}
    return hashlib.sha256(json.dumps(_canonical(payload),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def authority_identity(authority:Mapping[str,Any])->str:
    return hashlib.sha256(json.dumps(_canonical({k:v for k,v in authority.items() if k!="authority_identity"}),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def author_from_basis(basis:Mapping[str,Any],*,author_identity:str,adjudicator_identity:str,authorities:Iterable[Mapping[str,Any]],metadata:Mapping[str,Any]|None=None):
    """Create evidence authority content first, then candidate and final bindings."""
    rc=str(basis.get("relation_class"));spec=SPECS.get(rc)
    if not spec:raise ValueError("unknown relation class")
    required={"semantic_basis","actor_class","patient_class","operands","claimed_result","scope","authority_provenance"}
    if required-set(basis):raise ValueError("incomplete independent semantic basis")
    if basis.get("origin_order")!="INDEPENDENT_BASIS_BEFORE_EVIDENCE_BEFORE_CANDIDATE":raise ValueError("evidence-first protocol bypass")
    if basis.get("chain_slot") is not None:raise ValueError("V1 chain-slot recurrence")
    if basis.get("generic_produced_state") is True:raise ValueError("unlicensed generic produced-state manufacturing")
    basis_id=evidence_basis_identity(basis); required_kinds={spec.evidence_kind,"contrast_alternatives","semantic_authority"}; authority_list=list(authorities); authority_by_kind={a.get("kind"):a for a in authority_list}
    if len(authority_list)!=len(authority_by_kind):raise ValueError("duplicate authority kind")
    if set(authority_by_kind)!=required_kinds:raise ValueError("exact independent authority set required")
    for kind,a in authority_by_kind.items():
        if a.get("authority_identity")!=authority_identity(a):raise ValueError("authority identity mismatch")
        if a.get("basis_identity")!=basis_id or a.get("relation_class")!=rc or a.get("source_provenance_identity")!=basis["authority_provenance"]:raise ValueError("authority binding mismatch")
        if a.get("trust_domain_owner") in {author_identity,"RULE_AUTHOR","PLANNER"} or not a.get("independent"):raise ValueError("self-derived authority")
    authority={"basis_identity":basis_id,"provenance_identity":basis["authority_provenance"],"canonical_semantic_content":_canonical(basis)}
    c={"relation_class":rc,"actor_class":basis["actor_class"],"patient_class":basis["patient_class"],"roles":{"actor":basis.get("actor_role","ACTOR"),"patient":basis.get("patient_role","PATIENT")},"operands":list(basis["operands"]),"affordances":list(basis.get("affordances",spec.required_affordances)),"continuity":{"kind":spec.continuity,"binding":basis.get("continuity_binding")},"dependency_test":spec.dependency,"claimed_result":basis["claimed_result"],"scope":basis["scope"],"claimed_result_licensed":True,"arbitrary_substitution_rejected":True,"alternative_results_allowed":spec.alternatives_allowed,"terminal":{"enabled":False},"semantic_basis_identity":authority["basis_identity"],"author_identity":author_identity,"adjudicator_identity":adjudicator_identity,"candidate_identity":""}
    c["candidate_identity"]=candidate_identity(c)
    evidence=[]
    for kind in sorted(required_kinds):
        source=authority_by_kind[kind];e={"kind":kind,"relation_class":rc,"candidate_identity":c["candidate_identity"],"provenance_identity":source["authority_identity"],"trust_domain_owner":source["trust_domain_owner"],"independent":True,"operands":c["operands"],"roles":c["roles"],"canonical_content":source["canonical_semantic_content"],"evidence_identity":""};e["evidence_identity"]=evidence_identity(e);evidence.append(e)
    return c,evidence,{"basis":authority,"execution_metadata":dict(metadata or {})}

def duplicate_report(candidates:Iterable[Mapping[str,Any]])->dict[str,Any]:
    ids=[semantic_primitive_identity(c) for c in candidates];total=len(ids);unique=len(set(ids))
    return {"total":total,"unique":unique,"duplicate_count":total-unique,"duplicate_rate":0 if not total else (total-unique)/total,"identities":ids}

def paths_conform(dry_callable,execution_callable,bases):
    dry=[dry_callable(b) for b in bases];execution=[execution_callable(b) for b in bases]
    return [semantic_primitive_identity(x[0]) for x in dry]==[semantic_primitive_identity(x[0]) for x in execution]
