"""Non-consuming V15 R3 mechanics projection for a future signed successor route."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import execute_production_core_candidate_qualification_v15 as predecessor  # noqa: E402
from pastila_scout import production_core_successor_contract_v15_r3 as contract  # noqa: E402

SOURCE_PATHS = (
    "scripts/project_production_core_candidate_qualification_v15_r3.py",
    "src/pastila_scout/production_core_successor_contract_v15_r3.py",
)


def projected_mechanics() -> str:
    source = predecessor.projected_mechanics()
    old_preflight = "    rows = validate_preflight(generation, requests, candidates, qualification)"
    if source.count(old_preflight) != 1:
        raise ValueError("successor pre-consumption injection witness mismatch")
    source = source.replace(
        old_preflight,
        old_preflight + "\n    successor_cases = validate_manifest_contract(requests)",
    )
    old_case = '''            case = next(
                item
                for item in requests["requests"]
                if item["case_id"] == row["case_id"]
            )'''
    if source.count(old_case) != 1:
        raise ValueError("successor validator case projection witness mismatch")
    source = source.replace(old_case, "            case = case_for_row(successor_cases, row)")
    first = "    attempt = recovered_attempt or build_attempt("
    last = "    return 0\n\n\nif __name__ == \"__main__\":"
    if source.count(first) != 1 or source.count(last) != 1:
        raise ValueError("successor post-claim closure witness mismatch")
    beginning = source.index(first)
    ending = source.index(last) + len("    return 0\n")
    post_claim = source[beginning:ending]
    indented = "".join("    " + line if line.strip() else line
                       for line in post_claim.splitlines(keepends=True))
    handler = (
        "    try:\n" + indented
        + "    except BaseException as exc:\n"
        + "        if ((output / 'attempt.json').is_file() and not (output / 'attempt.json').is_symlink()\n"
        + "                and not (output / 'terminal-failure.json').exists()\n"
        + "                and not (output / 'completion.json').exists()):\n"
        + "            active = locals().get('current_batch')\n"
        + "            coordinates = None if active is None else {key: active[key] for key in "
          "('materialization', 'repetition', 'candidate_alias')}\n"
        + "            close_post_claim_failure(\n"
        + "                output, completed_rows=completed_receipt_count(output, attempt, rows),\n"
        + "                failure_class=f'UNHANDLED_{type(exc).__name__}',\n"
        + "                failed_batch=coordinates, build_failure=build_terminal_failure,\n"
        + "                validate_failure=validate_terminal_failure, atomic_no_replace=atomic,\n"
        + "                canonical=canonical,\n"
        + "            )\n"
        + "        raise\n"
    )
    return source[:beginning] + handler + source[ending:]


def build_namespace(boundary: dict) -> dict:
    """Construct corrected mechanics only if a new authority binds both new files."""
    sources = boundary.get("source_sha256")
    if not isinstance(sources, dict):
        raise ValueError("successor source authority absent")
    for name in SOURCE_PATHS:
        path = ROOT / name
        if (path.is_symlink() or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != sources.get(name)):
            raise ValueError(f"successor source authority mismatch: {name}")
    namespace = predecessor.build_namespace(boundary)
    namespace.update({
        "validate_manifest_contract": contract.validate_manifest_contract,
        "case_for_row": contract.case_for_row,
        "close_post_claim_failure": contract.close_post_claim_failure,
    })
    exec(compile(projected_mechanics(), __file__, "exec"), namespace, namespace)  # noqa: S102
    return namespace
