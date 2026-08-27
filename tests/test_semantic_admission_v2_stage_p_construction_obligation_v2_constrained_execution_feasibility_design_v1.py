from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-constrained-execution-feasibility-design-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-constrained-execution-feasibility-design-v1-evidence/preflight.json"


def test_design_identity_and_committed_dependencies_reproduce() -> None:
    design = json.loads(DESIGN.read_bytes())
    material = "\n".join(design["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == design["canonical_identity"]
    paths = {
        "system_prompt_sha256": ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
        "core_executor_sha256": "src/pastila_scout/experimental_core_v1_2.py",
        "unconstrained_runner_sha256": "src/pastila_scout/experimental_core_v1_2_runner.py",
        "wsl_boundary_v1_sha256": "src/pastila_scout/wsl_execution_v1/boundary.py",
        "wsl_boundary_v1_1_sha256": "src/pastila_scout/wsl_execution_v1_1/boundary.py",
    }
    for field, relative in paths.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == design["committed_bindings"][field]
    legacy = ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_construction_obligation_runner_v1.py"
    assert hashlib.sha256(legacy.read_bytes()).hexdigest() == design["legacy_non_equivalence"]["committed_v1_runner_sha256"]


def test_design_requires_new_lineage_and_stops_before_execution() -> None:
    design = json.loads(DESIGN.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert design["result"] == "FEASIBLE_NEW_V2_CONSTRAINED_EXECUTION_LINEAGE_REQUIRED"
    assert design["current_boundary_failure"]["code"] == "FROZEN_PROJECTOR_NOT_PROPAGATED_TO_EXECUTION_PROTOCOL"
    assert design["legacy_non_equivalence"]["disposition"] == "PRESERVE_BUT_PROHIBIT_AS_CURRENT_V2_IMPLEMENTATION"
    assert design["failure_separation"]["retry_repair_selection_fallback"] == 0
    assert design["authority"]["design_selection"] is True
    assert all(value is False for key, value in design["authority"].items() if key != "design_selection")
    assert preflight["design_identity"] == design["canonical_identity"]
    assert all(value == 0 for key, value in preflight.items() if key != "design_identity")
