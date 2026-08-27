"""Evaluation-only split-trie performance candidate for ordinary JSON strings."""
from __future__ import annotations

from typing import Iterable, Mapping

from .stage_p_construction_obligation_token_projector_v1 import StagePConstructionObligationTokenProjectorV1
from .stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1


class StagePConstructionObligationTokenProjectorV2(StagePConstructionObligationTokenProjectorV1):
    def __init__(self, *, token_pieces:Mapping[int,str], excluded_token_ids:Iterable[int]=(), **kwargs)->None:
        excluded=frozenset(excluded_token_ids)|{kwargs["eos_token_id"]}
        super().__init__(token_pieces=token_pieces,excluded_token_ids=excluded,**kwargs)
        self._ordinary_by_length:dict[int,list[int]]={}
        self._boundary_children:list[dict[str,int]]=[{}];self._boundary_terminals:list[list[int]]=[[]]
        for token_id,piece in sorted(token_pieces.items()):
            if token_id in excluded or not piece:continue
            ordinary=all(ord(char)>=0x20 and not 0xD800<=ord(char)<=0xDFFF and char not in {'"','\\'} for char in piece)
            if ordinary:
                self._ordinary_by_length.setdefault(len(piece),[]).append(token_id);continue
            node=0
            for char in piece:
                child=self._boundary_children[node].get(char)
                if child is None:
                    child=len(self._boundary_children);self._boundary_children[node][char]=child
                    self._boundary_children.append({});self._boundary_terminals.append([])
                node=child
            self._boundary_terminals[node].append(token_id)
        self.ordinary_token_count=sum(map(len,self._ordinary_by_length.values()))
        self.boundary_trie_node_count=len(self._boundary_children)

    def _project_state(self,state)->tuple[int,...]:
        if state.mode!="STRING" or state.string_escape or state.unicode_remaining:
            return super()._project_state(state)
        remaining=16000-state.characters
        allowed=[]
        for length,token_ids in self._ordinary_by_length.items():
            if length<=remaining:allowed.extend(token_ids)
        stack=[(0,state)]
        while stack:
            node,current=stack.pop();allowed.extend(self._boundary_terminals[node])
            for char,child in self._boundary_children[node].items():
                try:advanced=current.feed(char)
                except StagePRoleCoherenceConstraintViolationV1:continue
                stack.append((child,advanced))
        return tuple(sorted(allowed))


__all__=("StagePConstructionObligationTokenProjectorV2",)
