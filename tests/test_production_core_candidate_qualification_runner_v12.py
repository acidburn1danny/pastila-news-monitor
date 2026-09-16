import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = ROOT / "scripts/materialize_production_core_candidate_qualification_runner_v12.py"
RUNNER = ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v12.py"
RESOLUTION = ROOT / ".pastila-runtime/production-core-successor-qualification-v10/local-object-resolution-v10.json"


def module():
    spec = importlib.util.spec_from_file_location("runner_v12_materializer", MATERIALIZER)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def constants():
    tree = ast.parse(RUNNER.read_text("utf-8"))
    names = {"EXPECTED_GENERATION", "EXPECTED_ADAPTERS", "EXPECTED_PROMPTS"}
    return {target.id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name) and target.id in names}


def manifest(root: Path):
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        assert not path.is_symlink() and path.is_file()
        raw = path.read_bytes()
        rows.append(path.name.encode() + b"\0" + len(raw).to_bytes(8, "big") + hashlib.sha256(raw).digest())
    return hashlib.sha256(b"".join(rows)).hexdigest()


def test_v12_runner_is_exact_five_binding_projection():
    value = module()
    assert RUNNER.read_bytes() == value.build()
    original = value.SOURCE.read_bytes()
    projected = RUNNER.read_bytes()
    for old, new in value.CHANGES.items():
        assert old.encode() in original and old.encode() not in projected
        assert new.encode() in projected


def test_v12_generation_and_prompt_bindings_match_v10_authority():
    values = constants()
    generation = json.loads((ROOT / "docs/artifacts/production-core-successor-comparative-qualification-generation-v10.json").read_bytes())
    assert values["EXPECTED_GENERATION"] == generation["qualification_generation_identity"]
    assert values["EXPECTED_PROMPTS"] == {
        "pastila-editor-core-v1.1-json-successor-v2": hashlib.sha256((ROOT / "docs/artifacts/pastila-editor-core-v1.1-json-successor-v10-system-prompt.txt").read_bytes()).hexdigest(),
        "pastila-editor-core-v1.2-json-successor": hashlib.sha256((ROOT / "docs/artifacts/pastila-editor-core-v1.2-json-successor-v10-system-prompt.txt").read_bytes()).hexdigest(),
    }


def test_v12_adapter_bindings_match_both_independent_materializations():
    values = constants()
    resolution = json.loads(RESOLUTION.read_bytes())
    for candidate, expected in values["EXPECTED_ADAPTERS"].items():
        observed = []
        for label in ("A", "B"):
            linux = resolution["materializations"][label]["adapters"][candidate]
            observed.append(manifest(Path("//wsl.localhost/Ubuntu-24.04" + linux)))
        assert observed == [expected, expected]


def test_materializer_rejects_source_drift(monkeypatch, tmp_path):
    value = module()
    source = tmp_path / "runner.py"
    source.write_bytes(value.SOURCE.read_bytes() + b"x")
    monkeypatch.setattr(value, "SOURCE", source)
    with pytest.raises(ValueError, match="source drift"):
        value.build()
