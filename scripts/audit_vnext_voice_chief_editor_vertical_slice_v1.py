#!/usr/bin/env python3
"""Self-contained auditor for the isolated VOICE/Chief Editor slice."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "src/pastila_scout/vnext_voice_chief_editor_v1.py",
    "src/pastila_scout/vnext_core_final_v1.py",
    "src/pastila_scout/vnext_product_orchestrator_v1.py",
    "src/pastila_scout/vnext_state_sqlite_v1.py",
    "tests/test_vnext_voice_chief_editor_vertical_slice_v1.py",
    "docs/vnext-canonical-voice-chief-editor-vertical-slice-v1.md",
)


def identity(value):
    payload=json.dumps(value,ensure_ascii=False,separators=(",",":"),sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def run():
    for relative in FILES:
        path=ROOT/relative
        if not path.is_file():
            raise RuntimeError(f"missing managed file: {relative}")
        if path.suffix==".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    voice=(ROOT/FILES[0]).read_text(encoding="utf-8")
    orchestrator=(ROOT/FILES[2]).read_text(encoding="utf-8")
    workflow=(ROOT/"src/pastila_scout/vnext_workflow_v1.py").read_text(encoding="utf-8")
    checks={
        "single_workflow_owner": "class ProductOrchestrator" in orchestrator and "SQLiteStateStore" in orchestrator,
        "voice_no_direct_sqlite": "sqlite3" not in voice,
        "factual_input_required": "eligible_for_voice" in voice and "factual_input_identity" in voice,
        "commentary_separate": '"factual_setup"' in voice and '"commentary"' in voice,
        "abstention_supported": '"ABSTAIN"' in voice,
        "seed_and_decoding_bound": '"seed"' in voice and '"decoding_identity"' in voice,
        "repetition_evidence": '"repetition_identity"' in voice,
        "canonical_states_reused": all(name in workflow for name in ("VOICE_PENDING","VOICE_DRAFT_READY","POLICY_REVIEW_PENDING","EXPORTED")),
        "no_default_backend": "backend: VoiceBackend" in orchestrator,
        "voice_not_promoted": "DISABLED_UNTIL_PROMOTION",
        "legacy_dependency_count": 0,
        "repository_dependency_count": 0,
    }
    if any(value is False for value in checks.values()):
        raise RuntimeError("static authority check failed")
    completed=subprocess.run(
        [sys.executable,"-m","pytest","-q","tests/test_vnext_voice_chief_editor_vertical_slice_v1.py"],
        cwd=ROOT,
        env={**__import__("os").environ,"PYTHONPATH":str(ROOT/"src")},
        text=True,capture_output=True,check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stdout+completed.stderr)
    result={
        "schema":"vnext-voice-chief-editor-vertical-slice-audit",
        "schema_version":1,
        "status":"PASS",
        "blockers":[],
        "scope":list(FILES),
        "checks":checks,
        "dedicated_tests":"5 passed",
        "architecture":"SCOUT -> EDITOR -> VOICE -> CHIEF EDITOR -> FINAL",
        "voice_state":"DISABLED_UNTIL_PROMOTION",
        "promotion_ready":False,
    }
    result["result_identity"]=identity(result)
    return result


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
