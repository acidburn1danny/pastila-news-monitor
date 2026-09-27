import copy
import importlib.util
import json
from pathlib import Path


def load_module():
    spec = importlib.util.spec_from_file_location("vnext_fixture", "scripts/fixture_editor_vnext_minimal_source_authority_diagnostic_v1.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


B = load_module()


def resign(value, key):
    value = copy.deepcopy(value)
    value.pop(key, None)
    value[key] = B.digest(B.enc(value))
    return value


def test_self_contained_fixture_boundary():
    result = B.run()
    assert result["status"] == "PASS_FIXTURE_ONLY"
    assert result["cases"] == 48 and result["source_spans"] == 144
    assert result["legacy_runtime_dependencies"] == 0 and result["persistent_artifacts"] == 3


def test_selector_is_id_only_and_cannot_invent_span():
    bundle, _ = B.load()
    fixture = copy.deepcopy(bundle["fixtures"][0])
    fixture["bounded_selector_fixture"]["add_span_ids"].append("invented")
    fixture = resign(fixture, "fixture_identity")
    try:
        B.validate_fixture(fixture)
    except ValueError as exc:
        assert "invented span" in str(exc)
    else:
        raise AssertionError("invented selector span accepted")

    expanded = copy.deepcopy(bundle["fixtures"][0])
    expanded["bounded_selector_fixture"]["free_text_facts_allowed"] = True
    expanded = resign(expanded, "fixture_identity")
    try:
        B.validate_fixture(expanded)
    except ValueError as exc:
        assert "selector authority expanded" in str(exc)
    else:
        raise AssertionError("selector authority expansion accepted")


def test_source_bytes_and_full_source_arm_fail_closed():
    bundle, _ = B.load()
    altered = copy.deepcopy(bundle["fixtures"][0])
    altered["source_packet"]["spans"][0]["text"] += " altered"
    altered["source_packet"] = resign(altered["source_packet"], "packet_identity")
    altered = resign(altered, "fixture_identity")
    try:
        B.validate_fixture(altered)
    except ValueError as exc:
        assert "source byte binding" in str(exc)
    else:
        raise AssertionError("altered source accepted")


def test_dependency_manifest_names_every_real_runtime_object():
    _, manifest = B.load()
    required = manifest["required_real_runtime_objects"]
    assert set(required) == {"role", "adapter_identity", "checkpoint_identity", "tokenizer_identity"}
    assert manifest["real_runtime_preflight"].startswith("FAIL_CLOSED")
    assert manifest["third_party_runtime_dependencies"] == []
    assert len(manifest["diagnostic_tooling"]) == 3
    for name, expected in manifest["diagnostic_tooling"].items():
        assert B.digest(Path(name).read_bytes()) == expected

    injected = copy.deepcopy(manifest)
    injected["legacy_runtime_dependencies"] = ["legacy/runtime/path"]
    injected = resign(injected, "manifest_identity")
    try:
        B.validate_manifest(injected)
    except ValueError as exc:
        assert "legacy runtime dependency" in str(exc)
    else:
        raise AssertionError("legacy dependency injection accepted")
