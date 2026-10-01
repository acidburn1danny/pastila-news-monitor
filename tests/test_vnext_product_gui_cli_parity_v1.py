from __future__ import annotations
import json
from pathlib import Path
from pastila_scout.vnext_editor_vertical_slice_v1 import DECODING, GenerationEvidence
from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_product_gui_v1 import CanonicalProductGui, VOICE_STATE, render_html
from pastila_scout.vnext_product_orchestrator_v1 import FactualReviewInstruction, PolicyInstruction, ProductOrchestrator, bootstrap_store
from pastila_scout.vnext_r2_consolidation_binding_v1 import EXPECTED_LOCK_IDENTITY
from pastila_scout.vnext_scout_production_v1 import FetchResponse, SourceDefinition, source_set_from_definitions

class Backend:
    r2_lock_identity = EXPECTED_LOCK_IDENTITY
    def generate(self, messages, decoding):
        assert decoding == DECODING
        event = messages[1]["content"].split('"case_id":"', 1)[1].split('"', 1)[0]
        raw = json.dumps({"case_id": event, "text": "Guvernul a anuntat masura de 10 milioane de lei."}, separators=(",", ":")).encode()
        return GenerationEvidence(rendered_prompt=json.dumps(messages), input_token_ids=(1,2,3), raw_output=raw, eos_token_id=2, pad_token_id=0, chat_template_sha256="1"*64)

def startup(_root):
    return {"status":"PASS_STARTUP_READY","product_lock_identity":"test-lock","legacy_dependency_count":0}

def transport(definition, _timeout):
    body=("<rss><channel><item><title>Guvernul anunta masura</title>"+f"<link>https://{definition.source_id}.example/a</link>"+"<description>Guvernul a anuntat masura de 10 milioane de lei.</description></item></channel></rss>").encode()
    return FetchResponse(body,definition.url,"application/rss+xml")

def build_gui(tmp_path):
    product=tmp_path/"product";product.mkdir()
    store=bootstrap_store(tmp_path/"work",writer_identity="gui-test")
    return CanonicalProductGui(product_root=product,orchestrator=ProductOrchestrator(store),canonical_startup=startup),store

def test_gui_delegates_complete_e2e_and_matches_canonical_state(tmp_path):
    gui,store=build_gui(tmp_path);workflow="gui-flow"
    assert gui.create_workflow(workflow).workflow_state=="DISCOVERED"
    sources=source_set_from_definitions((SourceDefinition("s1","S1","https://s1.example/feed",("politica",),5),SourceDefinition("s2","S2","https://s2.example/feed",("politica",),5)))
    groups,failures=gui.capture_and_group(workflow_identity=workflow,source_set=sources,transport=transport,captured_at="2026-10-01T00:00:00Z",maximum_workers=2)
    assert failures==() and len(groups)==1
    gui.select_and_generate_editor_draft(workflow_identity=workflow,selected_event_identity=groups[0].event_identity,selection_actor="Daniel",selection_authorization_identity="a"*64,backend=Backend(),source_packet_observed_at="2026-10-01T00:01:00Z",editor_observed_at="2026-10-01T00:02:00Z")
    assert gui.snapshot(workflow).workflow_state=="FACTUAL_REVIEW_PENDING"
    gui.apply_factual_review(workflow,instruction=FactualReviewInstruction("reviewer","ACCEPT_DRAFT",object_identity({"authority":"factual"}),"SOURCE_BOUND_REVIEW",()),observed_at="2026-10-01T00:03:00Z")
    exported=gui.apply_policy_and_export(workflow,instruction=PolicyInstruction("publisher","APPROVE_FINAL",object_identity({"authority":"policy"}),"PUBLICATION_APPROVED"),policy_entry_observed_at="2026-10-01T00:04:00Z",policy_decision_observed_at="2026-10-01T00:05:00Z",final_observed_at="2026-10-01T00:06:00Z")
    view=gui.snapshot(workflow)
    assert view.workflow_state==store.load_workflow(workflow)["state"]=="EXPORTED"
    assert view.terminal and view.allowed_actions==()
    assert view.voice_state==VOICE_STATE=="DISABLED_UNTIL_PROMOTION"
    assert (store.root/exported.receipt["export_ref"]).is_file()
    assert store.verify_integrity()["status"]=="PASS"

def test_restart_recovery_uses_persisted_authority(tmp_path):
    gui,store=build_gui(tmp_path);workflow="recovery-flow";gui.create_workflow(workflow)
    restarted=CanonicalProductGui(product_root=gui.product_root,orchestrator=ProductOrchestrator(bootstrap_store(store.root,writer_identity="gui-test")),canonical_startup=startup)
    assert restarted.recover(workflow)==gui.snapshot(workflow)

def test_html_is_presentation_only_and_escapes_input(tmp_path):
    gui,_=build_gui(tmp_path);document=render_html(gui.create_workflow("<unsafe>"))
    assert "<unsafe>" not in document and "&lt;unsafe&gt;" in document
    assert "DISABLED_UNTIL_PROMOTION" in document and "sqlite" not in document.lower()

def test_gui_module_has_no_sql_or_second_workflow():
    source=(Path(__file__).resolve().parents[1]/"src/pastila_scout/vnext_product_gui_v1.py").read_text()
    assert "sqlite3" not in source and "SELECT " not in source and "INSERT " not in source
    assert "TransitionRequest" not in source and "PASS_STARTUP_READY" in source


def test_terminal_restart_rehydrates_and_cli_gui_share_startup(tmp_path):
    gui,store=build_gui(tmp_path)
    workflow="terminal-recovery"
    gui.create_workflow(workflow)
    sources=source_set_from_definitions((SourceDefinition("s1","S1","https://s1.example/feed",("politica",),5),))
    groups,_=gui.capture_and_group(workflow_identity=workflow,source_set=sources,transport=transport,captured_at="2026-10-01T01:00:00Z")
    gui.select_and_generate_editor_draft(workflow_identity=workflow,selected_event_identity=groups[0].event_identity,selection_actor="Daniel",selection_authorization_identity="b"*64,backend=Backend(),source_packet_observed_at="2026-10-01T01:01:00Z",editor_observed_at="2026-10-01T01:02:00Z")
    gui.apply_factual_review(workflow,instruction=FactualReviewInstruction("reviewer","ACCEPT_DRAFT",object_identity({"authority":"factual-2"}),"SOURCE_BOUND_REVIEW",()),observed_at="2026-10-01T01:03:00Z")
    gui.apply_policy_and_export(workflow,instruction=PolicyInstruction("publisher","APPROVE_FINAL",object_identity({"authority":"policy-2"}),"PUBLICATION_APPROVED"),policy_entry_observed_at="2026-10-01T01:04:00Z",policy_decision_observed_at="2026-10-01T01:05:00Z",final_observed_at="2026-10-01T01:06:00Z")
    restarted=CanonicalProductGui(product_root=gui.product_root,orchestrator=ProductOrchestrator(bootstrap_store(store.root,writer_identity="gui-test")),canonical_startup=startup)
    recovered=restarted.recover(workflow)
    assert recovered.workflow_state=="EXPORTED" and recovered.terminal
    launcher=(Path(__file__).resolve().parents[1]/"scripts/vnext_product_gui_cli_v1.py").read_text()
    assert launcher.count("from product import startup")==1
    assert "preflight" not in launcher
