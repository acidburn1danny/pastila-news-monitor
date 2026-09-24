from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_route_propagates_positional_arguments_10_through_14() -> None:
    values = [f"argument-{index}" for index in range(1, 15)]
    script = 'printf "%s\\n" "${10}" "${11}" "${12}" "${13}" "${14}"'
    result = subprocess.run(
        ["bash", "-c", script, "child", *values],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.splitlines() == values[9:14]

    route = (ROOT / "scripts/run_editor_core_bridge_causal_inference_v31.sh").read_text("utf-8")
    assert '"${14}:editor_core_bridge_json_constraint_v3.py"' in route
    assert '"$14:editor_core_bridge_json_constraint_v3.py"' not in route


def test_v31_authority_identity_and_source_closure() -> None:
    path = ROOT / "docs/artifacts/editor-core-editorial-bridge-causal-inference-authority-v31.json"
    value = json.loads(path.read_bytes())
    core = {key: item for key, item in value.items() if key != "authority_identity"}
    identity = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert value["authority_identity"] == identity
    assert value["supersedes_authority_identity"] == "06836c28596c8bd02d4539f10da6a9ae550ccd1f96ccaa6653a458ebfee23593"
    assert value["route_path"].endswith("_v31.sh")
    for name in ("worker", "route", "audit", "verifier", "supervisor", "constraint", "preflight", "design"):
        assert hashlib.sha256((ROOT / value[f"{name}_path"]).read_bytes()).hexdigest() == value[f"{name}_sha256"]
