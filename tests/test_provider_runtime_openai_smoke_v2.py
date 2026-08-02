from __future__ import annotations

import ast
import copy
import gc
import pickle
import subprocess
import sys
from dataclasses import fields, is_dataclass
from functools import partial
from pathlib import Path
from types import CellType, FunctionType, MethodType, ModuleType
from typing import ClassVar

import pytest
from pydantic import ValidationError

import pastila_scout.provider_runtime_openai_smoke_v2 as public_api
from pastila_scout.provider_runtime_openai_smoke_v2 import (
    OpenAISmokeTestConfigurationError,
    OpenAISmokeTestConfigurationV2,
    OpenAISmokeTestConfirmationError,
    OpenAISmokeTestDependencyError,
    OpenAISmokeTestError,
    OpenAISmokeTestRunnerV2,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_runtime_openai_smoke_v2"


def _configuration(*, confirm_live: bool = True) -> OpenAISmokeTestConfigurationV2:
    return OpenAISmokeTestConfigurationV2(
        confirm_live=confirm_live,
        model="gpt-contract-model",
        timeout_seconds=10,
    )


def test_public_api_is_exact_and_private_contract_is_not_exported() -> None:
    assert public_api.__all__ == (
        "OpenAISmokeTestConfigurationError",
        "OpenAISmokeTestConfigurationV2",
        "OpenAISmokeTestConfirmationError",
        "OpenAISmokeTestDependencyError",
        "OpenAISmokeTestError",
        "OpenAISmokeTestRunnerV2",
    )
    assert (
        tuple(name for name in public_api.__all__ if hasattr(public_api, name))
        == public_api.__all__
    )
    assert not hasattr(public_api, "_OpenAISmokeTestRunnerContractV2")


def test_error_taxonomy_is_stable() -> None:
    assert issubclass(OpenAISmokeTestConfigurationError, OpenAISmokeTestError)
    assert issubclass(OpenAISmokeTestConfirmationError, OpenAISmokeTestError)
    assert issubclass(OpenAISmokeTestDependencyError, OpenAISmokeTestError)


def test_configuration_accepts_exact_minimal_policy() -> None:
    configuration = _configuration()

    assert configuration.confirm_live is True
    assert configuration.model == "gpt-contract-model"
    assert configuration.timeout_seconds == 10
    assert type(configuration.timeout_seconds) is int
    assert set(type(configuration).model_fields) == {
        "confirm_live",
        "model",
        "timeout_seconds",
    }


@pytest.mark.parametrize("value", (None, 0, 1, "true", type("B", (int,), {})(1)))
def test_configuration_requires_exact_boolean_confirmation(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAISmokeTestConfigurationV2(
            confirm_live=value,  # type: ignore[arg-type]
            model="gpt-contract-model",
            timeout_seconds=10,
        )


@pytest.mark.parametrize("value", (None, False, 1, "", " ", " model", "model "))
def test_configuration_rejects_invalid_model(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAISmokeTestConfigurationV2(
            confirm_live=True,
            model=value,  # type: ignore[arg-type]
            timeout_seconds=10,
        )


@pytest.mark.parametrize(
    "value",
    (
        None,
        False,
        True,
        0,
        -1,
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
        -float("inf"),
        "10",
    ),
)
def test_configuration_rejects_invalid_timeout(value: object) -> None:
    with pytest.raises(ValidationError):
        OpenAISmokeTestConfigurationV2(
            confirm_live=True,
            model="gpt-contract-model",
            timeout_seconds=value,  # type: ignore[arg-type]
        )


def test_configuration_forbids_extra_operational_fields() -> None:
    for field in ("credential", "prompt", "headers", "max_retries"):
        with pytest.raises(ValidationError):
            OpenAISmokeTestConfigurationV2.model_validate(
                {
                    "confirm_live": True,
                    "model": "gpt-contract-model",
                    "timeout_seconds": 10,
                    field: "forbidden",
                }
            )


def test_configuration_is_immutable_and_copy_safe() -> None:
    configuration = _configuration()

    with pytest.raises(ValidationError):
        configuration.model = "changed"  # type: ignore[misc]
    assert copy.copy(configuration) == configuration
    assert copy.deepcopy(configuration) == configuration
    assert copy.copy(configuration) is not configuration
    assert copy.deepcopy(configuration) is not configuration


def test_runner_wraps_invalid_and_copied_invalid_configuration() -> None:
    runner = OpenAISmokeTestRunnerV2()
    invalid = _configuration().model_copy(update={"timeout_seconds": 0})

    for value in (None, object(), invalid):
        with pytest.raises(OpenAISmokeTestConfigurationError) as raised:
            runner.run(value)
        assert raised.value.args == ("invalid OpenAI smoke-test configuration",)
        _assert_isolated(raised.value)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("confirm_live", 1),
        ("confirm_live", "true"),
        ("model", ""),
        ("model", " padded "),
        ("timeout_seconds", 0),
        ("timeout_seconds", -1),
        ("timeout_seconds", float("nan")),
        ("timeout_seconds", object()),
    ),
)
def test_runner_defensively_rejects_complete_copied_invalid_matrix(
    field: str,
    value: object,
) -> None:
    configuration = _configuration().model_copy(update={field: value})

    with pytest.raises(OpenAISmokeTestConfigurationError) as raised:
        OpenAISmokeTestRunnerV2().run(configuration)

    assert raised.value.args == ("invalid OpenAI smoke-test configuration",)
    _assert_isolated(raised.value)
    _assert_smoke_traceback_is_safe(raised.value, configuration)


def test_confirmation_is_required_before_non_operational_failure() -> None:
    with pytest.raises(OpenAISmokeTestConfirmationError) as raised:
        OpenAISmokeTestRunnerV2().run(_configuration(confirm_live=False))

    assert raised.value.args == (
        "explicit live OpenAI smoke-test confirmation is required",
    )
    _assert_isolated(raised.value)


def test_confirmation_reaches_only_deterministic_non_operational_failure() -> None:
    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        OpenAISmokeTestRunnerV2().run(_configuration(confirm_live=True))

    assert raised.value.args == ("OpenAI live smoke test is not operational",)
    _assert_isolated(raised.value)


@pytest.mark.parametrize("confirmed", (False, True))
def test_errors_are_isolated_from_nested_active_exceptions(confirmed: bool) -> None:
    outer = RuntimeError("caller outer")
    inner = RuntimeError("caller inner")
    try:
        raise outer
    except RuntimeError:
        try:
            raise inner
        except RuntimeError:
            with pytest.raises(OpenAISmokeTestError) as raised:
                OpenAISmokeTestRunnerV2().run(_configuration(confirm_live=confirmed))

    _assert_isolated(raised.value)
    assert raised.value.__context__ is not outer
    assert raised.value.__context__ is not inner


def test_runner_traceback_and_recursive_graph_retain_no_configuration() -> None:
    runner = OpenAISmokeTestRunnerV2()
    configuration = _configuration()
    with pytest.raises(OpenAISmokeTestDependencyError) as raised:
        runner.run(configuration)

    roots: list[object] = [raised.value]
    traceback = raised.value.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("runner.py"):
            roots.extend(traceback.tb_frame.f_locals.values())
        traceback = traceback.tb_next
    seen: set[int] = set()

    def visit(value: object) -> None:
        if id(value) in seen:
            return
        seen.add(id(value))
        assert value is not configuration
        assert value is not runner
        if isinstance(value, BaseException):
            visit(value.args)
            if value.__context__ is not None:
                visit(value.__context__)
            if value.__cause__ is not None:
                visit(value.__cause__)
        elif isinstance(value, dict):
            for key, item in value.items():
                visit(key)
                visit(item)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)

    for root in roots:
        visit(root)


@pytest.mark.parametrize(
    ("confirmed", "error_type"),
    (
        (False, OpenAISmokeTestConfirmationError),
        (True, OpenAISmokeTestDependencyError),
    ),
)
def test_confirmation_scalar_and_configuration_fields_leave_no_traceback_state(
    confirmed: bool,
    error_type: type[OpenAISmokeTestError],
) -> None:
    configuration = OpenAISmokeTestConfigurationV2(
        confirm_live=confirmed,
        model="SECRET_MODEL_MARKER_R2",
        timeout_seconds=987654321,
    )

    with pytest.raises(error_type) as raised:
        OpenAISmokeTestRunnerV2().run(configuration)

    _assert_smoke_traceback_is_safe(
        raised.value,
        configuration,
        "SECRET_MODEL_MARKER_R2",
        987654321,
    )
    for frame_name, local_values in _smoke_traceback_locals(raised.value):
        assert not {"confirmed", "confirm_live", "model", "timeout_seconds"} & set(
            local_values
        )
        if frame_name == "run":
            assert tuple(local_values) == ("outcome",)


def test_hostile_copied_fields_execute_no_hooks_or_representations() -> None:
    class Hostile:
        calls: ClassVar[dict[str, int]] = {
            "bool": 0,
            "eq": 0,
            "float": 0,
            "int": 0,
            "repr": 0,
            "str": 0,
            "lt": 0,
            "gt": 0,
        }

        def _called(self, name: str):
            type(self).calls[name] += 1
            raise AssertionError(f"{name} hook executed")

        def __bool__(self):
            return self._called("bool")

        def __eq__(self, other):
            del other
            return self._called("eq")

        def __float__(self):
            return self._called("float")

        def __int__(self):
            return self._called("int")

        def __repr__(self):
            return self._called("repr")

        def __str__(self):
            return self._called("str")

        def __lt__(self, other):
            del other
            return self._called("lt")

        def __gt__(self, other):
            del other
            return self._called("gt")

    for field in ("confirm_live", "model", "timeout_seconds"):
        hostile = Hostile()
        configuration = _configuration().model_copy(update={field: hostile})
        with pytest.raises(OpenAISmokeTestConfigurationError) as raised:
            OpenAISmokeTestRunnerV2().run(configuration)
        _assert_smoke_traceback_is_safe(raised.value, configuration, hostile)
    assert set(Hostile.calls.values()) == {0}


def test_runner_is_immutable_stateless_and_copy_safe() -> None:
    runner = OpenAISmokeTestRunnerV2()

    assert not hasattr(runner, "__dict__")
    assert copy.copy(runner) is runner
    assert copy.deepcopy(runner) is runner
    memo: dict[int, object] = {}
    assert copy.deepcopy(runner, memo) is runner
    assert memo[id(runner)] is runner
    assert copy.deepcopy((runner, {"runner": runner}))[0] is runner
    with pytest.raises(AttributeError, match="OpenAI smoke-test runner is immutable"):
        runner.state = "forbidden"  # type: ignore[attr-defined]
    with pytest.raises(AttributeError, match="OpenAI smoke-test runner is immutable"):
        del runner.state  # type: ignore[attr-defined]


def test_runner_representation_is_fixed_and_state_free() -> None:
    first = OpenAISmokeTestRunnerV2()
    second = OpenAISmokeTestRunnerV2()

    assert repr(first) == str(first) == "OpenAISmokeTestRunnerV2()"
    assert repr(second) == repr(first)
    assert "0x" not in repr(first)


def test_runner_rejects_every_pickle_protocol() -> None:
    runner = OpenAISmokeTestRunnerV2()

    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError) as raised:
            pickle.dumps(runner, protocol=protocol)
        assert raised.value.args == ("OpenAI smoke-test runners cannot be serialized",)
        _assert_isolated(raised.value)


def test_repeated_calls_are_fresh_deterministic_and_stateless() -> None:
    runner = OpenAISmokeTestRunnerV2()
    cases = (
        (_configuration(confirm_live=False), OpenAISmokeTestConfirmationError),
        (_configuration(confirm_live=True), OpenAISmokeTestDependencyError),
        (
            _configuration().model_copy(update={"model": ""}),
            OpenAISmokeTestConfigurationError,
        ),
        (_configuration(confirm_live=False), OpenAISmokeTestConfirmationError),
        (_configuration(confirm_live=True), OpenAISmokeTestDependencyError),
    )
    errors: list[OpenAISmokeTestError] = []

    for configuration, error_type in cases:
        with pytest.raises(error_type) as raised:
            runner.run(configuration)
        errors.append(raised.value)
        _assert_smoke_traceback_is_safe(raised.value, configuration)

    assert len({id(error) for error in errors}) == len(errors)
    assert not hasattr(runner, "__dict__")
    assert repr(runner) == "OpenAISmokeTestRunnerV2()"


@pytest.mark.parametrize("path", ("invalid", "unconfirmed", "confirmed"))
def test_all_error_paths_isolate_hostile_nested_caller_context(path: str) -> None:
    class HostileCallerError(RuntimeError):
        repr_calls = 0
        str_calls = 0

        def __repr__(self):
            type(self).repr_calls += 1
            raise AssertionError("caller repr executed")

        def __str__(self):
            type(self).str_calls += 1
            raise AssertionError("caller str executed")

    if path == "invalid":
        configuration = _configuration().model_copy(update={"model": ""})
    else:
        configuration = _configuration(confirm_live=path == "confirmed")
    outer = HostileCallerError("outer")
    inner = HostileCallerError("inner")
    try:
        raise outer from RuntimeError("nested cause")
    except HostileCallerError:
        try:
            raise inner
        except HostileCallerError:
            with pytest.raises(OpenAISmokeTestError) as raised:
                OpenAISmokeTestRunnerV2().run(configuration)

    _assert_isolated(raised.value)
    _assert_smoke_traceback_is_safe(
        raised.value, configuration, outer, inner, "outer", "inner"
    )
    assert HostileCallerError.repr_calls == HostileCallerError.str_calls == 0


def test_mixed_failures_leave_no_smoke_module_global_history() -> None:
    import pastila_scout.provider_runtime_openai_smoke_v2.models as models_module
    import pastila_scout.provider_runtime_openai_smoke_v2.runner as runner_module

    marker = "GLOBAL_MODEL_MARKER_R2"
    runner = OpenAISmokeTestRunnerV2()
    configurations = (
        OpenAISmokeTestConfigurationV2(
            confirm_live=False, model=marker, timeout_seconds=123456789
        ),
        OpenAISmokeTestConfigurationV2(
            confirm_live=True, model=marker, timeout_seconds=123456789
        ),
        _configuration().model_copy(update={"model": ""}),
    )
    for configuration in configurations:
        with pytest.raises(OpenAISmokeTestError):
            runner.run(configuration)
    del configuration
    del configurations
    del runner
    gc.collect()

    for module in (models_module, runner_module):
        for value in vars(module).values():
            assert not isinstance(value, OpenAISmokeTestRunnerV2)
            assert not isinstance(value, OpenAISmokeTestConfigurationV2)
            if type(value) is str:
                assert value != marker


def test_package_contains_no_operational_capabilities_or_reverse_dependencies() -> None:
    forbidden_imports = {
        "dotenv",
        "httpx",
        "openai",
        "os",
        "requests",
        "socket",
        "urllib",
    }
    forbidden_calls = {
        "complete",
        "compose",
        "create",
        "create_client",
        "get_api_key",
        "request",
    }
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not imports & forbidden_imports
        assert not calls & forbidden_calls

    for package in (
        "provider_v2",
        "provider_execution_v2",
        "provider_execution_openai_v2",
        "provider_execution_openai_sdk_v2",
        "provider_runtime_openai_v2",
    ):
        for path in (ROOT / "src" / "pastila_scout" / package).glob("*.py"):
            assert "provider_runtime_openai_smoke_v2" not in path.read_text(
                encoding="utf-8"
            )


def test_real_cli_has_no_smoke_import_registration_or_dispatch() -> None:
    source = (ROOT / "src" / "pastila_scout" / "cli.py").read_text(encoding="utf-8")

    assert "provider_runtime_openai_smoke_v2" not in source
    assert "confirm-live" not in source
    assert "openai smoke" not in source
    assert "openai_smoke" not in source


def test_documentation_records_canonical_and_expanded_selector_accounting() -> None:
    document = (
        ROOT / "docs" / "editorial-script-composer" / "Phase7_5_OpenAISmokeTest.md"
    ).read_text(encoding="utf-8")

    assert (
        'pytest -k "editorial_script_composer or provider_execution or '
        'provider_runtime_openai_v2"' in document
    )
    assert (
        'pytest -k "editorial_script_composer or provider_execution or '
        'provider_runtime_openai_v2 or provider_runtime_openai_smoke_v2"' in document
    )
    assert "excludes the focused smoke tests" in document


def test_clean_process_import_is_non_operational() -> None:
    script = """
import contextlib
import io
import os
import sys
import warnings

credential_reads = []
original_getenv = os.getenv
def guarded_getenv(name, *args, **kwargs):
    if name == "OPENAI_API_KEY":
        credential_reads.append(name)
        raise AssertionError("credential access")
    return original_getenv(name, *args, **kwargs)
os.getenv = guarded_getenv
stdout = io.StringIO()
stderr = io.StringIO()
before = set(sys.modules)
with warnings.catch_warnings(record=True) as caught:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        import pastila_scout.provider_runtime_openai_smoke_v2 as api
loaded = set(sys.modules) - before
assert credential_reads == []
assert stdout.getvalue() == ""
assert stderr.getvalue() == ""
assert caught == []
assert "openai" not in loaded
assert "pastila_scout.provider_runtime_openai_v2" not in loaded
assert len(api.__all__) == 6
"""
    subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=True)


def _assert_isolated(error: BaseException) -> None:
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True


def _smoke_traceback_locals(
    error: BaseException,
) -> list[tuple[str, dict[str, object]]]:
    frames: list[tuple[str, dict[str, object]]] = []
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("runner.py"):
            frames.append(
                (traceback.tb_frame.f_code.co_name, dict(traceback.tb_frame.f_locals))
            )
        traceback = traceback.tb_next
    return frames


def _assert_smoke_traceback_is_safe(error: BaseException, *forbidden: object) -> None:
    roots: list[object] = [error]
    for _, local_values in _smoke_traceback_locals(error):
        roots.append(local_values)
    seen: set[int] = set()

    def visit(value: object) -> None:
        if id(value) in seen:
            return
        seen.add(id(value))
        assert all(value is not item for item in forbidden)
        if type(value) is str:
            assert all(type(item) is not str or value != item for item in forbidden)
        if type(value) is int and type(value) is not bool:
            assert all(type(item) is not int or value != item for item in forbidden)
        if isinstance(value, BaseException):
            visit(value.args)
            visit(value.__dict__)
            if value.__context__ is not None:
                visit(value.__context__)
            if value.__cause__ is not None:
                visit(value.__cause__)
            traceback = value.__traceback__
            while traceback is not None:
                if traceback.tb_frame.f_code.co_filename.endswith("runner.py"):
                    visit(dict(traceback.tb_frame.f_locals))
                traceback = traceback.tb_next
        elif isinstance(value, dict):
            for key, item in value.items():
                visit(key)
                visit(item)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)
        elif isinstance(value, partial):
            visit(value.func)
            visit(value.args)
            visit(value.keywords)
        elif isinstance(value, MethodType):
            visit(value.__self__)
            visit(value.__func__)
        elif isinstance(value, CellType):
            visit(value.cell_contents)
        elif isinstance(value, FunctionType):
            if value.__closure__ is not None:
                visit(value.__closure__)
        elif is_dataclass(value) and not isinstance(value, type):
            for item in fields(value):
                visit(getattr(value, item.name))
        elif not isinstance(value, (type, ModuleType)):
            for slot in getattr(type(value), "__slots__", ()):
                if type(slot) is str and hasattr(value, slot):
                    visit(getattr(value, slot))

    for root in roots:
        visit(root)
