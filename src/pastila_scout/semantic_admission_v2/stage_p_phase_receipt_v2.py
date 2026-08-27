"""Phase-separated, fail-closed Stage P evidence receipts."""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import asdict,dataclass
from enum import StrEnum
from pathlib import Path


class EvidencePhaseStatusV2(StrEnum):
    SUCCESS="SUCCESS"
    FAIL="FAIL"
    NOT_RUN="NOT_RUN"


@dataclass(frozen=True)
class StagePPhaseReceiptV2:
    schema_name:str
    schema_version:str
    provider_call_count:int
    transport:EvidencePhaseStatusV2
    raw_persistence:EvidencePhaseStatusV2
    raw_path:str|None
    raw_sha256:str|None
    raw_bytes:int
    schema_validation:EvidencePhaseStatusV2
    source_membership:EvidencePhaseStatusV2
    reason_code:str
    final_decision:str
    eligibility:str="QUARANTINED_EVALUATION_ONLY"

    def as_json_value(self)->dict[str,object]:
        return asdict(self)


def classify_persisted_stage_p_v2(*,raw_path:Path|None,provider_called:bool,transport_succeeded:bool,
        schema_validator:Callable[[bytes],object],membership_validator:Callable[[object],None])->StagePPhaseReceiptV2:
    calls=int(provider_called)
    if not provider_called:
        return _receipt(calls,EvidencePhaseStatusV2.NOT_RUN,EvidencePhaseStatusV2.NOT_RUN,None,None,0,
            EvidencePhaseStatusV2.NOT_RUN,EvidencePhaseStatusV2.NOT_RUN,"STAGE_P_NOT_CALLED")
    if not transport_succeeded:
        return _receipt(calls,EvidencePhaseStatusV2.FAIL,EvidencePhaseStatusV2.NOT_RUN,None,None,0,
            EvidencePhaseStatusV2.NOT_RUN,EvidencePhaseStatusV2.NOT_RUN,"STAGE_P_PROVIDER_OR_TRANSPORT_FAILURE")
    if raw_path is None or not raw_path.is_file():
        return _receipt(calls,EvidencePhaseStatusV2.SUCCESS,EvidencePhaseStatusV2.FAIL,None,None,0,
            EvidencePhaseStatusV2.NOT_RUN,EvidencePhaseStatusV2.NOT_RUN,"STAGE_P_RAW_PERSISTENCE_FAILURE")
    raw=raw_path.read_bytes();digest=hashlib.sha256(raw).hexdigest();path=str(raw_path)
    try: parsed=schema_validator(raw)
    except Exception:
        return _receipt(calls,EvidencePhaseStatusV2.SUCCESS,EvidencePhaseStatusV2.SUCCESS,path,digest,len(raw),
            EvidencePhaseStatusV2.FAIL,EvidencePhaseStatusV2.NOT_RUN,"STAGE_P_SCHEMA_VALIDATION_FAILURE")
    try: membership_validator(parsed)
    except Exception as exc:
        code=("STAGE_P_CANDIDATE_SPAN_SOURCE_MEMBERSHIP_FAILURE" if str(exc)=="CANDIDATE_SPAN_NOT_IN_CANDIDATE"
            else "STAGE_P_AUTHORITY_SUPPORT_SOURCE_MEMBERSHIP_FAILURE" if str(exc)=="AUTHORITY_SUPPORT_NOT_IN_FACTUAL_SUMMARY"
            else "STAGE_P_SOURCE_MEMBERSHIP_FAILURE")
        return _receipt(calls,EvidencePhaseStatusV2.SUCCESS,EvidencePhaseStatusV2.SUCCESS,path,digest,len(raw),
            EvidencePhaseStatusV2.SUCCESS,EvidencePhaseStatusV2.FAIL,code)
    return _receipt(calls,EvidencePhaseStatusV2.SUCCESS,EvidencePhaseStatusV2.SUCCESS,path,digest,len(raw),
        EvidencePhaseStatusV2.SUCCESS,EvidencePhaseStatusV2.SUCCESS,"STAGE_P_VALID")


def execute_and_capture_stage_p_v2(*,evaluator:Callable[[dict[str,object]],str],request:dict[str,object],raw_path:Path,
        schema_validator:Callable[[bytes],object],membership_validator:Callable[[object],None])->StagePPhaseReceiptV2:
    """Invoke exactly once, persist returned bytes before either validation phase."""
    try:
        output=evaluator(request)
        if type(output) is not str: raise TypeError("STAGE_P_OUTPUT_NOT_STRING")
    except Exception:
        return classify_persisted_stage_p_v2(raw_path=None,provider_called=True,transport_succeeded=False,
            schema_validator=schema_validator,membership_validator=membership_validator)
    data=output.encode("utf-8")
    try:
        with raw_path.open("xb") as handle: handle.write(data);handle.flush();os.fsync(handle.fileno())
    except Exception:
        return classify_persisted_stage_p_v2(raw_path=None,provider_called=True,transport_succeeded=True,
            schema_validator=schema_validator,membership_validator=membership_validator)
    return classify_persisted_stage_p_v2(raw_path=raw_path,provider_called=True,transport_succeeded=True,
        schema_validator=schema_validator,membership_validator=membership_validator)


def persist_phase_receipt_v2(path:Path,receipt:StagePPhaseReceiptV2)->None:
    data=(json.dumps(receipt.as_json_value(),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")
    with path.open("xb") as handle: handle.write(data);handle.flush();os.fsync(handle.fileno())


def _receipt(calls,transport,raw_status,path,digest,size,schema,membership,reason):
    final="PASS_TO_NEXT_STAGE" if reason=="STAGE_P_VALID" else "ABSTAIN_FAIL_CLOSED"
    return StagePPhaseReceiptV2("pastila-semantic-admission-v2-stage-p-phase-receipt","2.0.0-evaluation.1",calls,
        transport,raw_status,path,digest,size,schema,membership,reason,final)


__all__=("EvidencePhaseStatusV2","StagePPhaseReceiptV2","classify_persisted_stage_p_v2",
    "execute_and_capture_stage_p_v2","persist_phase_receipt_v2")
