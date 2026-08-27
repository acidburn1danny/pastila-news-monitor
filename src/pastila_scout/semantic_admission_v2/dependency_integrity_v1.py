"""Zero-inference dependency integrity checks for Semantic Admission runs."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


class DependencyIntegrityError(RuntimeError):
    """A provider-capable run must not be authorized after this error."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


@dataclass(frozen=True)
class VerifiedDependencySetV1:
    manifest_identity: str
    files: Mapping[str, Any]
    payloads: tuple[Mapping[str, Any], ...]
    receipt: Mapping[str, Any]


def verify_and_construct(
    project_root: Path,
    manifest_path: Path,
    *,
    output_targets: Iterable[Path] = (),
) -> VerifiedDependencySetV1:
    """Verify all dependencies and build probe payloads without an executor."""
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    declared_identity = manifest.get("canonical_identity")
    identity_input = {k: v for k, v in manifest.items() if k != "canonical_identity"}
    actual_identity = _sha256(_canonical(identity_input))
    if declared_identity != actual_identity:
        raise DependencyIntegrityError("MANIFEST_IDENTITY_MISMATCH")

    loaded: dict[str, Any] = {}
    verified: list[dict[str, str]] = []
    root = project_root.resolve()
    for spec in manifest["dependencies"]:
        rel = PurePosixPath(spec["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise DependencyIntegrityError(f"DEPENDENCY_PATH_INVALID:{rel}")
        path = (root / Path(*rel.parts)).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise DependencyIntegrityError(f"DEPENDENCY_MISSING:{rel}")
        raw = path.read_bytes()
        if _sha256(raw) != spec["sha256"]:
            raise DependencyIntegrityError(f"DEPENDENCY_HASH_MISMATCH:{rel}")
        value: Any = raw
        if spec.get("format") == "json":
            try:
                value = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DependencyIntegrityError(f"DEPENDENCY_JSON_INVALID:{rel}") from exc
            missing = set(spec.get("required_keys", ())) - set(value)
            if missing:
                raise DependencyIntegrityError(f"DEPENDENCY_REQUIRED_KEYS_MISSING:{rel}:{','.join(sorted(missing))}")
            for key, expected in spec.get("required_values", {}).items():
                if value.get(key) != expected:
                    raise DependencyIntegrityError(f"DEPENDENCY_REQUIRED_VALUE_MISMATCH:{rel}:{key}")
        loaded[spec["id"]] = value
        verified.append({"id": spec["id"], "path": str(rel), "sha256": spec["sha256"]})

    for target in output_targets:
        resolved = target.resolve()
        if not resolved.is_relative_to(root):
            raise DependencyIntegrityError("OUTPUT_TARGET_OUTSIDE_PROJECT")
        if resolved.exists():
            raise DependencyIntegrityError(f"OUTPUT_TARGET_NOT_EMPTY:{resolved.relative_to(root)}")

    payloads = _construct_probe_payloads(loaded)
    receipt = {
        "schema_name": "pastila-semantic-admission-v2-dependency-integrity-receipt",
        "schema_version": "1.0.0",
        "manifest_identity": actual_identity,
        "verified_dependencies": verified,
        "payload_hashes_sha256": [_sha256(_canonical(item)) for item in payloads],
        "payload_count": len(payloads),
        "executor_constructed": False,
        "model_calls": 0,
        "provider_calls": 0,
        "inference_authority_issued": False,
        "result": "PASS",
    }
    return VerifiedDependencySetV1(actual_identity, loaded, payloads, receipt)


def _construct_probe_payloads(loaded: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    pack = loaded["probe_pack"]
    generation = loaded["generation_pack"]
    raw = loaded["raw_run_results"]
    cases = {item["case_id"]: item for item in generation["cases"]}
    attempts = {item["case_id"]: item for item in raw["attempts"]}
    payloads: list[Mapping[str, Any]] = []
    for probe in pack["probes"]:
        case_id = probe["source_case_id"]
        if case_id not in cases or case_id not in attempts:
            raise DependencyIntegrityError(f"PROBE_SOURCE_CASE_MISSING:{case_id}")
        try:
            candidate = json.loads(attempts[case_id]["raw_output"])["commentary"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise DependencyIntegrityError(f"PROBE_CANDIDATE_INVALID:{case_id}") from exc
        request: dict[str, Any] = {
            "gate_id": probe["gate_id"],
            "factual_summary": cases[case_id]["factual_summary"],
            "candidate": candidate,
        }
        controls = probe["control_case_ids"]
        if probe["gate_id"] == "STORY_SPECIFICITY":
            try:
                request["controls"] = [
                    {key: cases[cid][key] for key in ("case_id", "factual_summary", "factual_summary_sha256", "authority_identity")}
                    for cid in controls
                ]
            except KeyError as exc:
                raise DependencyIntegrityError(f"PROBE_CONTROL_INVALID:{exc.args[0]}") from exc
        elif controls:
            raise DependencyIntegrityError(f"FACTUAL_GATE_HAS_CONTROLS:{probe['probe_id']}")
        payloads.append(request)
    if len(payloads) != 2:
        raise DependencyIntegrityError("PROBE_PAYLOAD_COUNT_INVALID")
    return tuple(payloads)
