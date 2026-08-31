from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

from pastila_scout.humor_batch2_constructor_access_v1 import prepare_development_constructor_access_v1

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "26403a36e5817d269cfd56f880398200170868da"
RELEASE = "docs/artifacts/humor-mechanics-batch2-development-pilot06-constructor-access-release-v2.json"


def test_pilot06_release_prepares_without_constructor_invocation():
    release_bytes = subprocess.check_output(["git", "show", f"{COMMIT}:{RELEASE}"], cwd=ROOT)
    prepared = prepare_development_constructor_access_v1(release_bytes=release_bytes)
    assert prepared.release_identity == "3412c9f6b7b0ec2ca459464967d7831d514b030668a5e5d780af54e9ba65bbe8"
    assert prepared.packet_identity == "2a167fcb462ccf7a860fc3b77f49343afd11a211e218919983cf60dc211cb76f"
    packet = json.loads(prepared.packet_bytes)
    context = packet["exact_authorized_visible_context_utf8"].encode()
    assert hashlib.sha256(context).hexdigest() == "51d1891c346d6e7aa1f6b33da5a1d964cc99c2789d255ac7fd54999181a20dcd"
    assert packet["selected_proposition_id"] == "P3"


def test_pilot06_constructor_branch_is_source_bound_without_invocation():
    path = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v1.py"
    text = path.read_text(encoding="utf-8")
    ast.parse(text)
    branch = text.split("2a167fcb462ccf7a860fc3b77f49343afd11a211e218919983cf60dc211cb76f", 1)[1].split("elif", 1)[0]
    assert "calendarul bibliotecii rămâne fără o zi" in branch
    assert "+ lines[-1]" in branch
    assert "construct_development_candidate_v1(" not in branch
