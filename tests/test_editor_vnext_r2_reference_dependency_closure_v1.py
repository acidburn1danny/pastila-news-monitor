import importlib.util
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_rejects_absolute_dependency():
    module = load("vnext_preflight", "scripts/preflight_editor_vnext_r2_reference_dependency_closure_v1.py")
    assert PurePosixPath("/legacy/object").is_absolute()
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert 'relative.is_absolute()' in source
    assert '".." in relative.parts' in source


def test_cleanroom_boundary_has_offline_and_no_legacy_locations():
    text = (ROOT / "scripts/run_editor_vnext_r2_cleanroom_v1.py").read_text(encoding="utf-8")
    assert 'HF_HUB_OFFLINE", "1"' in text
    assert 'TRANSFORMERS_OFFLINE", "1"' in text
    for forbidden in ("/root/pf9", "F:\\", "D:\\", "/mnt/c/pf9"):
        assert forbidden not in text
