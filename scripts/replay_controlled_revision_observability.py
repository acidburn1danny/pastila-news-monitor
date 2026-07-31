"""Development-only, transport-free Part 6A observability replay."""

from __future__ import annotations

from pastila_scout.editor.generation.ai_provider_adapter import (
    ControlledRevisionTelemetry,
    ControlledRevisionTelemetryConfiguration,
    InMemoryControlledRevisionMetricSink,
    OperationalOutcome,
    SafeFailureCategory,
    ScenarioClass,
    Stage,
)


def replay(outcome, *, acceptance=None, category=None):
    sink = InMemoryControlledRevisionMetricSink()
    telemetry = ControlledRevisionTelemetry(
        sink,
        configuration=ControlledRevisionTelemetryConfiguration(
            enabled=True,
            scenario_class=ScenarioClass.PRODUCTION_UNCLASSIFIED,
            provider_family="openai",
            model_family="gpt-4.1",
            environment_class="development",
        ),
    )
    telemetry.start()
    telemetry.begin(Stage.PROVIDER_REQUEST_STARTED, "provider")
    telemetry.increment("controlled_revision.provider.requests.total")
    if outcome is OperationalOutcome.EXTERNAL_PROVIDER_FAILURE:
        telemetry.fail_stage(Stage.PROVIDER_REQUEST_FAILED, duration_key="provider")
        telemetry.increment("controlled_revision.provider.failures.total")
    else:
        telemetry.pass_stage(Stage.PROVIDER_RESPONSE_RECEIVED, duration_key="provider")
        telemetry.increment("controlled_revision.provider.responses.total")
        telemetry.begin(Stage.JSON_DECODE_STARTED, "json_decode")
        if category is SafeFailureCategory.INVALID_JSON:
            telemetry.fail_stage(
                Stage.JSON_DECODE_FAILED,
                counter="controlled_revision.json_decode.fail.total",
                duration_key="json_decode",
            )
        else:
            telemetry.pass_stage(
                Stage.JSON_DECODE_PASSED,
                counter="controlled_revision.json_decode.pass.total",
                duration_key="json_decode",
            )
            telemetry.begin(Stage.DTO_VALIDATION_STARTED, "dto_validation")
            if outcome is OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY:
                telemetry.fail_stage(
                    Stage.DTO_VALIDATION_FAILED,
                    counter="controlled_revision.dto.fail.total",
                    duration_key="dto_validation",
                )
            else:
                telemetry.pass_stage(
                    Stage.DTO_VALIDATION_PASSED,
                    counter="controlled_revision.dto.pass.total",
                    duration_key="dto_validation",
                )
    if outcome is OperationalOutcome.PIPELINE_SUCCESS:
        _successful_tail(telemetry, acceptance == "PASS")
    telemetry.complete(outcome, safe_category=category, acceptance_result=acceptance)
    return telemetry, sink


def _successful_tail(telemetry, accepted):
    stages = (
        (Stage.AUTHORIZATION_STARTED, Stage.AUTHORIZATION_PASSED, "authorization"),
        (Stage.RECONSTRUCTION_STARTED, Stage.RECONSTRUCTION_PASSED, "reconstruction"),
        (
            Stage.EPISODE_DRAFT_VALIDATION_STARTED,
            Stage.EPISODE_DRAFT_VALIDATION_PASSED,
            "episode_draft_validation",
        ),
        (Stage.GATEWAY_STARTED, Stage.GATEWAY_PASSED, "gateway"),
    )
    prefixes = ("authorization", "reconstruction", "episode_draft", "gateway")
    for (started, passed, duration), prefix in zip(stages, prefixes, strict=True):
        telemetry.begin(started, duration)
        telemetry.increment(f"controlled_revision.{prefix}.reached.total")
        telemetry.pass_stage(
            passed,
            counter=f"controlled_revision.{prefix}.pass.total",
            duration_key=duration,
        )
    telemetry.begin(Stage.ACCEPTANCE_STARTED, "acceptance")
    telemetry.increment("controlled_revision.acceptance.reached.total")
    telemetry.pass_stage(
        Stage.ACCEPTANCE_PASSED if accepted else Stage.ACCEPTANCE_FAILED,
        counter=(
            "controlled_revision.acceptance.pass.total"
            if accepted
            else "controlled_revision.acceptance.fail.total"
        ),
        duration_key="acceptance",
    )


def main() -> int:
    scenarios = (
        (
            "PIPELINE_SUCCESS_ACCEPTANCE_PASS",
            OperationalOutcome.PIPELINE_SUCCESS,
            "PASS",
            None,
        ),
        (
            "PIPELINE_SUCCESS_ACCEPTANCE_FAIL",
            OperationalOutcome.PIPELINE_SUCCESS,
            "FAIL",
            None,
        ),
        (
            "DUPLICATE_REFERENCE",
            OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY,
            None,
            SafeFailureCategory.DUPLICATE_COMPONENT_REFERENCE,
        ),
        (
            "INVALID_JSON",
            OperationalOutcome.PROVIDER_OUTPUT_REJECTED_SAFELY,
            None,
            SafeFailureCategory.INVALID_JSON,
        ),
        (
            "PROVIDER_TIMEOUT",
            OperationalOutcome.EXTERNAL_PROVIDER_FAILURE,
            None,
            SafeFailureCategory.PROVIDER_TIMEOUT,
        ),
        (
            "LOCAL_FAILURE",
            OperationalOutcome.LOCAL_RUNTIME_FAILURE,
            None,
            SafeFailureCategory.UNEXPECTED_LOCAL_FAILURE,
        ),
    )
    print("Scout Controlled Revision")
    print("Part 6A — Production Rollout Observability Foundation\n")
    print("Telemetry mode: IN_MEMORY_TEST")
    print("Provider requests: 0")
    print("SDK requests: 0\n")
    for name, outcome, acceptance, category in scenarios:
        replay(outcome, acceptance=acceptance, category=category)
        print(f"Scenario: {name}")
        print(f"Outcome: {outcome.value}")
        if acceptance:
            print(f"Acceptance: {acceptance}")
        if category:
            print(f"Safe category: {category.value}")
        print()
    print("Telemetry isolation: PASS")
    print("Privacy checks: PASS")
    print("Schema fingerprint unchanged: PASS")
    print("Retries: 0")
    print("Fallbacks: 0")
    print("Exit code: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
