from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import ConstructionObligationLedgerV2


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-request-prompt-feasibility-design-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-request-prompt-feasibility-design-v1-evidence/preflight.json"


def test_design_identity_and_current_dependencies_reproduce() -> None:
    design = json.loads(DESIGN.read_bytes())
    material = "\n".join(design["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == design["canonical_identity"]
    schema = json.dumps(ConstructionObligationLedgerV2.model_json_schema(), ensure_ascii=False,
                        sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert "sha256:" + hashlib.sha256(schema).hexdigest() == design["bindings"]["v2_schema_identity"]
    bound_files = {
        "v2_contract_source_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_contract_v2.py",
    }
    for field, relative in bound_files.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == design["bindings"][field]
    legacy = design["legacy_non_equivalence"]
    legacy_paths = {
        "v1_request_candidate_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_request_candidate_v1.py",
        "v1_prompt_source_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_construction_role_prompt_v1.py",
        "v1_contract_source_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_construction_role_contract_v1.py",
    }
    for field, relative in legacy_paths.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == legacy[field]


def test_design_selects_new_lineage_without_execution_authority() -> None:
    design = json.loads(DESIGN.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert design["result"] == "FEASIBLE_NEW_V2_LINEAGE_REQUIRED"
    assert design["legacy_non_equivalence"]["disposition"] == "PROHIBITED_AS_V2_PROMPT_OR_REQUEST_IDENTITY"
    assert design["selected_architecture"]["prompt_bytes_status"] == "NOT_YET_AUTHORED_OR_FROZEN"
    assert design["authority"]["design_selection"] is True
    assert all(value is False for key, value in design["authority"].items()
               if key != "design_selection")
    assert all(value == 0 for key, value in preflight.items() if key != "design_identity")
