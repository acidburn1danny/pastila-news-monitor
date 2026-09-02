"""Executable, zero-family implementation of the frozen relation contract V2."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json
from typing import Any, Mapping

@dataclass(frozen=True)
class RelationSpec:
    evidence_kind: str; continuity: str; dependency: str
    actor_classes: tuple[str,...]; patient_classes: tuple[str,...]
    required_affordances: tuple[str,...]=(); alternatives_allowed: bool=True

SPECS: dict[str,RelationSpec] = {
"CAUSAL":RelationSpec("causal_dependency","exact_result","counterfactual",("EVENT","PROCESS"),("STATE","EVENT")),
"TRIGGER":RelationSpec("causal_dependency","exact_result","counterfactual",("EVENT","STATE"),("EVENT","PROCESS")),
"PHYSICAL_ACTION":RelationSpec("semantic_authority","exact_result","capability",("INTENTIONAL_ACTOR",),("PHYSICAL_ENTITY",),("ACTION_CAPABILITY",)),
"STATE_TRANSITION":RelationSpec("causal_dependency","exact_result","counterfactual",("EVENT","PROCESS"),("STATE",)),
"PROCEDURAL":RelationSpec("procedure_authority","exact_result","precondition",("INTENTIONAL_ACTOR","PROCESS"),("PROCEDURE","STATE")),
"NORMATIVE_AUTHORIZATION":RelationSpec("normative_authority","normative_authority","jurisdiction",("NORMATIVE_SOURCE",),("ADDRESSEE","REGULATED_ACT")),
"NORMATIVE_OBLIGATION":RelationSpec("normative_authority","normative_authority","jurisdiction",("NORMATIVE_SOURCE",),("ADDRESSEE","REGULATED_ACT")),
"LOGICAL_INFERENCE":RelationSpec("inference_rule","premise","entailment",("PROPOSITION_CONTENT",),("PROPOSITION_CONTENT",)),
"REPRESENTATIONAL":RelationSpec("representation_convention","referential","denotation",("REPRESENTATION",),("ENTITY","EVENT","STATE","PROPOSITION_CONTENT")),
"RECORDING_EVIDENTIARY":RelationSpec("evidentiary_provenance","evidentiary","provenance",("RECORDING_ACT",),("OBSERVED_EVENT","OBSERVED_STATE")),
"MEASUREMENT":RelationSpec("measurement_method","evidentiary","method",("MEASUREMENT_ACT",),("MEASURED_PROPERTY",)),
"CLASSIFICATION_CONSTITUTIVE":RelationSpec("classification_criterion","criterion","criterion",("CLASSIFICATION_RULE",),("ENTITY","EVENT","STATE")),
"INFORMATION_TRANSFER":RelationSpec("transfer_provenance","content_channel","transfer",("SENDER",),("INFORMATION_CONTENT","RECEIVER")),
"TEMPORAL":RelationSpec("temporal_ordering","temporal_reference","ordering",("EVENT","STATE"),("TIME_REFERENCE","EVENT","STATE")),
"MOVEMENT_LOCATION":RelationSpec("semantic_authority","exact_result","path",("INTENTIONAL_ACTOR","PHYSICAL_ENTITY"),("LOCATION",),("MOVEMENT_CAPABILITY",)),
"OBSERVATION_PERCEPTION":RelationSpec("evidentiary_provenance","evidentiary","observation",("INTENTIONAL_ACTOR","SENSOR"),("OBSERVED_EVENT","OBSERVED_STATE"),("OBSERVATION_CAPABILITY",)),
"COMPARISON_VERIFICATION":RelationSpec("classification_criterion","criterion","criterion",("INTENTIONAL_ACTOR","PROCESS"),("MEASURED_VALUE","RECORD","REPRESENTATION")),
}

def canonical(value: Mapping[str,Any], omit: tuple[str,...]=()) -> str:
    body={k:v for k,v in value.items() if k not in omit}
    return hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def evidence_identity(e: Mapping[str,Any])->str: return canonical(e,("evidence_identity",))
def candidate_identity(c: Mapping[str,Any])->str: return canonical(c,("candidate_identity",))

def validate_candidate(candidate: Mapping[str,Any], evidence: list[Mapping[str,Any]]) -> tuple[str,...]:
    b=[]; rc=candidate.get("relation_class"); spec=SPECS.get(rc)
    if not spec:return ("UNKNOWN_RELATION_CLASS",)
    cid=candidate_identity(candidate)
    if candidate.get("candidate_identity")!=cid:b.append("CANDIDATE_IDENTITY_MISMATCH")
    if candidate.get("author_identity")==candidate.get("adjudicator_identity"):b.append("AUTHOR_ADJUDICATOR_COLLISION")
    if candidate.get("actor_class") not in spec.actor_classes:b.append("ACTOR_CLASS_MISMATCH")
    if candidate.get("patient_class") not in spec.patient_classes:b.append("PATIENT_CLASS_MISMATCH")
    if not set(spec.required_affordances)<=set(candidate.get("affordances",[])):b.append("AFFORDANCE_MISMATCH")
    required={spec.evidence_kind,"contrast_alternatives","semantic_authority"}
    bound=[]
    for e in evidence:
        if e.get("evidence_identity")!=evidence_identity(e):b.append("EVIDENCE_IDENTITY_MISMATCH");continue
        if e.get("candidate_identity")!=cid:b.append("EVIDENCE_CANDIDATE_IDENTITY_SKEW");continue
        if e.get("relation_class")!=rc:b.append("EVIDENCE_RELATION_CLASS_SKEW");continue
        if e.get("trust_domain_owner") in {"RULE_AUTHOR","PLANNER"}:b.append("SELF_AUTHORIZING_EVIDENCE");continue
        if e.get("independent") is not True or not e.get("provenance_identity"):b.append("UNTRUSTED_EVIDENCE");continue
        if e.get("operands")!=candidate.get("operands"):b.append("EVIDENCE_OPERAND_SKEW");continue
        if e.get("roles")!=candidate.get("roles"):b.append("EVIDENCE_ROLE_SKEW");continue
        bound.append(e)
    kinds={e["kind"] for e in bound}
    for kind in required-kinds:b.append("MISSING_EVIDENCE:"+kind)
    if candidate.get("continuity",{}).get("kind")!=spec.continuity:b.append("CONTINUITY_MISMATCH")
    if candidate.get("dependency_test")!=spec.dependency:b.append("DEPENDENCY_TEST_MISMATCH")
    if not candidate.get("claimed_result_licensed"):b.append("CLAIMED_RESULT_UNLICENSED")
    if not candidate.get("arbitrary_substitution_rejected"):b.append("ARBITRARY_CONSEQUENCE")
    t=candidate.get("terminal",{})
    if t.get("enabled") and not all(t.get(x) for x in ("authority","continuity","licensed_result","non_arbitrary")):b.append("ARBITRARY_TERMINAL")
    return tuple(dict.fromkeys(b))

def adjudicate(candidate:Mapping[str,Any], evidence:list[Mapping[str,Any]], reviews:list[Mapping[str,Any]])->dict[str,Any]:
    blockers=list(validate_candidate(candidate,evidence)); cid=candidate_identity(candidate); rc=candidate.get("relation_class")
    required={"SEMANTIC","LICENSING","ADVERSARIAL"}; seen=set()
    for r in reviews:
        if r.get("candidate_identity")!=cid or r.get("relation_class")!=rc:blockers.append("REVIEW_BINDING_SKEW");continue
        if not r.get("evidence_identities") or r.get("verdict") not in {"PASS","FAIL"}:blockers.append("EVIDENCE_FREE_REVIEW")
        seen.add(r.get("dimension"))
        if r.get("verdict")!="PASS":blockers.append("REVIEW_FAILED:"+str(r.get("dimension")))
    for x in required-seen:blockers.append("MISSING_REVIEW:"+x)
    reviewers={r.get("reviewer_identity") for r in reviews};
    if candidate.get("author_identity") in reviewers or candidate.get("adjudicator_identity") in reviewers:blockers.append("REVIEWER_INDEPENDENCE_FAILURE")
    blockers=tuple(dict.fromkeys(blockers))
    return {"candidate_identity":cid,"relation_class":rc,"verdict":"PASS_ZERO_FAMILY_DIAGNOSTIC" if not blockers else "FAIL_CLOSED","blockers":blockers,"evidence_path":[e.get("evidence_identity") for e in evidence] if not blockers else []}

def validate_composition(left:Mapping[str,Any],right:Mapping[str,Any],boundary:Mapping[str,Any])->tuple[str,...]:
    b=[]
    if boundary.get("from_candidate")!=candidate_identity(left) or boundary.get("to_candidate")!=candidate_identity(right):b.append("BOUNDARY_IDENTITY_SKEW")
    if boundary.get("from_class")!=left.get("relation_class") or boundary.get("to_class")!=right.get("relation_class"):b.append("BOUNDARY_CLASS_SKEW")
    if boundary.get("continuity")!=SPECS[right["relation_class"]].continuity:b.append("CROSS_CLASS_CONTINUITY_MISMATCH")
    if boundary.get("inherits_affordances"):b.append("HIDDEN_AFFORDANCE_INHERITANCE")
    if not boundary.get("authority_identity"):b.append("BOUNDARY_AUTHORITY_MISSING")
    return tuple(b)
