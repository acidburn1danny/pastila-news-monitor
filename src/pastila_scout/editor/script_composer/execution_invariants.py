"""Shared pure structural invariants for Phase 3 execution contracts."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionInvariantViolation:
    code: str
    field_path: tuple[str | int, ...]
    related_references: tuple[str, ...] = ()


def duplicate_reference_violations(artifact) -> tuple[ExecutionInvariantViolation, ...]:
    issues: list[ExecutionInvariantViolation] = []
    for name, value in artifact.__dict__.items():
        if (
            name.endswith("_references")
            and isinstance(value, tuple)
            and len(value) != len(set(value))
        ):
            issues.append(
                ExecutionInvariantViolation("execution-reference-duplicate", (name,))
            )
    return tuple(issues)


def capability_requirement_violations(item) -> tuple[ExecutionInvariantViolation, ...]:
    custom = item.capability.value == "custom"
    if custom == (item.custom_identifier is not None):
        return ()
    return (
        ExecutionInvariantViolation(
            "execution-custom-capability-mismatch", ("custom_identifier",)
        ),
    )


def capability_set_violations(item) -> tuple[ExecutionInvariantViolation, ...]:
    keys = [
        (requirement.capability.value, requirement.custom_identifier)
        for requirement in item.requirements
    ]
    if len(keys) == len(set(keys)):
        return ()
    return (
        ExecutionInvariantViolation(
            "execution-capability-duplicate", ("requirements",)
        ),
    )


def retry_policy_violations(policy) -> tuple[ExecutionInvariantViolation, ...]:
    overlap = set(policy.retryable_failure_types) & set(
        policy.non_retryable_failure_types
    )
    if not overlap:
        return ()
    return (
        ExecutionInvariantViolation(
            "execution-retry-classification-conflict",
            ("retryable_failure_types",),
            tuple(sorted(item.value for item in overlap)),
        ),
    )


def failure_policy_violations(policy) -> tuple[ExecutionInvariantViolation, ...]:
    if not (
        set(policy.required_output_binding_references)
        & set(policy.optional_output_binding_references)
    ):
        return ()
    return (
        ExecutionInvariantViolation(
            "execution-failure-binding-classification-conflict",
            ("required_output_binding_references",),
        ),
    )


def outcome_violations(outcome) -> tuple[ExecutionInvariantViolation, ...]:
    status = outcome.status.value
    issues: list[ExecutionInvariantViolation] = []
    has_failure_type = outcome.failure_type is not None
    has_failure_code = outcome.failure_code is not None
    failure_metadata_paired = has_failure_type == has_failure_code
    has_failure = has_failure_type and has_failure_code
    if not failure_metadata_paired:
        issues.append(
            ExecutionInvariantViolation(
                "execution-failure-metadata-pair-invalid",
                ("failure_type",),
            )
        )
    if set(outcome.satisfied_output_binding_references) & set(
        outcome.missing_output_binding_references
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-outcome-binding-state-conflict",
                ("satisfied_output_binding_references",),
            )
        )
    if status == "success" and (
        (has_failure if failure_metadata_paired else False)
        or outcome.retry_eligible
        or outcome.missing_output_binding_references
        or not outcome.produced_output_artifact_references
    ):
        issues.append(
            ExecutionInvariantViolation("execution-success-shape-invalid", ("status",))
        )
    elif status == "partial_success" and (
        not outcome.produced_output_artifact_references
        or not outcome.missing_output_binding_references
        or not outcome.satisfied_output_binding_references
        or not outcome.retry_eligible
    ):
        issues.append(
            ExecutionInvariantViolation("execution-partial-shape-invalid", ("status",))
        )
    elif status == "failure" and (
        (not has_failure if failure_metadata_paired else False)
        or outcome.produced_output_artifact_references
        or outcome.satisfied_output_binding_references
    ):
        issues.append(
            ExecutionInvariantViolation("execution-failure-shape-invalid", ("status",))
        )
    return tuple(issues)


def observation_violations(observation) -> tuple[ExecutionInvariantViolation, ...]:
    issues: list[ExecutionInvariantViolation] = []
    if (
        observation.sequence_number == 0
        and observation.previous_observation_fingerprint
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-previous-invalid",
                ("previous_observation_fingerprint",),
            )
        )
    if (
        observation.sequence_number > 0
        and not observation.previous_observation_fingerprint
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-previous-required",
                ("previous_observation_fingerprint",),
            )
        )
    terminal = observation.observed_state.value
    nonterminal = {"planned", "eligible", "blocked", "submitted", "accepted", "running"}
    if terminal in nonterminal and (
        observation.outcome_reference
        or observation.failure_reference
        or observation.superseding_execution_reference
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-nonterminal-payload-invalid",
                ("observed_state",),
            )
        )
    if (
        terminal in {"succeeded", "partially_succeeded"}
        and not observation.outcome_reference
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-outcome-required", ("outcome_reference",)
            )
        )
    if (
        terminal in {"succeeded", "partially_succeeded"}
        and observation.failure_reference
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-failure-forbidden", ("failure_reference",)
            )
        )
    if terminal in {"succeeded", "partially_succeeded", "failed"} and (
        observation.superseding_execution_reference
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-supersession-forbidden",
                ("superseding_execution_reference",),
            )
        )
    if terminal == "failed" and not (
        observation.failure_reference or observation.outcome_reference
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-failure-required", ("failure_reference",)
            )
        )
    if terminal == "cancelled" and observation.outcome_reference:
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-outcome-forbidden", ("outcome_reference",)
            )
        )
    if terminal == "cancelled" and (
        observation.failure_reference or observation.superseding_execution_reference
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-cancelled-payload-invalid",
                ("observed_state",),
            )
        )
    if terminal == "superseded" and not observation.superseding_execution_reference:
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-supersession-required",
                ("superseding_execution_reference",),
            )
        )
    if terminal == "superseded" and (
        observation.outcome_reference or observation.failure_reference
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-superseded-payload-invalid",
                ("observed_state",),
            )
        )
    if (
        terminal == "superseded"
        and observation.superseding_execution_reference
        == observation.execution_request_reference
    ):
        issues.append(
            ExecutionInvariantViolation(
                "execution-observation-self-supersession",
                ("superseding_execution_reference",),
            )
        )
    return tuple(issues)


def execution_plan_violations(plan) -> tuple[ExecutionInvariantViolation, ...]:
    """Validate the closed unit dependency graph and embedded references."""
    issues: list[ExecutionInvariantViolation] = []
    ids = [item.execution_unit_id for item in plan.ordered_execution_units]
    ordinals = [item.ordinal for item in plan.ordered_execution_units]
    known = set(ids)
    if len(ids) != len(known):
        issues.append(
            ExecutionInvariantViolation(
                "execution-unit-identity-duplicate", ("ordered_execution_units",)
            )
        )
    if len(ordinals) != len(set(ordinals)):
        issues.append(
            ExecutionInvariantViolation(
                "execution-unit-ordinal-duplicate", ("ordered_execution_units",)
            )
        )
    if ordinals != list(range(len(ordinals))):
        issues.append(
            ExecutionInvariantViolation(
                "execution-unit-order-invalid", ("ordered_execution_units",)
            )
        )
    graph: dict[str, tuple[str, ...]] = {}
    for index, unit in enumerate(plan.ordered_execution_units):
        graph[unit.execution_unit_id] = unit.dependency_unit_references
        for dependency in unit.dependency_unit_references:
            if dependency == unit.execution_unit_id:
                issues.append(
                    ExecutionInvariantViolation(
                        "execution-unit-self-dependency",
                        (
                            "ordered_execution_units",
                            index,
                            "dependency_unit_references",
                        ),
                        (dependency,),
                    )
                )
            elif dependency not in known:
                issues.append(
                    ExecutionInvariantViolation(
                        "execution-unit-dependency-missing",
                        (
                            "ordered_execution_units",
                            index,
                            "dependency_unit_references",
                        ),
                        (dependency,),
                    )
                )
    for cycle in _cycles(graph):
        issues.append(
            ExecutionInvariantViolation(
                "execution-unit-dependency-cycle",
                ("ordered_execution_units",),
                cycle,
            )
        )
    declared_edges = [
        (item.source_unit_reference, item.dependency_unit_reference)
        for item in plan.dependency_declarations
    ]
    if len(declared_edges) != len(set(declared_edges)):
        issues.append(
            ExecutionInvariantViolation(
                "execution-dependency-declaration-duplicate",
                ("dependency_declarations",),
            )
        )
    actual_edges = {
        (item.execution_unit_id, dependency)
        for item in plan.ordered_execution_units
        for dependency in item.dependency_unit_references
    }
    declared_edge_set = set(declared_edges)
    for index, (source, dependency) in enumerate(declared_edges):
        if source not in known or dependency not in known:
            issues.append(
                ExecutionInvariantViolation(
                    "execution-dependency-declaration-unit-missing",
                    ("dependency_declarations", index),
                    tuple(sorted({source, dependency} - known)),
                )
            )
        if source == dependency:
            issues.append(
                ExecutionInvariantViolation(
                    "execution-dependency-declaration-self-dependency",
                    ("dependency_declarations", index),
                    (source,),
                )
            )
    if declared_edge_set != actual_edges:
        issues.append(
            ExecutionInvariantViolation(
                "execution-dependency-declarations-mismatch",
                ("dependency_declarations",),
            )
        )
    binding_ids = {item.output_binding_id for item in plan.expected_output_bindings}
    if len(binding_ids) != len(plan.expected_output_bindings):
        issues.append(
            ExecutionInvariantViolation(
                "execution-output-binding-identity-duplicate",
                ("expected_output_bindings",),
            )
        )
    capability_ids = {item.capability_set_id for item in plan.capability_sets}
    if len(capability_ids) != len(plan.capability_sets):
        issues.append(
            ExecutionInvariantViolation(
                "execution-capability-set-identity-duplicate", ("capability_sets",)
            )
        )
    for index, unit in enumerate(plan.ordered_execution_units):
        if unit.expected_output_binding_reference not in binding_ids:
            issues.append(
                ExecutionInvariantViolation(
                    "execution-unit-output-binding-missing",
                    (
                        "ordered_execution_units",
                        index,
                        "expected_output_binding_reference",
                    ),
                )
            )
    for index, binding in enumerate(plan.expected_output_bindings):
        if binding.unit_reference not in known:
            issues.append(
                ExecutionInvariantViolation(
                    "execution-output-binding-unit-missing",
                    ("expected_output_bindings", index, "unit_reference"),
                )
            )
    if plan.retry_policy_reference != plan.retry_policy.retry_policy_id:
        issues.append(
            ExecutionInvariantViolation(
                "execution-retry-policy-linkage-mismatch",
                ("retry_policy_reference",),
            )
        )
    if plan.failure_policy_reference != plan.failure_policy.failure_policy_id:
        issues.append(
            ExecutionInvariantViolation(
                "execution-failure-policy-linkage-mismatch",
                ("failure_policy_reference",),
            )
        )
    return tuple(issues)


def _cycles(graph: dict[str, tuple[str, ...]]) -> tuple[tuple[str, ...], ...]:
    found: set[tuple[str, ...]] = set()

    def visit(node: str, path: tuple[str, ...]) -> None:
        if node in path:
            cycle = path[path.index(node) :]
            rotations = [cycle[index:] + cycle[:index] for index in range(len(cycle))]
            found.add(min(rotations))
            return
        if node not in graph:
            return
        for dependency in sorted(graph[node]):
            visit(dependency, (*path, node))

    for node in sorted(graph):
        visit(node, ())
    return tuple(sorted(found))


__all__ = (
    "ExecutionInvariantViolation",
    "capability_requirement_violations",
    "capability_set_violations",
    "duplicate_reference_violations",
    "execution_plan_violations",
    "failure_policy_violations",
    "observation_violations",
    "outcome_violations",
    "retry_policy_violations",
)
