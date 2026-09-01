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
        "batch2-development-pilot05-constructor-access-release-v1":
            "B2_DEVELOPMENT_PILOT05_CONSTRUCTOR_ACCESS_RELEASE_V1",
        "batch2-development-pilot06-constructor-access-release-v2":
            "B2_DEVELOPMENT_PILOT06_CONSTRUCTOR_ACCESS_RELEASE_V2",
        "batch2-development-pilot07-constructor-access-release-v3":
            "B2_DEVELOPMENT_PILOT07_CONSTRUCTOR_ACCESS_RELEASE_V3",
        "batch2-development-pilot08-constructor-access-release-v4":
            "B2_DEVELOPMENT_PILOT08_CONSTRUCTOR_ACCESS_RELEASE_V4",
        "batch2-development-pilot09-constructor-access-release-v5-1":
            "B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_ACCESS_RELEASE_V5_1",
        "batch2-development-pilot10-constructor-access-release-v5-2":
            "B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_ACCESS_RELEASE_V5_2",
        "batch2-development-pilot11-constructor-access-release-v5-3":
            "B2_DEVELOPMENT_PILOT11_CONSTRUCTOR_ACCESS_RELEASE_V5_3",
        "batch2-development-pilot12-constructor-access-release-v5-3-1":
            "B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_ACCESS_RELEASE_V5_3_1",
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
        "B2_DEVELOPMENT_PILOT05_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1",
        "B2_DEVELOPMENT_PILOT06_CONSTRUCTOR_PACKET_G02B_V2",
        "B2_DEVELOPMENT_PILOT07_CONSTRUCTOR_PACKET_G02B_V3",
        "B2_DEVELOPMENT_PILOT08_CONSTRUCTOR_PACKET_G02B_V4",
        "B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_PACKET_G02B_V5_1",
        "B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_PACKET_G02B_V5_2",
        "B2_DEVELOPMENT_PILOT11_CONSTRUCTOR_PACKET_G02B_V5_3",
        "B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_PACKET_G02B_V5_3_1",
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
    if "exact_authorized_visible_context_utf8" in packet:
        source_text = packet["exact_authorized_visible_context_utf8"]
        if not isinstance(source_text, str):
            raise ValueError("authorized context unavailable")
        source_bytes = source_text.encode("utf-8")
        if hashlib.sha256(source_bytes).hexdigest() != packet.get("authorized_visible_context_sha256"):
            raise ValueError("authorized context hash")
        allowed_selected_propositions = {
            "batch2-development-pilot06-constructor-access-release-v2": "P3",
            "batch2-development-pilot07-constructor-access-release-v3": "P5",
            "batch2-development-pilot08-constructor-access-release-v4": "P5",
            "batch2-development-pilot09-constructor-access-release-v5-1": "P5",
            "batch2-development-pilot10-constructor-access-release-v5-2": "P3",
            "batch2-development-pilot11-constructor-access-release-v5-3": "P3",
            "batch2-development-pilot12-constructor-access-release-v5-3-1": "P5",
        }
        if (packet.get("selected_proposition_id") != allowed_selected_propositions.get(release["schema_name"])
                or len(packet["closed_factual_authority_envelope"]["propositions"]) != 1):
            raise ValueError("selected proposition boundary")
        if release["schema_name"] == "batch2-development-pilot08-constructor-access-release-v4":
            if not (
                packet.get("constructor_implementation_generation") == 4
                and packet.get("constructor_implementation_identity")
                == release["release_core"].get("constructor_implementation_identity")
                and packet.get("fragment_denyset_identity")
                == release["release_core"].get("fragment_denyset_identity")
            ):
                raise ValueError("V4 implementation or denyset binding")
        if release["schema_name"] == "batch2-development-pilot09-constructor-access-release-v5-1":
            if not (
                packet.get("constructor_implementation_generation") == "5.1"
                and packet.get("constructor_contract_identity")
                == release["release_core"].get("constructor_contract_identity")
                and packet.get("constructor_implementation_identity")
                == release["release_core"].get("constructor_implementation_identity")
                and packet.get("constructor_source_compatibility_identity")
                == release["release_core"].get("constructor_source_compatibility_identity")
                and packet.get("fragment_denyset_identity")
                == release["release_core"].get("fragment_denyset_identity")
            ):
                raise ValueError("V5.1 contract, implementation, compatibility, or denyset binding")
        if release["schema_name"] == "batch2-development-pilot10-constructor-access-release-v5-2":
            plan = packet.get("proposition_derived_typed_plan")
            if not (
                packet.get("constructor_contract_identity")
                == release["release_core"].get("constructor_contract_identity")
                and packet.get("constructor_implementation_identity")
                == release["release_core"].get("constructor_implementation_identity")
                and packet.get("realization_provider_identity")
                == release["release_core"].get("realization_provider_identity")
                and packet.get("candidate_emitter_identity")
                == release["release_core"].get("candidate_emitter_identity")
                and packet.get("constructor_source_compatibility_identity")
                == release["release_core"].get("constructor_source_compatibility_identity")
                and packet.get("typed_plan_commitment")
                == release["release_core"].get("typed_plan_commitment")
                and packet.get("fragment_denyset_identity")
                == release["release_core"].get("fragment_denyset_identity")
                and packet.get("pre_emission_governance_identity")
                == release["release_core"].get("pre_emission_governance_identity")
                and packet.get("pre_emission_conformance_schema_identity")
                == release["release_core"].get("pre_emission_conformance_schema_identity")
                and packet.get("pre_emission_enforcement_identity")
                == release["release_core"].get("pre_emission_enforcement_identity")
                and isinstance(plan, list) and len(plan) == 3
                and sum(len(node.get("predecessor_node_ids", [])) for node in plan) == 2
            ):
                raise ValueError("V5.2 implementation, plan, enforcement, compatibility, or denyset binding")
        if release["schema_name"] == "batch2-development-pilot11-constructor-access-release-v5-3":
            plan = packet.get("proposition_derived_typed_plan")
            semantic_edges = packet.get("edge_necessity_witnesses")
            if not (
                packet.get("constructor_contract_identity")
                == release["release_core"].get("constructor_contract_identity")
                and packet.get("constructor_implementation_identity")
                == release["release_core"].get("constructor_implementation_identity")
                and packet.get("realization_provider_identity")
                == release["release_core"].get("realization_provider_identity")
                and packet.get("candidate_emitter_identity")
                == release["release_core"].get("candidate_emitter_identity")
                and packet.get("constructor_source_compatibility_identity")
                == release["release_core"].get("constructor_source_compatibility_identity")
                and packet.get("constructor_source_compatibility_audit_identity")
                == release["release_core"].get("constructor_source_compatibility_audit_identity")
                and packet.get("semantic_plan_commitment")
                == release["release_core"].get("semantic_plan_commitment")
                and packet.get("fragment_denyset_identity")
                == release["release_core"].get("fragment_denyset_identity")
                and packet.get("pre_emission_governance_identity")
                == release["release_core"].get("pre_emission_governance_identity")
                and packet.get("pre_emission_conformance_schema_identity")
                == release["release_core"].get("pre_emission_conformance_schema_identity")
                and packet.get("pre_emission_enforcement_identity")
                == release["release_core"].get("pre_emission_enforcement_identity")
                and isinstance(plan, list) and len(plan) == 3
                and sum(len(node.get("predecessor_node_ids", [])) for node in plan) == 2
                and isinstance(semantic_edges, list) and len(semantic_edges) == 2
                and all(edge.get("counterfactual_dependency") is True
                        and edge.get("non_arbitrary") is True for edge in semantic_edges)
            ):
                raise ValueError("V5.3 semantic plan, enforcement, compatibility, or denyset binding")
        if release["schema_name"] == "batch2-development-pilot12-constructor-access-release-v5-3-1":
            plan = packet.get("proposition_derived_typed_plan")
            semantic_edges = packet.get("edge_necessity_witnesses")
            if not (
                packet.get("base_constructor_contract_identity")
                == release["release_core"].get("base_constructor_contract_identity")
                and packet.get("alignment_contract_identity")
                == release["release_core"].get("alignment_contract_identity")
                and packet.get("constructor_implementation_identity")
                == release["release_core"].get("constructor_implementation_identity")
                and packet.get("realization_provider_identity")
                == release["release_core"].get("realization_provider_identity")
                and packet.get("candidate_emitter_identity")
                == release["release_core"].get("candidate_emitter_identity")
                and packet.get("constructor_source_compatibility_identity")
                == release["release_core"].get("constructor_source_compatibility_identity")
                and packet.get("constructor_source_compatibility_audit_identity")
                == release["release_core"].get("constructor_source_compatibility_audit_identity")
                and packet.get("semantic_plan_commitment")
                == release["release_core"].get("semantic_plan_commitment")
                and packet.get("fragment_denyset_identity")
                == release["release_core"].get("fragment_denyset_identity")
                and packet.get("pre_emission_governance_identity")
                == release["release_core"].get("pre_emission_governance_identity")
                and packet.get("pre_emission_conformance_schema_identity")
                == release["release_core"].get("pre_emission_conformance_schema_identity")
                and packet.get("pre_emission_semantic_enforcement_identity")
                == release["release_core"].get("pre_emission_semantic_enforcement_identity")
                and packet.get("pre_emission_coordinate_alignment_identity")
                == release["release_core"].get("pre_emission_coordinate_alignment_identity")
                and packet.get("unselected_proposition_or_fallback_authority") == "ABSENT"
                and isinstance(plan, list) and len(plan) == 3
                and sum(len(node.get("predecessor_node_ids", [])) for node in plan) == 2
                and isinstance(semantic_edges, list) and len(semantic_edges) == 2
                and all(edge.get("counterfactual_dependency") is True
                        and edge.get("non_arbitrary") is True for edge in semantic_edges)
            ):
                raise ValueError("V5.3.1 semantic plan, alignment, enforcement, compatibility, or denyset binding")
    else:
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
