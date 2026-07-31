"""Versioned, reusable controlled-experiment manifest contracts and validation."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_NAME = "scout_revision_quality_experiment_manifest"
SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = 1


class StrictModel(BaseModel):
    """Immutable manifest value object with fail-closed unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ExperimentType(StrEnum):
    BASELINE = "BASELINE"
    PROMPT_EXPERIMENT = "PROMPT_EXPERIMENT"
    SCHEMA_EXPERIMENT = "SCHEMA_EXPERIMENT"
    PROVIDER_EXPERIMENT = "PROVIDER_EXPERIMENT"
    RUBRIC_EXPERIMENT = "RUBRIC_EXPERIMENT"
    OFFLINE_ANALYSIS = "OFFLINE_ANALYSIS"
    INFRASTRUCTURE = "INFRASTRUCTURE"


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_EVALUATED = "NOT_EVALUATED"


class Gate(StrictModel):
    status: GateStatus
    expected: Any
    observed: Any
    failure_reason: str | None = None


class ManifestIdentity(StrictModel):
    schema_name: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    schema_version: str = Field(pattern=r"^1\.[0-9]+\.[0-9]+$")
    contract_version: int = Field(ge=1)
    generated_at: str
    generator: str
    generator_version: str
    manifest_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    fingerprint_algorithm: str = "SHA-256"


class ExperimentIdentity(StrictModel):
    experiment_id: str = Field(min_length=1)
    milestone: str = Field(min_length=1)
    experiment_name: str = Field(min_length=1)
    experiment_type: ExperimentType
    run_id: str = Field(min_length=1)
    benchmark_series: str = Field(min_length=1)
    repository_revision: str | None = None
    created_at: str
    completed_at: str


class Lifecycle(StrictModel):
    status: str
    design_status: str
    execution_status: str
    evaluation_status: str
    validation_status: str
    promotion_status: str


class LineageEntry(StrictModel):
    milestone: str
    relationship: str
    artifact_path: str
    artifact_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    required: bool


class Hypothesis(StrictModel):
    hypothesis_id: str
    hypothesis_text: str
    targeted_behavior: str
    targeted_metric: str
    expected_direction: str
    evidence_source: list[str]
    falsifiable: bool
    status: str


class IndependentVariable(StrictModel):
    variable_type: str
    variable_name: str
    control_value_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    treatment_value_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    documented_change_count: int = Field(ge=0)
    behavioral_mechanism_count: int = Field(ge=0)


class Variant(StrictModel):
    identity: str
    milestone: str | None = None
    run_id: str | None = None
    prompt_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    corpus_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    rubric_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_paths: list[str]


class PromptDeltaBudget(StrictModel):
    budget_limit: int = Field(ge=0)
    budget_consumed: int = Field(ge=0)
    independent_behavioral_mechanisms: int = Field(ge=0)
    evidence_derived_hypotheses: int = Field(ge=0)
    undocumented_semantic_changes: int = Field(ge=0)
    benchmark_specific_instructions: int = Field(ge=0)
    evaluator_specific_instructions: int = Field(ge=0)
    production_irrelevant_instructions: int = Field(ge=0)
    budget_exceeded: bool
    validation_status: GateStatus


class Provider(StrictModel):
    provider_name: str
    model: str
    model_alias: str
    model_revision: str | None
    api_version: str | None
    sdk_version: str | None
    provider_configuration: dict[str, Any]
    provider_configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    comparability: str
    provider_drift_observed: bool
    provider_drift_notes: str | None


class Benchmark(StrictModel):
    benchmark_id: str
    benchmark_version: str
    scenario_count: int = Field(gt=0)
    scenario_order_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario_corpus_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario_ids: list[str]
    editorial_rubric_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    editorial_threshold: str
    provider_schema_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    dto_contract_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_contract_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reconstruction_contract_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_draft_contract_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExecutionCounts(StrictModel):
    provider_requests: int = Field(ge=0)
    provider_responses: int | None = Field(default=None, ge=0)
    retries: int = Field(ge=0)
    fallbacks: int = Field(ge=0)
    replays: int = Field(ge=0)


class Execution(StrictModel):
    planned: ExecutionCounts
    actual: ExecutionCounts


class TechnicalResults(StrictModel):
    technical_pipeline_successes: int = Field(ge=0)
    technical_pipeline_failures: int = Field(ge=0)
    dto_validation_passes: int = Field(ge=0)
    authorization_passes: int = Field(ge=0)
    reconstruction_passes: int = Field(ge=0)
    episode_draft_validation_passes: int = Field(ge=0)
    technical_non_regression: GateStatus


class ReferenceResults(StrictModel):
    unknown_references: int = Field(ge=0)
    unauthorized_references: int = Field(ge=0)
    missing_authorized_references: int = Field(ge=0)
    duplicate_references: int = Field(ge=0)
    malformed_references: int = Field(ge=0)
    reference_precision: float = Field(ge=0, le=1)
    reference_recall: float = Field(ge=0, le=1)
    exact_reference_compliance_count: int = Field(ge=0)
    exact_reference_compliance_total: int = Field(ge=0)
    reference_non_regression: GateStatus


class TargetedMetric(StrictModel):
    metric_name: str
    control_value: float
    treatment_value: float
    resolved_cases: int = Field(ge=0)
    persisting_cases: int = Field(ge=0)
    new_cases: int = Field(ge=0)
    net_change: float
    net_change_convention: str
    expected_direction: str
    direction_satisfied: bool


class EditorialResults(StrictModel):
    editorial_evaluations: int = Field(ge=0)
    editorial_acceptance_passes: int = Field(ge=0)
    editorial_acceptance_failures: int = Field(ge=0)
    mean_editorial_score: float
    median_editorial_score: float
    editorial_improvement: GateStatus
    acceptance_transitions: dict[str, int]
    failure_category_transitions: dict[str, int]
    targeted_metric: TargetedMetric


class OperationalResults(StrictModel):
    median_latency_ms: float = Field(ge=0)
    p95_latency_ms: float = Field(ge=0)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    cost_currency: str


class Results(StrictModel):
    technical: TechnicalResults
    reference: ReferenceResults
    editorial: EditorialResults
    operational: OperationalResults


class Decision(StrictModel):
    candidate_decision: str
    decision_reason: str
    decision_gates: dict[str, GateStatus]
    root_conclusion: str
    recommendation: str


class Promotion(StrictModel):
    production_promotion: bool
    production_prompt_changed: bool
    authoritative_production_baseline: str
    promotion_approved_by: str | None
    promotion_timestamp: str | None


class ArtifactReference(StrictModel):
    artifact_type: str
    artifact_path: str
    required: bool
    exists: bool
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    fingerprint_algorithm: str
    validation_status: GateStatus


class ManifestValidation(StrictModel):
    status: GateStatus
    errors: list[str]
    warnings: list[str]
    validated_artifacts: int = Field(ge=0)
    failed_invariants: list[str]


class ExperimentManifest(StrictModel):
    """Canonical controlled-experiment contract."""

    manifest: ManifestIdentity
    experiment: ExperimentIdentity
    lifecycle: Lifecycle
    lineage: list[LineageEntry]
    hypothesis: Hypothesis
    independent_variable: IndependentVariable
    baseline: Variant
    treatment: Variant
    prompt_delta_budget: PromptDeltaBudget
    provider: Provider
    benchmark: Benchmark
    execution: Execution
    integrity: dict[str, Gate]
    results: Results
    decision: Decision
    promotion: Promotion
    artifacts: list[ArtifactReference]
    validation: ManifestValidation
    historical_backfill_assessment: dict[str, str]

    @model_validator(mode="after")
    def cross_field_invariants(self) -> ExperimentManifest:
        errors: list[str] = []
        scenario_count = self.benchmark.scenario_count
        technical = self.results.technical
        editorial = self.results.editorial
        reference = self.results.reference
        actual = self.execution.actual
        budget = self.prompt_delta_budget
        if self.manifest.schema_name != SCHEMA_NAME:
            errors.append("unsupported schema name")
        if self.manifest.schema_version != SCHEMA_VERSION:
            errors.append("unsupported schema version")
        if self.manifest.contract_version != CONTRACT_VERSION:
            errors.append("unsupported contract version")
        if len(self.benchmark.scenario_ids) != scenario_count:
            errors.append("scenario count mismatch")
        if (
            technical.technical_pipeline_successes
            + technical.technical_pipeline_failures
            != scenario_count
        ):
            errors.append("technical total mismatch")
        if (
            editorial.editorial_acceptance_passes
            + editorial.editorial_acceptance_failures
            != editorial.editorial_evaluations
        ):
            errors.append("editorial total mismatch")
        if actual.provider_requests != actual.provider_responses:
            errors.append("provider request count mismatch")
        if any((actual.retries, actual.fallbacks, actual.replays)):
            errors.append("retry/fallback/replay invariant failed")
        if reference.exact_reference_compliance_total != scenario_count:
            errors.append("reference total mismatch")
        if budget.budget_exceeded != (
            budget.budget_consumed > budget.budget_limit
            or budget.undocumented_semantic_changes > 0
        ):
            errors.append("prompt delta budget mismatch")
        if budget.validation_status == GateStatus.PASS and budget.budget_exceeded:
            errors.append("budget exceeded but status PASS")
        if (
            self.independent_variable.variable_type == "PROMPT_TEXT"
            and self.baseline.prompt_fingerprint == self.treatment.prompt_fingerprint
        ):
            errors.append("prompt fingerprints equal")
        decision = self.decision.candidate_decision
        if decision not in {"ADOPT", "REJECT", "INCONCLUSIVE"}:
            errors.append("invalid candidate decision")
        if decision == "ADOPT" and any(
            value != GateStatus.PASS
            for value in (
                technical.technical_non_regression,
                reference.reference_non_regression,
                editorial.editorial_improvement,
            )
        ):
            errors.append("ADOPT has failed decision gate")
        if self.promotion.production_promotion and decision != "ADOPT":
            errors.append("promotion requires ADOPT")
        if decision == "REJECT" and self.promotion.production_promotion:
            errors.append("REJECT cannot promote")
        if (
            decision == "REJECT"
            and self.decision.root_conclusion == "H2_PROMPT_EFFECTIVE"
        ):
            errors.append("root conclusion inconsistent with decision")
        if errors:
            raise ValueError("; ".join(errors))
        return self


class ManifestDiagnostics(StrictModel):
    status: GateStatus
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    validated_artifacts: int = 0
    failed_invariants: tuple[str, ...] = ()


def sha256_file(path: Path) -> str:
    """Fingerprint raw artifact bytes."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_manifest_fingerprint(
    manifest: ExperimentManifest | dict[str, Any],
) -> str:
    """Fingerprint stable contract data, excluding validation and artifact hashes.

    Artifact identities and paths remain inside the boundary. Their raw hashes and
    validation metadata are excluded to break the intentional manifest/history link.
    """

    payload = (
        manifest.model_dump(mode="json")
        if isinstance(manifest, ExperimentManifest)
        else json.loads(json.dumps(manifest))
    )
    payload["manifest"].pop("manifest_fingerprint", None)
    payload["manifest"].pop("generated_at", None)
    payload.pop("validation", None)
    for artifact in payload["artifacts"]:
        for key in ("fingerprint", "exists", "validation_status"):
            artifact.pop(key, None)
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def serialize_manifest(path: Path, manifest: ExperimentManifest) -> None:
    """Atomically serialize canonical UTF-8 JSON."""

    payload = (
        json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def deserialize_manifest(path: Path) -> ExperimentManifest:
    """Load and strictly validate one manifest."""

    return ExperimentManifest.model_validate_json(path.read_text(encoding="utf-8"))


def validate_manifest(
    manifest: ExperimentManifest, repository_root: Path
) -> ManifestDiagnostics:
    """Validate fingerprint, safe paths, lineage, and raw artifact hashes."""

    errors: list[str] = []
    warnings: list[str] = []
    validated = 0
    if (
        canonical_manifest_fingerprint(manifest)
        != manifest.manifest.manifest_fingerprint
    ):
        errors.append("manifest fingerprint mismatch")
    for artifact in manifest.artifacts:
        pure = PurePosixPath(artifact.artifact_path)
        if pure.is_absolute() or ".." in pure.parts:
            errors.append(f"unsafe artifact path: {artifact.artifact_path}")
            continue
        path = repository_root.joinpath(*pure.parts)
        if not path.is_file():
            if artifact.required:
                errors.append(f"missing required artifact: {artifact.artifact_path}")
            continue
        if artifact.fingerprint_algorithm != "SHA-256":
            errors.append(
                f"unsupported fingerprint algorithm: {artifact.artifact_path}"
            )
        elif sha256_file(path) != artifact.fingerprint:
            errors.append(f"artifact fingerprint mismatch: {artifact.artifact_path}")
        else:
            validated += 1
    lineage_paths = {item.artifact_path for item in manifest.artifacts}
    for item in manifest.lineage:
        if item.required and item.artifact_path not in lineage_paths:
            errors.append(
                f"lineage artifact absent from inventory: {item.artifact_path}"
            )
    if manifest.provider.model_revision is None:
        warnings.append("provider model revision unavailable")
    if manifest.provider.api_version is None:
        warnings.append("provider API version unavailable")
    return ManifestDiagnostics(
        status=GateStatus.FAIL if errors else GateStatus.PASS,
        errors=tuple(errors),
        warnings=tuple(warnings),
        validated_artifacts=validated,
        failed_invariants=tuple(errors),
    )


def json_schema() -> dict[str, Any]:
    """Return the structural JSON Schema for the supported contract."""

    return ExperimentManifest.model_json_schema()


def utc_timestamp_is_valid(value: str) -> bool:
    """Return whether a stored timestamp is timezone-aware ISO 8601."""

    return datetime.fromisoformat(value).tzinfo is not None
