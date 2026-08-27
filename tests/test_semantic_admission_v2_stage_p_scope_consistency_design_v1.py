import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DESIGN=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-case01-v2-scope-consistency-design-v1.json"

def _value(): return json.loads(DESIGN.read_text("utf-8"))
def test_design_is_bound_and_has_no_authority():
 value=_value();assert value["source_probe_identity"]=="bd1ee45ed047f8aababc88586f2ee5d5aa98243f9d9638d996f6abeae442da1f";assert not any(value["authority"].values())
def test_overlap_is_reconciled_not_banned():
 value=_value();principles=" ".join(value["governing_principles"]);assert "Overlap is not inherently invalid" in principles
 assert any(x["class"]=="UNSUPPORTED_PRESUPPOSITION_INSIDE_CREATIVE_HOST" for x in value["legitimate_overlap_examples"])
def test_scope_graph_has_host_relation_and_fail_closed_receipts():
 candidate=_value()["recommended_contract_candidate"];fields=" ".join(candidate["entry_additions"]);receipts=" ".join(candidate["coverage_receipt_additions"])
 assert "creative_host_entry_id" in fields and "factual_return_basis" in fields
 assert "overlapping_spans_reconciled" in receipts and "INDETERMINATE" in candidate["fail_closed"]
def test_case01_does_not_manufacture_real_world_components():
 result=_value()["factual_return_test"]["case01_application"];assert all("NO_INDEPENDENT_FACTUAL_RETURN" in x for x in result["component_results"].values())
def test_next_step_stops_before_prompt_and_runner():
 value=_value();assert "schema" in value["bounded_next_step_if_authorized"].lower();assert "do not modify the prompt" in value["bounded_next_step_if_authorized"]
