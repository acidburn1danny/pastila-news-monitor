"""Authoritative immutable provider registry."""

import ast
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from inspect import Parameter, Signature, getattr_static, isfunction, signature
from types import FunctionType, GenericAlias, MappingProxyType, UnionType
from typing import Any

from .authority import validate_provider_descriptor
from .errors import (
    DuplicateProviderRegistrationError,
    InvalidProviderAdapterError,
    InvalidProviderDescriptorError,
    InvalidProviderIdentifierError,
    UnknownProviderError,
)
from .interface import ProviderAdapter
from .models import (
    PROVIDER_IDENTIFIER_PATTERN,
    ProviderDescriptorV2,
    ProviderRequestEnvelopeV2,
    ProviderRequestIntentV2,
    ProviderResultEnvelopeV2,
    ProviderResultProjectionV2,
    ProviderV2ValidationIssue,
)

_TRUSTED_ANNOTATION_SYMBOLS = MappingProxyType(
    {
        "Any": Any,
        "None": type(None),
        "ProviderDescriptorV2": ProviderDescriptorV2,
        "ProviderRequestEnvelopeV2": ProviderRequestEnvelopeV2,
        "ProviderRequestIntentV2": ProviderRequestIntentV2,
        "ProviderResultEnvelopeV2": ProviderResultEnvelopeV2,
        "ProviderResultProjectionV2": ProviderResultProjectionV2,
        "ProviderV2ValidationIssue": ProviderV2ValidationIssue,
        "bool": bool,
        "bytes": bytes,
        "dict": dict,
        "float": float,
        "frozenset": frozenset,
        "int": int,
        "list": list,
        "object": object,
        "set": set,
        "str": str,
        "tuple": tuple,
        "type": type,
    }
)
_TRUSTED_QUALIFIED_ANNOTATIONS = MappingProxyType({"typing.Any": Any})
_SAFE_SUBSCRIPT_BASES = (dict, frozenset, list, set, tuple, type)
_TRUSTED_RESOLVED_ANNOTATIONS = tuple(
    dict.fromkeys(_TRUSTED_ANNOTATION_SYMBOLS.values())
)

_LIFECYCLE_METHODS = (
    "construct_request",
    "validate_request",
    "execute",
    "extract_response",
    "project_result",
    "validate_result",
)
_LIFECYCLE_ANNOTATIONS = MappingProxyType(
    {
        "construct_request": MappingProxyType(
            {
                "intent": ProviderRequestIntentV2,
                "return": ProviderRequestEnvelopeV2,
            }
        ),
        "validate_request": MappingProxyType(
            {
                "request": ProviderRequestEnvelopeV2,
                "intent": ProviderRequestIntentV2,
                "return": tuple[ProviderV2ValidationIssue, ...],
            }
        ),
        "execute": MappingProxyType(
            {
                "request": ProviderRequestEnvelopeV2,
                "return": ProviderResultProjectionV2,
            }
        ),
        "extract_response": MappingProxyType(
            {
                "execution_result": ProviderResultProjectionV2,
                "return": ProviderResultProjectionV2,
            }
        ),
        "project_result": MappingProxyType(
            {
                "request": ProviderRequestEnvelopeV2,
                "intent": ProviderRequestIntentV2,
                "projection": ProviderResultProjectionV2,
                "return": ProviderResultEnvelopeV2,
            }
        ),
        "validate_result": MappingProxyType(
            {
                "result": ProviderResultEnvelopeV2,
                "request": ProviderRequestEnvelopeV2,
                "intent": ProviderRequestIntentV2,
                "projection": ProviderResultProjectionV2,
                "return": tuple[ProviderV2ValidationIssue, ...],
            }
        ),
    }
)


@dataclass(frozen=True, slots=True, init=False)
class ProviderRegistry:
    _adapters: Mapping[str, ProviderAdapter]

    def __init__(self, adapters: Iterable[ProviderAdapter]) -> None:
        registered: dict[str, ProviderAdapter] = {}
        for adapter in tuple(adapters):
            if _has_custom_getattribute(adapter):
                raise InvalidProviderAdapterError(
                    "incompatible adapter lifecycle: dynamic attribute interception"
                )
            for method_name in _LIFECYCLE_METHODS:
                _validate_lifecycle_method(adapter, method_name)
            descriptor = _static_metadata(adapter, "descriptor")
            provider_value = _static_metadata(adapter, "provider_id")
            adapter_identity = _static_metadata(adapter, "adapter_identity")
            if not isinstance(descriptor, ProviderDescriptorV2):
                raise InvalidProviderDescriptorError("invalid provider descriptor type")
            provider_id = self.validate_provider_identifier(provider_value)
            if descriptor.provider_id != provider_id:
                raise InvalidProviderAdapterError("adapter provider ownership mismatch")
            if descriptor.adapter_identity != adapter_identity:
                raise InvalidProviderAdapterError("adapter identity ownership mismatch")
            if validate_provider_descriptor(descriptor):
                raise InvalidProviderDescriptorError(
                    "invalid provider descriptor authority"
                )
            if provider_id in registered:
                raise DuplicateProviderRegistrationError(
                    f"duplicate provider registration: {provider_id}"
                )
            registered[provider_id] = adapter
        object.__setattr__(
            self, "_adapters", MappingProxyType(dict(sorted(registered.items())))
        )

    @staticmethod
    def validate_provider_identifier(provider_id: str) -> str:
        if not isinstance(provider_id, str) or not re.fullmatch(
            PROVIDER_IDENTIFIER_PATTERN, provider_id
        ):
            raise InvalidProviderIdentifierError("invalid provider identifier")
        return provider_id

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(self._adapters)

    def resolve(self, provider_id: str) -> ProviderAdapter:
        identifier = self.validate_provider_identifier(provider_id)
        try:
            return self._adapters[identifier]
        except KeyError:
            raise UnknownProviderError(f"unknown provider: {identifier}") from None


def _validate_lifecycle_method(adapter: ProviderAdapter, method_name: str) -> None:
    """Reject callables that cannot substitute for the protocol lifecycle method."""

    if _has_instance_member(adapter, method_name):
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: "
            "non-method lifecycle member"
        )
    try:
        raw = getattr_static(adapter, method_name)
    except AttributeError as error:
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: missing lifecycle member"
        ) from error
    implementation, drop_receiver = _method_implementation(raw, method_name)
    if _is_abstract_lifecycle(raw, implementation):
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: abstract lifecycle method"
        )
    authority = getattr(ProviderAdapter, method_name)
    try:
        expected = _without_self(_actual_function_signature(authority))
        actual = _actual_function_signature(implementation)
    except (TypeError, ValueError) as error:
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: unavailable signature"
        ) from error
    if drop_receiver:
        actual = _without_receiver(actual)
    positional = tuple(object() for _ in expected.parameters)
    try:
        actual.bind(*positional)
    except TypeError as error:
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: callable signature"
        ) from error
    _validate_annotations(method_name, implementation, expected, actual)


def _method_implementation(raw, method_name: str):
    if isfunction(raw):
        return raw, True
    if isinstance(raw, staticmethod) and isfunction(raw.__func__):
        return raw.__func__, False
    if isinstance(raw, classmethod) and isfunction(raw.__func__):
        return raw.__func__, True
    raise InvalidProviderAdapterError(
        f"incompatible lifecycle method {method_name}: non-method lifecycle member"
    )


def _actual_function_signature(implementation: FunctionType) -> Signature:
    clone = FunctionType(
        implementation.__code__,
        implementation.__globals__,
        implementation.__name__,
        implementation.__defaults__,
        implementation.__closure__,
    )
    clone.__kwdefaults__ = implementation.__kwdefaults__
    return signature(clone, follow_wrapped=False)


def _is_abstract_lifecycle(raw, implementation: FunctionType) -> bool:
    function_marker = getattr_static(implementation, "__isabstractmethod__", False)
    if function_marker is True:
        return True
    if type(raw) in (staticmethod, classmethod):
        return raw.__isabstractmethod__ is True
    return False


def _has_custom_getattribute(adapter: ProviderAdapter) -> bool:
    implementation = getattr_static(type(adapter), "__getattribute__")
    return implementation is not object.__getattribute__


def _has_instance_member(adapter: ProviderAdapter, name: str) -> bool:
    try:
        namespace = object.__getattribute__(adapter, "__dict__")
    except AttributeError:
        return False
    return name in namespace


def _static_metadata(adapter: ProviderAdapter, name: str):
    try:
        return getattr_static(adapter, name)
    except AttributeError as error:
        raise InvalidProviderAdapterError(
            f"invalid adapter metadata: missing {name}"
        ) from error


def _without_self(value: Signature) -> Signature:
    parameters = tuple(value.parameters.values())
    if parameters and parameters[0].name == "self":
        parameters = parameters[1:]
    return value.replace(parameters=parameters)


def _without_receiver(value: Signature) -> Signature:
    parameters = tuple(value.parameters.values())
    if parameters:
        parameters = parameters[1:]
    return value.replace(parameters=parameters)


def _validate_annotations(
    method_name: str,
    implementation,
    expected_signature: Signature,
    actual_signature: Signature,
) -> None:
    try:
        expected_hints = _LIFECYCLE_ANNOTATIONS[method_name]
        actual_hints = _static_type_hints(implementation)
    except _DeferredAnnotationError as error:
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: "
            "deferred annotations require execution"
        ) from error
    except _UnsafeAnnotationError as error:
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: "
            "unsafe annotation expression"
        ) from error
    except _UnresolvedAnnotationError as error:
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: unresolved annotation"
        ) from error
    expected_parameters = tuple(expected_signature.parameters.values())
    actual_parameters = tuple(actual_signature.parameters.values())
    for index, expected_parameter in enumerate(expected_parameters):
        actual_parameter = _positional_parameter(actual_parameters, index)
        if actual_parameter is None:
            continue
        expected = expected_hints.get(expected_parameter.name, Parameter.empty)
        actual = actual_hints.get(actual_parameter.name, Parameter.empty)
        if not _parameter_annotation_compatible(expected, actual):
            raise InvalidProviderAdapterError(
                f"incompatible lifecycle method {method_name}: "
                f"parameter {index} annotation"
            )
    expected_return = expected_hints.get("return", Signature.empty)
    actual_return = actual_hints.get("return", Signature.empty)
    if not _return_annotation_compatible(expected_return, actual_return):
        raise InvalidProviderAdapterError(
            f"incompatible lifecycle method {method_name}: return annotation"
        )


def _positional_parameter(
    parameters: tuple[Parameter, ...], index: int
) -> Parameter | None:
    positional = tuple(
        item
        for item in parameters
        if item.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
    )
    if index < len(positional):
        return positional[index]
    return None


def _parameter_annotation_compatible(expected, actual) -> bool:
    if actual is Parameter.empty or actual is Any or actual is object:
        return True
    if expected == actual:
        return True
    try:
        return (
            isinstance(expected, type)
            and isinstance(actual, type)
            and issubclass(expected, actual)
        )
    except TypeError:
        return False


def _return_annotation_compatible(expected, actual) -> bool:
    if actual is Signature.empty or actual is Any:
        return True
    if expected == actual:
        return True
    try:
        return (
            isinstance(expected, type)
            and isinstance(actual, type)
            and issubclass(actual, expected)
        )
    except TypeError:
        return False


class _UnsafeAnnotationError(ValueError):
    """An annotation contains executable or unsupported syntax."""


class _UnresolvedAnnotationError(ValueError):
    """An annotation names a symbol outside the trusted contract namespace."""


class _DeferredAnnotationError(ValueError):
    """A lifecycle annotation mapping would require executing bytecode."""


def _static_type_hints(implementation: FunctionType) -> dict[str, object]:
    annotator = object.__getattribute__(implementation, "__annotate__")
    if annotator is not None:
        raise _DeferredAnnotationError
    annotations = object.__getattribute__(implementation, "__annotations__")
    if type(annotations) is not dict:
        raise _UnsafeAnnotationError
    copied = dict(annotations)
    if not all(type(name) is str for name in copied):
        raise _UnsafeAnnotationError
    return {
        name: _resolve_safe_annotation(annotation)
        for name, annotation in copied.items()
    }


def _resolve_safe_annotation(annotation, *, depth: int = 0):
    if annotation is None:
        return type(None)
    if type(annotation) is not str:
        return _normalize_resolved_annotation(annotation)
    if depth > 2:
        raise _UnsafeAnnotationError
    try:
        expression = ast.parse(annotation, mode="eval").body
    except (SyntaxError, ValueError) as error:
        raise _UnsafeAnnotationError from error
    return _resolve_annotation_node(expression, depth=depth)


def _normalize_resolved_annotation(annotation):
    if any(annotation is trusted for trusted in _TRUSTED_RESOLVED_ANNOTATIONS):
        return annotation
    if type(annotation) is GenericAlias:
        origin = annotation.__origin__
        arguments = annotation.__args__
        if not any(origin is base for base in _SAFE_SUBSCRIPT_BASES):
            raise _UnsafeAnnotationError
        for argument in arguments:
            if argument is not Ellipsis:
                _normalize_resolved_annotation(argument)
        return annotation
    if type(annotation) is UnionType:
        for argument in annotation.__args__:
            _normalize_resolved_annotation(argument)
        return annotation
    raise _UnsafeAnnotationError


def _resolve_annotation_node(node: ast.expr, *, depth: int):
    if isinstance(node, ast.Name):
        try:
            return _TRUSTED_ANNOTATION_SYMBOLS[node.id]
        except KeyError as error:
            raise _UnresolvedAnnotationError from error
    if isinstance(node, ast.Constant):
        if node.value is None:
            return type(None)
        if isinstance(node.value, str):
            return _resolve_safe_annotation(node.value, depth=depth + 1)
        if node.value is Ellipsis:
            return Ellipsis
        raise _UnsafeAnnotationError
    if isinstance(node, ast.Attribute):
        qualified = _qualified_annotation_name(node)
        try:
            return _TRUSTED_QUALIFIED_ANNOTATIONS[qualified]
        except KeyError as error:
            raise _UnresolvedAnnotationError from error
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _resolve_annotation_node(node.left, depth=depth)
        right = _resolve_annotation_node(node.right, depth=depth)
        try:
            return left | right
        except TypeError as error:
            raise _UnsafeAnnotationError from error
    if isinstance(node, ast.Subscript):
        base = _resolve_annotation_node(node.value, depth=depth)
        if not any(base is trusted for trusted in _SAFE_SUBSCRIPT_BASES):
            raise _UnsafeAnnotationError
        if isinstance(node.slice, ast.Tuple):
            arguments = tuple(
                _resolve_annotation_node(item, depth=depth) for item in node.slice.elts
            )
        else:
            arguments = _resolve_annotation_node(node.slice, depth=depth)
        try:
            return base[arguments]
        except TypeError as error:
            raise _UnsafeAnnotationError from error
    raise _UnsafeAnnotationError


def _qualified_annotation_name(node: ast.Attribute) -> str:
    parts = [node.attr]
    value = node.value
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if not isinstance(value, ast.Name):
        raise _UnsafeAnnotationError
    parts.append(value.id)
    return ".".join(reversed(parts))


__all__ = ("ProviderRegistry",)
