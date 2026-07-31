"""Manifest-faithful reviewer execution-plan resolution."""

from pastila_scout.editor.qa.models import fingerprint
from pastila_scout.editor.qa.pipeline.models import (
    ReviewerExecutionPlan,
    ReviewerExecutionUnit,
)
from pastila_scout.editor.qa.pipeline.registry import ReviewerRegistryError
from pastila_scout.editor.qa.validation import draft_component_ids


class ReviewerPlanResolutionError(ValueError):
    pass


class ReviewerPlanResolver:
    def resolve(self, *, manifest, draft, registry, policy):
        review_items = tuple(
            item for item in manifest.items if item.operation == "review"
        )
        if len(review_items) > policy.maximum_execution_units:
            raise ReviewerPlanResolutionError("PIPELINE_EXECUTION_LIMIT_REACHED")
        item_ids = {item.manifest_item_id for item in review_items}
        known_components = set(draft_component_ids(draft))
        units = []
        for order, item in enumerate(review_items):
            try:
                descriptor = registry.descriptor(item.reviewer_id)
            except ReviewerRegistryError as error:
                raise ReviewerPlanResolutionError(str(error)) from error
            if descriptor.reviewer_version != item.reviewer_version:
                raise ReviewerPlanResolutionError("REVIEWER_VERSION_MISMATCH")
            if item.scope not in descriptor.supported_scopes:
                raise ReviewerPlanResolutionError("REVIEW_SCOPE_UNSUPPORTED")
            if not set(item.target_component_ids) <= known_components:
                raise ReviewerPlanResolutionError("TARGET_COMPONENT_UNKNOWN")
            if item.scope.value != "episode" and not item.target_component_ids:
                raise ReviewerPlanResolutionError("TARGET_COMPONENT_INVALID")
            dependencies = tuple(sorted(item.dependencies))
            if item.manifest_item_id in dependencies:
                raise ReviewerPlanResolutionError("DEPENDENCY_SELF_REFERENCE")
            if not set(dependencies) <= item_ids:
                raise ReviewerPlanResolutionError("DEPENDENCY_UNKNOWN")
            payload = {
                "manifest": manifest.manifest_fingerprint,
                "reviewer_id": item.reviewer_id,
                "reviewer_version": item.reviewer_version,
                "required": item.required,
                "scope": item.scope,
                "targets": item.target_component_ids,
                "capabilities": descriptor.capabilities,
                "dependencies": dependencies,
            }
            units.append(
                ReviewerExecutionUnit(
                    execution_id="execution:" + fingerprint(payload),
                    manifest_item_id=item.manifest_item_id,
                    manifest_order=order,
                    reviewer_id=item.reviewer_id,
                    reviewer_version=item.reviewer_version,
                    required=item.required,
                    scope=item.scope,
                    target_component_ids=item.target_component_ids,
                    required_capabilities=descriptor.capabilities,
                    depends_on_execution_ids=dependencies,
                )
            )
        item_to_execution = {unit.manifest_item_id: unit.execution_id for unit in units}
        units = [
            unit.model_copy(
                update={
                    "depends_on_execution_ids": tuple(
                        item_to_execution[item]
                        for item in unit.depends_on_execution_ids
                    )
                }
            )
            for unit in units
        ]
        _reject_cycles(tuple(units))
        return ReviewerExecutionPlan.build(
            draft_fingerprint=fingerprint(draft),
            manifest_fingerprint=manifest.manifest_fingerprint,
            registry_fingerprint=registry.registry_fingerprint,
            policy_fingerprint=policy.policy_fingerprint,
            execution_units=tuple(units),
        )


def _reject_cycles(units):
    graph = {unit.execution_id: unit.depends_on_execution_ids for unit in units}
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            raise ReviewerPlanResolutionError("DEPENDENCY_CYCLE")
        if node in visited:
            return
        visiting.add(node)
        for dependency in sorted(graph[node]):
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
