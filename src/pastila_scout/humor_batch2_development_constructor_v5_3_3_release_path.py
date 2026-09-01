"""Executable V5.3.3 release-facing path for authority-partition qualification.

No family release or capability is represented here. The provider accepts one
field and returns bytes. The trusted observer derives all evidence from bytes;
the emitter accepts only the observer's opaque, hash-bound conformance receipt.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,re,unicodedata
from typing import Any,Mapping

from pastila_scout.humor_batch2_development_constructor_v5_3_3_integration import parse_provider_creative_payload

@dataclass(frozen=True,slots=True)
class FrozenSurfaceRoleRule:
    node_id:str
    role:str
    semantic_identity:str
    canonical_form:str
    licensed_surface_forms:tuple[str,...]

@dataclass(frozen=True,slots=True)
class FrozenNodeRelationRule:
    node_id:str
    actor_identity:str
    predicate_identity:str
    patient_identity:str
    produced_identity:str|None
    terminal:bool
    predecessor_node_id:str|None

@dataclass(frozen=True,slots=True)
class FrozenExecutableAuthorityV533:
    authority_identity:str
    implementation_identity:str
    release_binding_identity:str
    proposition_span_identity:str
    denyset_identity:str
    alignment_policy_identity:str
    role_rules:tuple[FrozenSurfaceRoleRule,...]
    node_rules:tuple[FrozenNodeRelationRule,...]

@dataclass(frozen=True,slots=True)
class ObservedRoleEvidence:
    node_id:str
    role:str
    semantic_identity:str
    surface_form:str
    character_start:int
    character_end:int
    utf8_byte_start:int
    utf8_byte_end:int

@dataclass(frozen=True,slots=True)
class TrustedConformanceReceiptV533:
    authority_identity:str
    surface_sha256:str
    surface_byte_length:int
    observed_roles:tuple[ObservedRoleEvidence,...]
    nodes_realized:int
    edges_realized:int
    terminal_results:int
    semantic_conformance:str
    receipt_identity:str

def _norm(value:str)->str: return " ".join(unicodedata.normalize("NFKC",value).casefold().split())

def close_executable_authority(authority:FrozenExecutableAuthorityV533)->FrozenExecutableAuthorityV533:
    values=(authority.authority_identity,authority.implementation_identity,authority.release_binding_identity,
        authority.proposition_span_identity,authority.denyset_identity,authority.alignment_policy_identity)
    if not all(values): raise ValueError("incomplete Class A pre-invocation closure")
    node_ids=[x.node_id for x in authority.node_rules]
    if not node_ids or len(node_ids)!=len(set(node_ids)) or sum(x.terminal for x in authority.node_rules)!=1:
        raise ValueError("invalid frozen node or terminal topology")
    expected={(node.node_id,role) for node in authority.node_rules for role in (("ACTOR","PREDICATE","PATIENT","PRODUCED") if node.produced_identity else ("ACTOR","PREDICATE","PATIENT"))}
    observed={(x.node_id,x.role) for x in authority.role_rules}
    if len(observed)!=len(authority.role_rules) or observed!=expected: raise ValueError("frozen role-rule closure differs from topology")
    by_node={x.node_id:x for x in authority.node_rules}
    for index,node in enumerate(authority.node_rules):
        if index==0 and node.predecessor_node_id is not None: raise ValueError("first node predecessor")
        if index and node.predecessor_node_id!=authority.node_rules[index-1].node_id: raise ValueError("causal direction or edge necessity")
        if node.predecessor_node_id and by_node[node.predecessor_node_id].produced_identity!=node.actor_identity:
            raise ValueError("produced/consumed semantic identity mismatch")
    return authority

def invoke_clause_only_provider(payload:Mapping[str,Any])->bytes:
    creative=parse_provider_creative_payload(payload)
    return creative.clause.encode("utf-8")

def _unique_span(text:str,variants:tuple[str,...])->tuple[int,int,str]:
    matches=[]
    folded=text.casefold()
    for variant in variants:
        needle=variant.casefold()
        if len(needle)!=len(variant): raise ValueError("casefold changes coordinate length")
        start=folded.find(needle)
        while start>=0:
            end=start+len(variant); matches.append((start,end,text[start:end])); start=folded.find(needle,start+1)
    unique={(a,b,v) for a,b,v in matches}
    if len(unique)!=1: raise ValueError("missing or ambiguous actual-surface role witness")
    return next(iter(unique))

def observe_and_conform_surface(*,authority:FrozenExecutableAuthorityV533,surface_bytes:bytes)->TrustedConformanceReceiptV533:
    authority=close_executable_authority(authority)
    text=surface_bytes.decode("utf-8"); evidence=[]
    segments=[match for match in re.finditer(r"[^.;!?]+[.;!?]?",text) if match.group().strip()]
    if len(segments)!=len(authority.node_rules): raise ValueError("material node clause coverage differs from frozen topology")
    segment_by_node={node.node_id:segments[index] for index,node in enumerate(authority.node_rules)}
    for rule in authority.role_rules:
        segment=segment_by_node[rule.node_id]; local=segment.group()
        local_start,local_end,form=_unique_span(local,rule.licensed_surface_forms)
        start,end=segment.start()+local_start,segment.start()+local_end
        if not any(_norm(form)==_norm(licensed) for licensed in rule.licensed_surface_forms): raise ValueError("unlicensed alignment")
        bs=len(text[:start].encode("utf-8")); be=len(text[:end].encode("utf-8"))
        if surface_bytes[bs:be]!=form.encode("utf-8"): raise ValueError("non-round-tripping UTF-8 evidence")
        evidence.append(ObservedRoleEvidence(rule.node_id,rule.role,rule.semantic_identity,form,start,end,bs,be))
    indexed={(x.node_id,x.role):x for x in evidence}
    occupied=[]
    for item in evidence:
        for start,end in occupied:
            if max(start,item.character_start)<min(end,item.character_end): raise ValueError("overlapping role witnesses")
        occupied.append((item.character_start,item.character_end))
    for node in authority.node_rules:
        actor,predicate,patient=(indexed[(node.node_id,x)] for x in ("ACTOR","PREDICATE","PATIENT"))
        if not (actor.character_start<predicate.character_start<patient.character_start): raise ValueError("actor/predicate/patient direction drift")
        if (actor.semantic_identity,predicate.semantic_identity,patient.semantic_identity)!=(node.actor_identity,node.predicate_identity,node.patient_identity): raise ValueError("semantic-role or predicate drift")
        if node.produced_identity:
            produced=indexed[(node.node_id,"PRODUCED")]
            if produced.semantic_identity!=node.produced_identity or produced.character_start<=patient.character_start: raise ValueError("produced operand drift")
    for previous,current in zip(authority.node_rules,authority.node_rules[1:]):
        produced=indexed[(previous.node_id,"PRODUCED")]; actor=indexed[(current.node_id,"ACTOR")]
        if produced.semantic_identity!=actor.semantic_identity or produced.character_start>=actor.character_start: raise ValueError("broken edge necessity or causal direction")
    terminal=sum(x.terminal for x in authority.node_rules)
    core="|".join((authority.authority_identity,hashlib.sha256(surface_bytes).hexdigest(),str(len(evidence)),str(len(authority.node_rules)-1),str(terminal)))
    identity=hashlib.sha256(core.encode()).hexdigest()
    return TrustedConformanceReceiptV533(authority.authority_identity,hashlib.sha256(surface_bytes).hexdigest(),len(surface_bytes),tuple(evidence),len(authority.node_rules),len(authority.node_rules)-1,terminal,"PASS_ACTUAL_SURFACE_SEMANTIC_CONFORMANCE",identity)

def conditional_emit(*,authority:FrozenExecutableAuthorityV533,surface_bytes:bytes,receipt:TrustedConformanceReceiptV533)->bytes:
    if receipt.authority_identity!=authority.authority_identity or receipt.surface_sha256!=hashlib.sha256(surface_bytes).hexdigest() or receipt.surface_byte_length!=len(surface_bytes) or receipt.semantic_conformance!="PASS_ACTUAL_SURFACE_SEMANTIC_CONFORMANCE": raise ValueError("emitter requires matching trusted conformance receipt")
    return surface_bytes

def execute_release_facing_path(*,authority:FrozenExecutableAuthorityV533,provider_payload:Mapping[str,Any])->tuple[bytes,TrustedConformanceReceiptV533]:
    closed=close_executable_authority(authority)
    surface=invoke_clause_only_provider(provider_payload)
    receipt=observe_and_conform_surface(authority=closed,surface_bytes=surface)
    return conditional_emit(authority=closed,surface_bytes=surface,receipt=receipt),receipt

__all__=["FrozenSurfaceRoleRule","FrozenNodeRelationRule","FrozenExecutableAuthorityV533","ObservedRoleEvidence","TrustedConformanceReceiptV533","close_executable_authority","invoke_clause_only_provider","observe_and_conform_surface","conditional_emit","execute_release_facing_path"]
