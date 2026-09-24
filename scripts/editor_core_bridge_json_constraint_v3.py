"""Streaming JSON grammar and tokenizer-trie projection for Bridge responses."""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping

ABSTENTION_CODES=("INSUFFICIENT_AUTHORITY","CONFLICTING_AUTHORITY","AMBIGUOUS_SCOPE",
                  "UNRESOLVED_REFERENCE","INSTRUCTION_AUTHORITY_CONFLICT",
                  "CANNOT_SATISFY_OUTPUT_CONTRACT","SAFETY_ENVELOPE_EXCEEDED")

@dataclass(frozen=True)
class BridgeJSONStateV3:
    payload: dict
    mode: str="LITERAL"
    remaining: str=""
    step: str="START"
    buffer: str=""
    choices: tuple[str,...]=()
    outcome: str|None=None
    binding_index: int=1
    binding_count: int=0
    text_characters: int=0
    string_escape: bool=False
    unicode_remaining: int=0
    terminal: bool=False

    @classmethod
    def start(cls,payload:dict)->"BridgeJSONStateV3":
        prefix=(f'{{"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,'
                f'"case_id":"{payload["case_id"]}","request_identity":"{payload["request_identity"]}",'
                f'"output_type":"{payload["output_type"]}","outcome":"')
        return cls(payload=payload,remaining=prefix,step="OUTCOME")

    @property
    def can_eos(self)->bool: return self.terminal

    def feed(self,text:str)->"BridgeJSONStateV3":
        state=self
        for char in text: state=state._char(char)
        return state

    def _char(self,char:str)->"BridgeJSONStateV3":
        if self.terminal: raise ValueError("TRAILING_BYTES")
        if self.mode=="LITERAL":
            if not self.remaining or char!=self.remaining[0]: raise ValueError("LITERAL")
            left=self.remaining[1:]; state=replace(self,remaining=left)
            return state._advance(self.step) if not left else state
        if self.mode=="CHOICE":
            candidate=self.buffer+char; viable=tuple(x for x in self.choices if x.startswith(candidate))
            if not viable: raise ValueError("CHOICE")
            state=replace(self,buffer=candidate,choices=viable)
            if len(viable)==1 and candidate==viable[0]: return state._advance(self.step,candidate)
            return state
        if self.mode=="TEXT":
            if self.unicode_remaining:
                if char not in "0123456789abcdefABCDEF": raise ValueError("UNICODE_ESCAPE")
                left=self.unicode_remaining-1
                return replace(self,unicode_remaining=left,string_escape=False if left==0 else self.string_escape)
            if self.string_escape:
                if char=="u": return replace(self,unicode_remaining=4)
                if char not in '"\\/bfnrt': raise ValueError("JSON_ESCAPE")
                return replace(self,string_escape=False,text_characters=self.text_characters+1)
            if char=="\\": return replace(self,string_escape=True)
            if char=='"':
                if self.text_characters==0: raise ValueError("EMPTY_TEXT")
                return self._advance("BINDINGS")
            if ord(char)<0x20 or self.text_characters>=650: raise ValueError("TEXT_LIMIT")
            return replace(self,text_characters=self.text_characters+1)
        if self.mode=="AFTER_SPAN":
            if char==',' : return replace(self,mode="LITERAL",remaining='"',step="SPAN")
            if char==']': return replace(self,mode="LITERAL",remaining='}',step="AFTER_BINDING")
            raise ValueError("SPAN_SEPARATOR")
        if self.mode=="AFTER_BINDING":
            if char==',' and self.binding_count<3:
                nxt=self.binding_count+1
                return replace(self,mode="LITERAL",remaining=f'{{"claim_index":{nxt},"source_span_ids":["',step="SPAN",binding_index=nxt)
            if char==']': return replace(self,mode="LITERAL",remaining=',"abstention_code":null}',step="TERMINAL")
            raise ValueError("BINDING_SEPARATOR")
        raise ValueError("STATE")

    def _advance(self,step:str,value:str|None=None)->"BridgeJSONStateV3":
        if step=="OUTCOME": return replace(self,mode="CHOICE",choices=("ANSWER","ABSTAIN"),buffer="",step="AFTER_OUTCOME")
        if step=="AFTER_OUTCOME":
            if value=="ANSWER": return replace(self,outcome=value,mode="LITERAL",remaining='","text":"',step="TEXT")
            return replace(self,outcome=value,mode="LITERAL",remaining='","text":null,"claim_bindings":[],"abstention_code":"',step="ABSTENTION")
        if step=="TEXT": return replace(self,mode="TEXT",text_characters=0,string_escape=False,unicode_remaining=0)
        if step=="BINDINGS": return replace(self,mode="LITERAL",remaining=',"claim_bindings":[{"claim_index":1,"source_span_ids":["',step="SPAN",binding_count=1,binding_index=1)
        if step=="SPAN":
            spans=tuple(row["span_id"] for row in self.payload["authority_spans"])
            return replace(self,mode="CHOICE",choices=spans,buffer="",step="AFTER_SPAN_QUOTE")
        if step=="AFTER_SPAN_QUOTE": return replace(self,mode="LITERAL",remaining='"',step="AFTER_SPAN_MODE")
        if step=="AFTER_SPAN_MODE": return replace(self,mode="AFTER_SPAN")
        if step=="AFTER_BINDING": return replace(self,mode="AFTER_BINDING",binding_count=self.binding_index)
        if step=="ABSTENTION": return replace(self,mode="CHOICE",choices=ABSTENTION_CODES,buffer="",step="ABSTENTION_END")
        if step=="ABSTENTION_END": return replace(self,mode="LITERAL",remaining='"}',step="TERMINAL")
        if step=="TERMINAL": return replace(self,mode="TERMINAL",terminal=True,remaining="")
        raise ValueError("ADVANCE")


class BridgeTokenTrieV3:
    def __init__(self,*,token_pieces:Mapping[int,str],eos_token_id:int,excluded_token_ids:Iterable[int]=()):
        excluded=frozenset(excluded_token_ids)|{eos_token_id}; self.eos=eos_token_id
        self.children=[{}]; self.terminals=[[]]; self.cache={}
        for token,piece in sorted(token_pieces.items()):
            if token in excluded or not piece: continue
            node=0
            for char in piece:
                node=self.children[node].setdefault(char,len(self.children))
                if node==len(self.children): self.children.append({}); self.terminals.append([])
            self.terminals[node].append(token)
    def allowed_token_ids(self,state:BridgeJSONStateV3)->tuple[int,...]:
        if state.can_eos:return (self.eos,)
        key=repr(state)
        cached=self.cache.get(key)
        if cached is not None:return cached
        allowed=[]; stack=[(0,state)]
        while stack:
            node,current=stack.pop(); allowed.extend(self.terminals[node])
            for char,child in self.children[node].items():
                try: advanced=current.feed(char)
                except ValueError: continue
                stack.append((child,advanced))
        if not allowed: raise ValueError("EMPTY_ALLOWED_TOKEN_SET")
        result=tuple(sorted(allowed)); self.cache[key]=result; return result
