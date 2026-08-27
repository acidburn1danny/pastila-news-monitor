"""Zero-inference feasibility projector for exact Stage P source substrings."""
from __future__ import annotations

from collections.abc import Iterable,Mapping
from dataclasses import dataclass
from typing import Any

from .stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1

_CANDIDATE_MARKER=',"candidate_span":"'
_AUTHORITY_MARKER=',"authority_support":"'
_ESCAPES={'"':'"','\\':'\\','/':'/','b':'\b','f':'\f','n':'\n','r':'\r','t':'\t'}


@dataclass(frozen=True)
class SourceBoundProjectionReceiptV1:
    allowed_token_ids:tuple[int,...]
    grammar_allowed_count:int
    source_bound_count:int
    field:str|None


class StagePSourceBoundTokenProjectorV1:
    """Intersect grammar tokens with exact-source feasibility only inside source span strings."""
    def __init__(self,*,token_pieces:Mapping[int,str],eos_token_id:int,excluded_token_ids:Iterable[int]=())->None:
        self._pieces=dict(token_pieces)
        self._grammar=StagePTokenTrieProjectorV1(token_pieces=token_pieces,eos_token_id=eos_token_id,
            excluded_token_ids=excluded_token_ids)

    def allowed_token_ids(self,*,state:Any,decoded_prefix:str,candidate:str,factual_summary:str)->SourceBoundProjectionReceiptV1:
        grammar=self._grammar.allowed_token_ids(state);field=_field(state)
        if field is None:
            allowed=tuple(item for item in grammar if _transition_piece_preserves_sources(state,self._pieces[item],candidate,factual_summary))
            if not allowed: raise ValueError("EMPTY_SOURCE_BOUND_TOKEN_SET")
            return SourceBoundProjectionReceiptV1(allowed,len(grammar),len(allowed),None)
        source=candidate if field=="candidate_span" else factual_summary
        raw=_raw_fragment(decoded_prefix,_CANDIDATE_MARKER if field=="candidate_span" else _AUTHORITY_MARKER)
        existing,complete=_decode_raw_prefix(raw)
        allowed=tuple(item for item in grammar if (_piece_preserves_from_decoded(existing,self._pieces[item],source)
            if complete else _piece_preserves_exact_substring(raw,self._pieces[item],source)))
        if not allowed: raise ValueError("EMPTY_SOURCE_BOUND_TOKEN_SET")
        return SourceBoundProjectionReceiptV1(allowed,len(grammar),len(allowed),field)


def _field(state:Any)->str|None:
    if state.mode!="STRING": return None
    if state.next_step=="AUTHORITY_LITERAL": return "candidate_span"
    if state.next_step=="COMMITMENT_LITERAL": return "authority_support"
    return None


def _raw_fragment(prefix:str,marker:str)->str:
    index=prefix.rfind(marker)
    if index<0: raise ValueError("SOURCE_FIELD_MARKER_MISSING")
    return prefix[index+len(marker):]


def _piece_preserves_exact_substring(existing_raw:str,piece:str,source:str)->bool:
    raw=existing_raw;escaped=False;unicode_left=0
    for char in piece:
        if unicode_left:
            raw+=char;unicode_left-=1
            continue
        if escaped:
            raw+=char;escaped=False
            if char=="u": unicode_left=4
            continue
        if char=="\\": raw+=char;escaped=True;continue
        if char=='"':
            decoded,complete=_decode_raw_prefix(raw)
            return complete and bool(decoded) and decoded in source
        raw+=char
        decoded,_complete=_decode_raw_prefix(raw)
        if decoded and decoded not in source: return False
    decoded,_complete=_decode_raw_prefix(raw)
    return not decoded or decoded in source


def _piece_preserves_from_decoded(existing:str,piece:str,source:str)->bool:
    raw="";escaped=False;unicode_left=0
    for char in piece:
        if unicode_left:
            raw+=char;unicode_left-=1
        elif escaped:
            raw+=char;escaped=False
            if char=="u": unicode_left=4
        elif char=="\\": raw+=char;escaped=True
        elif char=='"':
            addition,complete=_decode_raw_prefix(raw);combined=existing+addition
            return complete and bool(combined) and combined in source
        else: raw+=char
        addition,_complete=_decode_raw_prefix(raw);combined=existing+addition
        if combined and combined not in source: return False
    addition,_complete=_decode_raw_prefix(raw);combined=existing+addition
    return not combined or combined in source


def _transition_piece_preserves_sources(state:Any,piece:str,candidate:str,factual_summary:str)->bool:
    current=state;raw=""
    for char in piece:
        before=_field(current)
        if before is not None:
            source=candidate if before=="candidate_span" else factual_summary
            if not _piece_preserves_exact_substring(raw,char,source): return False
        try: after=current.feed(char)
        except ValueError: return False
        after_field=_field(after)
        if before is not None and after_field==before: raw+=char
        elif after_field is None: raw=""
        current=after
    return True


def _decode_raw_prefix(raw:str)->tuple[str,bool]:
    output=[];index=0;complete=True
    while index<len(raw):
        char=raw[index]
        if char!="\\": output.append(char);index+=1;continue
        if index+1>=len(raw): complete=False;break
        escape=raw[index+1]
        if escape=="u":
            digits=raw[index+2:index+6]
            if len(digits)<4: complete=False;break
            try: output.append(chr(int(digits,16)))
            except ValueError: return "",False
            index+=6;continue
        mapped=_ESCAPES.get(escape)
        if mapped is None: return "",False
        output.append(mapped);index+=2
    return "".join(output),complete


__all__=("SourceBoundProjectionReceiptV1","StagePSourceBoundTokenProjectorV1")
