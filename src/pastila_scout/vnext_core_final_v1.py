"""Isolated workflow policy and deterministic FINAL vertical slice."""
from __future__ import annotations
import json, re
from collections.abc import Mapping
from pathlib import Path
from .vnext_foundation_v1 import BoundaryError, atomic_json, canonical_json, contained_path, object_identity, sha256_bytes
from .vnext_state_sqlite_v1 import SQLiteStateStore
from .vnext_workflow_v1 import TransitionRequest

_SHA256=re.compile(r'[0-9a-f]{64}')
POLICY_OUTCOMES={'APPROVE_FINAL':'APPROVED_FOR_FINAL','REJECT':'REJECTED','REVISE':'REVISION_REQUIRED'}
FACTUAL_KINDS={'ACCEPTED_SETUP','SOURCE_FALLBACK'}
class CoreFinalError(BoundaryError):
    pass


def _load_owned_json(store: SQLiteStateStore, relative: Path, label: str) -> dict[str, object]:
    try:
        path = contained_path(store.root, relative, allow_missing=False)
        value = json.loads(path.read_text(encoding="utf-8"))
    except (BoundaryError, OSError, json.JSONDecodeError) as exc:
        raise CoreFinalError(f"{label} is missing or invalid") from exc
    if not isinstance(value, dict):
        raise CoreFinalError(f"{label} must be a JSON object")
    return value

def _identity(value:Mapping[str,object],key:str)->str:
    actual=value.get(key)
    if not isinstance(actual,str) or _SHA256.fullmatch(actual) is None or actual!=object_identity({k:v for k,v in value.items() if k!=key}): raise CoreFinalError(f'{key} mismatch')
    return actual

def _owned_factual(store:SQLiteStateStore,workflow_identity:str,artifact:Mapping[str,object])->None:
    identity=_identity(artifact,'artifact_identity'); kind=str(artifact.get('artifact_kind'))
    if kind not in FACTUAL_KINDS or artifact.get('workflow_identity')!=workflow_identity or not artifact.get('eligible_for_voice') or not isinstance(artifact.get('text'),str) or not artifact['text'].strip(): raise CoreFinalError('ineligible factual input')
    with store.read() as connection:
        row = connection.execute(
            "SELECT artifact_kind,payload_identity,payload_ref FROM workflow_artifacts "
            "WHERE workflow_identity=? AND artifact_identity=?",
            (workflow_identity, identity),
        ).fetchone()
        decision_row = connection.execute(
            "SELECT outcome,input_identity,receipt_identity FROM decisions "
            "WHERE workflow_identity=? AND decision_identity=? AND decision_kind='FACTUAL'",
            (workflow_identity, artifact.get("decision_identity")),
        ).fetchone()
        transition_row = connection.execute(
            "SELECT 1 FROM state_transitions WHERE workflow_identity=? "
            "AND resulting_state=? AND output_identity=?",
            (workflow_identity, kind, identity),
        ).fetchone()
    if row is None or tuple(row[:2]) != (kind, identity):
        raise CoreFinalError("factual input is not owned by workflow")
    expected_outcome = "ACCEPT_DRAFT" if kind == "ACCEPTED_SETUP" else "APPROVE_SOURCE_FALLBACK"
    if (
        decision_row is None
        or decision_row["outcome"] != expected_outcome
        or decision_row["input_identity"] != artifact.get("review_input_identity")
        or transition_row is None
    ):
        raise CoreFinalError("persisted factual acceptance provenance missing")
    persisted_artifact = _load_owned_json(store, Path(str(row["payload_ref"])), "factual input")
    if persisted_artifact != artifact:
        raise CoreFinalError("factual input payload mismatch")
    decision = _load_owned_json(
        store,
        Path("blobs/factual-decisions") / f"{artifact['decision_identity']}.json",
        "factual decision",
    )
    _identity(decision, "decision_identity")
    if (
        decision.get("decision_identity") != artifact.get("decision_identity")
        or decision.get("workflow_identity") != workflow_identity
        or decision.get("outcome") != expected_outcome
        or decision.get("input_identity") != artifact.get("review_input_identity")
    ):
        raise CoreFinalError("persisted factual decision payload mismatch")
    receipt = _load_owned_json(
        store,
        Path("blobs/factual-receipts") / f"{decision_row['receipt_identity']}.json",
        "factual receipt",
    )
    _identity(receipt, "receipt_identity")
    if (
        receipt.get("receipt_identity") != decision_row["receipt_identity"]
        or receipt.get("workflow_identity") != workflow_identity
        or receipt.get("decision_identity") != artifact.get("decision_identity")
        or receipt.get("input_identity") != artifact.get("review_input_identity")
        or receipt.get("output_identity") != identity
        or receipt.get("resulting_state") != kind
    ):
        raise CoreFinalError("persisted factual receipt payload mismatch")

def _transition(store:SQLiteStateStore,workflow:str,left:str,right:str,operation:str,input_identity:str,output_identity:str|None,actor:str,outcome:str,observed_at:str)->None:
    semantic={'workflow':workflow,'left':left,'right':right,'operation':operation,'input':input_identity,'output':output_identity,'actor':actor,'outcome':outcome}
    ident=object_identity(semantic)
    store.transition(TransitionRequest(workflow,operation,left,right,actor,outcome,input_identity,output_identity,f'attempt:{ident}',f'idempotency:{ident}',observed_at,{'component':'VNext Core Workflow to Deterministic FINAL Vertical Slice v1'}))

def enter_policy_review(store:SQLiteStateStore,*,workflow_identity:str,factual_output:Mapping[str,object],observed_at:str)->None:
    _owned_factual(store,workflow_identity,factual_output); ident=str(factual_output['artifact_identity']); state=store.load_workflow(workflow_identity)['state']; kind=str(factual_output['artifact_kind'])
    if state==kind:
        _transition(store,workflow_identity,kind,'VOICE_DISABLED','core:voice-disabled',ident,None,'system','VOICE_DISABLED',observed_at); state='VOICE_DISABLED'
    if state=='VOICE_DISABLED': _transition(store,workflow_identity,'VOICE_DISABLED','POLICY_REVIEW_PENDING','core:policy-pending',ident,None,'system','POLICY_REQUIRED',observed_at); state='POLICY_REVIEW_PENDING'
    if state!='POLICY_REVIEW_PENDING': raise CoreFinalError(f'workflow is not policy-ready: {state}')

def authorize_policy_session(store:SQLiteStateStore,*,workflow_identity:str,factual_output:Mapping[str,object],actor:str,allowed_outcome:str,authorization_identity:str)->dict[str,object]:
    _owned_factual(store,workflow_identity,factual_output)
    if allowed_outcome not in POLICY_OUTCOMES or not actor.strip() or _SHA256.fullmatch(authorization_identity) is None: raise CoreFinalError('invalid policy authority request')
    if store.load_workflow(workflow_identity)['state']!='POLICY_REVIEW_PENDING': raise CoreFinalError('workflow is not ready for policy authority')
    request=object_identity({'workflow_identity':workflow_identity,'actor':actor.strip(),'input_identity':factual_output['artifact_identity'],'allowed_outcome':allowed_outcome,'authorization_identity':authorization_identity})
    session={'schema':'vnext-policy-session','schema_version':1,'request_identity':request,'workflow_identity':workflow_identity,'issued_by':store.writer_identity,'actor':actor.strip(),'input_kind':factual_output['artifact_kind'],'input_identity':factual_output['artifact_identity'],'allowed_outcome':allowed_outcome,'authorization_identity':authorization_identity,'status':'OPEN'}
    session['policy_session_identity']=object_identity(session)
    with store.write() as connection:
        row=connection.execute('SELECT policy_session_identity,workflow_identity,issued_by,actor,input_kind,input_identity,allowed_outcome,authorization_identity,request_identity FROM policy_sessions WHERE request_identity=?',(request,)).fetchone()
        expected=(session['policy_session_identity'],workflow_identity,store.writer_identity,session['actor'],session['input_kind'],session['input_identity'],allowed_outcome,authorization_identity,request)
        if row is not None:
            if tuple(row)!=expected: raise CoreFinalError('conflicting policy-session replay')
            return session
        insert_values=(session['policy_session_identity'],request,workflow_identity,store.writer_identity,session['actor'],session['input_kind'],session['input_identity'],allowed_outcome,authorization_identity)
        connection.execute('INSERT INTO policy_sessions(policy_session_identity,request_identity,workflow_identity,issued_by,actor,input_kind,input_identity,allowed_outcome,authorization_identity,status,decision_identity) VALUES(?,?,?,?,?,?,?,?,?,\'OPEN\',NULL)',insert_values)
    return session

def build_policy_decision(*,workflow_identity:str,factual_output:Mapping[str,object],session:Mapping[str,object],outcome:str,actor:str,reason_code:str)->dict[str,object]:
    sid=_identity(session,'policy_session_identity')
    if session.get('schema')!='vnext-policy-session' or session.get('schema_version')!=1 or session.get('workflow_identity')!=workflow_identity or session.get('input_kind')!=factual_output.get('artifact_kind') or session.get('input_identity')!=factual_output.get('artifact_identity') or session.get('allowed_outcome')!=outcome or session.get('actor')!=actor.strip() or session.get('status')!='OPEN' or outcome not in POLICY_OUTCOMES or not reason_code.strip(): raise CoreFinalError('policy-session authority mismatch')
    value={'schema':'vnext-policy-decision','schema_version':1,'decision_kind':'APPROVAL','outcome':outcome,'workflow_identity':workflow_identity,'policy_session_identity':sid,'actor':actor.strip(),'reason_code':reason_code.strip(),'input_kind':factual_output['artifact_kind'],'input_identity':factual_output['artifact_identity']}
    value['decision_identity']=object_identity(value); return value

def persist_policy_decision(store:SQLiteStateStore,*,workflow_identity:str,factual_output:Mapping[str,object],session:Mapping[str,object],decision:Mapping[str,object],observed_at:str)->None:
    _owned_factual(store,workflow_identity,factual_output); did=_identity(decision,'decision_identity'); sid=_identity(session,'policy_session_identity'); outcome=str(decision.get('outcome'))
    if outcome not in POLICY_OUTCOMES or decision.get('workflow_identity')!=workflow_identity or decision.get('policy_session_identity')!=sid or decision.get('input_identity')!=factual_output.get('artifact_identity') or session.get('allowed_outcome')!=outcome: raise CoreFinalError('policy decision provenance mismatch')
    target=POLICY_OUTCOMES[outcome]; relative=Path('blobs/policy-decisions')/f'{did}.json'; path=contained_path(store.root,relative)
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=decision: raise CoreFinalError('immutable policy decision conflict')
    else: atomic_json(path,dict(decision),root=store.root,overwrite=False)
    state=store.load_workflow(workflow_identity)['state']
    if state==target:
        with store.read() as connection: row=connection.execute('SELECT status,decision_identity FROM policy_sessions WHERE policy_session_identity=?',(sid,)).fetchone()
        if row is not None and tuple(row)==('CONSUMED',did): return
        raise CoreFinalError('policy replay state mismatch')
    if state!='POLICY_REVIEW_PENDING': raise CoreFinalError('workflow is not policy-ready')
    def rows(connection):
        row=connection.execute('SELECT workflow_identity,issued_by,actor,input_kind,input_identity,allowed_outcome,authorization_identity,status FROM policy_sessions WHERE policy_session_identity=?',(sid,)).fetchone()
        expected=(workflow_identity,store.writer_identity,decision['actor'],decision['input_kind'],decision['input_identity'],outcome)
        if row is None or tuple(row[:6])!=expected or _SHA256.fullmatch(str(row['authorization_identity'])) is None or row['status']!='OPEN': raise CoreFinalError('policy session absent, mismatched, or consumed')
        connection.execute('INSERT INTO decisions VALUES(?,?,?,?,?,?,?)',(did,workflow_identity,'APPROVAL',outcome,decision['actor'],decision['input_identity'],object_identity({'decision':did,'target':target})))
        if connection.execute("UPDATE policy_sessions SET status='CONSUMED',decision_identity=? WHERE policy_session_identity=? AND status='OPEN'",(did,sid)).rowcount!=1: raise CoreFinalError('policy session was not consumed exactly once')
    semantic={'workflow':workflow_identity,'decision':did,'target':target}; ident=object_identity(semantic)
    store.transition(TransitionRequest(workflow_identity,'core:policy-decision','POLICY_REVIEW_PENDING',target,'POLICY',outcome,str(factual_output['artifact_identity']),did,f'attempt:{ident}',f'idempotency:{ident}',observed_at,{'component':'VNext Core Workflow to Deterministic FINAL Vertical Slice v1'}),before_commit=rows)

def _final_value(
    workflow_identity: str,
    factual_output: Mapping[str, object],
    decision_identity: str,
) -> dict[str, object]:
    final: dict[str, object] = {
        "schema": "vnext-final-output",
        "schema_version": 1,
        "artifact_kind": "FINAL_OUTPUT",
        "workflow_identity": workflow_identity,
        "source_packet_identity": factual_output["source_packet_identity"],
        "factual_input_kind": factual_output["artifact_kind"],
        "factual_input_identity": factual_output["artifact_identity"],
        "policy_decision_identity": decision_identity,
        "voice_mode": "DISABLED",
        "text": factual_output["text"],
        "assembly": "DETERMINISTIC_PASSTHROUGH_V1",
    }
    final["artifact_identity"] = object_identity(final)
    return final


def _export_receipt(
    workflow_identity: str,
    final_identity: str,
    export_ref: Path,
    payload: bytes,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema": "vnext-final-export-receipt",
        "schema_version": 1,
        "workflow_identity": workflow_identity,
        "final_identity": final_identity,
        "export_ref": export_ref.as_posix(),
        "export_sha256": sha256_bytes(payload),
        "export_size": len(payload),
    }
    receipt["receipt_identity"] = object_identity(receipt)
    return receipt


def load_exported_final(
    store: SQLiteStateStore,
    *,
    workflow_identity: str,
    final_identity: str,
) -> tuple[dict[str, object], dict[str, object]]:
    if store.load_workflow(workflow_identity)["state"] != "EXPORTED":
        raise CoreFinalError("FINAL output is not export-eligible")
    with store.read() as connection:
        row = connection.execute(
            "SELECT payload_identity,payload_ref FROM workflow_artifacts "
            "WHERE workflow_identity=? AND artifact_identity=? AND artifact_kind='FINAL_OUTPUT'",
            (workflow_identity, final_identity),
        ).fetchone()
    if row is None or row["payload_identity"] != final_identity:
        raise CoreFinalError("persisted FINAL ownership missing")
    final = _load_owned_json(store, Path(str(row["payload_ref"])), "FINAL payload")
    _identity(final, "artifact_identity")
    if (
        final.get("artifact_identity") != final_identity
        or final.get("workflow_identity") != workflow_identity
    ):
        raise CoreFinalError("persisted FINAL payload mismatch")
    receipt = _load_owned_json(
        store,
        Path("receipts/final-exports") / f"{final_identity}.json",
        "FINAL export receipt",
    )
    _identity(receipt, "receipt_identity")
    export_ref = receipt.get("export_ref")
    if (
        receipt.get("workflow_identity") != workflow_identity
        or receipt.get("final_identity") != final_identity
        or not isinstance(export_ref, str)
    ):
        raise CoreFinalError("FINAL export receipt provenance mismatch")
    export_path = contained_path(store.root, Path(export_ref), allow_missing=False)
    payload = export_path.read_bytes()
    if (
        receipt.get("export_sha256") != sha256_bytes(payload)
        or receipt.get("export_size") != len(payload)
        or payload != canonical_json(final) + b"\n"
    ):
        raise CoreFinalError("FINAL export bytes mismatch")
    return final, receipt


def assemble_and_export_final(
    store: SQLiteStateStore,
    *,
    workflow_identity: str,
    factual_output: Mapping[str, object],
    decision: Mapping[str, object],
    observed_at: str,
) -> tuple[dict[str, object], dict[str, object]]:
    _owned_factual(store, workflow_identity, factual_output)
    decision_identity = _identity(decision, "decision_identity")
    if (
        decision.get("outcome") != "APPROVE_FINAL"
        or decision.get("workflow_identity") != workflow_identity
        or decision.get("input_identity") != factual_output.get("artifact_identity")
    ):
        raise CoreFinalError("FINAL requires approved factual input")
    with store.read() as connection:
        row = connection.execute(
            "SELECT 1 FROM decisions WHERE workflow_identity=? AND decision_identity=? "
            "AND decision_kind='APPROVAL' AND outcome='APPROVE_FINAL'",
            (workflow_identity, decision_identity),
        ).fetchone()
    if row is None:
        raise CoreFinalError("persisted policy approval missing")

    final = _final_value(workflow_identity, factual_output, decision_identity)
    final_identity = str(final["artifact_identity"])
    payload = canonical_json(final) + b"\n"
    output_ref = Path("blobs/final-outputs") / f"{final_identity}.json"
    export_ref = Path("exports") / f"{final_identity}.json"
    receipt_ref = Path("receipts/final-exports") / f"{final_identity}.json"
    receipt = _export_receipt(workflow_identity, final_identity, export_ref, payload)

    state = store.load_workflow(workflow_identity)["state"]
    if state not in {"APPROVED_FOR_FINAL", "FINAL_READY", "EXPORTED"}:
        raise CoreFinalError(f"workflow is not FINAL-ready: {state}")

    output_path = contained_path(store.root, output_ref)
    if output_path.exists():
        if output_path.read_bytes() != payload:
            raise CoreFinalError(f"immutable FINAL conflict: {output_ref}")
    else:
        from .vnext_foundation_v1 import atomic_write
        atomic_write(output_path, payload, root=store.root, overwrite=False)

    if state == "APPROVED_FOR_FINAL":
        def persist_final(connection):
            connection.execute(
                "INSERT INTO workflow_artifacts VALUES(?,?,?,?,?,?)",
                (
                    final_identity,
                    workflow_identity,
                    "FINAL_OUTPUT",
                    final_identity,
                    output_ref.as_posix(),
                    "vnext-final-output-v1",
                ),
            )

        semantic = {"workflow": workflow_identity, "final": final_identity}
        transition_identity = object_identity(semantic)
        store.transition(
            TransitionRequest(
                workflow_identity,
                "core:final-assembly",
                "APPROVED_FOR_FINAL",
                "FINAL_READY",
                "FINAL",
                "PASS",
                decision_identity,
                final_identity,
                f"attempt:{transition_identity}",
                f"idempotency:{transition_identity}",
                observed_at,
                {"component": "VNext FINAL Atomic Publication, Recovery & Authority Semantics Repair v1"},
            ),
            before_commit=persist_final,
        )
        state = "FINAL_READY"

    if state == "FINAL_READY":
        from .vnext_foundation_v1 import atomic_write
        export_path = contained_path(store.root, export_ref)
        if export_path.exists():
            if export_path.read_bytes() != payload:
                raise CoreFinalError(f"immutable FINAL conflict: {export_ref}")
        else:
            atomic_write(export_path, payload, root=store.root, overwrite=False)
        receipt_path = contained_path(store.root, receipt_ref)
        if receipt_path.exists():
            if json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
                raise CoreFinalError("immutable FINAL export receipt conflict")
        else:
            atomic_json(receipt_path, receipt, root=store.root, overwrite=False)
        _transition(
            store,
            workflow_identity,
            "FINAL_READY",
            "EXPORTED",
            "core:final-export",
            final_identity,
            str(receipt["receipt_identity"]),
            "FINAL",
            "PASS",
            observed_at,
        )
        state = "EXPORTED"

    if state != "EXPORTED":
        raise CoreFinalError(f"workflow is not export-ready: {state}")
    persisted_final, persisted_receipt = load_exported_final(
        store,
        workflow_identity=workflow_identity,
        final_identity=final_identity,
    )
    if persisted_final != final or persisted_receipt != receipt:
        raise CoreFinalError("FINAL replay mismatch")
    return final, receipt
