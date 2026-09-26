from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def worker():
    path = ROOT / "scripts/editor_core_factual_setup_r2_anchored_contrastive_safety_fixture_v1.py"
    spec = importlib.util.spec_from_file_location("anchored_fixture", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_build_audit_and_fixture_smoke_are_reproducible():
    commands = (
        "build_editor_core_factual_setup_r2_anchored_contrastive_safety_v1.py",
        "audit_editor_core_factual_setup_r2_anchored_contrastive_safety_v1.py",
        "smoke_editor_core_factual_setup_r2_anchored_contrastive_safety_v1.py",
    )
    for name in commands:
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, check=True, capture_output=True, text=True)
        if name != commands[0]:
            assert json.loads(result.stdout)["status"].startswith("PASS")


def test_pairs_change_only_text_and_mutations_fail_closed():
    module = worker()
    path = ROOT / "docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-minimal-pairs.jsonl"
    pairs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(pairs) == 48
    for pair in pairs:
        module.validate_pair(pair)
    bad = copy.deepcopy(pairs[0]); bad["rejected_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="rejected identity"):
        module.validate_pair(bad)
    bad = copy.deepcopy(pairs[0]); bad_rejected = json.loads(bad["rejected_response"]); bad_rejected["case_id"] = "mutated"; bad["rejected_response"] = json.dumps(bad_rejected, ensure_ascii=False, sort_keys=True, separators=(",", ":")); bad["rejected_sha256"] = module.identity(bad_rejected)
    with pytest.raises(ValueError, match="pair scaffold"):
        module.validate_pair(bad)


def test_objectives_gradient_probe_and_decisions():
    module = worker()
    assert module.contrastive_hinge(-0.5, -1.0) == 0.0
    assert module.contrastive_hinge(-1.0, -1.0) == 0.25
    assert module.forward_kl([0.5, 0.5], [0.5, 0.5]) == 0.0
    with pytest.raises(ValueError, match="zero required gradient"):
        module.cosine([0.0, 0.0], [1.0, 0.0])
    matrix = {(failure, layer): [1.0, 0.5] for failure in module.FAILURE_CLASSES for layer in module.LAYER_GROUPS}
    probe = module.gradient_probe(matrix, matrix)
    assert len(probe["rows"]) == 36 and probe["strong_conflicts"] == 0
    good = {"material_regressions": 0, "novel_actor_or_repetition": False, "replicated_gain_seeds": 3, "pairwise_margin_classes": 6, "retention_pass_seeds": 3, "strong_unresolved_conflicts": 0}
    assert module.decide(good) == "CONTINUE_RESEARCH"
    bad = {**good, "material_regressions": 1}
    assert module.decide(bad) == "STOP"
    revise = {**good, "retention_pass_seeds": 2}
    assert module.decide(revise) == "REVISE"


def test_boundary_has_zero_real_authority_and_no_ml_imports():
    boundary = json.loads((ROOT / "docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-execution-boundary.json").read_text(encoding="utf-8"))
    assert len(boundary["slots"]) == 12
    assert all(not row["real_execution_authorized"] for row in boundary["slots"])
    for field in ("model_load_authorized", "optimizer_creation_authorized", "training_authorized", "inference_authorized", "parent_selection_authority", "historical_holdouts_allowed"):
        assert boundary[field] is False
    source = (ROOT / "scripts/editor_core_factual_setup_r2_anchored_contrastive_safety_fixture_v1.py").read_text(encoding="utf-8")
    assert "\nimport torch" not in source and "\nfrom torch" not in source
    assert "\nimport transformers" not in source and "\nfrom transformers" not in source
    assert "def train" not in source.casefold() and "def create_optimizer" not in source.casefold()
