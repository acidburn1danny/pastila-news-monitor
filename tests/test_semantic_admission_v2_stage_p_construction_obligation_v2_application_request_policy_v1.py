from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_provider_identity_v1 import MODEL_IDENTITY


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-application-request-policy-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-application-request-policy-v1-evidence/preflight.json"


def test_policy_identity_dependencies_and_model_reproduce() -> None:
    policy = json.loads(POLICY.read_bytes())
    material = "\n".join(policy["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == policy["canonical_identity"]
    assert MODEL_IDENTITY == policy["policy"]["model_identity"]
    for relative, expected in policy["bound_dependencies"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_policy_stops_before_execution_request_or_adapter_resolution() -> None:
    policy = json.loads(POLICY.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert policy["policy"]["provider_choice"] == "ollama"
    assert policy["policy"]["timeout_seconds"] == 240.0
    assert policy["policy"]["cancellation_requested"] is False
    assert policy["policy"]["authority_ceiling"] == "APPLICATION_PROVIDER_REQUEST_V1_CONSTRUCTION_ONLY"
    assert all(value == "NOT_AUTHORIZED" for value in
               policy["separated_future_authority"].values())
    allowed = "policy_design_and_future_application_request_construction"
    assert policy["authority"][allowed] is True
    assert all(value is False for key, value in policy["authority"].items()
               if key != allowed)
    assert all(value == 0 for key, value in preflight.items() if key != "policy_identity")
