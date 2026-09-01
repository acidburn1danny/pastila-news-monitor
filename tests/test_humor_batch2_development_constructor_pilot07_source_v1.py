from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

from pastila_scout.humor_batch2_constructor_access_v1 import prepare_development_constructor_access_v1

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v1.py"
RELEASE_COMMIT = "3e49315afab444f3ab80f09ce63ffa327bc1031b"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-constructor-access-release-v3.json"


def test_pilot07_access_is_exactly_p5_and_constructor_branch_is_source_bound_without_invocation():
    release_bytes = subprocess.check_output(["git", "show", f"{RELEASE_COMMIT}:{RELEASE_PATH}"], cwd=ROOT)
    prepared = prepare_development_constructor_access_v1(release_bytes=release_bytes)
    packet = json.loads(prepared.packet_bytes)
    assert prepared.release_identity == "74c25b8c033c1c0d65a2c1196a92bccf0d556785d4754308d604d321ff78f8fe"
    assert prepared.packet_identity == "f52a1d542ddfb2ff10667dec1c22094132322500583ff39c07b80591e2dacdcf"
    assert packet["selected_proposition_id"] == "P5"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    text = SOURCE.read_text(encoding="utf-8")
    ast.parse(text)
    assert text.count(prepared.packet_identity) == 1
    branch = text.split(prepared.packet_identity, 1)[1].split("else:", 1)[0]
    assert "Într-o continuare imaginară" in branch
    assert "rubrica trebuie și ea analizată" in branch
    assert "lines[-1]" in branch
    assert "constructor_packet_bytes=" not in text.split("def construct_development_candidate_v1", 1)[0]
