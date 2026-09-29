from __future__ import annotations
import copy, json
from pathlib import Path
import pytest
from pastila_scout.vnext_core_final_v1 import CoreFinalError, assemble_and_export_final, authorize_policy_session, build_policy_decision, enter_policy_review, persist_policy_decision
from pastila_scout.vnext_foundation_v1 import atomic_json, canonical_json, object_identity, sha256_bytes
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION, SQLiteStateStore
from pastila_scout.vnext_workflow_v1 import TransitionRequest

def transition(store,flow,left,right,index,output=None):
    sem={'flow':flow,'left':left,'right':right,'index':index}; ident=object_identity(sem)
    store.transition(TransitionRequest(flow,f'fixture:{index}',left,right,'fixture','PASS',object_identity(index),output,f'attempt:{ident}',f'idempotency:{ident}','2026-09-29T00:00:00Z'))

def make_store(tmp_path,kind='ACCEPTED_SETUP',flow='flow'):
    store=SQLiteStateStore(root=tmp_path,database=Path('state.db'),writer_identity='writer'); store.bootstrap(); store.create_workflow(flow)
    outcome='ACCEPT_DRAFT' if kind=='ACCEPTED_SETUP' else 'APPROVE_SOURCE_FALLBACK'
    review_input_identity='b'*64
    decision={
        'schema':'vnext-factual-review-decision','schema_version':2,'decision_kind':'FACTUAL',
        'outcome':outcome,'workflow_identity':flow,'review_session_identity':'e'*64,
        'actor':'reviewer','reason_code':'REVIEWED','source_packet_identity':'a'*64,
        'input_kind':'EDITOR_DRAFT','input_identity':review_input_identity,
        'fallback_span_ids':[] if kind=='ACCEPTED_SETUP' else ['span:1'],
        'authority_mode':'PERSISTED_SINGLE_USE_REVIEW_SESSION',
    }
    decision['decision_identity']=object_identity(decision)
    artifact={'schema':'vnext-factual-output','schema_version':2,'artifact_kind':kind,'workflow_identity':flow,'event_identity':'event:1','source_packet_identity':'a'*64,'review_input_kind':'EDITOR_DRAFT','review_input_identity':review_input_identity,'decision_identity':decision['decision_identity'],'text':'Un fapt verificat, păstrat exact.','eligible_for_voice':True,'requires_explicit_approval':kind=='SOURCE_FALLBACK'}
    artifact['artifact_identity']=object_identity(artifact)
    receipt={'schema':'vnext-factual-acceptance-receipt','schema_version':2,'workflow_identity':flow,'decision_identity':decision['decision_identity'],'input_identity':review_input_identity,'output_identity':artifact['artifact_identity'],'resulting_state':kind}
    receipt['receipt_identity']=object_identity(receipt)
    chain=[('DISCOVERED','CAPTURED'),('CAPTURED','GROUPED'),('GROUPED','SELECTED'),('SELECTED','SOURCE_PACKET_READY'),('SOURCE_PACKET_READY','EDITOR_PENDING'),('EDITOR_PENDING','EDITOR_DRAFT_READY'),('EDITOR_DRAFT_READY','FACTUAL_REVIEW_PENDING'),('FACTUAL_REVIEW_PENDING',kind)]
    for i,(left,right) in enumerate(chain,1): transition(store,flow,left,right,i,artifact['artifact_identity'] if right==kind else object_identity({'i':i}))
    artifact_rel=Path('blobs/factual-outputs')/f"{artifact['artifact_identity']}.json"
    decision_rel=Path('blobs/factual-decisions')/f"{decision['decision_identity']}.json"
    receipt_rel=Path('blobs/factual-receipts')/f"{receipt['receipt_identity']}.json"
    atomic_json(tmp_path/artifact_rel,artifact,root=tmp_path,overwrite=False)
    atomic_json(tmp_path/decision_rel,decision,root=tmp_path,overwrite=False)
    atomic_json(tmp_path/receipt_rel,receipt,root=tmp_path,overwrite=False)
    with store.write() as connection:
        connection.execute('INSERT INTO decisions VALUES(?,?,?,?,?,?,?)',(decision['decision_identity'],flow,'FACTUAL',outcome,'reviewer',review_input_identity,receipt['receipt_identity']))
        connection.execute('INSERT INTO workflow_artifacts VALUES(?,?,?,?,?,?)',(artifact['artifact_identity'],flow,kind,artifact['artifact_identity'],artifact_rel.as_posix(),'vnext-factual-output-v2'))
    return store,artifact

def approve(store,artifact,flow='flow'):
    enter_policy_review(store,workflow_identity=flow,factual_output=artifact,observed_at='2026-09-29T00:01:00Z')
    auth=object_identity({'owner':'Daniel','flow':flow})
    session=authorize_policy_session(store,workflow_identity=flow,factual_output=artifact,actor='Daniel',allowed_outcome='APPROVE_FINAL',authorization_identity=auth)
    assert authorize_policy_session(store,workflow_identity=flow,factual_output=artifact,actor='Daniel',allowed_outcome='APPROVE_FINAL',authorization_identity=auth)==session
    decision=build_policy_decision(workflow_identity=flow,factual_output=artifact,session=session,outcome='APPROVE_FINAL',actor='Daniel',reason_code='APPROVED')
    persist_policy_decision(store,workflow_identity=flow,factual_output=artifact,session=session,decision=decision,observed_at='2026-09-29T00:02:00Z')
    persist_policy_decision(store,workflow_identity=flow,factual_output=artifact,session=session,decision=decision,observed_at='2026-09-29T00:02:00Z')
    return decision

def test_approved_factual_output_reaches_byte_reproducible_export(tmp_path):
    store,artifact=make_store(tmp_path); decision=approve(store,artifact)
    final,receipt=assemble_and_export_final(store,workflow_identity='flow',factual_output=artifact,decision=decision,observed_at='2026-09-29T00:03:00Z')
    final2,receipt2=assemble_and_export_final(store,workflow_identity='flow',factual_output=artifact,decision=decision,observed_at='2026-09-29T00:03:00Z')
    assert (final2,receipt2)==(final,receipt) and store.load_workflow('flow')['state']=='EXPORTED'
    payload=(tmp_path/receipt['export_ref']).read_bytes(); assert payload==canonical_json(final)+b'\n' and sha256_bytes(payload)==receipt['export_sha256']
    assert final['text']==artifact['text'] and final['voice_mode']=='DISABLED'

def test_source_fallback_uses_same_explicit_policy_gate(tmp_path):
    store,artifact=make_store(tmp_path,kind='SOURCE_FALLBACK'); decision=approve(store,artifact)
    final,_=assemble_and_export_final(store,workflow_identity='flow',factual_output=artifact,decision=decision,observed_at='2026-09-29T00:03:00Z')
    assert final['factual_input_kind']=='SOURCE_FALLBACK'

@pytest.mark.parametrize(('outcome','state'),(('REJECT','REJECTED'),('REVISE','REVISION_REQUIRED')))
def test_nonapproval_stops_before_final(tmp_path,outcome,state):
    store,artifact=make_store(tmp_path); enter_policy_review(store,workflow_identity='flow',factual_output=artifact,observed_at='2026-09-29T00:01:00Z')
    auth=object_identity({'owner':'Daniel','outcome':outcome}); session=authorize_policy_session(store,workflow_identity='flow',factual_output=artifact,actor='Daniel',allowed_outcome=outcome,authorization_identity=auth)
    decision=build_policy_decision(workflow_identity='flow',factual_output=artifact,session=session,outcome=outcome,actor='Daniel',reason_code=outcome)
    persist_policy_decision(store,workflow_identity='flow',factual_output=artifact,session=session,decision=decision,observed_at='2026-09-29T00:02:00Z')
    assert store.load_workflow('flow')['state']==state
    with pytest.raises(CoreFinalError): assemble_and_export_final(store,workflow_identity='flow',factual_output=artifact,decision=decision,observed_at='2026-09-29T00:03:00Z')

def test_unowned_tampered_and_editor_draft_inputs_fail_closed(tmp_path):
    store,artifact=make_store(tmp_path)
    changed=copy.deepcopy(artifact); changed['text']='inventat'; changed['artifact_identity']=object_identity({k:v for k,v in changed.items() if k!='artifact_identity'})
    with pytest.raises(CoreFinalError): enter_policy_review(store,workflow_identity='flow',factual_output=changed,observed_at='2026-09-29T00:01:00Z')
    draft=copy.deepcopy(artifact); draft['artifact_kind']='EDITOR_DRAFT'; draft['artifact_identity']=object_identity({k:v for k,v in draft.items() if k!='artifact_identity'})
    with pytest.raises(CoreFinalError): enter_policy_review(store,workflow_identity='flow',factual_output=draft,observed_at='2026-09-29T00:01:00Z')

def test_schema_v6_and_integrity(tmp_path):
    store,_=make_store(tmp_path); assert SCHEMA_VERSION==6 and store.verify_integrity()['schema_version']==6
