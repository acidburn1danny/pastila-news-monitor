"""V5.3.3 authority-partitioned provider/emitter integration.

This module grants no release authority and performs no invocation by itself.
Provider payloads contain only Class C surface choices. Class A closure is
created before invocation; Class B evidence can be created only from bytes.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from typing import Any,Mapping

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness,OperandSemanticSpec,PredicateSemanticSignature,validate_semantic_plan,
)

CLASS_C_FIELDS=frozenset({"clause"})

@dataclass(frozen=True,slots=True)
class ProviderCreativeRealizationV533:
    clause:str

@dataclass(frozen=True,slots=True)
class FrozenAuthorityClosureV533:
    exact_source_utf8:str
    proposition_id:str
    supporting_span_sha256:str
    typed_plan:tuple[TypedPlanNode,...]
    operand_specs:tuple[OperandSemanticSpec,...]
    predicate_signatures:tuple[PredicateSemanticSignature,...]
    edge_witnesses:tuple[EdgeNecessityWitness,...]
    release_identity:str
    constructor_contract_identity:str
    provider_identity:str
    emitter_identity:str
    fragment_denyset_identity:str
    alignment_policy_identity:str
    authority_closure_sha256:str

@dataclass(frozen=True,slots=True)
class AuthorityBoundCreativeNodeV533:
    """Trusted-boundary product; never deserialized from provider output."""
    clause:str
    node_id:str
    actor_operand_id:str
    predicate_id:str
    patient_operand_id:str
    introduced_operand_ids:tuple[str,...]
    predecessor_node_ids:tuple[str,...]
    predecessor_causal_rule_ids:tuple[str,...]
    actor_roles:tuple[str,...]
    actor_affordances:tuple[str,...]
    patient_roles:tuple[str,...]
    patient_affordances:tuple[str,...]
    terminal_result:bool

@dataclass(frozen=True,slots=True)
class SurfaceObservedEvidenceV533:
    """Class B evidence whose constructor requires actual immutable bytes."""
    surface_sha256:str
    surface_byte_length:int
    character_spans:tuple[tuple[int,int],...]
    utf8_byte_spans:tuple[tuple[int,int],...]
    observed_forms:tuple[str,...]
    observed_roles:tuple[str,...]

def parse_provider_creative_payload(payload:Mapping[str,Any])->ProviderCreativeRealizationV533:
    if set(payload)!=CLASS_C_FIELDS:
        raise ValueError("provider payload must contain exactly the single Class C clause field")
    if not isinstance(payload["clause"],str) or not payload["clause"].strip():
        raise ValueError("creative text fields must be nonempty strings")
    return ProviderCreativeRealizationV533(payload["clause"])

def close_pre_invocation_authority(*,exact_source_utf8:str,proposition_id:str,supporting_span_sha256:str,
        typed_plan:tuple[TypedPlanNode,...],operand_specs:tuple[OperandSemanticSpec,...],
        predicate_signatures:tuple[PredicateSemanticSignature,...],edge_witnesses:tuple[EdgeNecessityWitness,...],
        release_identity:str,constructor_contract_identity:str,provider_identity:str,emitter_identity:str,
        fragment_denyset_identity:str,alignment_policy_identity:str)->FrozenAuthorityClosureV533:
    values=(exact_source_utf8,proposition_id,supporting_span_sha256,release_identity,constructor_contract_identity,
            provider_identity,emitter_identity,fragment_denyset_identity,alignment_policy_identity)
    if not all(isinstance(x,str) and x.strip() for x in values): raise ValueError("incomplete Class A authority closure")
    validate_semantic_plan(typed_plan=typed_plan,operand_specs=operand_specs,predicate_signatures=predicate_signatures,edge_witnesses=edge_witnesses)
    if len(typed_plan)<1 or typed_plan[-1].introduces_ids: raise ValueError("terminal topology closure")
    material="\n".join(values+(repr(typed_plan),repr(operand_specs),repr(predicate_signatures),repr(edge_witnesses))).encode()
    return FrozenAuthorityClosureV533(exact_source_utf8,proposition_id,supporting_span_sha256,typed_plan,operand_specs,
        predicate_signatures,edge_witnesses,release_identity,constructor_contract_identity,provider_identity,
        emitter_identity,fragment_denyset_identity,alignment_policy_identity,hashlib.sha256(material).hexdigest())

def bind_creative_choices(*,closure:FrozenAuthorityClosureV533,creative:tuple[ProviderCreativeRealizationV533,...])->tuple[AuthorityBoundCreativeNodeV533,...]:
    if len(creative)!=len(closure.typed_plan): raise ValueError("creative N/N coverage differs from frozen topology")
    specs={x.operand_id:x for x in closure.operand_specs}
    rules={(x.predecessor_node_id,x.successor_node_id):x.explicit_licensing_rule for x in closure.edge_witnesses}
    result=[]
    for index,(node,item) in enumerate(zip(closure.typed_plan,creative,strict=True)):
        actor,patient=specs[node.bound_actor_id],specs[node.bound_patient_id]
        result.append(AuthorityBoundCreativeNodeV533(item.clause,node.node_id,node.bound_actor_id,node.predicate_id,node.bound_patient_id,
            node.introduces_ids,node.predecessor_node_ids,tuple(rules[(p,node.node_id)] for p in node.predecessor_node_ids),
            actor.semantic_roles,actor.affordances,patient.semantic_roles,patient.affordances,index==len(closure.typed_plan)-1))
    return tuple(result)

def observe_surface_bytes(*,surface_bytes:bytes,character_spans:tuple[tuple[int,int],...],utf8_byte_spans:tuple[tuple[int,int],...],observed_roles:tuple[str,...])->SurfaceObservedEvidenceV533:
    text=surface_bytes.decode("utf-8")
    if len(character_spans)!=len(utf8_byte_spans) or len(character_spans)!=len(observed_roles) or not character_spans: raise ValueError("missing coordinate-bound surface evidence")
    forms=[]
    for chars,rawspan in zip(character_spans,utf8_byte_spans,strict=True):
        cs,ce=chars; bs,be=rawspan
        if not (0<=cs<ce<=len(text) and 0<=bs<be<=len(surface_bytes)): raise ValueError("invalid actual-surface coordinates")
        form=text[cs:ce]
        if surface_bytes[bs:be]!=form.encode("utf-8"): raise ValueError("character and UTF-8 evidence disagree")
        forms.append(form)
    return SurfaceObservedEvidenceV533(hashlib.sha256(surface_bytes).hexdigest(),len(surface_bytes),character_spans,utf8_byte_spans,tuple(forms),observed_roles)

__all__=["CLASS_C_FIELDS","ProviderCreativeRealizationV533","FrozenAuthorityClosureV533","AuthorityBoundCreativeNodeV533","SurfaceObservedEvidenceV533","parse_provider_creative_payload","close_pre_invocation_authority","bind_creative_choices","observe_surface_bytes"]
