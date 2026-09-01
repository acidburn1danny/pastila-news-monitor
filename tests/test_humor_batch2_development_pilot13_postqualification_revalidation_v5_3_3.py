import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.humor_batch2_constructor_access_v1 import prepare_development_constructor_access_v1
from pastila_scout.humor_batch2_development_constructor_v5_3_3_release_path import (
    FrozenExecutableAuthorityV533,
    FrozenNodeRelationRule,
    FrozenSurfaceRoleRule,
    execute_release_facing_path,
)

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"
RELEASE_PATH = ART / "humor-mechanics-batch2-development-pilot13-constructor-access-release-v5-3-3.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def reseal(value):
    packet = value["constructor_packet"]
    packet_core = dict(packet)
    packet_core.pop("constructor_facing_packet_identity", None)
    packet_id = seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_PACKET_G02B_V5_3_3", packet_core)
    value["constructor_packet"] = {**packet_core, "constructor_facing_packet_identity": packet_id}
    value["release_core"]["constructor_facing_packet_identity"] = packet_id
    value["release_identity"] = seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_ACCESS_RELEASE_V5_3_3", value["release_core"])
    return canonical(value)


def load_release():
    return json.loads(RELEASE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("mutation", [
    lambda r: r["constructor_packet"].__setitem__("unknown_family_field", "x"),
    lambda r: r["constructor_packet"].pop("class_b_state"),
    lambda r: r.__setitem__("schema_version", "5.3.2"),
    lambda r: r.__setitem__("schema_name", "batch2-development-pilot13-constructor-access-release-v5-3-1"),
    lambda r: r["constructor_packet"].__setitem__("construction_revision_family_id", "ALTERNATE_FAMILY"),
    lambda r: r["constructor_packet"].__setitem__("qualified_executable_implementation_identity", "0" * 64),
    lambda r: r["constructor_packet"].__setitem__("fragment_denyset_identity", "1" * 64),
    lambda r: r["constructor_packet"].__setitem__("selected_supporting_span_sha256", "2" * 64),
    lambda r: r["constructor_packet"].__setitem__("authorized_visible_context_sha256", "3" * 64),
    lambda r: r["release_core"].__setitem__("stale_implementation_identity", "4" * 64),
])
def test_resealed_release_schema_binding_and_hydration_variants_fail_closed(mutation):
    release = load_release()
    mutation(release)
    with pytest.raises(ValueError):
        prepare_development_constructor_access_v1(release_bytes=reseal(release))


def test_committed_release_hydrates_without_consuming_capability():
    prepared = prepare_development_constructor_access_v1(release_bytes=RELEASE_PATH.read_bytes())
    release = load_release()
    assert prepared.packet_identity == release["constructor_packet"]["constructor_facing_packet_identity"]
    assert prepared.release_identity == release["release_identity"]


def test_synthetic_nonfamily_path_runs_after_committed_binding_hydration():
    release = load_release()
    prepared = prepare_development_constructor_access_v1(release_bytes=RELEASE_PATH.read_bytes())
    packet = release["constructor_packet"]
    nodes = (
        FrozenNodeRelationRule("L1", "A1", "P1", "B1", "X1", False, None),
        FrozenNodeRelationRule("L2", "X1", "P2", "B2", "X2", False, "L1"),
        FrozenNodeRelationRule("RESULT", "X2", "P3", "B3", None, True, "L2"),
    )
    forms = {
        "a1": "regula locală", "p1": "activează", "b1": "condiția sintetică", "o1": "semnalul intermediar",
        "a2": "semnalul intermediar", "p2": "deschide", "b2": "registrul sintetic", "o2": "starea finală",
        "a3": "starea finală", "p3": "închide", "b3": "circuitul sintetic",
    }
    roles = []
    for node, suffix in zip(nodes, ("1", "2", "3")):
        for role, prefix, identity in (
            ("ACTOR", "a", node.actor_identity), ("PREDICATE", "p", node.predicate_identity),
            ("PATIENT", "b", node.patient_identity),
        ):
            form = forms[prefix + suffix]
            roles.append(FrozenSurfaceRoleRule(node.node_id, role, identity, form, (form,)))
        if node.produced_identity:
            form = forms["o" + suffix]
            roles.append(FrozenSurfaceRoleRule(node.node_id, "PRODUCED", node.produced_identity, form, (form,)))
    authority = FrozenExecutableAuthorityV533(
        packet["class_a_closure_identity"], packet["qualified_executable_implementation_identity"],
        prepared.release_identity, packet["selected_supporting_span_sha256"], packet["fragment_denyset_identity"],
        packet["authority_partition_contract_identity"], tuple(roles), nodes,
    )
    clause = (
        "Regula locală activează condiția sintetică și produce semnalul intermediar. "
        "Semnalul intermediar deschide registrul sintetic și produce starea finală. "
        "Starea finală închide circuitul sintetic."
    )
    emitted, receipt = execute_release_facing_path(authority=authority, provider_payload={"clause": clause})
    assert emitted == clause.encode("utf-8")
    assert (receipt.nodes_realized, receipt.edges_realized, receipt.terminal_results) == (3, 2, 1)
    assert all(emitted[item.utf8_byte_start:item.utf8_byte_end] == item.surface_form.encode("utf-8")
               for item in receipt.observed_roles)
    with pytest.raises(ValueError):
        execute_release_facing_path(authority=replace(authority, denyset_identity=""), provider_payload={"clause": clause})
