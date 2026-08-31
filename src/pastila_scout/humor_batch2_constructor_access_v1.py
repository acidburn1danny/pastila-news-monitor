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
    common = {"schema_name", "schema_version", "release_core", "release_identity",
              "constructor_packet", "transport_policy"}
    visible_field = ("constructor_visible_file_set" if "constructor_visible_file_set" in release
                     else "constructor_visible_object_set")
    if set(release) != common | {visible_field}:
        raise ValueError("release field set")
    release_namespaces = {
        "batch2-development-pilot01-constructor-access-release-v1":
            "B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_ACCESS_RELEASE_V1",
        "batch2-development-pilot02-constructor-access-release-v1":
            "B2_DEVELOPMENT_PILOT02_CONSTRUCTOR_ACCESS_RELEASE_V1",
        "batch2-development-pilot03-constructor-access-release-v1":
            "B2_DEVELOPMENT_PILOT03_CONSTRUCTOR_ACCESS_RELEASE_V1",
        "batch2-development-pilot04-constructor-access-release-v1":
            "B2_DEVELOPMENT_PILOT04_CONSTRUCTOR_ACCESS_RELEASE_V1",
    }
    release_namespace = release_namespaces.get(release["schema_name"])
    if release_namespace is None:
        raise ValueError("release schema")
    if release["release_identity"] != _seal(release_namespace, release["release_core"]):
        raise ValueError("release seal")
    expected_visible = (["CONSTRUCTOR_PACKET"] if visible_field == "constructor_visible_file_set"
                        else ["CONSTRUCTOR_PACKET_EXACT_BYTES"])
    if release[visible_field] != expected_visible:
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
    namespace = release["release_core"].get("packet_seal_namespace")
    if namespace not in {
        "B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1",
        "B2_DEVELOPMENT_PILOT02_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1",
        "B2_DEVELOPMENT_PILOT03_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1",
        "B2_DEVELOPMENT_PILOT04_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1",
    }:
        raise ValueError("packet seal namespace")
    if packet_identity != _seal(namespace, packet_core):
        raise ValueError("packet seal")
    packet_bytes = _canonical(packet)
    forbidden = (b"HMCV1-B02-M03", b"M13", b"ABSURD_LOGICAL_EXTENSION",
                 b"mechanism_id", b"mechanism_name", b"BLIND_EVALUATION")
    if any(token.lower() in packet_bytes.lower() for token in forbidden):
        raise ValueError("label or blind leakage")
    if packet["creative_premise_family_id"] != "UNASSIGNED":
        raise ValueError("creative premise assigned")
    source = packet.get("source_object", {})
    source_text = source.get("source_text_utf8")
    if not isinstance(source_text, str):
        raise ValueError("source text unavailable")
    source_bytes = source_text.encode("utf-8")
    if hashlib.sha256(source_bytes).hexdigest() != source.get("sha256"):
        raise ValueError("source text hash")
    if len(source_bytes) != source.get("byte_length") or source.get("encoding") != "UTF-8":
        raise ValueError("source byte binding")
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
