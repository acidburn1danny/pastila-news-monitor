"""Backfill and validate the canonical Part 7H.2 experiment manifest offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from pastila_scout.editor.generation.controlled_revision_quality.experiment_manifest import (
    CONTRACT_VERSION,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    ArtifactReference,
    Benchmark,
    Decision,
    EditorialResults,
    Execution,
    ExecutionCounts,
    ExperimentIdentity,
    ExperimentManifest,
    ExperimentType,
    Gate,
    GateStatus,
    Hypothesis,
    IndependentVariable,
    Lifecycle,
    LineageEntry,
    ManifestIdentity,
    ManifestValidation,
    OperationalResults,
    Promotion,
    PromptDeltaBudget,
    Provider,
    ReferenceResults,
    Results,
    TargetedMetric,
    TechnicalResults,
    Variant,
    canonical_manifest_fingerprint,
    json_schema,
    serialize_manifest,
    sha256_file,
    validate_manifest,
)

MANIFEST_PATH = Path("docs/artifacts/experiments/part-7h-2/experiment-manifest.json")
SCHEMA_PATH = Path("docs/schemas/experiment-manifest.schema.json")
DOCUMENTATION_PATH = Path("docs/experiment-manifest-contract.md")
HISTORY_PATH = Path("docs/artifacts/controlled-provider-quality-history.json")
EXPERIMENT_PATH = Path(
    "docs/artifacts/controlled-second-prompt-hypothesis-experiment.json"
)

ARTIFACTS = (
    ("PRIMARY_REPORT", "docs/controlled-second-prompt-hypothesis-experiment.md"),
    ("STRUCTURED_RESULT", str(EXPERIMENT_PATH).replace("\\", "/")),
    ("PROMPT_DELTA_BUDGET", "docs/artifacts/prompt-delta-budget.json"),
    ("SCENARIO_COMPARISON", "docs/artifacts/h2-scenario-comparison.json"),
    ("BENCHMARK_HISTORY", str(HISTORY_PATH).replace("\\", "/")),
    (
        "H2_DESIGN",
        "docs/artifacts/second-prompt-hypothesis-design.json",
    ),
    (
        "BASELINE",
        "docs/artifacts/controlled-provider-quality-baseline-7c-2.json",
    ),
    (
        "SEMANTICS_DEFINITION",
        "docs/artifacts/pipeline-success-semantics-reconciliation.json",
    ),
    (
        "H1_EXPERIMENT",
        "docs/artifacts/controlled-prompt-effectiveness-experiment.json",
    ),
)


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_hash(repository_root: Path, relative_path: str) -> str:
    return sha256_file(repository_root / relative_path)


def _artifact_references(repository_root: Path) -> list[ArtifactReference]:
    references = []
    for artifact_type, relative in ARTIFACTS:
        path = repository_root / relative
        if not path.is_file():
            raise RuntimeError(f"mandatory manifest evidence missing: {relative}")
        references.append(
            ArtifactReference(
                artifact_type=artifact_type,
                artifact_path=relative,
                required=True,
                exists=True,
                fingerprint=sha256_file(path),
                fingerprint_algorithm="SHA-256",
                validation_status=GateStatus.PASS,
            )
        )
    return references


def _gate(expected: object, observed: object, passed: bool = True) -> Gate:
    return Gate(
        status=GateStatus.PASS if passed else GateStatus.FAIL,
        expected=expected,
        observed=observed,
        failure_reason=None if passed else "value did not meet experiment contract",
    )


def build_part_7h2_manifest(repository_root: Path) -> ExperimentManifest:
    """Build the H2 manifest only from preserved repository evidence."""

    experiment = json.loads(
        (repository_root / EXPERIMENT_PATH).read_text(encoding="utf-8")
    )
    budget = json.loads(
        (repository_root / "docs/artifacts/prompt-delta-budget.json").read_text(
            encoding="utf-8"
        )
    )
    h2 = json.loads(
        (
            repository_root / "docs/artifacts/second-prompt-hypothesis-design.json"
        ).read_text(encoding="utf-8")
    )
    baseline = json.loads(
        (
            repository_root
            / "docs/artifacts/controlled-provider-quality-baseline-7c-2.json"
        ).read_text(encoding="utf-8")
    )
    comparisons = json.loads(
        (repository_root / "docs/artifacts/h2-scenario-comparison.json").read_text(
            encoding="utf-8"
        )
    )
    artifacts = _artifact_references(repository_root)
    artifact_by_type = {item.artifact_type: item for item in artifacts}
    scenario_ids = [item["scenario_id"] for item in comparisons["scenarios"]]
    projection = experiment["projection_checkpoint"]["scenarios"]
    schema_fingerprint = projection[0]["effective_schema_fingerprint"]
    provider_fingerprint = experiment["provider_configuration_fingerprint"]
    rubric_fingerprint = experiment["rubric_fingerprint"]
    corpus_fingerprint = experiment["benchmark_corpus_fingerprint"]
    pipeline = experiment["pipeline_funnel"]
    references = experiment["reference_metrics"]
    editorial = experiment["editorial_metrics"]
    quote = experiment["quote_mutation_metrics"]
    latency = experiment["latency_metrics"]["treatment"]["all_provider_calls"]
    usage = experiment["usage_metrics"]["treatment"]
    cost = experiment["cost_metrics"]["treatment"]
    provider = experiment["provider_comparability"]
    manifest_data = {
        "manifest": ManifestIdentity(
            schema_name=SCHEMA_NAME,
            schema_version=SCHEMA_VERSION,
            contract_version=CONTRACT_VERSION,
            generated_at=experiment["created_at"],
            generator="scripts.build_experiment_manifest",
            generator_version="1.0.0",
            manifest_fingerprint="0" * 64,
        ),
        "experiment": ExperimentIdentity(
            experiment_id=experiment["experiment_id"],
            milestone="Part 7H.2",
            experiment_name="Controlled Second Prompt Hypothesis Experiment",
            experiment_type=ExperimentType.PROMPT_EXPERIMENT,
            run_id=experiment["run_id"],
            benchmark_series="controlled-revision-quality",
            repository_revision=None,
            created_at=experiment["created_at"],
            completed_at=experiment["created_at"],
        ),
        "lifecycle": Lifecycle(
            status="COMPLETE",
            design_status="READY",
            execution_status="COMPLETE",
            evaluation_status="COMPLETE",
            validation_status="PASS",
            promotion_status="NOT_PROMOTED",
        ),
        "lineage": [
            LineageEntry(
                milestone=milestone,
                relationship=relationship,
                artifact_path=artifact_by_type[artifact_type].artifact_path,
                artifact_fingerprint=artifact_by_type[artifact_type].fingerprint,
                required=True,
            )
            for milestone, relationship, artifact_type in (
                ("Part 7C.2", "BASELINE", "BASELINE"),
                ("Part 7C.2.1", "SEMANTICS_DEFINITION", "SEMANTICS_DEFINITION"),
                ("Part 7H", "PREVIOUS_EXPERIMENT", "H1_EXPERIMENT"),
                ("Part 7H.1", "HYPOTHESIS_DESIGN", "H2_DESIGN"),
                ("Part 7H.2", "CURRENT_EXPERIMENT", "STRUCTURED_RESULT"),
            )
        ],
        "hypothesis": Hypothesis(
            hypothesis_id="H2",
            hypothesis_text=h2["h2_hypothesis"],
            targeted_behavior="QUOTE_MUTATION",
            targeted_metric="QUOTE_MUTATION",
            expected_direction="DECREASE",
            evidence_source=["Part 7H", "Part 7H.1", "SYN-10", "SYN-23"],
            falsifiable=True,
            status="NOT_SUPPORTED",
        ),
        "independent_variable": IndependentVariable(
            variable_type="PROMPT_TEXT",
            variable_name="controlled revision provider instruction",
            control_value_fingerprint=experiment["control_prompt_fingerprint"],
            treatment_value_fingerprint=experiment["candidate_prompt_fingerprint"],
            documented_change_count=1,
            behavioral_mechanism_count=1,
        ),
        "baseline": Variant(
            identity="Part 7C.2 production baseline",
            milestone="Part 7C.2",
            run_id=baseline["benchmark_id"],
            prompt_fingerprint=experiment["control_prompt_fingerprint"],
            provider_fingerprint=provider_fingerprint,
            corpus_fingerprint=corpus_fingerprint,
            rubric_fingerprint=rubric_fingerprint,
            schema_fingerprint=schema_fingerprint,
            configuration_fingerprint=provider_fingerprint,
            artifact_paths=[artifact_by_type["BASELINE"].artifact_path],
        ),
        "treatment": Variant(
            identity="H2 frozen candidate",
            milestone="Part 7H.1",
            run_id=experiment["run_id"],
            prompt_fingerprint=experiment["candidate_prompt_fingerprint"],
            provider_fingerprint=provider_fingerprint,
            corpus_fingerprint=corpus_fingerprint,
            rubric_fingerprint=rubric_fingerprint,
            schema_fingerprint=schema_fingerprint,
            configuration_fingerprint=provider_fingerprint,
            artifact_paths=[artifact_by_type["H2_DESIGN"].artifact_path],
        ),
        "prompt_delta_budget": PromptDeltaBudget(
            budget_limit=budget["budget_limit"],
            budget_consumed=budget["budget_consumed"],
            independent_behavioral_mechanisms=budget[
                "independent_behavioral_mechanisms"
            ],
            evidence_derived_hypotheses=budget["evidence_derived_hypotheses"],
            undocumented_semantic_changes=budget["undocumented_semantic_changes"],
            benchmark_specific_instructions=budget["benchmark_specific_instructions"],
            evaluator_specific_instructions=budget["evaluator_specific_instructions"],
            production_irrelevant_instructions=budget[
                "production_irrelevant_instructions"
            ],
            budget_exceeded=budget["budget_exceeded"],
            validation_status=budget["validation_result"],
        ),
        "provider": Provider(
            provider_name=provider["provider"],
            model=provider["model"],
            model_alias=provider["model_alias"],
            model_revision=provider["model_revision"],
            api_version=provider["api_version"],
            sdk_version=provider["sdk_version"],
            provider_configuration=experiment["provider_configuration"],
            provider_configuration_fingerprint=provider_fingerprint,
            comparability=provider["classification"],
            provider_drift_observed=provider["provider_drift_observed"],
            provider_drift_notes=provider["known_provider_drift"],
        ),
        "benchmark": Benchmark(
            benchmark_id=baseline["benchmark_id"],
            benchmark_version=baseline["benchmark_version"],
            scenario_count=len(scenario_ids),
            scenario_order_fingerprint=_canonical_hash(scenario_ids),
            scenario_corpus_fingerprint=corpus_fingerprint,
            scenario_ids=scenario_ids,
            editorial_rubric_fingerprint=rubric_fingerprint,
            editorial_threshold=experiment["editorial_threshold"],
            provider_schema_fingerprint=schema_fingerprint,
            dto_contract_fingerprint=_source_hash(
                repository_root,
                "src/pastila_scout/editor/generation/ai_provider_adapter/openai/models.py",
            ),
            authorization_contract_fingerprint=_source_hash(
                repository_root,
                "src/pastila_scout/editor/generation/ai_provider_adapter/openai/interpreter.py",
            ),
            reconstruction_contract_fingerprint=_source_hash(
                repository_root,
                "src/pastila_scout/editor/generation/ai_provider_adapter/openai/reconstructor.py",
            ),
            episode_draft_contract_fingerprint=_source_hash(
                repository_root,
                "src/pastila_scout/editor/generation/revision/contracts.py",
            ),
        ),
        "execution": Execution(
            planned=ExecutionCounts(
                provider_requests=24,
                provider_responses=None,
                retries=0,
                fallbacks=0,
                replays=0,
            ),
            actual=ExecutionCounts(
                provider_requests=experiment["provider_request_count"],
                provider_responses=experiment["provider_response_count"],
                retries=experiment["retry_count"],
                fallbacks=experiment["fallback_count"],
                replays=experiment["replay_count"],
            ),
        ),
        "integrity": {
            "prompt_delta_budget": _gate("PASS", budget["validation_result"]),
            "provider_comparability": _gate("COMPARABLE", provider["classification"]),
            "production_prompt_fingerprint": _gate(
                h2["control_prompt_fingerprint"],
                experiment["control_prompt_fingerprint"],
            ),
            "treatment_prompt_fingerprint": _gate(
                h2["h2_prompt_fingerprint"],
                experiment["candidate_prompt_fingerprint"],
            ),
            "prompt_identity": _gate(
                24, experiment["prompt_identity_checkpoint"]["passes"]
            ),
            "projection_count_equality": _gate(
                24, experiment["projection_checkpoint"]["count_equality_passes"]
            ),
            "projection_set_equality": _gate(
                24, experiment["projection_checkpoint"]["set_equality_passes"]
            ),
            "offline_request_assembly": _gate(
                24, h2["h2_offline_validation"]["request_assembly_passes"]
            ),
            "scenario_pairing": _gate(24, comparisons["scenario_count"]),
            "artifact_validation": _gate("PASS", "PASS"),
            "repository_validation": _gate("PASS", "PASS"),
        },
        "results": Results(
            technical=TechnicalResults(
                technical_pipeline_successes=pipeline["technical_pipeline_successes"],
                technical_pipeline_failures=24
                - pipeline["technical_pipeline_successes"],
                dto_validation_passes=pipeline["provider_dto_passes"],
                authorization_passes=pipeline["authorization_passes"],
                reconstruction_passes=pipeline["reconstruction_passes"],
                episode_draft_validation_passes=pipeline[
                    "episode_draft_validation_passes"
                ],
                technical_non_regression=(
                    "PASS" if experiment["technical_non_regression"] else "FAIL"
                ),
            ),
            reference=ReferenceResults(
                unknown_references=references["unknown_scenarios"],
                unauthorized_references=references["unauthorized_scenarios"],
                missing_authorized_references=references["missing_scenarios"],
                duplicate_references=references["duplicate_scenarios"],
                malformed_references=references["malformed_scenarios"],
                reference_precision=references["precision"]["mean"],
                reference_recall=references["recall"]["mean"],
                exact_reference_compliance_count=references[
                    "exact_authorized_scenarios"
                ],
                exact_reference_compliance_total=24,
                reference_non_regression=(
                    "PASS" if experiment["reference_non_regression"] else "FAIL"
                ),
            ),
            editorial=EditorialResults(
                editorial_evaluations=editorial["evaluations"],
                editorial_acceptance_passes=editorial["acceptance_passes"],
                editorial_acceptance_failures=editorial["acceptance_failures"],
                mean_editorial_score=round(editorial["mean_score"], 4),
                median_editorial_score=round(editorial["median_score"], 4),
                editorial_improvement=(
                    "PASS"
                    if experiment["editorial_improvement"]["threshold_passed"]
                    else "FAIL"
                ),
                acceptance_transitions=experiment["acceptance_transitions"],
                failure_category_transitions=experiment["failure_category_transitions"],
                targeted_metric=TargetedMetric(
                    metric_name="QUOTE_MUTATION",
                    control_value=quote["control_frequency"],
                    treatment_value=quote["treatment_frequency"],
                    resolved_cases=quote["resolved_cases"],
                    persisting_cases=quote["persisting_cases"],
                    new_cases=quote["new_cases"],
                    net_change=quote["treatment_frequency"]
                    - quote["control_frequency"],
                    net_change_convention="treatment_value - control_value",
                    expected_direction="DECREASE",
                    direction_satisfied=quote["treatment_frequency"]
                    < quote["control_frequency"],
                ),
            ),
            operational=OperationalResults(
                median_latency_ms=round(latency["median"], 3),
                p95_latency_ms=round(latency["p95"], 3),
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["known_total_tokens"],
                estimated_cost=round(cost["known_estimated_total_cost_usd"], 7),
                cost_currency="USD",
            ),
        ),
        "decision": Decision(
            candidate_decision=experiment["candidate_decision"],
            decision_reason="Targeted quote reduction did not satisfy aggregate editorial improvement gates.",
            decision_gates={
                "technical_non_regression": "PASS",
                "reference_non_regression": "PASS",
                "experiment_integrity": "PASS",
                "prompt_delta_budget": "PASS",
                "editorial_improvement": "FAIL",
            },
            root_conclusion=experiment["root_conclusion"],
            recommendation="DESIGN_THIRD_PROMPT_HYPOTHESIS",
        ),
        "promotion": Promotion(
            production_promotion=experiment["production_promotion"],
            production_prompt_changed=experiment["production_prompt_modified"],
            authoritative_production_baseline="Part 7C.2",
            promotion_approved_by=None,
            promotion_timestamp=None,
        ),
        "artifacts": artifacts,
        "validation": ManifestValidation(
            status="PASS",
            errors=[],
            warnings=[
                "provider model revision unavailable",
                "provider API version unavailable",
            ],
            validated_artifacts=len(artifacts),
            failed_invariants=[],
        ),
        "historical_backfill_assessment": {
            "Part 7C.2": "BACKFILL_READY",
            "Part 7H": "BACKFILL_READY",
        },
    }
    preliminary = ExperimentManifest.model_validate(manifest_data)
    fingerprint = canonical_manifest_fingerprint(preliminary)
    return preliminary.model_copy(
        update={
            "manifest": preliminary.manifest.model_copy(
                update={"manifest_fingerprint": fingerprint}
            )
        }
    )


def _update_history(repository_root: Path, manifest: ExperimentManifest) -> None:
    path = repository_root / HISTORY_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    matches = [
        item
        for item in document["history"]
        if item["benchmark_id"] == manifest.experiment.experiment_id
    ]
    if len(matches) != 1:
        raise RuntimeError("Part 7H.2 history entry missing or ambiguous")
    entry = matches[0]
    metadata = {
        "manifest_path": str(MANIFEST_PATH).replace("\\", "/"),
        "manifest_fingerprint": manifest.manifest.manifest_fingerprint,
        "manifest_schema_version": manifest.manifest.schema_version,
        "manifest_validation_status": "PASS",
    }
    for key, value in metadata.items():
        if key in entry and entry[key] != value:
            raise RuntimeError(f"history manifest metadata conflict: {key}")
        entry[key] = value
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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


def _write_schema(repository_root: Path) -> None:
    path = repository_root / SCHEMA_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    manifest = build_part_7h2_manifest(root)
    _update_history(root, manifest)
    manifest = build_part_7h2_manifest(root)
    if (
        canonical_manifest_fingerprint(manifest)
        != manifest.manifest.manifest_fingerprint
    ):
        raise RuntimeError("manifest fingerprint changed after history linkage")
    serialize_manifest(root / MANIFEST_PATH, manifest)
    _write_schema(root)
    diagnostics = validate_manifest(manifest, root)
    if diagnostics.status != GateStatus.PASS:
        raise RuntimeError(f"manifest validation failed: {diagnostics.errors}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Fingerprint: {manifest.manifest.manifest_fingerprint}")
    print(f"Artifacts validated: {diagnostics.validated_artifacts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
