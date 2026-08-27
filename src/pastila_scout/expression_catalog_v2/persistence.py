"""Canonical loading and integrity verification for Catalog V2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from pydantic import ValidationError

from pastila_scout.expression_retrieval_v1.catalog import load_catalog_v1
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_bytes

from .models import ZERO_SHA256, ExpressionCatalogOverlayV2


class ExpressionCatalogV2IntegrityError(ValueError):
    pass


class UnknownExpressionCatalogV2VersionError(ValueError):
    pass


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha_value(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _sealed(overlay: ExpressionCatalogOverlayV2) -> str:
    payload = overlay.model_copy(update={"overlay_identity": ZERO_SHA256})
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def validate_overlay_v2(
    overlay: ExpressionCatalogOverlayV2, *, catalog_path=None
) -> None:
    catalog = load_catalog_v1(catalog_path, use_cache=False)
    if overlay.catalog_v1_file_sha256 != catalog.content_sha256:
        raise ExpressionCatalogV2IntegrityError("stale Catalog V1 identity")
    catalog_data = json.loads(
        (
            Path(catalog_path)
            if catalog_path
            else Path(
                str(
                    files("pastila_scout.resources.expression_retrieval_v1").joinpath(
                        "catalog.json"
                    )
                )
            )
        ).read_text(encoding="utf-8")
    )
    if overlay.catalog_v1_content_sha256 != catalog_data["bundle_content_sha256"]:
        raise ExpressionCatalogV2IntegrityError("Catalog V1 content identity mismatch")
    records = {item.expression_id: item for item in overlay.records}
    v1 = {item.expression_id: item for item in catalog.expressions}
    if len(records) != len(overlay.records) or set(records) != set(v1):
        raise ExpressionCatalogV2IntegrityError("Catalog V1 accounting mismatch")
    surfaces = {item.surface_id: item for item in overlay.approved_surfaces}
    if len(surfaces) != len(overlay.approved_surfaces):
        raise ExpressionCatalogV2IntegrityError("duplicate approved surface identity")
    for expression_id, record in records.items():
        source = v1[expression_id]
        if record.source_surface_utf8_sha256 != _sha_text(source.text):
            raise ExpressionCatalogV2IntegrityError("invalid source surface hash")
        if record.legacy_metadata_sha256 != _sha_value(asdict(source)):
            raise ExpressionCatalogV2IntegrityError("stale legacy metadata identity")
        for surface_id in record.approved_surface_ids:
            if (
                surface_id not in surfaces
                or surfaces[surface_id].expression_id != expression_id
            ):
                raise ExpressionCatalogV2IntegrityError("orphan approved surface")
    for surface in surfaces.values():
        if surface.expression_id not in records:
            raise ExpressionCatalogV2IntegrityError("orphan approved surface")
        if surface.surface_utf8_sha256 != _sha_text(surface.exact_surface):
            raise ExpressionCatalogV2IntegrityError("invalid approved surface hash")
    preferred = {item.surface_id: item for item in catalog.preferred_surfaces}
    evidence = {item.surface_id: item for item in overlay.preferred_surface_evidence}
    if len(evidence) != len(overlay.preferred_surface_evidence) or set(evidence) != set(
        preferred
    ):
        raise ExpressionCatalogV2IntegrityError("preferred-surface evidence mismatch")
    for surface_id, item in preferred.items():
        saved = evidence[surface_id]
        if (
            saved.source_expression_id != item.source_expression_id
            or saved.surface_utf8_sha256 != _sha_text(item.surface)
            or saved.relation_type != item.relation_type
        ):
            raise ExpressionCatalogV2IntegrityError("preferred-surface ambiguity")
    families = {item.family_id: item for item in catalog.productive_families}
    family_evidence = {
        item.family_id: item for item in overlay.productive_family_evidence
    }
    if len(family_evidence) != len(overlay.productive_family_evidence) or set(
        family_evidence
    ) != set(families):
        raise ExpressionCatalogV2IntegrityError("productive-family evidence mismatch")
    for family_id, family in families.items():
        saved = family_evidence[family_id]
        if saved.members != family.members or saved.evidence_sha256 != _sha_value(
            asdict(family)
        ):
            raise ExpressionCatalogV2IntegrityError("productive-family evidence drift")
    queue_ids = [item.expression_id for item in overlay.owner_review_queue]
    expected_queue = [
        item.expression_id
        for item in overlay.records
        if item.adjudication_status.value == "candidate_owner_review"
    ]
    if len(queue_ids) != len(set(queue_ids)) or set(queue_ids) != set(expected_queue):
        raise ExpressionCatalogV2IntegrityError("owner-review queue mismatch")
    if overlay.overlay_identity != _sealed(overlay):
        raise ExpressionCatalogV2IntegrityError("overlay identity mismatch")


def load_expression_catalog_overlay_v2(
    path: str | Path | None = None, *, catalog_path=None
) -> ExpressionCatalogOverlayV2:
    resource = (
        Path(path)
        if path
        else Path(
            str(
                files("pastila_scout.resources.expression_catalog_v2").joinpath(
                    "catalog-overlay.json"
                )
            )
        )
    )
    raw = resource.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExpressionCatalogV2IntegrityError("invalid Catalog V2 JSON") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_name") != "pastilaacida-voice-expression-catalog-overlay"
        or value.get("schema_version") != "2"
    ):
        raise UnknownExpressionCatalogV2VersionError(
            "unsupported Catalog V2 schema/version"
        )
    try:
        overlay = ExpressionCatalogOverlayV2.model_validate(value)
    except ValidationError as exc:
        raise ExpressionCatalogV2IntegrityError("invalid Catalog V2 structure") from exc
    if canonical_bytes(overlay) != raw:
        raise ExpressionCatalogV2IntegrityError("Catalog V2 is not canonical")
    validate_overlay_v2(overlay, catalog_path=catalog_path)
    return overlay


__all__ = [
    "ExpressionCatalogV2IntegrityError",
    "UnknownExpressionCatalogV2VersionError",
    "load_expression_catalog_overlay_v2",
    "validate_overlay_v2",
]
