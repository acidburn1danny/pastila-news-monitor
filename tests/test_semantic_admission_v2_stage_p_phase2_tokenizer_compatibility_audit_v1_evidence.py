import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs" / "artifacts" / (
    "semantic-admission-v2-stage-p-phase2-tokenizer-compatibility-audit-v1.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_audit_identity_harness_and_state_sequence_are_reproducible():
    evidence = _load(ARTIFACT)
    fields = evidence["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == evidence["canonical_identity"]
    harness = ROOT / evidence["audit_harness"]["path"]
    assert hashlib.sha256(harness.read_bytes()).hexdigest() == evidence["audit_harness"]["sha256"]
    state_hashes = [row["set_sha256"] for row in evidence["state_evidence"]]
    assert hashlib.sha256("\n".join(state_hashes).encode()).hexdigest() == (
        evidence["authoritative_run"]["allowed_token_set_sequence_sha256"]
    )


def test_all_frozen_plan_phases_and_acceptance_criteria_passed():
    evidence = _load(ARTIFACT)
    run = evidence["authoritative_run"]
    assert run["completed_phases"] == list(range(8))
    assert run["false_accepts"] == run["false_rejects"] == 0
    assert run["contextual_prefix_rewrites"] == 0
    assert run["standalone_suffix_mismatches"] == 0
    assert run["eos_only_at_terminal"] is True
    assert run["request_context_identity_isolation"] is True
    assert run["shortest_start_and_longest_end_reference_covered"] is True
    assert run["two_finding_supporting_to_decisive_transition_covered"] is True


def test_preliminary_run_is_preserved_but_not_misrepresented_as_complete():
    preliminary = _load(ARTIFACT)["preliminary_run"]
    assert preliminary["disposition"] == "PRESERVED_SUPERSEDED_FOR_FROZEN_PLAN_COVERAGE_ONLY"
    assert "missing" in preliminary["reason_superseded"]
    assert preliminary["model_or_inference_calls"] == 0


def test_audit_loaded_only_tokenizer_and_grants_no_further_authority():
    evidence = _load(ARTIFACT)
    assert evidence["activity"]["tokenizer_loads_authoritative_run"] == 1
    for key, value in evidence["activity"].items():
        if key != "tokenizer_loads_authoritative_run":
            assert value == 0
    assert not any(evidence["authority"].values())
    assert evidence["status"] == "OWNER_REVIEW_REQUIRED"
