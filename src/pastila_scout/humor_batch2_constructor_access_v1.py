"""Pathless G02B constructor packet access for Batch 2 DEVELOPMENT work.

This module prepares and exposes packet bytes only. It has no construction or
process-launch edge and intentionally offers no filesystem or enumeration API.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Final

_MINT: Final[object] = object()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(_canonical({"namespace": namespace, "value": value})).hexdigest()


@dataclass(frozen=True, slots=True, init=False)
class PreparedDevelopmentConstructorAccessV1:
    packet_bytes: bytes
    packet_identity: str
    release_identity: str
    _mint: object

    def __init__(self, *, packet_bytes: bytes, packet_identity: str,
                 release_identity: str, _mint: object) -> None:
        if _mint is not _MINT:
            raise TypeError("prepared access must be minted by the canonical factory")
        object.__setattr__(self, "packet_bytes", packet_bytes)
        object.__setattr__(self, "packet_identity", packet_identity)
        object.__setattr__(self, "release_identity", release_identity)
        object.__setattr__(self, "_mint", _mint)


def prepare_development_constructor_access_v1(*, release_bytes: bytes) -> PreparedDevelopmentConstructorAccessV1:
    release = json.loads(release_bytes)
    if set(release) != {
        "schema_name", "schema_version", "release_core", "release_identity",
        "constructor_packet", "constructor_visible_file_set", "transport_policy",
    }:
        raise ValueError("release field set")
    if release["schema_name"] != "batch2-development-pilot01-constructor-access-release-v1":
        raise ValueError("release schema")
    if release["release_identity"] != _seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_ACCESS_RELEASE_V1",
                                            release["release_core"]):
        raise ValueError("release seal")
    if release["constructor_visible_file_set"] != ["CONSTRUCTOR_PACKET"]:
        raise ValueError("visible file set")
    policy = release["transport_policy"]
    if not (policy["repository_access"] is False and policy["filesystem_path_access"] is False
            and policy["environment_inheritance"] is False and policy["command_line_payload"] is False
            and policy["metadata_enumeration"] is False and policy["logs_contain_packet_or_mapping"] is False):
        raise ValueError("transport policy")
    packet = release["constructor_packet"]
    packet_core = dict(packet)
    packet_identity = packet_core.pop("constructor_facing_packet_identity")
    if packet_identity != release["release_core"]["constructor_facing_packet_identity"]:
        raise ValueError("release/packet identity")
    if packet_identity != _seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_PACKET_G02B_V1", packet_core):
        raise ValueError("packet seal")
    packet_bytes = _canonical(packet)
    forbidden = (b"HMCV1-B02-M03", b"M13", b"ABSURD_LOGICAL_EXTENSION",
                 b"mechanism_id", b"mechanism_name", b"BLIND_EVALUATION")
    if any(token.lower() in packet_bytes.lower() for token in forbidden):
        raise ValueError("label or blind leakage")
    if packet["creative_premise_family_id"] != "UNASSIGNED":
        raise ValueError("creative premise assigned")
    if not all(value is False for value in packet["authority_matrix"].values()):
        raise ValueError("downstream authority")
    return PreparedDevelopmentConstructorAccessV1(
        packet_bytes=packet_bytes, packet_identity=packet_identity,
        release_identity=release["release_identity"], _mint=_MINT)


class ConstructorPacketCapabilityV1:
    """Single-object capability. There is deliberately no path/list/env API."""

    __slots__ = ("__prepared", "__consumed")

    def __init__(self, prepared: PreparedDevelopmentConstructorAccessV1) -> None:
        if type(prepared) is not PreparedDevelopmentConstructorAccessV1 or prepared._mint is not _MINT:
            raise TypeError("exact prepared constructor access required")
        self.__prepared = prepared
        self.__consumed = False

    def read_constructor_packet(self) -> bytes:
        if self.__consumed:
            raise RuntimeError("constructor packet capability already consumed")
        self.__consumed = True
        return self.__prepared.packet_bytes


__all__ = ["PreparedDevelopmentConstructorAccessV1", "ConstructorPacketCapabilityV1",
           "prepare_development_constructor_access_v1"]
