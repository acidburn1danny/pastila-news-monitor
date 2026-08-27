from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_tokenizer_dfa_audit_v1.py"
BRIDGE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-zero-inference-dependency-bridge-v1.json"
AUDIT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-dfa-audit-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_bytes())


def _reproduce(artifact: dict) -> str:
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    return hashlib.sha256(material.encode()).hexdigest()


def test_bridge_and_audit_identities_reproduce() -> None:
    bridge = _load(BRIDGE); audit = _load(AUDIT)
    assert _reproduce(bridge) == bridge["canonical_identity"]
    assert _reproduce(audit) == audit["canonical_identity"]
    assert audit["dependency_bridge_identity"] == bridge["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == audit["audit_harness_sha256"]


def test_matrix_has_exact_equivalence_and_terminal_eos() -> None:
    audit = _load(AUDIT); matrix = audit["state_matrix"]
    assert audit["phases_executed"] == [5, 6, 7]
    assert matrix["false_accepts"] == matrix["false_rejects"] == 0
    assert matrix["contextual_suffix_mismatches"] == 0
    assert matrix["eos_only_at_terminal"] is True
    assert all(row["sets_equal"] for row in matrix["states"])
    assert [row["state"] for row in matrix["states"] if row["eos_allowed"]] == ["TERMINAL"]


def test_no_projector_or_runtime_authority_was_created() -> None:
    bridge = _load(BRIDGE); audit = _load(AUDIT)
    assert audit["resource_characterization"]["projector_or_cache_created"] is False
    assert audit["strategy_recommendation"]["implementation_authorized"] is False
    assert all(value is False for value in bridge["authority"].values())
    assert all(value is False for value in audit["authority"].values())
    receipt = audit["execution_receipt"]
    assert receipt["tokenizer_loads"] == 1
    assert all(receipt[key] == 0 for key in receipt if key != "tokenizer_loads")
