"""Deterministic identities and fingerprints for V2 provider authority."""

import re
from typing import Any

from .canonical import semantic_sha256
from .models import (
    ProviderDescriptorV2,
    ProviderRequestEnvelopeV2,
    ProviderRequestMessageV2,
    ProviderRequestUnitV2,
    ProviderResultEnvelopeV2,
    ProviderResultUnitV2,
)


def _identity(kind: str, payload: Any) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", kind):
        raise ValueError("identity kind must be canonical")
    return f"scout:{kind}:{semantic_sha256(payload)}"


def _payload(value, *, identity: bool) -> dict:
    excluded = {"fingerprint"}
    if identity:
        excluded.add("identity")
    return value.model_dump(mode="python", exclude=excluded, warnings=False)


def descriptor_identity(value: ProviderDescriptorV2) -> str:
    return _identity("provider-descriptor-v2", _payload(value, identity=True))


def descriptor_fingerprint(value: ProviderDescriptorV2) -> str:
    return semantic_sha256(_payload(value, identity=False))


def request_message_identity(value: ProviderRequestMessageV2) -> str:
    return _identity("provider-request-message-v2", _payload(value, identity=True))


def request_message_fingerprint(value: ProviderRequestMessageV2) -> str:
    return semantic_sha256(_payload(value, identity=False))


def request_unit_identity(value: ProviderRequestUnitV2) -> str:
    return _identity("provider-request-unit-v2", _payload(value, identity=True))


def request_unit_fingerprint(value: ProviderRequestUnitV2) -> str:
    return semantic_sha256(_payload(value, identity=False))


def request_envelope_identity(value: ProviderRequestEnvelopeV2) -> str:
    return _identity("provider-request-envelope-v2", _payload(value, identity=True))


def request_envelope_fingerprint(value: ProviderRequestEnvelopeV2) -> str:
    return semantic_sha256(_payload(value, identity=False))


def result_unit_identity(value: ProviderResultUnitV2) -> str:
    return _identity("provider-result-unit-v2", _payload(value, identity=True))


def result_unit_fingerprint(value: ProviderResultUnitV2) -> str:
    return semantic_sha256(_payload(value, identity=False))


def result_envelope_identity(value: ProviderResultEnvelopeV2) -> str:
    return _identity("provider-result-envelope-v2", _payload(value, identity=True))


def result_envelope_fingerprint(value: ProviderResultEnvelopeV2) -> str:
    return semantic_sha256(_payload(value, identity=False))


__all__ = (
    "descriptor_fingerprint",
    "descriptor_identity",
    "request_envelope_fingerprint",
    "request_envelope_identity",
    "request_message_fingerprint",
    "request_message_identity",
    "request_unit_fingerprint",
    "request_unit_identity",
    "result_envelope_fingerprint",
    "result_envelope_identity",
    "result_unit_fingerprint",
    "result_unit_identity",
)
