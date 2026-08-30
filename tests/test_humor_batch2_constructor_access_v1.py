from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.humor_batch2_constructor_access_v1 import (
    ConstructorPacketCapabilityV1,
    PreparedDevelopmentConstructorAccessV1,
    prepare_development_constructor_access_v1,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-constructor-access-release-v1.json"


def prepared() -> PreparedDevelopmentConstructorAccessV1:
    return prepare_development_constructor_access_v1(release_bytes=RELEASE.read_bytes())


def test_exact_release_is_pathless_single_use_and_label_blind() -> None:
    access = prepared()
    capability = ConstructorPacketCapabilityV1(access)
    packet = capability.read_constructor_packet()
    assert b"HMCV1-B02-M03" not in packet
    assert b"mapping_commitment" not in packet
    assert json.loads(packet)["creative_premise_family_id"] == "UNASSIGNED"
    with pytest.raises(RuntimeError):
        capability.read_constructor_packet()


@pytest.mark.parametrize("name", ["open", "open_path", "listdir", "glob", "environment", "command_line", "logs", "mapping"])
def test_no_traversal_enumeration_environment_or_sibling_api(name: str) -> None:
    assert not hasattr(ConstructorPacketCapabilityV1(prepared()), name)


def test_mutation_stale_reseal_and_role_substitution_fail_closed() -> None:
    value = json.loads(RELEASE.read_text(encoding="utf-8"))
    for mutation in (
        lambda x: x["constructor_packet"].update({"creative_premise_family_id": "MUTATED"}),
        lambda x: x["release_core"].update({"constructor_facing_packet_identity": "0" * 64}),
        lambda x: x["constructor_packet"].update({"mapping_commitment": "oracle"}),
    ):
        altered = json.loads(json.dumps(value))
        mutation(altered)
        with pytest.raises(ValueError):
            prepare_development_constructor_access_v1(release_bytes=json.dumps(altered).encode())
    with pytest.raises(TypeError):
        PreparedDevelopmentConstructorAccessV1(packet_bytes=b"{}", packet_identity="x", release_identity="y", _mint=object())


def test_import_and_preparation_have_zero_construction_side_effects() -> None:
    access = prepared()
    assert access.packet_identity
    assert not hasattr(ConstructorPacketCapabilityV1, "execute")
    assert not hasattr(ConstructorPacketCapabilityV1, "construct")
