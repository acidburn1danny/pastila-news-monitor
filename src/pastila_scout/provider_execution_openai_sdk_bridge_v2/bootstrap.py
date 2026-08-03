"""Explicit atomic SDK authority bootstrap for the passive bridge package.

Importing this private module is an operational dependency-loading decision. It
may transitively import the official ``openai`` package, but it never retrieves
credentials, constructs a client, performs networking, or owns lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from inspect import signature
from types import FunctionType, MappingProxyType, ModuleType

from .client import OpenAIExecutionSDKBridgeClientV2, _raise_dependency_error

_SDK_PACKAGE = "pastila_scout.provider_execution_openai_sdk_v2"
_SDK_CLIENT_MODULE = f"{_SDK_PACKAGE}.client"
_SDK_MAPPING_MODULE = f"{_SDK_PACKAGE}.mapping"
_SDK_MODELS_MODULE = f"{_SDK_PACKAGE}.models"


@dataclass(frozen=True, slots=True)
class _AuthorityGeneration:
    client_type: type[object]
    complete_function: FunctionType
    mapper_function: FunctionType
    request_type: type[object]


_AUTHORITY_GENERATION: _AuthorityGeneration | None = None


def _bootstrap_bridge(sdk_client: object) -> OpenAIExecutionSDKBridgeClientV2:
    """Atomically validate current SDK authority and construct one bridge."""

    outcome = _bootstrap_isolated(sdk_client)
    del sdk_client
    if outcome is None:
        _raise_dependency_error()
    return outcome


def _bootstrap_isolated(
    sdk_client: object,
) -> OpenAIExecutionSDKBridgeClientV2 | None:
    global _AUTHORITY_GENERATION
    try:
        candidate = _resolve_authority_generation()
        if not _sdk_authority_is_valid(sdk_client, candidate):
            del candidate
            del sdk_client
            return None
        generation = _AUTHORITY_GENERATION
        if generation is not None and not _generation_is_identical(
            candidate, generation
        ):
            del generation
            del candidate
            del sdk_client
            return None
        bridge = object.__new__(OpenAIExecutionSDKBridgeClientV2)
        object.__setattr__(bridge, "_complete_function", candidate.complete_function)
        object.__setattr__(bridge, "_mapper_function", candidate.mapper_function)
        object.__setattr__(bridge, "_sdk_client", sdk_client)
        object.__setattr__(bridge, "_sdk_request_type", candidate.request_type)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        del sdk_client
        raise
    except Exception:  # noqa: BLE001 - expose only the fixed dependency error
        del sdk_client
        return None
    if _AUTHORITY_GENERATION is None:
        _AUTHORITY_GENERATION = candidate
    del candidate
    del sdk_client
    return bridge


def _generation_is_identical(
    candidate: _AuthorityGeneration, trusted: _AuthorityGeneration
) -> bool:
    return (
        candidate.client_type is trusted.client_type
        and candidate.complete_function is trusted.complete_function
        and candidate.mapper_function is trusted.mapper_function
        and candidate.request_type is trusted.request_type
    )


def _resolve_authority_generation() -> _AuthorityGeneration:
    package = import_module(_SDK_PACKAGE)
    client_module = import_module(_SDK_CLIENT_MODULE)
    mapping_module = import_module(_SDK_MAPPING_MODULE)
    models_module = import_module(_SDK_MODELS_MODULE)
    if any(
        type(module) is not ModuleType
        for module in (package, client_module, mapping_module, models_module)
    ):
        raise TypeError
    client_type = vars(package).get("OpenAISDKClientV2")
    source_client_type = vars(client_module).get("OpenAISDKClientV2")
    mapper = vars(package).get("build_openai_sdk_request")
    source_mapper = vars(mapping_module).get("build_openai_sdk_request")
    request_type = vars(package).get("OpenAISDKRequestV2")
    source_request_type = vars(models_module).get("OpenAISDKRequestV2")
    if client_type is not source_client_type:
        raise TypeError
    if mapper is not source_mapper or type(mapper) is not FunctionType:
        raise TypeError
    if request_type is not source_request_type or not isinstance(request_type, type):
        raise TypeError
    namespace = type.__getattribute__(client_type, "__dict__")
    if type(namespace) is not MappingProxyType:
        raise TypeError
    complete = namespace.get("complete")
    if type(complete) is not FunctionType:
        raise TypeError
    return _AuthorityGeneration(client_type, complete, mapper, request_type)


def _sdk_authority_is_valid(value: object, generation: _AuthorityGeneration) -> bool:
    client_type = generation.client_type
    function = generation.complete_function
    if type(value) is not client_type:
        return False
    try:
        hierarchy = type.__getattribute__(client_type, "__mro__")
        namespaces = tuple(
            type.__getattribute__(owner, "__dict__") for owner in hierarchy
        )
        if any(type(namespace) is not MappingProxyType for namespace in namespaces):
            return False
        if any(
            "__getattr__" in namespace
            or (
                "__getattribute__" in namespace
                and namespace["__getattribute__"] is not object.__getattribute__
            )
            for namespace in namespaces
        ):
            return False
        current = type.__getattribute__(client_type, "__dict__").get("complete")
        if type(current) is not FunctionType or current is not function:
            return False
        clone = FunctionType(
            function.__code__,
            function.__globals__,
            function.__name__,
            function.__defaults__,
            function.__closure__,
        )
        clone.__kwdefaults__ = function.__kwdefaults__
        signature(clone, follow_wrapped=False).bind(value, object())
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    return True


__all__: tuple[str, ...] = ()
