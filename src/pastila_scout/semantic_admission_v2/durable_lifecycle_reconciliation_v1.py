"""Authoritative reconciliation of append-only Stage P lifecycle evidence."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict,dataclass
from enum import StrEnum
from pathlib import Path


class ObservedPhaseStatusV1(StrEnum):
    OBSERVED="OBSERVED"
    NOT_OBSERVED_BEFORE_TERMINAL_EVENT="NOT_OBSERVED_BEFORE_TERMINAL_EVENT"
    LIFECYCLE_UNAVAILABLE="LIFECYCLE_UNAVAILABLE"
    NOT_APPLICABLE="NOT_APPLICABLE"


@dataclass(frozen=True)
class DurableLifecycleReconciliationV1:
    lifecycle_relative_path:str
    file_count:int
    tree_identity:str
    last_host_event:str|None
    last_runner_event:str|None
    reconciliation_status:str
    tokenizer_load:str
    model_load:str
    generation:str
    terminal_eos:str
    response_persisted:str
    host_timeout:str

    def as_json_value(self)->dict[str,object]: return asdict(self)


def reconcile_durable_lifecycle_v1(*,root:Path,relative_path:str,expected_runner_sha256:str,
        expected_dependency_identities:dict[str,str])->DurableLifecycleReconciliationV1:
    if not root.is_dir(): return _unavailable(relative_path)
    files=sorted(root.glob("*.json"),key=lambda item:item.name)
    if not files: return _unavailable(relative_path)
    events=[];tree_lines=[]
    try:
        for path in sorted(files,key=lambda item:item.name):
            raw=path.read_bytes();value=json.loads(raw);events.append(value)
            if not path.name.startswith(f"{value.get('actor')}-{value.get('sequence',-1):05d}-"):
                raise ValueError("LIFECYCLE_FILENAME_IDENTITY_MISMATCH")
            tree_lines.append(f"{path.name}\t{hashlib.sha256(raw).hexdigest()}")
        _validate_sequences(events)
        launch=next(item for item in events if item["actor"]=="host" and item["event"]=="HOST_LAUNCH")
        if launch.get("runner_sha256")!=expected_runner_sha256 or launch.get("dependency_identities")!=expected_dependency_identities:
            raise ValueError("LIFECYCLE_IDENTITY_MISMATCH")
        _validate_order(events)
    except Exception:
        return _unavailable(relative_path)
    host=[item for item in events if item["actor"]=="host"];runner=[item for item in events if item["actor"]=="runner"]
    terminal=any(item["event"] in {"HOST_PROCESS_EXITED","HOST_TIMEOUT","RUNNER_EXCEPTION","RESPONSE_PERSISTED"} for item in events)
    names={item["event"] for item in events}
    status=lambda name:_phase(name in names,terminal)
    tree=hashlib.sha256("\n".join(tree_lines).encode()).hexdigest()
    return DurableLifecycleReconciliationV1(relative_path,len(files),tree,host[-1]["event"] if host else None,
        runner[-1]["event"] if runner else None,"VALID",status("TOKENIZER_LOAD_COMPLETED"),status("MODEL_LOAD_COMPLETED"),
        status("GENERATION_STARTED"),status("TERMINAL_EOS"),status("RESPONSE_PERSISTED"),status("HOST_TIMEOUT"))


def _validate_sequences(events):
    for actor in ("host","runner"):
        group=sorted((item for item in events if item.get("actor")==actor),key=lambda item:item.get("sequence",-1))
        if group and [item.get("sequence") for item in group]!=list(range(1,len(group)+1)): raise ValueError("LIFECYCLE_SEQUENCE_INVALID")
    if any(item.get("actor") not in {"host","runner"} for item in events): raise ValueError("LIFECYCLE_ACTOR_INVALID")


def _validate_order(events):
    runner=[item["event"] for item in sorted((x for x in events if x["actor"]=="runner"),key=lambda x:x["sequence"])]
    ordered=("RUNNER_STARTED","REQUEST_VALIDATED","TOKENIZER_LOAD_STARTED","TOKENIZER_LOAD_COMPLETED","TRIE_BUILD_STARTED",
        "TRIE_BUILD_COMPLETED","PREWARM_STARTED","PREWARM_COMPLETED","MODEL_LOAD_STARTED","MODEL_LOAD_COMPLETED",
        "PROMPT_TOKENIZED","GENERATION_STARTED")
    positions=[runner.index(item) for item in ordered if item in runner]
    if positions!=sorted(positions): raise ValueError("LIFECYCLE_ORDER_INVALID")
    if "TERMINAL_EOS" in runner and "GENERATION_STARTED" not in runner: raise ValueError("LIFECYCLE_ORDER_INVALID")
    if "RESPONSE_PERSISTED" in runner and "TERMINAL_EOS" not in runner: raise ValueError("LIFECYCLE_ORDER_INVALID")


def _phase(observed,terminal):
    return (ObservedPhaseStatusV1.OBSERVED if observed else ObservedPhaseStatusV1.NOT_OBSERVED_BEFORE_TERMINAL_EVENT
        if terminal else ObservedPhaseStatusV1.LIFECYCLE_UNAVAILABLE).value


def _unavailable(relative):
    unavailable=ObservedPhaseStatusV1.LIFECYCLE_UNAVAILABLE.value
    return DurableLifecycleReconciliationV1(relative,0,"",None,None,"INVALID_OR_UNAVAILABLE",unavailable,unavailable,
        unavailable,unavailable,unavailable,unavailable)


__all__=("DurableLifecycleReconciliationV1","ObservedPhaseStatusV1","reconcile_durable_lifecycle_v1")
