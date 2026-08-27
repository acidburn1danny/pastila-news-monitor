from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_token_projector_v1.py"
HARNESS = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_token_projector_zero_inference_v1.py"
FREEZE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-audit-freeze-v1.json"
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-token-projector-v1-candidate.json"


def _load(path): return json.loads(path.read_bytes())
def _identity(value): return hashlib.sha256("\n".join(value["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest()


def test_freeze_and_candidate_identities_reproduce():
    freeze = _load(FREEZE); candidate = _load(CANDIDATE)
    assert _identity(freeze) == freeze["canonical_identity"]
    assert _identity(candidate) == candidate["canonical_identity"]
    assert candidate["frozen_audit_receipt_identity"] == freeze["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == candidate["implementation_sha256"]
    assert hashlib.sha256(HARNESS.read_bytes()).hexdigest() == candidate["zero_inference_harness_sha256"]


def test_candidate_preserves_exact_cache_and_zero_inference_boundaries():
    candidate = _load(CANDIDATE)
    assert candidate["behavior"]["exact_state_cache"] is True
    assert candidate["behavior"]["string_state_canonicalization"] is False
    evidence = candidate["real_tokenizer_zero_inference"]
    assert evidence["all_allowed_sets_equal_frozen_oracle"] is True
    for key in ("model_loads", "model_calls", "provider_calls", "inference_calls",
                "evaluator_objects", "runner_objects", "probe_constructions", "probe_executions"):
        assert evidence[key] == 0
    assert all(value is False for value in candidate["authority"].values())
