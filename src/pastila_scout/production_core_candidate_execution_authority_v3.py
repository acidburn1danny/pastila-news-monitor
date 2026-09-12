"""Fail-closed execution authority for the accepted Core V2 generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

GENERATION_IDENTITY = "6d388a99731e3d4a08fa2a629374c37dd97994806ac54ffe49ab9fb1b41d630d"
QUALIFICATION_IDENTITY = (
    "4d2a4b7a42141668e907bd90cb96cf8d28dce518761b3c0dc0375954ea6575f4"
)
REQUEST_MANIFEST_IDENTITY = (
    "f3b0e0d11c5b73fba39ce21f5daa040e788a2ea09d455389bf990ee8264b4d03"
)
CANDIDATE_MANIFEST_IDENTITY = (
    "7bff8d58e56c1fd8e29f91f440b4f4c91ce4d79413d4186d895406f852c6abf9"
)
MATRIX_ROWS = 2400
ALIASES = ("CANDIDATE-A", "CANDIDATE-B")
RUNTIME_VERSIONS = {
    "bitsandbytes": "0.50.1",
    "peft": "0.20.0",
    "torch": "2.13.0+cu130",
    "transformers": "5.15.0",
}
UNICODE_AUTHORITY_SHA256 = (
    "20aab5eca3842c7a27cc6756d74488a4a5f744c8dca2948ec1128f26a60d1f79",
    "0aef84034ee1789eb71021454fac384e83080b05922272d63cf297f4bf08150e",
    "4579c185bd45feac761de590d874aca71788e339b35179318a4c43412fd4f9e4",
)
ALIAS_SECRET_COMMITMENT = (
    "ee86684da529d0b1a75c172d5ed2c3ec65f21da5f350d53cb7dda500f4449dca"
)
EXPECTED_OBJECTS = (
    (
        "rootfs",
        "file",
        "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4",
    ),
    (
        "base_model",
        "flat-dir",
        "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
    ),
    (
        "adapter_v1_1",
        "flat-dir",
        "0b3b8c317b8bfbf73dd4c131d92f1bc768d5e638034a49cecdc76da2d4e07f4b",
    ),
    (
        "adapter_v1_2",
        "flat-dir",
        "dccfee343ad1e305a0e193501b3a8adba11da01afd3d890ee38275dda82ac719",
    ),
)


class ExecutionAuthorityError(ValueError):
    """An execution input escaped the frozen authority."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _unseal(value: Mapping[str, object], field: str, expected: str) -> None:
    core = dict(value)
    if core.pop(field, None) != expected or identity(core) != expected:
        raise ExecutionAuthorityError(f"{field} mismatch")


def _unseal_sorted(value: Mapping[str, object], field: str, expected: str) -> None:
    core = dict(value)
    claimed = core.pop(field, None)
    observed = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    if claimed != expected or observed != expected:
        raise ExecutionAuthorityError(f"{field} mismatch")


def validate_preflight(
    generation: Mapping[str, object],
    request_manifest: Mapping[str, object],
    candidate_manifest: Mapping[str, object],
    qualification: Mapping[str, object],
) -> tuple[dict[str, object], ...]:
    """Validate every public input before an attempt may be consumed."""
    _unseal(generation, "qualification_generation_identity", GENERATION_IDENTITY)
    _unseal(request_manifest, "request_manifest_identity", REQUEST_MANIFEST_IDENTITY)
    _unseal_sorted(candidate_manifest, "manifest_identity", CANDIDATE_MANIFEST_IDENTITY)
    _unseal(qualification, "qualification_identity", QUALIFICATION_IDENTITY)
    if (
        generation.get("schema_version") != 2
        or generation.get("request_manifest_identity") != REQUEST_MANIFEST_IDENTITY
        or generation.get("candidate_object_manifest_identity")
        != CANDIDATE_MANIFEST_IDENTITY
        or generation.get("retry_or_redraw_authorized") is not False
        or generation.get("candidate_execution_performed") is not False
        or qualification.get("qualification_generation_identity") != GENERATION_IDENTITY
        or qualification.get("request_manifest_identity") != REQUEST_MANIFEST_IDENTITY
        or qualification.get("candidate_object_manifest_identity")
        != CANDIDATE_MANIFEST_IDENTITY
        or qualification.get("candidate_execution_performed") is not False
    ):
        raise ExecutionAuthorityError("terminal V2 authority mismatch")
    requests = request_manifest.get("requests")
    schedule = generation.get("schedule")
    if not isinstance(requests, list) or len(requests) != 200:
        raise ExecutionAuthorityError("request cardinality mismatch")
    by_case: dict[str, Mapping[str, object]] = {}
    for row in requests:
        if not isinstance(row, Mapping):
            raise ExecutionAuthorityError("request row malformed")
        case_id, prompt = row.get("case_id"), row.get("candidate_visible_request")
        if (
            not isinstance(case_id, str)
            or case_id in by_case
            or not isinstance(prompt, str)
        ):
            raise ExecutionAuthorityError("request key mismatch")
        if hashlib.sha256(prompt.encode()).hexdigest() != row.get(
            "candidate_visible_request_sha256"
        ):
            raise ExecutionAuthorityError("request bytes mismatch")
        by_case[case_id] = row
    if not isinstance(schedule, list) or len(schedule) != MATRIX_ROWS:
        raise ExecutionAuthorityError("schedule cardinality mismatch")
    materialized = []
    for expected, item in enumerate(schedule, 1):
        if not isinstance(item, Mapping) or item.get("global_ordinal") != expected:
            raise ExecutionAuthorityError("schedule order mismatch")
        source = by_case.get(str(item.get("case_id")))
        if source is None:
            raise ExecutionAuthorityError("schedule request absent")
        materialized.append(
            {
                "global_ordinal": expected,
                "materialization": item.get("materialization"),
                "repetition": item.get("repetition"),
                "candidate_alias": item.get("candidate_alias"),
                "batch_ordinal": item.get("batch_ordinal"),
                "case_id": source["case_id"],
                "request_identity": source["request_identity"],
                "candidate_visible_request": source["candidate_visible_request"],
                "candidate_visible_request_sha256": source[
                    "candidate_visible_request_sha256"
                ],
            }
        )
    return tuple(materialized)


def validate_preflight_receipt(preflight: Mapping[str, object]) -> None:
    core = dict(preflight)
    recorded = core.pop("preflight_identity", None)
    observed = preflight.get("observed_materializations")
    sources = preflight.get("source_sha256")
    prompts = preflight.get("system_prompt_sha256")
    if (
        tuple(preflight)
        != (
            "schema",
            "schema_version",
            "execution_authority_identity",
            "qualification_generation_identity",
            "request_manifest_identity",
            "candidate_object_manifest_identity",
            "qualification_identity",
            "source_sha256",
            "system_prompt_sha256",
            "unicode_authority_sha256",
            "alias_secret_commitment",
            "alias_secret_sha256",
            "observed_materializations",
            "batch_count",
            "matrix_rows",
            "attempt_consumed",
            "candidate_execution_performed",
            "preflight_identity",
        )
        or preflight.get("schema")
        != "pastila-production-core-comparative-execution-preflight-v2"
        or preflight.get("schema_version") != 2
        or preflight.get("qualification_generation_identity") != GENERATION_IDENTITY
        or preflight.get("request_manifest_identity") != REQUEST_MANIFEST_IDENTITY
        or preflight.get("candidate_object_manifest_identity")
        != CANDIDATE_MANIFEST_IDENTITY
        or preflight.get("qualification_identity") != QUALIFICATION_IDENTITY
        or not isinstance(preflight.get("execution_authority_identity"), str)
        or len(str(preflight["execution_authority_identity"])) != 64
        or not isinstance(sources, Mapping)
        or set(sources) != {
            "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
            "scripts/execute_production_core_candidate_qualification_v3.py",
            "scripts/launch_production_core_candidate_qualification_v4.py",
            "scripts/resolve_production_core_object_authority_v2.sh",
            "scripts/run_production_core_candidate_qualification_v3.sh",
            "scripts/smoke_production_core_checkpoint_resume_v6.py",
            "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
            "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
            "src/pastila_scout/production_core_checkpoint_resume_v6.py",
            "src/pastila_scout/production_core_semantic_authority_v2.py",
        }
        or any(
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
            for value in sources.values()
        )
        or prompts
        != {
            "pastila-editor-core-v1.1-json-successor-v2": "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
            "pastila-editor-core-v1.2-json-successor": "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
        }
        or preflight.get("unicode_authority_sha256") != list(UNICODE_AUTHORITY_SHA256)
        or preflight.get("alias_secret_commitment") != ALIAS_SECRET_COMMITMENT
        or preflight.get("alias_secret_sha256") != ALIAS_SECRET_COMMITMENT
        or not isinstance(observed, Mapping)
        or tuple(observed) != ("A", "B")
        or preflight.get("batch_count") != 12
        or preflight.get("matrix_rows") != MATRIX_ROWS
        or preflight.get("attempt_consumed") is not False
        or preflight.get("candidate_execution_performed") is not False
        or recorded != identity(core)
    ):
        raise ExecutionAuthorityError("preflight evidence mismatch")
    physical_identities = []
    provenance_identities = []
    for label in ("A", "B"):
        provenance = observed[label]
        if not isinstance(provenance, Mapping):
            raise ExecutionAuthorityError("materialization provenance malformed")
        pcore = dict(provenance)
        pid = pcore.pop("materialization_provenance_identity", None)
        objects = provenance.get("objects")
        if (
            tuple(provenance)
            != (
                "schema",
                "materialization",
                "objects",
                "materialization_provenance_identity",
            )
            or provenance.get("schema")
            != "pastila-production-core-observed-materialization-provenance-v2"
            or provenance.get("materialization") != label
            or not isinstance(objects, list)
            or len(objects) != 4
            or pid != identity(pcore)
        ):
            raise ExecutionAuthorityError("materialization provenance mismatch")
        provenance_identities.append(pid)
        for item, (role, kind, expected_identity) in zip(
            objects, EXPECTED_OBJECTS, strict=True
        ):
            if (
                not isinstance(item, Mapping)
                or tuple(item)
                != (
                    "role",
                    "kind",
                    "expected_content_identity",
                    "physical_identity",
                    "content_identity",
                )
                or item.get("role") != role
                or item.get("kind") != kind
                or item.get("expected_content_identity") != expected_identity
                or item.get("content_identity") != item.get("expected_content_identity")
                or not isinstance(item.get("physical_identity"), str)
                or not item["physical_identity"]
            ):
                raise ExecutionAuthorityError("observed object closure mismatch")
            physical_identities.append(item["physical_identity"])
    if len(physical_identities) != len(set(physical_identities)) or len(
        provenance_identities
    ) != len(set(provenance_identities)):
        raise ExecutionAuthorityError("materialization independence mismatch")


def build_attempt(
    execution_authority_identity: str, preflight: Mapping[str, object]
) -> dict[str, object]:
    if (
        not isinstance(execution_authority_identity, str)
        or len(execution_authority_identity) != 64
    ):
        raise ExecutionAuthorityError("execution authority identity invalid")
    validate_preflight_receipt(preflight)
    if preflight.get("execution_authority_identity") != execution_authority_identity:
        raise ExecutionAuthorityError("preflight execution authority mismatch")
    preflight_identity = preflight["preflight_identity"]
    core = {
        "schema": "pastila-production-core-comparative-execution-attempt-v2",
        "schema_version": 2,
        "execution_authority_identity": execution_authority_identity,
        "preflight": dict(preflight),
        "preflight_identity": preflight_identity,
        "qualification_generation_identity": GENERATION_IDENTITY,
        "attempt_ordinal": 1,
        "matrix_rows": MATRIX_ROWS,
        "retry_or_redraw_authorized": False,
        "promotion_effect": False,
        "status": "CONSUMED_BEFORE_EXECUTION",
    }
    return {**core, "attempt_identity": identity(core)}


def validate_attempt(
    attempt: Mapping[str, object], execution_authority_identity: str
) -> None:
    core = dict(attempt)
    recorded = core.pop("attempt_identity", None)
    preflight = attempt.get("preflight")
    if not isinstance(preflight, Mapping):
        raise ExecutionAuthorityError("attempt preflight absent")
    if recorded != identity(core) or core != {
        key: value
        for key, value in build_attempt(execution_authority_identity, preflight).items()
        if key != "attempt_identity"
    }:
        raise ExecutionAuthorityError("attempt authority mismatch")


def resolve_aliases(secret: Mapping[str, object], commitment: str) -> dict[str, str]:
    aliases = secret.get("aliases")
    nonce = secret.get("nonce_hex")
    if (
        tuple(secret) != ("schema", "schema_version", "nonce_hex", "aliases")
        or secret.get("schema") != "pastila-production-core-candidate-alias-secret"
        or secret.get("schema_version") != 1
        or not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
        or not isinstance(aliases, dict)
        or tuple(aliases) != ALIASES
        or set(aliases.values())
        != {
            "pastila-editor-core-v1.1-json-successor-v2",
            "pastila-editor-core-v1.2-json-successor",
        }
        or hashlib.sha256(canonical(secret)).hexdigest() != commitment
    ):
        raise ExecutionAuthorityError("alias secret authority mismatch")
    return {str(key): str(value) for key, value in aliases.items()}


def materialize_batches(
    rows: Sequence[Mapping[str, object]],
    secret: Mapping[str, object],
    commitment: str,
) -> tuple[dict[str, object], ...]:
    """Create exactly twelve batches without rebuilding candidate-visible bytes."""
    aliases = resolve_aliases(secret, commitment)
    if len(rows) != MATRIX_ROWS:
        raise ExecutionAuthorityError("matrix row cardinality mismatch")
    result = []
    cursor = 0
    for materialization in ("A", "B"):
        for repetition in (1, 2, 3):
            for alias in ALIASES:
                selected = rows[cursor : cursor + 200]
                cursor += 200
                if any(
                    row.get("materialization") != materialization
                    or row.get("repetition") != repetition
                    or row.get("candidate_alias") != alias
                    or row.get("batch_ordinal") != index
                    for index, row in enumerate(selected, 1)
                ):
                    raise ExecutionAuthorityError("batch schedule mismatch")
                batch = [
                    {
                        "case_id": row["case_id"],
                        "request_identity": row["request_identity"],
                        "prompt": row["candidate_visible_request"],
                        "prompt_sha256": row["candidate_visible_request_sha256"],
                    }
                    for row in selected
                ]
                result.append(
                    {
                        "materialization": materialization,
                        "repetition": repetition,
                        "candidate_alias": alias,
                        "candidate": aliases[alias],
                        "batch": batch,
                        "batch_sha256": hashlib.sha256(canonical(batch)).hexdigest(),
                        "first_global_ordinal": selected[0]["global_ordinal"],
                        "last_global_ordinal": selected[-1]["global_ordinal"],
                    }
                )
    if cursor != MATRIX_ROWS or len(result) != 12:
        raise ExecutionAuthorityError("batch closure mismatch")
    return tuple(result)


def build_terminal_failure(
    attempt: Mapping[str, object],
    completed: int,
    failure: str,
    *,
    failed_batch: Mapping[str, object] | None = None,
    partial_artifacts: Sequence[Mapping[str, object]] = (),
) -> dict[str, object]:
    execution_authority_identity = attempt.get("execution_authority_identity")
    if not isinstance(execution_authority_identity, str):
        raise ExecutionAuthorityError("attempt execution authority absent")
    validate_attempt(attempt, execution_authority_identity)
    if (
        type(completed) is not int
        or not 0 <= completed <= MATRIX_ROWS
        or not failure
        or any(not isinstance(row, Mapping) for row in partial_artifacts)
    ):
        raise ExecutionAuthorityError("terminal failure input invalid")
    core = {
        "schema": "pastila-production-core-comparative-terminal-failure-v2",
        "schema_version": 2,
        "attempt_identity": attempt.get("attempt_identity"),
        "qualification_generation_identity": GENERATION_IDENTITY,
        "completed_rows": completed,
        "failure_class": failure,
        "failed_batch": dict(failed_batch) if failed_batch is not None else None,
        "partial_artifact_count": len(partial_artifacts),
        "partial_artifact_root": identity(list(partial_artifacts)),
        "retry_or_redraw_authorized": False,
        "promotion_effect": False,
    }
    return {**core, "terminal_failure_identity": identity(core)}


def result_status(
    raw: bytes,
    validator,
    case: Mapping[str, object],
    authority: object,
    candidate_output_status: str,
) -> str:
    """Invalid candidate bytes fail only their case and remain available to receipts."""
    if candidate_output_status != "EXECUTION_ENVELOPE_PASS":
        return "FAIL_CLOSED_INVALID_OUTPUT"
    try:
        validator(raw, case, authority)
    except TypeError, ValueError:
        return "FAIL_CLOSED_INVALID_OUTPUT"
    return "STRUCTURALLY_VALID_PENDING_ADJUDICATION"


def validate_boundary_logs(
    network: Mapping[str, object], file_boundary: Mapping[str, object]
) -> None:
    if network != {
        "schema": "pastila-production-core-network-boundary-log",
        "schema_version": 1,
        "policy": "DENY_ALL_NEW_CHILD_NAMESPACE",
        "observed_interfaces": ["lo"],
        "observed_ipv4_route_rows": 0,
        "namespace_init_pid": 1,
        "network_namespace_differs_from_parent": True,
        "pid_namespace_differs_from_parent": True,
        "promotion_effect": False,
    }:
        raise ExecutionAuthorityError("network boundary evidence mismatch")
    if (
        tuple(file_boundary)
        != (
            "schema",
            "schema_version",
            "model_mount_read_only",
            "adapter_mount_read_only",
            "candidate_private_snapshots",
            "authority_inputs_from_open_descriptors",
            "private_rootfs_from_open_descriptor",
            "mountinfo_sha256",
            "host_pid_namespace_reachable",
        )
        or file_boundary.get("schema") != "pastila-production-core-file-boundary-log"
        or file_boundary.get("schema_version") != 1
        or any(
            file_boundary.get(key) is not True
            for key in (
                "model_mount_read_only",
                "adapter_mount_read_only",
                "candidate_private_snapshots",
                "authority_inputs_from_open_descriptors",
                "private_rootfs_from_open_descriptor",
            )
        )
        or file_boundary.get("host_pid_namespace_reachable") is not False
        or not isinstance(file_boundary.get("mountinfo_sha256"), str)
        or len(str(file_boundary["mountinfo_sha256"])) != 64
        or any(
            c not in "0123456789abcdef" for c in str(file_boundary["mountinfo_sha256"])
        )
    ):
        raise ExecutionAuthorityError("file boundary evidence mismatch")


def validate_observation(
    observation: Mapping[str, object], raw: bytes, expected: Mapping[str, object]
) -> str:
    fields = (
        "schema",
        "schema_version",
        "qualification_generation_identity",
        "candidate",
        "rootfs_sha256",
        "base_manifest_sha256",
        "adapter_manifest_sha256",
        "system_prompt_sha256",
        "batch_sha256",
        "runner_sha256",
        "case_id",
        "request_identity",
        "input_tokens",
        "output_tokens",
        "load_wall_ns",
        "generation_wall_ns",
        "peak_rss_bytes",
        "raw_output_sha256",
        "runtime_versions",
        "terminal_eos",
        "termination_reason",
        "candidate_output_status",
        "observation_identity",
    )
    core = dict(observation)
    recorded = core.pop("observation_identity", None)
    if (
        tuple(observation) != fields
        or observation.get("schema")
        != "pastila-production-core-frozen-runner-observation"
        or observation.get("schema_version") != 2
        or recorded != identity(core)
        or any(
            observation.get(key) != expected.get(key)
            for key in (
                "qualification_generation_identity",
                "candidate",
                "rootfs_sha256",
                "base_manifest_sha256",
                "adapter_manifest_sha256",
                "system_prompt_sha256",
                "batch_sha256",
                "runner_sha256",
                "case_id",
                "request_identity",
            )
        )
        or observation.get("raw_output_sha256") != hashlib.sha256(raw).hexdigest()
        or observation.get("runtime_versions") != RUNTIME_VERSIONS
        or type(observation.get("terminal_eos")) is not bool
        or observation.get("termination_reason")
        not in {
            "TERMINAL_EOS",
            "OUTPUT_BYTE_CEILING_EXCEEDED",
            "MAX_NEW_TOKENS_EXHAUSTED",
            "GENERATION_STOPPED_WITHOUT_EOS",
        }
    ):
        raise ExecutionAuthorityError("runner observation closure mismatch")
    for key, maximum, positive in (
        ("input_tokens", 1924, True),
        ("output_tokens", 6268, False),
        ("peak_rss_bytes", 16_106_127_360, False),
        ("load_wall_ns", 600_000_000_000, False),
        ("generation_wall_ns", 600_000_000_000, False),
    ):
        value = observation.get(key)
        if type(value) is not int or value < (1 if positive else 0) or value > maximum:
            raise ExecutionAuthorityError("runner observation envelope mismatch")
    if (
        int(observation["load_wall_ns"]) + int(observation["generation_wall_ns"])
        > 600_000_000_000
    ):
        raise ExecutionAuthorityError("runner observation wall-time mismatch")
    expected_status = (
        "EXECUTION_ENVELOPE_PASS"
        if observation["terminal_eos"] is True and len(raw) <= 6268
        else "EXECUTION_ENVELOPE_FAIL_CLOSED"
    )
    if observation.get("candidate_output_status") != expected_status:
        raise ExecutionAuthorityError("candidate output status mismatch")
    expected_reason = (
        "TERMINAL_EOS"
        if observation["terminal_eos"] is True
        else "OUTPUT_BYTE_CEILING_EXCEEDED"
        if len(raw) > 6268
        else "MAX_NEW_TOKENS_EXHAUSTED"
        if observation["output_tokens"] == 6268
        else "GENERATION_STOPPED_WITHOUT_EOS"
    )
    if observation.get("termination_reason") != expected_reason:
        raise ExecutionAuthorityError("candidate termination reason mismatch")
    return expected_status


def validate_case_receipt(
    receipt: Mapping[str, object],
    attempt: Mapping[str, object],
    expected: Mapping[str, object],
) -> int:
    """Validate one durable case receipt and return its global ordinal."""
    fields = (
        "schema",
        "schema_version",
        "execution_authority_identity",
        "attempt_identity",
        "qualification_generation_identity",
        "global_ordinal",
        "materialization",
        "repetition",
        "candidate_alias",
        "case_id",
        "request_identity",
        "candidate_visible_request_sha256",
        "raw_output_sha256",
        "observation_identity",
        "structural_status",
        "retry_or_redraw",
        "adjudication_performed",
        "promotion_effect",
        "receipt_identity",
    )
    core = dict(receipt)
    recorded = core.pop("receipt_identity", None)
    ordinal = receipt.get("global_ordinal")
    if (
        tuple(receipt) != fields
        or receipt.get("schema") != "pastila-production-core-case-execution-receipt-v2"
        or receipt.get("schema_version") != 2
        or receipt.get("attempt_identity") != attempt.get("attempt_identity")
        or receipt.get("execution_authority_identity")
        != attempt.get("execution_authority_identity")
        or receipt.get("qualification_generation_identity") != GENERATION_IDENTITY
        or type(ordinal) is not int
        or not 1 <= ordinal <= MATRIX_ROWS
        or receipt.get("materialization") not in ("A", "B")
        or receipt.get("repetition") not in (1, 2, 3)
        or receipt.get("candidate_alias") not in ALIASES
        or receipt.get("structural_status")
        not in (
            "FAIL_CLOSED_INVALID_OUTPUT",
            "STRUCTURALLY_VALID_PENDING_ADJUDICATION",
        )
        or not isinstance(receipt.get("case_id"), str)
        or not receipt["case_id"]
        or not isinstance(receipt.get("request_identity"), str)
        or not str(receipt["request_identity"]).startswith("sha256:")
        or len(str(receipt["request_identity"])) != 71
        or any(
            c not in "0123456789abcdef" for c in str(receipt["request_identity"])[7:]
        )
        or any(
            not isinstance(receipt.get(key), str)
            or len(str(receipt[key])) != 64
            or any(c not in "0123456789abcdef" for c in str(receipt[key]))
            for key in (
                "execution_authority_identity",
                "candidate_visible_request_sha256",
                "raw_output_sha256",
                "observation_identity",
            )
        )
        or receipt.get("retry_or_redraw") is not False
        or receipt.get("adjudication_performed") is not False
        or receipt.get("promotion_effect") is not False
        or recorded != identity(core)
        or any(
            receipt.get(receipt_key) != expected.get(schedule_key)
            for receipt_key, schedule_key in (
                ("global_ordinal", "global_ordinal"),
                ("materialization", "materialization"),
                ("repetition", "repetition"),
                ("candidate_alias", "candidate_alias"),
                ("case_id", "case_id"),
                ("request_identity", "request_identity"),
                (
                    "candidate_visible_request_sha256",
                    "candidate_visible_request_sha256",
                ),
            )
        )
    ):
        raise ExecutionAuthorityError("case receipt closure mismatch")
    return ordinal


def validate_inference_lifecycle_events(
    started: Mapping[str, object],
    completed: Mapping[str, object],
    expected: Mapping[str, object],
    observation: Mapping[str, object],
) -> None:
    """Validate one durable per-inference STARTED/COMPLETED evidence pair."""
    started_core, completed_core = dict(started), dict(completed)
    started_identity = started_core.pop("event_identity", None)
    completed_identity = completed_core.pop("event_identity", None)
    sequence = expected.get("batch_ordinal")
    if (
        tuple(started)
        != (
            "schema",
            "schema_version",
            "phase",
            "sequence",
            "completed_count",
            "case_id",
            "request_identity",
            "input_tokens",
            "started_boottime_ns",
            "event_identity",
        )
        or tuple(completed)
        != (
            "schema",
            "schema_version",
            "phase",
            "sequence",
            "completed_count",
            "case_id",
            "request_identity",
            "started_event_identity",
            "generation_wall_ns",
            "output_tokens",
            "terminal_eos",
            "termination_reason",
            "event_identity",
        )
        or started.get("schema") != "pastila-production-core-inference-lifecycle-event"
        or completed.get("schema")
        != "pastila-production-core-inference-lifecycle-event"
        or started.get("schema_version") != 1
        or completed.get("schema_version") != 1
        or started.get("phase") != "STARTED"
        or completed.get("phase") != "COMPLETED"
        or type(sequence) is not int
        or started.get("sequence") != sequence
        or completed.get("sequence") != sequence
        or started.get("completed_count") != sequence - 1
        or completed.get("completed_count") != sequence
        or started.get("case_id") != expected.get("case_id")
        or completed.get("case_id") != expected.get("case_id")
        or started.get("request_identity") != expected.get("request_identity")
        or completed.get("request_identity") != expected.get("request_identity")
        or completed.get("started_event_identity") != started_identity
        or started.get("input_tokens") != observation.get("input_tokens")
        or completed.get("generation_wall_ns") != observation.get("generation_wall_ns")
        or completed.get("output_tokens") != observation.get("output_tokens")
        or completed.get("terminal_eos") != observation.get("terminal_eos")
        or completed.get("termination_reason")
        != observation.get("termination_reason")
        or type(started.get("started_boottime_ns")) is not int
        or int(started["started_boottime_ns"]) < 0
        or started_identity != identity(started_core)
        or completed_identity != identity(completed_core)
    ):
        raise ExecutionAuthorityError("inference lifecycle evidence mismatch")


def validate_terminal_failure(
    failure: Mapping[str, object],
    attempt: Mapping[str, object],
    partial_artifacts: Sequence[Mapping[str, object]],
) -> None:
    """Validate terminal recovery evidence against its consumed attempt."""
    core = dict(failure)
    recorded = core.pop("terminal_failure_identity", None)
    if (
        tuple(failure)
        != (
            "schema",
            "schema_version",
            "attempt_identity",
            "qualification_generation_identity",
            "completed_rows",
            "failure_class",
            "failed_batch",
            "partial_artifact_count",
            "partial_artifact_root",
            "retry_or_redraw_authorized",
            "promotion_effect",
            "terminal_failure_identity",
        )
        or failure.get("schema")
        != "pastila-production-core-comparative-terminal-failure-v2"
        or failure.get("schema_version") != 2
        or failure.get("attempt_identity") != attempt.get("attempt_identity")
        or failure.get("qualification_generation_identity") != GENERATION_IDENTITY
        or type(failure.get("completed_rows")) is not int
        or not 0 <= int(failure["completed_rows"]) <= MATRIX_ROWS
        or not isinstance(failure.get("failure_class"), str)
        or not failure["failure_class"]
        or type(failure.get("partial_artifact_count")) is not int
        or int(failure["partial_artifact_count"]) != len(partial_artifacts)
        or failure.get("partial_artifact_root") != identity(list(partial_artifacts))
        or not isinstance(failure.get("partial_artifact_root"), str)
        or len(str(failure["partial_artifact_root"])) != 64
        or failure.get("retry_or_redraw_authorized") is not False
        or failure.get("promotion_effect") is not False
        or recorded != identity(core)
    ):
        raise ExecutionAuthorityError("terminal failure closure mismatch")
    _validate_inventory(partial_artifacts)


def _validate_inventory(inventory: Sequence[Mapping[str, object]]) -> None:
    paths = []
    for row in inventory:
        if tuple(row) != ("path", "sha256"):
            raise ExecutionAuthorityError("artifact inventory row mismatch")
        path, digest = row.get("path"), row.get("sha256")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith(("/", "\\"))
            or "\\" in path
            or any(part in ("", ".", "..") for part in path.split("/"))
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ExecutionAuthorityError("artifact inventory containment mismatch")
        paths.append(path)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ExecutionAuthorityError("artifact inventory order mismatch")


def validate_completion(
    completion: Mapping[str, object],
    attempt: Mapping[str, object],
    expected_rows: Sequence[Mapping[str, object]],
    artifact_bytes: Mapping[str, bytes],
) -> None:
    """Validate successful completion evidence without trusting producer claims."""
    core = dict(completion)
    recorded = core.pop("completion_identity", None)
    inventory = completion.get("artifact_inventory")
    observed_inventory = [
        {"path": path, "sha256": hashlib.sha256(data).hexdigest()}
        for path, data in sorted(artifact_bytes.items())
    ]
    if (
        tuple(completion)
        != (
            "schema",
            "schema_version",
            "attempt_identity",
            "execution_authority_identity",
            "qualification_generation_identity",
            "completed_rows",
            "artifact_inventory",
            "artifact_root",
            "retry_or_redraw",
            "adjudication_performed",
            "promotion_effect",
            "completion_identity",
        )
        or completion.get("schema")
        != "pastila-production-core-comparative-execution-completion-v2"
        or completion.get("schema_version") != 2
        or completion.get("attempt_identity") != attempt.get("attempt_identity")
        or completion.get("execution_authority_identity")
        != attempt.get("execution_authority_identity")
        or completion.get("qualification_generation_identity") != GENERATION_IDENTITY
        or completion.get("completed_rows") != MATRIX_ROWS
        or not isinstance(inventory, list)
        or not inventory
        or inventory != observed_inventory
        or completion.get("artifact_root") != identity(inventory)
        or completion.get("retry_or_redraw") is not False
        or completion.get("adjudication_performed") is not False
        or completion.get("promotion_effect") is not False
        or recorded != identity(core)
    ):
        raise ExecutionAuthorityError("completion closure mismatch")
    _validate_inventory(inventory)
    if len(expected_rows) != MATRIX_ROWS:
        raise ExecutionAuthorityError("completion schedule cardinality mismatch")
    if artifact_bytes.get("attempt.json") != canonical(attempt):
        raise ExecutionAuthorityError("completion attempt bytes mismatch")
    expected_paths = {"attempt.json"} | {f"checkpoint-{ordinal:02d}.json" for ordinal in range(1, 13)}
    batches: dict[str, list[Mapping[str, object]]] = {}
    for row in expected_rows:
        ordinal = row.get("global_ordinal")
        if type(ordinal) is not int:
            raise ExecutionAuthorityError("completion schedule malformed")
        directory = (
            f"materialization-{row['materialization']}/"
            f"repetition-{row['repetition']}/{row['candidate_alias']}"
        )
        batches.setdefault(directory, []).append(row)
        stem = (
            f"{row['case_id']}.{str(row['request_identity']).removeprefix('sha256:')}"
        )
        receipt_path = f"{directory}/{stem}.receipt.json"
        receipt_raw = artifact_bytes.get(receipt_path)
        raw_path = f"{directory}/results/{stem}.raw"
        observation_path = f"{directory}/results/{stem}.observation.json"
        started_path = (
            f"{directory}/results/inference-{row['batch_ordinal']:03d}-started.json"
        )
        completed_path = (
            f"{directory}/results/inference-{row['batch_ordinal']:03d}-completed.json"
        )
        raw = artifact_bytes.get(raw_path)
        observation_raw = artifact_bytes.get(observation_path)
        started_raw = artifact_bytes.get(started_path)
        completed_raw = artifact_bytes.get(completed_path)
        if (
            receipt_raw is None
            or raw is None
            or observation_raw is None
            or started_raw is None
            or completed_raw is None
        ):
            raise ExecutionAuthorityError("completion receipt absent")
        try:
            receipt = json.loads(receipt_raw)
            observation = json.loads(observation_raw)
            started = json.loads(started_raw)
            completed = json.loads(completed_raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExecutionAuthorityError("completion artifact JSON malformed") from exc
        if (
            receipt_raw != canonical(receipt)
            or observation_raw != canonical(observation)
            or started_raw != canonical(started)
            or completed_raw != canonical(completed)
        ):
            raise ExecutionAuthorityError("completion artifact noncanonical")
        validate_case_receipt(receipt, attempt, row)
        candidate = observation.get("candidate")
        adapters = {
            "pastila-editor-core-v1.1-json-successor-v2": EXPECTED_OBJECTS[2][2],
            "pastila-editor-core-v1.2-json-successor": EXPECTED_OBJECTS[3][2],
        }
        prompts = {
            "pastila-editor-core-v1.1-json-successor-v2": "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
            "pastila-editor-core-v1.2-json-successor": "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
        }
        if candidate not in adapters:
            raise ExecutionAuthorityError("completion candidate identity mismatch")
        prompt_bytes = artifact_bytes.get(f"{directory}/system-prompt.txt")
        if (
            prompt_bytes is None
            or hashlib.sha256(prompt_bytes).hexdigest() != prompts[candidate]
        ):
            raise ExecutionAuthorityError("completion system-prompt binding mismatch")
        expected_observation = {
            "qualification_generation_identity": GENERATION_IDENTITY,
            "candidate": candidate,
            "rootfs_sha256": EXPECTED_OBJECTS[0][2],
            "base_manifest_sha256": EXPECTED_OBJECTS[1][2],
            "adapter_manifest_sha256": adapters[candidate],
            "system_prompt_sha256": prompts[candidate],
            "batch_sha256": hashlib.sha256(
                artifact_bytes[f"{directory}/batch.json"]
            ).hexdigest(),
            "runner_sha256": attempt["preflight"]["source_sha256"][
                "src/pastila_scout/production_core_candidate_qualification_runner_v3.py"
            ],
            "case_id": row["case_id"],
            "request_identity": row["request_identity"],
        }
        validate_observation(observation, raw, expected_observation)
        validate_inference_lifecycle_events(started, completed, row, observation)
        if (
            receipt["raw_output_sha256"] != hashlib.sha256(raw).hexdigest()
            or receipt["observation_identity"] != observation["observation_identity"]
        ):
            raise ExecutionAuthorityError("completion case artifact binding mismatch")
        expected_paths.update(
            {
                receipt_path,
                raw_path,
                observation_path,
                started_path,
                completed_path,
            }
        )
    previous_checkpoint = None
    for checkpoint_ordinal, (directory, batch_rows) in enumerate(batches.items(), 1):
        batch = [
            {
                "case_id": row["case_id"],
                "request_identity": row["request_identity"],
                "prompt": row["candidate_visible_request"],
                "prompt_sha256": row["candidate_visible_request_sha256"],
            }
            for row in batch_rows
        ]
        if artifact_bytes.get(f"{directory}/batch.json") != canonical(batch):
            raise ExecutionAuthorityError("completion batch bytes mismatch")
        try:
            network = json.loads(
                artifact_bytes[f"{directory}/results/network-boundary.json"]
            )
            file_boundary = json.loads(
                artifact_bytes[f"{directory}/results/file-boundary.json"]
            )
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExecutionAuthorityError(
                "completion boundary evidence absent"
            ) from exc
        validate_boundary_logs(network, file_boundary)
        checkpoint_path = f"checkpoint-{checkpoint_ordinal:02d}.json"
        checkpoint_raw = artifact_bytes.get(checkpoint_path)
        try:
            checkpoint = json.loads(checkpoint_raw) if checkpoint_raw is not None else None
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExecutionAuthorityError("completion checkpoint malformed") from exc
        if not isinstance(checkpoint, dict) or checkpoint_raw != canonical(checkpoint):
            raise ExecutionAuthorityError("completion checkpoint noncanonical")
        checkpoint_core = dict(checkpoint)
        checkpoint_identity = checkpoint_core.pop("checkpoint_identity", None)
        closure = [
            {"path": path.removeprefix(directory + "/"), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for path, data in sorted(artifact_bytes.items())
            if path.startswith(directory + "/")
        ]
        materialization, repetition, candidate_alias = directory.split("/")
        coordinates = {
            "materialization": materialization.removeprefix("materialization-"),
            "repetition": int(repetition.removeprefix("repetition-")),
            "candidate_alias": candidate_alias,
        }
        if (
            checkpoint_identity != identity(checkpoint_core)
            or checkpoint.get("schema") != "pastila-production-core-qualification-checkpoint-receipt"
            or checkpoint.get("schema_version") != 6
            or checkpoint.get("attempt_identity") != attempt.get("attempt_identity")
            or checkpoint.get("execution_authority_identity") != attempt.get("execution_authority_identity")
            or checkpoint.get("qualification_generation_identity") != GENERATION_IDENTITY
            or checkpoint.get("checkpoint_ordinal") != checkpoint_ordinal
            or checkpoint.get("previous_checkpoint_identity") != previous_checkpoint
            or checkpoint.get("batch_coordinates") != coordinates
            or checkpoint.get("batch_sha256") != hashlib.sha256(canonical(batch)).hexdigest()
            or checkpoint.get("batch_directory") != directory
            or checkpoint.get("finalized_rows") != 200
            or checkpoint.get("first_global_ordinal") != batch_rows[0]["global_ordinal"]
            or checkpoint.get("last_global_ordinal") != batch_rows[-1]["global_ordinal"]
            or checkpoint.get("artifact_closure") != closure
            or checkpoint.get("retry_or_redraw") is not False
            or checkpoint.get("same_attempt_resume_only") is not True
        ):
            raise ExecutionAuthorityError("completion checkpoint closure mismatch")
        previous_checkpoint = checkpoint_identity
        expected_paths.update(
            {
                f"{directory}/batch.json",
                f"{directory}/system-prompt.txt",
                f"{directory}/results/heartbeat.json",
                f"{directory}/results/network-boundary.json",
                f"{directory}/results/file-boundary.json",
            }
        )
    observed_paths = {str(row["path"]) for row in inventory}
    if observed_paths != expected_paths:
        raise ExecutionAuthorityError("completion artifact-set closure mismatch")


__all__ = (
    "ExecutionAuthorityError",
    "build_attempt",
    "build_terminal_failure",
    "canonical",
    "identity",
    "materialize_batches",
    "resolve_aliases",
    "result_status",
    "validate_attempt",
    "validate_boundary_logs",
    "validate_case_receipt",
    "validate_completion",
    "validate_inference_lifecycle_events",
    "validate_observation",
    "validate_preflight",
    "validate_preflight_receipt",
    "validate_terminal_failure",
)
