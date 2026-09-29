from __future__ import annotations
import copy, json, subprocess, sys
from pathlib import Path
import pytest
from pastila_scout.vnext_editor_vertical_slice_v1 import EditorVerticalSliceError, GenerationEvidence, run_editor_vertical_slice, validate_editor_draft
from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION
from pastila_scout.vnext_r2_consolidation_binding_v1 import EXPECTED_LOCK_IDENTITY
ART=Path('docs/artifacts')

def load(name): return json.loads((ART/name).read_text(encoding='utf-8'))
def test_authorities_and_transitive_auditor():
    for name,key in (('vnext-consolidated-operational-state-sqlite-boundary-v6-contract.json','authority_identity'),('vnext-active-authority-audit-manifest-v1.json','manifest_identity'),('vnext-cross-component-eligibility-evidence-recovery-transitive-repair-v1.json','closure_identity')):
        value=load(name); assert value[key]==object_identity({k:v for k,v in value.items() if k!=key})
    manifest=load('vnext-active-authority-audit-manifest-v1.json')
    assert 'src/pastila_scout/vnext_r2_consolidation_binding_v1.py' in manifest['active_runtime_modules']
    assert SCHEMA_VERSION==6
    run=subprocess.run([sys.executable,'scripts/audit_vnext_final_atomic_publication_recovery_authority_v1.py'],check=True,capture_output=True,text=True)
    assert json.loads(run.stdout)['status']=='PASS'
def test_draft_text_is_bound_to_parsed_evidence():
    fixture=load('vnext-critical-path-authority-repair-editor-vertical-slice-v1-fixture.json')
    packet=load('vnext-sourcepacket-production-binding-v1-fixture.json')['source_packet']
    evidence=GenerationEvidence(fixture['rendered_prompt'],tuple(fixture['input_token_ids']),fixture['raw_output'].encode(),fixture['eos_token_id'],fixture['pad_token_id'],fixture['chat_template_sha256'])
    class Backend:
        r2_lock_identity=EXPECTED_LOCK_IDENTITY
        def generate(self,messages,decoding): return evidence
    invocation,draft=run_editor_vertical_slice(packet,Backend())
    draft=copy.deepcopy(draft); draft['text']+=' alterat'; draft['draft_identity']=object_identity({k:v for k,v in draft.items() if k!='draft_identity'})
    with pytest.raises(EditorVerticalSliceError,match='parsed-text'):
        validate_editor_draft(draft,source_packet=packet,invocation_receipt=invocation)
def test_five_findings_declared_closed_without_activation():
    closure=load('vnext-cross-component-eligibility-evidence-recovery-transitive-repair-v1.json')
    assert len(closure['blocker_closure'])==5 and {v['status'] for v in closure['blocker_closure'].values()}=={'CLOSED'}
    assert closure['invariants']['audit_streak']=='0/2' and not closure['invariants']['active_integration']
