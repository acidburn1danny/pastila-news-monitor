"""Freeze-grade regressions for Phase 6.2 deterministic provider mapping."""

import ast
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_editorial_script_composer_provider_mapping import (
    UPSTREAM,
    _descriptor,
    _generic,
    _openai,
    _replace_message,
    _replace_request,
    _seal,
    _seal_generic,
    _seal_message,
    _seal_openai_plan,
    _seal_request,
)

import pastila_scout.editor.script_composer as public_api
from pastila_scout.editor.script_composer import (
    DomainValidationError,
    build_draft_provider_request_plan,
    build_openai_provider_request_plan,
    derive_draft_provider_request_plan_fingerprint,
    derive_draft_provider_request_plan_identity,
    derive_openai_provider_message_fingerprint,
    derive_openai_provider_message_identity,
    derive_openai_provider_request_fingerprint,
    derive_openai_provider_request_identity,
    derive_openai_provider_request_plan_fingerprint,
    derive_openai_provider_request_plan_identity,
    derive_provider_request_plan_descriptor_fingerprint,
    derive_provider_request_plan_descriptor_identity,
    validate_draft_provider_request_plan,
    validate_openai_provider_request_plan,
)


def _alternate(field, value):
    if isinstance(value, str):
        if field.endswith("fingerprint"):
            return "f" * 64 if value != "f" * 64 else "e" * 64
        if field.endswith("identity"):
            return value[:-1] + ("f" if value[-1] != "f" else "e")
        if field == "role":
            return "developer" if value == "user" else "user"
        if field == "provider":
            return "foreign-provider"
        if field == "mapping_contract_version":
            return "phase-6.2-openai-v2"
        return value + "-changed"
    if isinstance(value, int):
        return value + 1
    if isinstance(value, tuple):
        return value + value[:1] if value else (_openai()[0].requests[0],)
    if hasattr(value, "model_copy"):
        return value.model_copy(update={"fingerprint": "f" * 64})
    raise AssertionError(field)


def test_every_mutable_semantic_field_changes_identity_and_fingerprint():
    openai, _ = _openai()
    generic, _ = _generic()
    artifacts = (
        (
            _descriptor(),
            derive_provider_request_plan_descriptor_identity,
            derive_provider_request_plan_descriptor_fingerprint,
            set(),
        ),
        (
            generic,
            derive_draft_provider_request_plan_identity,
            derive_draft_provider_request_plan_fingerprint,
            set(),
        ),
        (
            openai.requests[0].messages[0],
            derive_openai_provider_message_identity,
            derive_openai_provider_message_fingerprint,
            set(),
        ),
        (
            openai.requests[0],
            derive_openai_provider_request_identity,
            derive_openai_provider_request_fingerprint,
            set(),
        ),
        (
            openai,
            derive_openai_provider_request_plan_identity,
            derive_openai_provider_request_plan_fingerprint,
            set(),
        ),
    )
    checked = 0
    for artifact, identity_function, fingerprint_function, closed in artifacts:
        for field in artifact.__class__.model_fields:
            if field in {"identity", "fingerprint"} | closed:
                continue
            changed = artifact.model_copy(
                update={field: _alternate(field, getattr(artifact, field))}
            )
            new_identity = identity_function(changed)
            assert new_identity != artifact.identity, field
            changed = changed.model_copy(update={"identity": new_identity})
            assert fingerprint_function(changed) != artifact.fingerprint, field
            checked += 1
    assert checked == 48


_REFERENCE_ATTACKS = (
    "arbitrary",
    "provider-request-plan:wrong",
    "https://example.test/item",
    "https://user:secret@example.test/item",
    "item?token=private",
    "item#private",
    r"C:\Users\private\item.json",
    "/home/private/item.json",
    "line\nbreak",
    "x" * 201,
    " leading",
    "trailing ",
    "CaseMutation",
    "cоnfusable",
    "object:0x7ffdeadbeef",
)


@pytest.mark.parametrize("value", _REFERENCE_ATTACKS)
@pytest.mark.parametrize(
    "level", ("descriptor", "generic", "openai-plan", "request", "message")
)
def test_canonical_reference_attack_matrix(level, value):
    generic, context = _generic()
    openai = generic.openai_request_plan
    if level == "descriptor":
        descriptor = _seal(
            generic.provider_descriptor.model_copy(
                update={"provider_descriptor_reference": value}
            ),
            derive_provider_request_plan_descriptor_identity,
            derive_provider_request_plan_descriptor_fingerprint,
        )
        changed = _seal_generic(
            generic.model_copy(update={"provider_descriptor": descriptor})
        )
        issues = validate_draft_provider_request_plan(changed, context)
    elif level == "generic":
        issues = validate_draft_provider_request_plan(
            _seal_generic(
                generic.model_copy(update={"provider_request_plan_reference": value})
            ),
            context,
        )
    elif level == "openai-plan":
        issues = validate_openai_provider_request_plan(
            _seal_openai_plan(
                openai.model_copy(update={"openai_request_plan_reference": value})
            ),
            context,
        )
    elif level == "request":
        request = _seal_request(
            openai.requests[0].model_copy(update={"openai_request_reference": value})
        )
        issues = validate_openai_provider_request_plan(
            _replace_request(openai, 0, request), context
        )
    else:
        message = _seal_message(
            openai.requests[0]
            .messages[0]
            .model_copy(update={"openai_message_reference": value})
        )
        issues = validate_openai_provider_request_plan(
            _replace_message(openai, 0, 0, message), context
        )
    assert issues


@pytest.mark.parametrize(
    "kind",
    ("identity-stale", "identity-forged", "fingerprint-stale", "fingerprint-forged"),
)
@pytest.mark.parametrize(
    "level", ("descriptor", "generic", "message", "request", "openai-plan")
)
def test_all_stale_and_forged_seals(level, kind):
    generic, context = _generic()
    openai = generic.openai_request_plan
    target = {
        "descriptor": generic.provider_descriptor,
        "generic": generic,
        "message": openai.requests[0].messages[0],
        "request": openai.requests[0],
        "openai-plan": openai,
    }[level]
    field = "identity" if kind.startswith("identity") else "fingerprint"
    value = (
        target.identity[:-1] + ("e" if target.identity.endswith("f") else "f")
        if field == "identity"
        else ("e" * 64 if target.fingerprint == "f" * 64 else "f" * 64)
    )
    changed = target.model_copy(update={field: value})
    if kind.endswith("stale"):
        semantic_field = next(
            name
            for name in target.__class__.model_fields
            if name
            not in {"identity", "fingerprint", "provider", "mapping_contract_version"}
        )
        changed = target.model_copy(
            update={
                semantic_field: _alternate(
                    semantic_field, getattr(target, semantic_field)
                )
            }
        )
        other = "fingerprint" if field == "identity" else "identity"
        derive = {
            (
                "descriptor",
                "identity",
            ): derive_provider_request_plan_descriptor_identity,
            (
                "descriptor",
                "fingerprint",
            ): derive_provider_request_plan_descriptor_fingerprint,
            ("generic", "identity"): derive_draft_provider_request_plan_identity,
            ("generic", "fingerprint"): derive_draft_provider_request_plan_fingerprint,
            ("message", "identity"): derive_openai_provider_message_identity,
            ("message", "fingerprint"): derive_openai_provider_message_fingerprint,
            ("request", "identity"): derive_openai_provider_request_identity,
            ("request", "fingerprint"): derive_openai_provider_request_fingerprint,
            ("openai-plan", "identity"): derive_openai_provider_request_plan_identity,
            (
                "openai-plan",
                "fingerprint",
            ): derive_openai_provider_request_plan_fingerprint,
        }[(level, other)]
        changed = changed.model_copy(update={other: derive(changed)})
    if level == "descriptor":
        submitted = _seal_generic(
            generic.model_copy(update={"provider_descriptor": changed})
        )
        issues = validate_draft_provider_request_plan(submitted, context)
    elif level == "generic":
        issues = validate_draft_provider_request_plan(changed, context)
    elif level == "message":
        issues = validate_openai_provider_request_plan(
            _replace_message(openai, 0, 0, changed), context
        )
    elif level == "request":
        issues = validate_openai_provider_request_plan(
            _replace_request(openai, 0, changed), context
        )
    else:
        issues = validate_openai_provider_request_plan(changed, context)
    assert issues


def test_duplicate_dimensions_are_rejected_before_lookup_overwrite():
    plan, context = _openai(False)
    duplicated = _seal_openai_plan(
        plan.model_copy(update={"requests": plan.requests + (plan.requests[0],)})
    )
    codes = {
        item.code for item in validate_openai_provider_request_plan(duplicated, context)
    }
    assert (
        len({code for code in codes if code.startswith("provider-mapping-duplicate-")})
        >= 5
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "plan-identity",
        "plan-fingerprint",
        "plan-reference",
        "request-identity",
        "request-fingerprint",
        "message-identity",
        "message-fingerprint",
        "missing-request",
    ),
)
def test_builder_rejects_malformed_phase_6_1_authority(mutation):
    generic, context = _generic(False)
    source = context.execution_plans[0]
    if mutation == "plan-identity":
        changed = source.model_copy(update={"identity": source.identity[:-1] + "e"})
    elif mutation == "plan-fingerprint":
        changed = source.model_copy(update={"fingerprint": "f" * 64})
    elif mutation == "plan-reference":
        changed = source.model_copy(
            update={"execution_plan_reference": "llm-execution-plan:foreign"}
        )
    elif mutation == "missing-request":
        changed = source.model_copy(
            update={"execution_requests": source.execution_requests[1:]}
        )
    else:
        request = source.execution_requests[0]
        if mutation.startswith("request"):
            field = mutation.removeprefix("request-")
            value = request.identity[:-1] + "e" if field == "identity" else "f" * 64
            request = request.model_copy(update={field: value})
        else:
            message = request.execution_messages[0]
            field = mutation.removeprefix("message-")
            value = message.identity[:-1] + "e" if field == "identity" else "f" * 64
            message = message.model_copy(update={field: value})
            request = request.model_copy(
                update={
                    "execution_messages": (message,) + request.execution_messages[1:]
                }
            )
        changed = source.model_copy(
            update={"execution_requests": (request,) + source.execution_requests[1:]}
        )
    malformed_context = context.model_copy(update={"execution_plans": (changed,)})
    with pytest.raises(DomainValidationError):
        build_openai_provider_request_plan(
            changed, generic.provider_descriptor, malformed_context
        )


def test_foreign_valid_request_and_message_are_rejected():
    plan, context = _openai(False)
    foreign, _ = _openai(True)
    changed = _seal_openai_plan(
        plan.model_copy(update={"requests": plan.requests + (foreign.requests[0],)})
    )
    assert "provider-mapping-extra-request" in {
        item.code for item in validate_openai_provider_request_plan(changed, context)
    }
    request = plan.requests[0]
    request = _seal_request(
        request.model_copy(
            update={"messages": request.messages + (foreign.requests[0].messages[0],)}
        )
    )
    changed = _replace_request(plan, 0, request)
    assert "provider-mapping-extra-message" in {
        item.code for item in validate_openai_provider_request_plan(changed, context)
    }


def test_complete_canonical_empty_adversarial_matrix():
    _, _, rendered, rendered_context = UPSTREAM["FREEZE"]["_empty_authority"]()
    execution_context = UPSTREAM["_context"](rendered, rendered_context)
    execution = UPSTREAM["build_draft_llm_execution_plan"](rendered, execution_context)
    descriptor = _descriptor()
    context = public_api.ProviderMappingValidationContext(
        execution_plans=(execution,),
        execution_validation_context=execution_context,
        provider_descriptors=(descriptor,),
    )
    plan = build_openai_provider_request_plan(execution, descriptor, context)
    assert plan.requests == ()
    assert validate_openai_provider_request_plan(plan, context) == ()
    payload = plan.model_dump(mode="python")
    payload["requests"] = []
    assert type(plan).model_validate(payload).requests == ()
    nonempty, _ = _openai()
    placeholder = _seal_openai_plan(
        plan.model_copy(update={"requests": (nonempty.requests[0],)})
    )
    assert "provider-mapping-extra-request" in {
        item.code
        for item in validate_openai_provider_request_plan(placeholder, context)
    }
    assert validate_openai_provider_request_plan(
        plan.model_copy(update={"identity": plan.identity[:-1] + "e"}), context
    )
    assert validate_openai_provider_request_plan(
        plan.model_copy(update={"fingerprint": "f" * 64}), context
    )
    with pytest.raises(ValidationError):
        type(plan).model_validate({**payload, "requests": None})


def test_fresh_snapshot_and_context_isolation():
    plan, context = _openai(False)
    requests = list(plan.requests)
    submitted = plan.model_construct(**{**plan.__dict__, "requests": requests})
    first = validate_openai_provider_request_plan(submitted, context)
    requests.append(requests[0])
    second = validate_openai_provider_request_plan(submitted, context)
    assert first == ()
    assert second
    other_plan, other_context = _openai()
    assert validate_openai_provider_request_plan(other_plan, other_context) == ()
    assert validate_openai_provider_request_plan(plan, context) == ()
    request = plan.requests[0]
    repeated = _seal_request(
        request.model_copy(
            update={"messages": request.messages + (request.messages[0],)}
        )
    )
    codes = {
        item.code
        for item in validate_openai_provider_request_plan(
            _replace_request(plan, 0, repeated), context
        )
    }
    assert (
        len({code for code in codes if code.startswith("provider-mapping-duplicate-")})
        >= 5
    )


class _Hostile:
    def __init__(self, error_type):
        self.error_type = error_type

    def model_dump(self, **_kwargs):
        raise self.error_type("secret traceback C:\\private 0x7ff")


@pytest.mark.parametrize(
    "error_type", (KeyError, LookupError, RuntimeError, ValueError, TypeError)
)
@pytest.mark.parametrize(
    "operation",
    (
        "build-generic-plan",
        "build-generic-descriptor",
        "build-generic-context",
        "build-openai-plan",
        "build-openai-descriptor",
        "build-openai-context",
        "validate-generic-plan",
        "validate-generic-context",
        "validate-openai-plan",
        "validate-openai-context",
    ),
)
def test_ordinary_reconstruction_failures_are_contained(error_type, operation):
    generic, context = _generic()
    openai = generic.openai_request_plan
    descriptor = generic.provider_descriptor
    hostile = _Hostile(error_type)
    if operation.startswith("build-"):
        args = [context.execution_plans[0], descriptor, context]
        args[
            {"plan": 0, "descriptor": 1, "context": 2}[operation.rsplit("-", 1)[-1]]
        ] = hostile
        builder = (
            build_draft_provider_request_plan
            if "generic" in operation
            else build_openai_provider_request_plan
        )
        with pytest.raises(DomainValidationError) as caught:
            builder(*args)
        issues = caught.value.issues
    else:
        validator = (
            validate_draft_provider_request_plan
            if "generic" in operation
            else validate_openai_provider_request_plan
        )
        issues = (
            validator(hostile, context)
            if operation.endswith("plan")
            else validator(generic if "generic" in operation else openai, hostile)
        )
    payload = json.dumps([asdict(item) for item in issues], default=str)
    assert issues and all(
        value not in payload for value in ("secret", "traceback", "0x7ff")
    )


@pytest.mark.parametrize("error_type", (KeyboardInterrupt, SystemExit, GeneratorExit))
@pytest.mark.parametrize(
    "operation",
    (
        "build-generic-plan",
        "build-generic-descriptor",
        "build-generic-context",
        "build-openai-plan",
        "build-openai-descriptor",
        "build-openai-context",
        "validate-generic-plan",
        "validate-generic-context",
        "validate-openai-plan",
        "validate-openai-context",
    ),
)
def test_process_control_propagates(error_type, operation):
    generic, context = _generic()
    openai = generic.openai_request_plan
    descriptor = generic.provider_descriptor
    hostile = _Hostile(error_type)
    with pytest.raises(error_type):
        if operation.startswith("build-"):
            args = [context.execution_plans[0], descriptor, context]
            args[
                {"plan": 0, "descriptor": 1, "context": 2}[operation.rsplit("-", 1)[-1]]
            ] = hostile
            (
                build_draft_provider_request_plan
                if "generic" in operation
                else build_openai_provider_request_plan
            )(*args)
        else:
            validator = (
                validate_draft_provider_request_plan
                if "generic" in operation
                else validate_openai_provider_request_plan
            )
            (
                validator(hostile, context)
                if operation.endswith("plan")
                else validator(generic if "generic" in operation else openai, hostile)
            )


def test_independent_process_complete_artifacts_and_diagnostics_are_equal():
    code = "import sys,runpy,json;sys.path.insert(0,'tests');n=runpy.run_path('tests/test_editorial_script_composer_provider_mapping.py');p,c=n['_generic']();print(json.dumps(p.model_dump(mode='json'),sort_keys=True,separators=(',',':')));p=p.model_copy(update={'fingerprint':'f'*64});from dataclasses import asdict;print(json.dumps([asdict(x) for x in n['validate_draft_provider_request_plan'](p,c)],sort_keys=True,separators=(',',':'),default=str))"
    assert subprocess.check_output(
        [sys.executable, "-c", code]
    ) == subprocess.check_output([sys.executable, "-c", code])


def test_public_api_internal_exclusions_dependency_and_execution_boundary():
    expected = {
        "ProviderRequestPlanDescriptor",
        "DraftProviderRequestPlan",
        "ProviderMappingValidationContext",
        "OpenAIProviderMessage",
        "OpenAIProviderRequest",
        "OpenAIProviderRequestPlan",
        "build_draft_provider_request_plan",
        "validate_draft_provider_request_plan",
        "build_openai_provider_request_plan",
        "validate_openai_provider_request_plan",
        "derive_provider_request_plan_descriptor_identity",
        "derive_draft_provider_request_plan_identity",
        "derive_openai_provider_message_identity",
        "derive_openai_provider_request_identity",
        "derive_openai_provider_request_plan_identity",
        "derive_provider_request_plan_descriptor_fingerprint",
        "derive_draft_provider_request_plan_fingerprint",
        "derive_openai_provider_message_fingerprint",
        "derive_openai_provider_request_fingerprint",
        "derive_openai_provider_request_plan_fingerprint",
    }
    assert expected <= set(dir(public_api))
    assert not {
        "_openai_role",
        "_project",
        "_duplicates",
        "_safe_reference",
        "_Reconstruction",
    } & set(dir(public_api))
    root = Path("src/pastila_scout/editor/script_composer")
    files = tuple(root.glob("*mapping*.py"))
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(
            name.split(".")[0] in {"openai", "httpx", "requests", "aiohttp", "socket"}
            for name in imports
        )
    for path in root.glob("*.py"):
        if (
            path.name == "__init__.py"
            or "mapping" in path.name
            or "result" in path.name
        ):
            continue
        assert "provider_mapping" not in path.read_text(encoding="utf-8")
