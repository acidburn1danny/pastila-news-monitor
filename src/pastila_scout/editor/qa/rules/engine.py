"""Deterministic, failure-isolating editorial rule execution engine."""

from pastila_scout.editor.qa.models import EditorialFinding, fingerprint
from pastila_scout.editor.qa.rules.context import RuleContext
from pastila_scout.editor.qa.rules.models import (
    CompletedRuleRecord,
    FailedRuleRecord,
    RuleApplicabilityStatus,
    RuleExecutionKey,
    RuleExecutionResult,
    RuleExecutionState,
    RuleFailureCode,
    RuleTraceEventType,
    RuleTraceRecord,
    SkippedRuleRecord,
)
from pastila_scout.editor.qa.rules.registry import RuleRegistry, RuleSet


class RuleEngine:
    """Run selected rules atomically and continue after local rule failures."""

    def execute(
        self, context: RuleContext, registry: RuleRegistry, rule_set: RuleSet
    ) -> RuleExecutionResult:
        rules = registry.resolve(rule_set)
        keys = tuple(_execution_key(rule, context).value for rule in rules)
        state = RuleExecutionState(
            revision=0,
            context_fingerprint=context.context_fingerprint,
            rule_set_fingerprint=rule_set.rule_set_fingerprint,
            pending_rule_keys=keys,
        )
        for rule, key in zip(rules, keys, strict=True):
            state = _run_one(state, rule, key, context)
        findings = state.accepted_findings[: context.policy.maximum_total_findings]
        trace = tuple(
            item.model_copy(update={"sequence_number": index})
            for index, item in enumerate(state.trace_records, start=1)
        )
        return RuleExecutionResult.build(
            context_fingerprint=context.context_fingerprint,
            rule_set_fingerprint=rule_set.rule_set_fingerprint,
            executed_rule_count=len(rules),
            successful_rule_count=len(state.completed_rules),
            skipped_rule_count=len(state.skipped_rules),
            failed_rule_count=len(state.failed_rules),
            findings=findings,
            completed_rules=state.completed_rules,
            skipped_rules=state.skipped_rules,
            failed_rules=state.failed_rules,
            trace=trace,
        )


def _run_one(state, rule, key, context):
    trace = state.trace_records + (
        _trace(state, RuleTraceEventType.RULE_STARTED, key, "RULE_STARTED"),
    )
    try:
        applicability = rule.applicability(context)
        if applicability.status is not RuleApplicabilityStatus.APPLICABLE:
            skipped = SkippedRuleRecord(
                execution_key=key, reason_code=applicability.reason_code
            )
            return state.model_copy(
                update={
                    "revision": state.revision + 1,
                    "pending_rule_keys": tuple(
                        item for item in state.pending_rule_keys if item != key
                    ),
                    "skipped_rules": state.skipped_rules + (skipped,),
                    "trace_records": trace
                    + (
                        _trace(
                            state,
                            RuleTraceEventType.RULE_SKIPPED,
                            key,
                            applicability.reason_code.value,
                        ),
                    ),
                }
            )
        output = rule.evaluate(context)
        if not isinstance(output, tuple):
            return _fail(state, key, trace, RuleFailureCode.INVALID_RULE_OUTPUT_TYPE)
        if not all(isinstance(item, EditorialFinding) for item in output):
            return _fail(state, key, trace, RuleFailureCode.INVALID_FINDING)
        if any(item.issue_code != rule.rule_id for item in output):
            return _fail(state, key, trace, RuleFailureCode.FINDING_RULE_ID_MISMATCH)
        ids = tuple(item.finding_id for item in output)
        if len(ids) != len(set(ids)) or set(ids) & {
            item.finding_id for item in state.accepted_findings
        }:
            return _fail(state, key, trace, RuleFailureCode.DUPLICATE_FINDING_ID)
        completed = CompletedRuleRecord(
            execution_key=key,
            finding_ids=ids,
            result_fingerprint=fingerprint(output),
        )
        base_sequence = len(trace)
        emitted = tuple(
            RuleTraceRecord(
                sequence_number=base_sequence + index,
                event_type=RuleTraceEventType.FINDING_EMITTED,
                execution_key=key,
                finding_id=item,
                message_code="FINDING_EMITTED",
            )
            for index, item in enumerate(ids, start=1)
        )
        return state.model_copy(
            update={
                "revision": state.revision + 1,
                "pending_rule_keys": tuple(
                    item for item in state.pending_rule_keys if item != key
                ),
                "completed_rules": state.completed_rules + (completed,),
                "accepted_findings": state.accepted_findings + output,
                "trace_records": trace
                + emitted
                + (
                    RuleTraceRecord(
                        sequence_number=base_sequence + len(emitted) + 1,
                        event_type=RuleTraceEventType.RULE_COMPLETED,
                        execution_key=key,
                        message_code="RULE_COMPLETED",
                    ),
                ),
            }
        )
    except Exception as error:  # noqa: BLE001 - isolate a plugin-style rule boundary
        del error
        return _fail(state, key, trace, RuleFailureCode.RULE_EXCEPTION)


def _fail(state, key, trace, code):
    record = FailedRuleRecord(
        execution_key=key, failure_code=code, message_code=code.value
    )
    return state.model_copy(
        update={
            "revision": state.revision + 1,
            "pending_rule_keys": tuple(
                item for item in state.pending_rule_keys if item != key
            ),
            "failed_rules": state.failed_rules + (record,),
            "trace_records": trace
            + (_trace(state, RuleTraceEventType.RULE_FAILED, key, code.value),),
        }
    )


def _trace(state, event, key, code, finding_id=None):
    return RuleTraceRecord(
        sequence_number=len(state.trace_records) + 1,
        event_type=event,
        execution_key=key,
        finding_id=finding_id,
        message_code=code,
    )


def _execution_key(rule, context):
    targets = tuple(
        item.component_id for item in context.target_entries(rule.supported_scopes)
    )
    return RuleExecutionKey(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        scope=context.requested_scope,
        target_component_ids=targets,
    )
