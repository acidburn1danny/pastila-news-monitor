"""V15 R3 request contract and post-claim failure closure.

This module does not grant execution authority. A separately signed successor
route must bind these bytes before it can consume a new attempt.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path

from pastila_scout.production_core_semantic_authority_v2 import (
    build_candidate_prompt_v2,
    validate_response_v2,
)

INPUT_MARKER = "\nINPUT="
INPUT_FIELDS = (
    "case_id", "request_identity", "output_type", "required_factual_shape",
    "expected_material_proposition_count", "required_commentary_components",
    "request", "authority_spans",
)
MANIFEST_FIELDS = (
    "case_id", "case_sha256", "request_identity", "output_type",
    "required_factual_shape", "expected_material_proposition_count",
    "required_commentary_components", "candidate_visible_request",
    "candidate_visible_request_sha256", "candidate_visible_request_bytes",
)
HISTORICAL_R2_OUTPUT = Path("/root/pf9-v15-preconsumption-output")


def validator_case(row: Mapping[str, object]) -> dict[str, object]:
    """Recover the exact INPUT shown to the candidate, without redrawing it."""
    if not isinstance(row, Mapping) or tuple(row) != MANIFEST_FIELDS:
        raise ValueError("successor request-manifest fields mismatch")
    prompt = row["candidate_visible_request"]
    if not isinstance(prompt, str) or prompt.count(INPUT_MARKER) != 1:
        raise ValueError("successor candidate INPUT marker mismatch")
    encoded = prompt.encode("utf-8")
    if (hashlib.sha256(encoded).hexdigest() != row["candidate_visible_request_sha256"]
            or len(encoded) != row["candidate_visible_request_bytes"]):
        raise ValueError("successor candidate prompt bytes mismatch")
    try:
        case = json.loads(prompt.split(INPUT_MARKER, 1)[1])
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("successor candidate INPUT invalid") from exc
    if not isinstance(case, dict) or tuple(case) != INPUT_FIELDS:
        raise ValueError("successor validator INPUT fields mismatch")
    if build_candidate_prompt_v2(case) != prompt:
        raise ValueError("successor candidate INPUT reconstruction mismatch")
    for field in ("case_id", "request_identity", "output_type",
                  "required_factual_shape", "expected_material_proposition_count",
                  "required_commentary_components"):
        if case[field] != row[field]:
            raise ValueError(f"successor validator {field} mismatch")
    spans = case["authority_spans"]
    if (not isinstance(case["request"], str) or not case["request"]
            or not isinstance(spans, list) or not spans
            or any(not isinstance(span, dict) or tuple(span) != ("span_id", "text")
                   or not isinstance(span["span_id"], str) or not span["span_id"]
                   or not isinstance(span["text"], str) or not span["text"]
                   for span in spans)
            or len({span["span_id"] for span in spans}) != len(spans)):
        raise ValueError("successor validator authority_spans malformed")
    # Exercise the *actual* semantic validator's case access before consumption.
    # This synthetic abstention is a contract probe, not candidate inference.
    probe = {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 2, "case_id": case["case_id"],
        "request_identity": case["request_identity"],
        "output_type": case["output_type"], "outcome": "ABSTAIN",
        "text": None, "claim_bindings": [],
        "abstention_code": "CANNOT_SATISFY_OUTPUT_CONTRACT",
    }
    validate_response_v2(
        json.dumps(probe, ensure_ascii=False, separators=(",", ":")).encode(),
        case, object(),
    )
    return case


def validate_manifest_contract(manifest: Mapping[str, object]) -> dict[str, dict[str, object]]:
    requests = manifest.get("requests")
    if not isinstance(requests, list) or len(requests) != 200:
        raise ValueError("successor request count mismatch")
    cases: dict[str, dict[str, object]] = {}
    for row in requests:
        case = validator_case(row)
        case_id = case["case_id"]
        if case_id in cases:
            raise ValueError("successor duplicate case")
        cases[case_id] = case
    return cases


def case_for_row(cases: Mapping[str, dict[str, object]], row: Mapping[str, object]) -> dict[str, object]:
    case = cases.get(row.get("case_id"))
    if case is None or case["request_identity"] != row.get("request_identity"):
        raise ValueError("successor schedule/validator case mismatch")
    return case


def close_post_claim_failure(
    output: Path,
    *,
    completed_rows: int,
    failure_class: str,
    failed_batch: Mapping[str, object] | None,
    build_failure: Callable,
    validate_failure: Callable,
    atomic_no_replace: Callable[[Path, bytes], None],
    canonical: Callable[[object], bytes],
) -> dict[str, object] | None:
    """Seal canonical terminal evidence after a real claim; never create a claim."""
    if output == HISTORICAL_R2_OUTPUT or output.resolve() == HISTORICAL_R2_OUTPUT:
        raise ValueError("historical R2 output is immutable")
    attempt_path = output / "attempt.json"
    if not attempt_path.is_file() or attempt_path.is_symlink():
        return None
    terminal_path = output / "terminal-failure.json"
    if terminal_path.exists() or terminal_path.is_symlink():
        raise ValueError("terminal evidence already exists")
    if (output / "completion.json").exists():
        raise ValueError("completion already exists")
    attempt = json.loads(attempt_path.read_bytes())
    inventory = []
    for path in sorted(output.rglob("*")):
        if path.is_symlink():
            raise ValueError("post-claim evidence symlink")
        if path.is_file():
            inventory.append({
                "path": path.relative_to(output).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    failure = build_failure(
        attempt, completed_rows, failure_class,
        failed_batch=failed_batch, partial_artifacts=inventory,
    )
    validate_failure(failure, attempt, inventory)
    atomic_no_replace(terminal_path, canonical(failure))
    return failure


def run_with_terminal_closure(
    run: Callable[[], object],
    output: Path,
    *,
    completed_rows: Callable[[], int],
    failed_batch: Callable[[], Mapping[str, object] | None],
    build_failure: Callable,
    validate_failure: Callable,
    atomic_no_replace: Callable[[Path, bytes], None],
    canonical: Callable[[object], bytes],
) -> object:
    """Catch every post-claim exit, seal failure once, then preserve that exit."""
    try:
        return run()
    except BaseException as exc:
        if (output / "attempt.json").is_file() and not (
            (output / "terminal-failure.json").exists()
            or (output / "completion.json").exists()
        ):
            try:
                close_post_claim_failure(
                    output,
                    completed_rows=completed_rows(),
                    failure_class=f"UNHANDLED_{type(exc).__name__}",
                    failed_batch=failed_batch(),
                    build_failure=build_failure,
                    validate_failure=validate_failure,
                    atomic_no_replace=atomic_no_replace,
                    canonical=canonical,
                )
            except BaseException as closure_exc:
                raise RuntimeError("post-claim terminal evidence closure failed") from closure_exc
        raise
