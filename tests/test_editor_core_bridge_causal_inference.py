from __future__ import annotations
import json, sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
from generate_editor_core_bridge_causal_responses import fixture_smoke, requests
from audit_editor_core_bridge_causal_responses import EXPECTED

def test_fixture_is_nonexecuting():
    result=fixture_smoke()
    assert result["model_loaded"] is False and result["optimizer_steps"]==0

def test_development_requests_are_target_free():
    path=ROOT/"docs/artifacts/editor-core-editorial-mechanics-bridge-v1-development-requests.jsonl"
    rows=requests(path)
    assert len(rows)==24
    assert all(all(m["role"]!="assistant" for m in row["messages"]) for row in rows)

def test_candidate_inventory():
    assert len(EXPECTED)==7 and "r2" in EXPECTED
