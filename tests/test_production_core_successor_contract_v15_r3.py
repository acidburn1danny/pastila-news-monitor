"""Fixture-only R3 contract and terminal closure tests; never run a candidate."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from pastila_scout import production_core_successor_contract_v15_r3 as repair  # noqa: E402
from pastila_scout.production_core_semantic_authority_v2 import build_candidate_prompt_v2  # noqa: E402
from pastila_scout.production_core_semantic_authority_v2 import validate_response_v2  # noqa: E402
import project_production_core_candidate_qualification_v15_r3 as projection  # noqa: E402
from pastila_scout.production_core_candidate_execution_authority_v15 import result_status  # noqa: E402


def manifest() -> dict:
    return json.loads((ROOT / "docs/artifacts/production-core-candidate-request-manifest-v2.json").read_bytes())


def test_all_frozen_requests_reach_actual_validator_contract() -> None:
    cases = repair.validate_manifest_contract(manifest())
    assert len(cases) == 200
    assert all(case["authority_spans"] for case in cases.values())
    row = manifest()["requests"][0]
    assert repair.case_for_row(cases, row) is cases[row["case_id"]]
    with pytest.raises(ValueError, match="schedule/validator"):
        repair.case_for_row(cases, {**row, "request_identity": "sha256:" + "0" * 64})


def test_demonstrated_r2_manifest_row_rejected_before_consumption() -> None:
    row = manifest()["requests"][0]
    assert "authority_spans" not in row
    with pytest.raises(KeyError, match="authority_spans"):
        _ = row["authority_spans"]  # The R2 executor passed this row to the validator.
    abstention = {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 2, "case_id": row["case_id"],
        "request_identity": row["request_identity"],
        "output_type": row["output_type"], "outcome": "ABSTAIN",
        "text": None, "claim_bindings": [],
        "abstention_code": "CANNOT_SATISFY_OUTPUT_CONTRACT",
    }
    with pytest.raises(KeyError, match="authority_spans"):
        validate_response_v2(
            json.dumps(abstention, separators=(",", ":")).encode(), row, object(),
        )
    case = repair.validator_case(row)
    assert case["authority_spans"]


def test_missing_spans_even_with_rehashed_prompt_is_rejected() -> None:
    row = dict(manifest()["requests"][0])
    case = repair.validator_case(row)
    del case["authority_spans"]
    prompt = build_candidate_prompt_v2({**case, "authority_spans": []})
    row["candidate_visible_request"] = prompt
    row["candidate_visible_request_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
    row["candidate_visible_request_bytes"] = len(prompt.encode())
    with pytest.raises(ValueError, match="authority_spans"):
        repair.validator_case(row)


def test_prompt_and_manifest_drift_are_rejected() -> None:
    row = dict(manifest()["requests"][0])
    row["request_identity"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="request_identity"):
        repair.validator_case(row)
    row = dict(manifest()["requests"][0])
    row["candidate_visible_request"] += " "
    with pytest.raises(ValueError, match="bytes"):
        repair.validator_case(row)


def test_existing_invalid_output_semantics_are_preserved() -> None:
    def invalid(*_args):
        raise ValueError("candidate output")
    assert result_status(b"fixture", invalid, {}, object(),
                         "EXECUTION_ENVELOPE_PASS") == "FAIL_CLOSED_INVALID_OUTPUT"
    def broken(*_args):
        raise KeyError("authority_spans")
    with pytest.raises(KeyError, match="authority_spans"):
        result_status(b"fixture", broken, {}, object(), "EXECUTION_ENVELOPE_PASS")


def test_projection_has_one_preclaim_gate_and_one_corrected_case_selection() -> None:
    source = projection.projected_mechanics()
    ast.parse(source)
    assert source.count("successor_cases = validate_manifest_contract(requests)") == 1
    assert source.count("case = case_for_row(successor_cases, row)") == 1
    assert "case = next(" not in source
    assert source.index("successor_cases = validate_manifest_contract(requests)") < source.index(
        'atomic(output / "attempt.json", canonical(attempt))'
    )
    assert source.count("close_post_claim_failure(") == 1
    assert source.index("    try:\n        attempt = recovered_attempt") < source.index(
        'atomic(output / "attempt.json", canonical(attempt))'
    )
    assert source.index("close_post_claim_failure(") > source.index(
        'atomic(output / "attempt.json", canonical(attempt))'
    )
    with pytest.raises(ValueError, match="source authority"):
        projection.build_namespace({"source_sha256": {}})


def _callbacks(output: Path):
    def build(attempt, completed, failure, *, failed_batch, partial_artifacts):
        return {"attempt_identity": attempt["attempt_identity"], "completed": completed,
                "failure": failure, "batch": failed_batch, "inventory": partial_artifacts}

    def validate(failure, attempt, inventory):
        assert failure["attempt_identity"] == attempt["attempt_identity"]
        assert failure["inventory"] == inventory

    def atomic(path, data):
        with path.open("xb") as handle:
            handle.write(data)

    return dict(build_failure=build, validate_failure=validate,
                atomic_no_replace=atomic,
                canonical=lambda value: json.dumps(value, sort_keys=True).encode())


@pytest.mark.parametrize("error", [KeyError("authority_spans"), OSError("supervisor"), SystemExit(1)])
def test_post_claim_exceptions_seal_once_and_preserve_exit(tmp_path: Path, error: BaseException) -> None:
    (tmp_path / "attempt.json").write_text('{"attempt_identity":"fixture-attempt"}')
    (tmp_path / "partial.raw").write_bytes(b"fixture only")

    def failing():
        raise error

    with pytest.raises(type(error)):
        repair.run_with_terminal_closure(
            failing, tmp_path, completed_rows=lambda: 0,
            failed_batch=lambda: {"materialization": "A"}, **_callbacks(tmp_path),
        )
    failure = json.loads((tmp_path / "terminal-failure.json").read_bytes())
    assert failure["failure"] == f"UNHANDLED_{type(error).__name__}"
    assert failure["completed"] == 0
    assert [item["path"] for item in failure["inventory"]] == ["attempt.json", "partial.raw"]
    original = (tmp_path / "terminal-failure.json").read_bytes()
    with pytest.raises(type(error)):
        repair.run_with_terminal_closure(
            failing, tmp_path, completed_rows=lambda: 0,
            failed_batch=lambda: None, **_callbacks(tmp_path),
        )
    assert (tmp_path / "terminal-failure.json").read_bytes() == original


def test_preclaim_failure_creates_no_attempt_or_terminal(tmp_path: Path) -> None:
    def failing():
        raise ValueError("preclaim")
    with pytest.raises(ValueError, match="preclaim"):
        repair.run_with_terminal_closure(
            failing, tmp_path, completed_rows=lambda: 0,
            failed_batch=lambda: None, **_callbacks(tmp_path),
        )
    assert list(tmp_path.iterdir()) == []


def test_terminal_symlink_and_completion_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "attempt.json").write_text('{"attempt_identity":"fixture-attempt"}')
    (tmp_path / "partial.raw").symlink_to(tmp_path / "attempt.json")
    with pytest.raises(ValueError, match="symlink"):
        repair.close_post_claim_failure(
            tmp_path, completed_rows=0, failure_class="UNHANDLED_KeyError",
            failed_batch=None, **_callbacks(tmp_path),
        )
    assert not (tmp_path / "terminal-failure.json").exists()
    (tmp_path / "partial.raw").unlink()
    (tmp_path / "completion.json").write_text("fixture")
    with pytest.raises(ValueError, match="completion"):
        repair.close_post_claim_failure(
            tmp_path, completed_rows=0, failure_class="UNHANDLED_KeyError",
            failed_batch=None, **_callbacks(tmp_path),
        )


def test_historical_r2_output_cannot_be_closed_post_hoc() -> None:
    with pytest.raises(ValueError, match="historical R2"):
        repair.close_post_claim_failure(
            repair.HISTORICAL_R2_OUTPUT, completed_rows=0,
            failure_class="UNHANDLED_KeyError", failed_batch=None,
            **_callbacks(repair.HISTORICAL_R2_OUTPUT),
        )
