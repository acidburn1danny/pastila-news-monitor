"""Final freeze-coverage regressions for Phase 6.1 execution planning."""

import ast
import json
from dataclasses import asdict
from pathlib import Path

import pytest
from test_editorial_script_composer_llm_execution import (
    FREEZE,
    _codes,
    _context,
    _multi,
    _plan,
    _replace_message,
    _replace_request,
    _seal_message,
    _seal_plan,
    _seal_request,
)

import pastila_scout.editor.script_composer as public_api
import pastila_scout.editor.script_composer.llm_execution_validation as validation
from pastila_scout.editor.script_composer import (
    build_draft_llm_execution_plan,
    derive_draft_llm_execution_plan_fingerprint,
    derive_draft_llm_execution_plan_identity,
    derive_llm_execution_message_fingerprint,
    derive_llm_execution_message_identity,
    derive_llm_execution_request_fingerprint,
    derive_llm_execution_request_identity,
    validate_draft_llm_execution_plan,
)


def _seal_codes(plan):
    return {
        code
        for code in _codes(plan)
        if code.startswith("llm-execution-invalid-")
        and code.endswith(("-identity", "-fingerprint"))
    }


def _stale_plan_identity():
    plan = _plan()
    changed = plan.model_copy(
        update={"execution_plan_reference": plan.execution_plan_reference + "-changed"}
    )
    return changed.model_copy(
        update={"fingerprint": derive_draft_llm_execution_plan_fingerprint(changed)}
    )


def _stale_plan_fingerprint():
    plan = _plan()
    changed = plan.model_copy(
        update={"execution_plan_reference": plan.execution_plan_reference + "-changed"}
    )
    return changed.model_copy(
        update={"identity": derive_draft_llm_execution_plan_identity(changed)}
    )


def _stale_request_identity():
    plan = _plan()
    request = plan.execution_requests[0]
    changed = request.model_copy(
        update={"draft_reference": request.draft_reference + "-changed"}
    )
    changed = changed.model_copy(
        update={"fingerprint": derive_llm_execution_request_fingerprint(changed)}
    )
    return _replace_request(plan, 0, changed)


def _stale_request_fingerprint():
    plan = _plan()
    request = plan.execution_requests[0]
    changed = request.model_copy(
        update={"draft_reference": request.draft_reference + "-changed"}
    )
    changed = changed.model_copy(
        update={"identity": derive_llm_execution_request_identity(changed)}
    )
    return _replace_request(plan, 0, changed)


def _stale_message_identity():
    plan = _plan()
    message = plan.execution_requests[0].execution_messages[0]
    changed = message.model_copy(
        update={"execution_text": message.execution_text + "x"}
    )
    changed = changed.model_copy(
        update={"fingerprint": derive_llm_execution_message_fingerprint(changed)}
    )
    return _replace_message(plan, 0, 0, changed)


def _stale_message_fingerprint():
    plan = _plan()
    message = plan.execution_requests[0].execution_messages[0]
    changed = message.model_copy(
        update={"execution_text": message.execution_text + "x"}
    )
    changed = changed.model_copy(
        update={"identity": derive_llm_execution_message_identity(changed)}
    )
    return _replace_message(plan, 0, 0, changed)


def test_stale_plan_identity_is_independently_rejected():
    assert _seal_codes(_stale_plan_identity()) == {
        "llm-execution-invalid-plan-identity"
    }


def test_forged_plan_identity_is_independently_rejected():
    plan = _plan().model_copy(
        update={"identity": f"scout:draft-llm-execution-plan:{'f' * 64}"}
    )
    plan = plan.model_copy(
        update={"fingerprint": derive_draft_llm_execution_plan_fingerprint(plan)}
    )
    assert _seal_codes(plan) == {"llm-execution-invalid-plan-identity"}


def test_stale_plan_fingerprint_is_independently_rejected():
    assert _seal_codes(_stale_plan_fingerprint()) == {
        "llm-execution-invalid-plan-fingerprint"
    }


def test_forged_plan_fingerprint_is_independently_rejected():
    assert _seal_codes(_plan().model_copy(update={"fingerprint": "f" * 64})) == {
        "llm-execution-invalid-plan-fingerprint"
    }


def test_stale_request_identity_is_independently_rejected():
    assert _seal_codes(_stale_request_identity()) == {
        "llm-execution-invalid-request-identity"
    }


def test_forged_request_identity_is_independently_rejected():
    plan = _plan()
    request = plan.execution_requests[0].model_copy(
        update={"identity": f"scout:llm-execution-request:{'f' * 64}"}
    )
    request = request.model_copy(
        update={"fingerprint": derive_llm_execution_request_fingerprint(request)}
    )
    assert _seal_codes(_replace_request(plan, 0, request)) == {
        "llm-execution-invalid-request-identity"
    }


def test_stale_request_fingerprint_is_independently_rejected():
    assert _seal_codes(_stale_request_fingerprint()) == {
        "llm-execution-invalid-request-fingerprint"
    }


def test_forged_request_fingerprint_is_independently_rejected():
    plan = _plan()
    request = plan.execution_requests[0].model_copy(update={"fingerprint": "f" * 64})
    assert _seal_codes(_replace_request(plan, 0, request)) == {
        "llm-execution-invalid-request-fingerprint"
    }


def test_stale_message_identity_is_independently_rejected():
    assert _seal_codes(_stale_message_identity()) == {
        "llm-execution-invalid-message-identity"
    }


def test_forged_message_identity_is_independently_rejected():
    plan = _plan()
    message = (
        plan.execution_requests[0]
        .execution_messages[0]
        .model_copy(update={"identity": f"scout:llm-execution-message:{'f' * 64}"})
    )
    message = message.model_copy(
        update={"fingerprint": derive_llm_execution_message_fingerprint(message)}
    )
    assert _seal_codes(_replace_message(plan, 0, 0, message)) == {
        "llm-execution-invalid-message-identity"
    }


def test_stale_message_fingerprint_is_independently_rejected():
    assert _seal_codes(_stale_message_fingerprint()) == {
        "llm-execution-invalid-message-fingerprint"
    }


def test_forged_message_fingerprint_is_independently_rejected():
    plan = _plan()
    message = (
        plan.execution_requests[0]
        .execution_messages[0]
        .model_copy(update={"fingerprint": "f" * 64})
    )
    assert _seal_codes(_replace_message(plan, 0, 0, message)) == {
        "llm-execution-invalid-message-fingerprint"
    }


_TEXT_ATTACKS = (
    pytest.param(
        lambda text: text.replace("claim-reference", "claim-ref"), id="altered"
    ),
    pytest.param(lambda text: text + " appended", id="appended"),
    pytest.param(lambda text: "prepended " + text, id="prepended"),
    pytest.param(lambda text: "\n".join(text.split("\n")[:-1]), id="missing-line"),
    pytest.param(lambda text: text + "\nextra", id="extra-line"),
    pytest.param(lambda text: text.replace("\n", "\r\n"), id="crlf"),
    pytest.param(lambda text: text.replace("\n", "\r"), id="cr-only"),
    pytest.param(lambda text: text.replace("\n", "\u2028"), id="line-separator"),
    pytest.param(lambda text: text.replace("\n", "\u2029"), id="paragraph-separator"),
    pytest.param(lambda text: text + "\n", id="trailing-newline"),
    pytest.param(lambda text: " " + text, id="leading-space"),
    pytest.param(lambda text: text + " ", id="trailing-space"),
    pytest.param(lambda text: text.replace(": ", ":\t"), id="tab"),
    pytest.param(lambda text: text.replace(": ", ":\u00a0"), id="nbsp"),
    pytest.param(lambda text: text.replace(": ", ":\u2009"), id="thin-space"),
    pytest.param(lambda text: text.replace("request", "requeѕt"), id="confusable"),
)


@pytest.mark.parametrize("transform", _TEXT_ATTACKS)
def test_complete_execution_text_attack_matrix(transform):
    plan = _plan()
    message = plan.execution_requests[0].execution_messages[0]
    changed = _seal_message(
        message.model_copy(update={"execution_text": transform(message.execution_text)})
    )
    codes = _codes(_replace_message(plan, 0, 0, changed))
    assert "llm-execution-message-execution-text-mismatch" in codes


_REFERENCE_ATTACKS = (
    pytest.param("arbitrary", id="arbitrary"),
    pytest.param("llm-execution-plan:wrong", id="canonical-looking-wrong"),
    pytest.param("https://example.test/item", id="url"),
    pytest.param("https://user:secret@example.test/item", id="credential-url"),
    pytest.param("https://example.test/item?token=private", id="query"),
    pytest.param("https://example.test/item#private", id="fragment"),
    pytest.param(r"C:\Users\private\item.json", id="windows-path"),
    pytest.param("/home/private/item.json", id="posix-path"),
    pytest.param("line\nbreak", id="multiline"),
    pytest.param("x" * 201, id="oversized"),
    pytest.param(" llm-execution-plan:wrong", id="leading-space"),
    pytest.param("llm-execution-plan:wrong ", id="trailing-space"),
    pytest.param("LLM-EXECUTION-PLAN:WRONG", id="case"),
    pytest.param("llm‐execution-plan:wrong", id="confusable"),
    pytest.param("0x7ffdeadbeef", id="memory-address"),
)


@pytest.mark.parametrize("level", ("plan", "request", "message"))
@pytest.mark.parametrize("value", _REFERENCE_ATTACKS)
def test_complete_canonical_reference_attack_matrix(level, value):
    plan = _plan()
    if level == "plan":
        changed = _seal_plan(
            plan.model_copy(update={"execution_plan_reference": value})
        )
    elif level == "request":
        request = _seal_request(
            plan.execution_requests[0].model_copy(
                update={"execution_request_reference": value}
            )
        )
        changed = _replace_request(plan, 0, request)
    else:
        message = _seal_message(
            plan.execution_requests[0]
            .execution_messages[0]
            .model_copy(update={"execution_message_reference": value})
        )
        changed = _replace_message(plan, 0, 0, message)
    assert _codes(changed)


def test_foreign_valid_identity_derived_canonical_references_are_rejected():
    plan, context = _multi()
    foreign_request = plan.execution_requests[1]
    request = _seal_request(
        plan.execution_requests[0].model_copy(
            update={
                "execution_request_reference": foreign_request.execution_request_reference
            }
        )
    )
    assert _codes(_replace_request(plan, 0, request), context)
    foreign_message = plan.execution_requests[1].execution_messages[0]
    message = _seal_message(
        plan.execution_requests[0]
        .execution_messages[0]
        .model_copy(
            update={
                "execution_message_reference": foreign_message.execution_message_reference
            }
        )
    )
    assert _codes(_replace_message(plan, 0, 0, message), context)


def _empty():
    _, _, rendered, rendered_context = FREEZE["_empty_authority"]()
    context = _context(rendered, rendered_context)
    return build_draft_llm_execution_plan(rendered, context), context


def test_empty_valid_authoritative_tuple():
    plan, context = _empty()
    assert plan.execution_requests == ()
    assert validate_draft_llm_execution_plan(plan, context) == ()


def test_empty_null_collection_is_reconstruction_failure():
    plan, context = _empty()
    changed = plan.model_construct(**{**plan.model_dump(), "execution_requests": None})
    assert _codes(changed, context) == {"llm-execution-invalid-reconstructed-plan"}


def test_empty_mutable_list_is_canonicalized_to_tuple():
    plan, context = _empty()
    changed = plan.model_construct(**{**plan.model_dump(), "execution_requests": []})
    assert validate_draft_llm_execution_plan(changed, context) == ()
    assert (
        build_draft_llm_execution_plan(
            context.rendered_prompt_plans[0], context
        ).execution_requests
        == ()
    )


def test_empty_placeholder_request_is_rejected():
    plan, context = _empty()
    changed = _seal_plan(
        plan.model_copy(update={"execution_requests": (_plan().execution_requests[0],)})
    )
    assert "llm-execution-extra-request" in _codes(changed, context)


def test_empty_placeholder_message_is_rejected():
    plan, context = _empty()
    placeholder = _plan().execution_requests[0]
    placeholder = _seal_request(
        placeholder.model_copy(
            update={"execution_messages": (placeholder.execution_messages[0],)}
        )
    )
    changed = _seal_plan(plan.model_copy(update={"execution_requests": (placeholder,)}))
    assert "llm-execution-extra-request" in _codes(changed, context)


def test_empty_stale_identity_is_rejected():
    plan, context = _empty()
    assert "llm-execution-invalid-plan-identity" in _codes(
        plan.model_copy(
            update={"identity": f"scout:draft-llm-execution-plan:{'f' * 64}"}
        ),
        context,
    )


def test_empty_stale_fingerprint_is_rejected():
    plan, context = _empty()
    assert "llm-execution-invalid-plan-fingerprint" in _codes(
        plan.model_copy(update={"fingerprint": "f" * 64}), context
    )


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    (
        (
            "execution_plan_reference",
            "llm-execution-plan:wrong",
            "llm-execution-execution-plan-reference-mismatch",
        ),
        (
            "rendered_plan_fingerprint",
            "f" * 64,
            "llm-execution-rendered-plan-fingerprint-mismatch",
        ),
        (
            "request_plan_fingerprint",
            "f" * 64,
            "llm-execution-request-plan-fingerprint-mismatch",
        ),
        (
            "normalized_input_reference",
            "input:wrong",
            "llm-execution-normalized-input-reference-mismatch",
        ),
        (
            "normalized_input_identity",
            f"scout:llm-execution-normalized-input-lineage:{'f' * 64}",
            "llm-execution-normalized-input-identity-mismatch",
        ),
        (
            "normalized_input_fingerprint",
            "f" * 64,
            "llm-execution-normalized-input-fingerprint-mismatch",
        ),
    ),
)
def test_empty_incorrect_lineage_is_rejected(field, value, expected):
    plan, context = _empty()
    changed = _seal_plan(plan.model_copy(update={field: value}))
    assert expected in _codes(changed, context)


def test_local_normalized_input_lineage_namespace_and_derivation():
    plan = _plan()
    assert plan.normalized_input_identity.startswith(
        "scout:llm-execution-normalized-input-lineage:"
    )
    assert plan.normalized_input_identity == (
        validation._local_normalized_input_lineage_identity(
            plan.normalized_input_reference
        )
    )
    assert plan.normalized_input_fingerprint == (
        validation._local_normalized_input_lineage_fingerprint(
            plan.normalized_input_reference
        )
    )
    other_reference = plan.normalized_input_reference + "-other"
    assert validation._local_normalized_input_lineage_identity(other_reference) != (
        plan.normalized_input_identity
    )
    assert validation._local_normalized_input_lineage_fingerprint(other_reference) != (
        plan.normalized_input_fingerprint
    )


def test_foreign_local_normalized_input_seals_are_not_lookup_authority():
    plan = _plan()
    foreign_reference = "input:foreign"
    changed = _seal_plan(
        plan.model_copy(
            update={
                "normalized_input_identity": validation._local_normalized_input_lineage_identity(
                    foreign_reference
                ),
                "normalized_input_fingerprint": validation._local_normalized_input_lineage_fingerprint(
                    foreign_reference
                ),
            }
        )
    )
    codes = _codes(changed)
    assert "llm-execution-normalized-input-identity-mismatch" in codes
    assert "llm-execution-normalized-input-fingerprint-mismatch" in codes
    assert "llm-execution-unknown-rendered-plan" not in codes


def test_complete_repeated_request_is_rejected_before_lookup_overwrite():
    plan, context = _multi()
    changed = _seal_plan(
        plan.model_copy(
            update={
                "execution_requests": (
                    *plan.execution_requests,
                    plan.execution_requests[0],
                )
            }
        )
    )
    first = validate_draft_llm_execution_plan(changed, context)
    second = validate_draft_llm_execution_plan(changed, context)
    assert first == second
    assert "llm-execution-duplicate-execution-request-reference" in {
        item.code for item in first
    }


def test_complete_repeated_message_is_rejected_before_lookup_overwrite():
    plan, context = _multi()
    request = plan.execution_requests[0]
    request = _seal_request(
        request.model_copy(
            update={
                "execution_messages": (
                    *request.execution_messages,
                    request.execution_messages[0],
                )
            }
        )
    )
    changed = _replace_request(plan, 0, request)
    first = validate_draft_llm_execution_plan(changed, context)
    second = validate_draft_llm_execution_plan(changed, context)
    assert first == second
    assert "llm-execution-duplicate-execution-message-reference" in {
        item.code for item in first
    }


def test_complete_same_process_diagnostic_payload_is_equal():
    plan = _plan().model_copy(update={"fingerprint": "f" * 64})
    first = validate_draft_llm_execution_plan(plan, _context())
    second = validate_draft_llm_execution_plan(plan, _context())
    assert first == second
    assert tuple(asdict(item) for item in first) == tuple(
        asdict(item) for item in second
    )
    assert json.dumps(
        [asdict(item) for item in first], sort_keys=True, separators=(",", ":")
    ) == json.dumps(
        [asdict(item) for item in second], sort_keys=True, separators=(",", ":")
    )
    assert str(first) == str(second)


def test_prior_diagnostics_are_immutable_and_later_calls_observe_mutation():
    plan, context = _multi()
    requests = list(plan.execution_requests)
    submitted = plan.model_construct(
        **{**plan.model_dump(), "execution_requests": requests}
    )
    before = validate_draft_llm_execution_plan(submitted, context)
    assert before == ()
    requests.append(requests[0])
    after = validate_draft_llm_execution_plan(submitted, context)
    assert before == ()
    assert after
    assert "llm-execution-duplicate-execution-request-reference" in {
        item.code for item in after
    }


def test_context_mutation_is_observed_without_cross_call_cache():
    plan = _plan()
    context = _context()
    plans = list(context.rendered_prompt_plans)
    submitted_context = context.model_construct(
        rendered_prompt_plans=plans,
        rendered_prompt_validation_context=context.rendered_prompt_validation_context,
    )
    assert validate_draft_llm_execution_plan(plan, submitted_context) == ()
    plans.clear()
    later = validate_draft_llm_execution_plan(plan, submitted_context)
    assert later
    assert validate_draft_llm_execution_plan(plan, context) == ()


def test_all_twelve_public_symbols_are_exported():
    expected = {
        "LLMExecutionMessage",
        "LLMExecutionRequest",
        "DraftLLMExecutionPlan",
        "LLMExecutionValidationContext",
        "build_draft_llm_execution_plan",
        "validate_draft_llm_execution_plan",
        "derive_llm_execution_message_identity",
        "derive_llm_execution_request_identity",
        "derive_draft_llm_execution_plan_identity",
        "derive_llm_execution_message_fingerprint",
        "derive_llm_execution_request_fingerprint",
        "derive_draft_llm_execution_plan_fingerprint",
    }
    assert {name for name in expected if hasattr(public_api, name)} == expected


def test_internal_helpers_are_not_package_exports():
    forbidden = {
        "_canonical_execution_plan_reference",
        "_local_normalized_input_lineage_identity",
        "_project",
        "_reconstruct",
        "_duplicates",
        "_safe_reference",
        "LLMExecutionDomainModel",
    }
    assert not {name for name in forbidden if hasattr(public_api, name)}


def test_dependency_direction_has_no_semantic_reverse_import():
    root = Path("src/pastila_scout/editor/script_composer")
    reverse = []
    for path in root.glob("*.py"):
        if (
            path.name == "__init__.py"
            or path.name.startswith("llm_execution_")
            or "mapping" in path.name
        ):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        reverse.extend(
            (path.name, node.module)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
            and "llm_execution" in node.module
        )
    assert reverse == []


def test_phase_is_provider_neutral_and_has_no_future_execution_dependency():
    root = Path("src/pastila_scout/editor/script_composer")
    forbidden_imports = {"openai", "anthropic", "gemini", "httpx", "requests"}
    forbidden_names = {
        "api_key",
        "endpoint",
        "model_name",
        "temperature",
        "top_p",
        "max_tokens",
        "retry",
        "stream",
        "tool_call",
        "response_format",
    }
    for path in root.glob("llm_execution_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not {
            module
            for module in imports
            if any(
                module == blocked or module.startswith(blocked + ".")
                for blocked in forbidden_imports
            )
        }
        identifiers = {
            node.id.casefold() for node in ast.walk(tree) if isinstance(node, ast.Name)
        }
        assert not (identifiers & forbidden_names)
