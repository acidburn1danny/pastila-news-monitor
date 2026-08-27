from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path

import pytest

from pastila_scout.expression_catalog_v2 import (
    AdjudicationStatusV2,
    ExpressionCatalogV2IntegrityError,
    RenderabilityStatusV2,
    UnknownExpressionCatalogV2VersionError,
    load_expression_catalog_overlay_v2,
)
from pastila_scout.expression_retrieval_v1.catalog import load_catalog_v1

CATALOG_V1_SHA256 = "79d487e010c60de26aec3ae1a2e366ad1d6276d738cef6c5fb62494bd0a8ae90"


def _resource() -> Path:
    return Path(
        str(
            files("pastila_scout.resources.expression_catalog_v2").joinpath(
                "catalog-overlay.json"
            )
        )
    )


def _write_canonical(path: Path, value: object) -> None:
    path.write_bytes(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def test_complete_inventory_and_owner_queue_are_inactive_and_exact() -> None:
    overlay = load_expression_catalog_overlay_v2()
    assert len(overlay.records) == 102
    assert len({item.expression_id for item in overlay.records}) == 102
    assert len(overlay.owner_review_queue) == 74
    assert len(overlay.approved_surfaces) == 23
    assert len(overlay.preferred_surface_evidence) == 11
    assert len(overlay.productive_family_evidence) == 4
    assert overlay.production_activations == 0
    assert all(not item.production_active for item in overlay.records)
    assert all(not item.production_active for item in overlay.approved_surfaces)
    assert all(
        not item.voice_v2_authorized for item in overlay.preferred_surface_evidence
    )
    assert all(
        not item.voice_v2_productive for item in overlay.productive_family_evidence
    )


def test_pilot_dispositions_and_five_surfaces_round_trip_exactly() -> None:
    overlay = load_expression_catalog_overlay_v2()
    records = {item.expression_id: item for item in overlay.records}
    approved_ids = {
        "ro-expression-v1:2e5417acdb78ee504d4b",
        "ro-expression-v1:746823d11b1460dac265",
        "ro-expression-v1:41136a4e8443b1239535",
        "ro-expression-v1:b37979ce96f5d03deda3",
        "ro-expression-v1:2aaa6fa3011f6a2ea8f0",
        "ro-expression-v1:2b65e40f861c797989a7",
        "ro-expression-v1:8c165e82d1f7002717ed",
        "ro-expression-v1:291dc70a3335d6c5a326",
        "ro-expression-v1:499847b2e206c615cb3f",
        "ro-expression-v1:5d8d914aa7485bd00357",
        "ro-expression-v1:741a112a615fd83b70c7",
        "ro-expression-v1:7ad0710287d639d1402e",
        "ro-expression-v1:844dedd262d2b832d6ee",
        "ro-expression-v1:9061edfa9121f3caa7c6",
        "ro-expression-v1:a128853989c1ea8dbc10",
        "ro-expression-v1:a932575dfe8f1ed9134b",
        "ro-expression-v1:cb128a3e07f2dbd87808",
        "ro-expression-v1:ee71f9fb9de0fe424b4c",
        "ro-expression-v1:fd75f40659d177a3a038",
        "ro-expression-v1:1068794b4bf34c8914dc",
        "ro-expression-v1:65f9b0c32e8e886b8d0f",
        "ro-expression-v1:0e6562965022d3dd391f",
        "ro-expression-v1:2ae8cdb574c10fbc2328",
        "ro-expression-v1:3df48761977436d385be",
        "ro-expression-v1:e9c624855a4d33760669",
        "ro-expression-v1:7a7cb37228c5608408c6",
        "ro-expression-v1:34d94191a3c600bc4f26",
    }
    assert {
        item.expression_id
        for item in overlay.records
        if item.adjudication_status is AdjudicationStatusV2.APPROVED_CANDIDATE_SCOPE
    } == approved_ids
    evidence = records["ro-expression-v1:993a3b3354ec1705d963"]
    assert evidence.adjudication_status is AdjudicationStatusV2.EVIDENCE_ONLY
    assert evidence.renderability_status is RenderabilityStatusV2.UNAVAILABLE
    assert not evidence.approved_surface_ids
    exact_v1_ids = {
        "ro-expression-v1:2e5417acdb78ee504d4b",
        "ro-expression-v1:8c165e82d1f7002717ed",
        "ro-expression-v1:7ad0710287d639d1402e",
        "ro-expression-v1:a932575dfe8f1ed9134b",
    }
    assert all(
        records[item].renderability_status is RenderabilityStatusV2.EXACT_V1_SURFACE
        for item in exact_v1_ids
    )
    surfaces = {item.expression_id: item for item in overlay.approved_surfaces}
    assert set(surfaces) == approved_ids - exact_v1_ids
    assert surfaces["ro-expression-v1:2aaa6fa3011f6a2ea8f0"].exact_surface == (
        "Aici deja vorbim de pus batista pe țambal."
    )
    assert surfaces["ro-expression-v1:2b65e40f861c797989a7"].exact_surface == (
        "Și uite așa ajungem la clasica întoarcere ca la Ploiești."
    )


def test_unreviewed_records_have_no_inferred_relationship_or_renderability() -> None:
    overlay = load_expression_catalog_overlay_v2()
    unreviewed = [
        item
        for item in overlay.records
        if item.adjudication_status is AdjudicationStatusV2.CANDIDATE_OWNER_REVIEW
    ]
    assert len(unreviewed) == 74
    assert all(item.adjudicated_scope is None for item in unreviewed)
    assert all(
        item.renderability_status is RenderabilityStatusV2.UNAVAILABLE
        for item in unreviewed
    )
    assert all(not item.approved_surface_ids for item in unreviewed)
    assert all(
        not item.semantic_approval_inferred for item in overlay.owner_review_queue
    )


def test_catalog_v1_and_legacy_evidence_remain_unchanged() -> None:
    catalog = load_catalog_v1(use_cache=False)
    assert catalog.content_sha256 == CATALOG_V1_SHA256
    assert len(catalog.expressions) == 102
    assert len(catalog.preferred_surfaces) == 11
    assert len(catalog.productive_families) == 4
    overlay = load_expression_catalog_overlay_v2()
    assert (
        sum(
            item.source_resolves_to_packaged_expression
            for item in overlay.preferred_surface_evidence
        )
        == 1
    )
    assert (
        sum(
            "multiple_surfaces_share_source" in item.ambiguity_codes
            for item in overlay.preferred_surface_evidence
        )
        == 5
    )


def test_first_twelve_behavioral_records_and_surfaces_are_additive_and_inactive():
    overlay = load_expression_catalog_overlay_v2()
    records = {item.expression_id: item for item in overlay.records}
    first_twelve = {
        "ro-expression-v1:291dc70a3335d6c5a326",
        "ro-expression-v1:499847b2e206c615cb3f",
        "ro-expression-v1:5d8d914aa7485bd00357",
        "ro-expression-v1:741a112a615fd83b70c7",
        "ro-expression-v1:7ad0710287d639d1402e",
        "ro-expression-v1:844dedd262d2b832d6ee",
        "ro-expression-v1:9061edfa9121f3caa7c6",
        "ro-expression-v1:a128853989c1ea8dbc10",
        "ro-expression-v1:a932575dfe8f1ed9134b",
        "ro-expression-v1:cb128a3e07f2dbd87808",
        "ro-expression-v1:ee71f9fb9de0fe424b4c",
        "ro-expression-v1:fd75f40659d177a3a038",
    }
    assert all(
        records[expression_id].review_group == "first_12_deep_reviewed"
        for expression_id in first_twelve
    )
    assert all(
        records[expression_id].adjudication_status
        is AdjudicationStatusV2.APPROVED_CANDIDATE_SCOPE
        for expression_id in first_twelve
    )
    surfaces = {item.surface_id: item for item in overlay.approved_surfaces}
    assert "surface-v1:07" not in surfaces
    assert all(not item.production_active for item in surfaces.values())
    assert all(
        item.expression_family_identity == item.equivalence_group_identity
        for item in surfaces.values()
    )
    legacy_collision = next(
        item
        for item in overlay.preferred_surface_evidence
        if item.surface_id == "surface-v1:07"
    )
    assert not legacy_collision.voice_v2_authorized


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda data: data.update(schema_version="999"), "version"),
        (
            lambda data: data.update(catalog_v1_file_sha256="0" * 64),
            "stale Catalog V1",
        ),
        (
            lambda data: data["approved_surfaces"][0].update(
                surface_utf8_sha256="0" * 64
            ),
            "surface hash",
        ),
        (
            lambda data: data["records"][0].update(production_active=True),
            "structure",
        ),
        (
            lambda data: data["records"][0].update(
                approved_surface_ids=["missing-surface"]
            ),
            "structure",
        ),
        (
            lambda data: data["preferred_surface_evidence"][0].update(
                relation_type="silently-changed"
            ),
            "preferred-surface ambiguity",
        ),
    ],
)
def test_tampered_overlay_fails_closed(tmp_path, mutation, error) -> None:
    data = json.loads(_resource().read_text(encoding="utf-8"))
    mutation(data)
    path = tmp_path / "overlay.json"
    _write_canonical(path, data)
    expected = (
        UnknownExpressionCatalogV2VersionError
        if error == "version"
        else ExpressionCatalogV2IntegrityError
    )
    with pytest.raises(expected, match=f"{error}|Catalog V2 is not canonical"):
        load_expression_catalog_overlay_v2(path)


def test_packaged_overlay_is_canonical_and_deterministic() -> None:
    first = load_expression_catalog_overlay_v2()
    second = load_expression_catalog_overlay_v2()
    assert first == second
    raw = _resource().read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "adfd4a75e7ac7e1f55a0922d18aa70dd022dea7735ed2932199f55513e1260b2"
    )
    assert (
        first.overlay_identity
        == "bb4cf9c84a46c69ce9ea1ef9887d34683fc5c5beeb01854279f2080bf1993cab"
    )
