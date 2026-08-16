from __future__ import annotations

import hashlib
import json
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

from .errors import ExpressionCatalogErrorV1
from .models import (
    ComedyDeviceRecordV1,
    ControlledTermRecordV1,
    ExpressionCatalogV1,
    ExpressionRecordV1,
    PreferredSurfaceV1,
    ProductiveFamilyV1,
    SignatureDeviceRecordV1,
)

_SUPPORTED_VERSION = 1
_CACHE: dict[str, ExpressionCatalogV1] = {}


def _timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _tuple(record: dict[str, Any], name: str) -> tuple[str, ...]:
    value = record.get(name, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ExpressionCatalogErrorV1(f"{name} must be a string array")
    return tuple(value)


def _unique(records: tuple[Any, ...], attribute: str, label: str) -> None:
    values = [getattr(record, attribute) for record in records]
    if len(values) != len(set(values)):
        raise ExpressionCatalogErrorV1(f"duplicate {label}")


def load_catalog_v1(
    path: str | Path | None = None, *, use_cache: bool = True
) -> ExpressionCatalogV1:
    resource = (
        Path(path)
        if path is not None
        else Path(
            str(
                files("pastila_scout.resources.expression_retrieval_v1").joinpath(
                    "catalog.json"
                )
            )
        )
    )
    try:
        raw = resource.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExpressionCatalogErrorV1(f"catalog load failed: {exc}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if use_cache and digest in _CACHE:
        return _CACHE[digest]
    catalog = _parse_catalog(data, digest)
    if use_cache:
        _CACHE[digest] = catalog
    return catalog


def reset_catalog_cache_v1() -> None:
    _CACHE.clear()


def _parse_catalog(data: Any, digest: str) -> ExpressionCatalogV1:
    if not isinstance(data, dict):
        raise ExpressionCatalogErrorV1("catalog root must be an object")
    for name in (
        "corpus_schema_version",
        "editorial_calibration_version",
        "device_catalog_version",
        "bundle_version",
    ):
        if data.get(name) != _SUPPORTED_VERSION:
            raise ExpressionCatalogErrorV1(f"unsupported {name}")
    declared_content = data.get("bundle_content_sha256")
    content = dict(data)
    content.pop("bundle_content_sha256", None)
    calculated_content = hashlib.sha256(
        json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if declared_content != calculated_content:
        raise ExpressionCatalogErrorV1("bundle content integrity failure")
    try:
        expressions = tuple(
            ExpressionRecordV1(
                expression_id=item["expression_id"],
                text=item["text"],
                owner_class=item["owner_class"],
                semantic_gloss=item["semantic_gloss"],
                semantic_families=_tuple(item, "semantic_families"),
                keywords=_tuple(item, "keywords"),
                risk_tags=_tuple(item, "risk_tags"),
                preferred_surface=item.get("preferred_surface"),
                regionalism=bool(item.get("regionalism", False)),
                regions=_tuple(item, "regions"),
                raw=bool(item.get("raw", False)),
                meme=bool(item.get("meme", False)),
                max_per_episode=int(item.get("max_per_episode", 1)),
                cooldown_episodes=int(item.get("cooldown_episodes", 0)),
                enabled=bool(item.get("enabled", True)),
                active_from=_timestamp(item.get("active_from")),
                active_until=_timestamp(item.get("active_until")),
            )
            for item in data["expressions"]
        )
        surfaces = tuple(
            PreferredSurfaceV1(
                surface_id=item["surface_id"],
                source_expression_id=item["source_expression_id"],
                surface=item["surface"],
                relation_type=item["relation_type"],
            )
            for item in data["preferred_surfaces"]
        )
        families = tuple(
            ProductiveFamilyV1(
                family_id=item["family_id"], members=_tuple(item, "members")
            )
            for item in data["productive_families"]
        )
        terms = tuple(
            ControlledTermRecordV1(
                term_id=item["term_id"],
                term=item["term"],
                domains=_tuple(item, "domains"),
                triggers=_tuple(item, "triggers"),
                factual_constraints=_tuple(item, "factual_constraints"),
                risk_tags=_tuple(item, "risk_tags"),
                temporal_sensitivity=item["temporal_sensitivity"],
                max_per_episode=int(item["max_per_episode"]),
                cooldown_episodes=int(item["cooldown_episodes"]),
                enabled=bool(item.get("enabled", True)),
                active_from=_timestamp(item.get("active_from")),
                active_until=_timestamp(item.get("active_until")),
            )
            for item in data["controlled_terms"]
        )
        devices = tuple(
            ComedyDeviceRecordV1(
                device_id=item["device_id"],
                device_type=item["device_type"],
                family=item["family"],
                structure=item["structure"],
                semantic_affordances=_tuple(item, "semantic_affordances"),
                best_for=_tuple(item, "best_for"),
                bad_for=_tuple(item, "bad_for"),
                replaceable_slots=_tuple(item, "replaceable_slots"),
                forbidden_transforms=_tuple(item, "forbidden_transforms"),
                source_expression_ids=_tuple(item, "source_expression_ids"),
                callback_capable=bool(item.get("callback_capable", False)),
                signature_capable=bool(item.get("signature_capable", False)),
                compound_capable=bool(item.get("compound_capable", False)),
                max_per_episode=int(item.get("max_per_episode", 1)),
                recurrence_mode=item.get("recurrence_mode", "ordinary"),
                risk_tags=_tuple(item, "risk_tags"),
            )
            for item in data["comedy_devices"]
        )
        signatures = tuple(
            SignatureDeviceRecordV1(
                signature_id=item["signature_id"],
                device_id=item["device_id"],
                family=item["family"],
                recurrence_mode=item["recurrence_mode"],
                max_per_episode=int(item["max_per_episode"]),
                hard_cooldown=int(item["hard_cooldown"]),
                preferred_spacing_episodes=int(item["preferred_spacing_episodes"]),
                canonical_signature=bool(item["canonical_signature"]),
            )
            for item in data["signature_devices"]
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ExpressionCatalogErrorV1(f"invalid catalog field: {exc}") from exc
    for record in expressions:
        if record.owner_class in {"REJECT_EDITOR", "DEFER_PROMOTION"}:
            raise ExpressionCatalogErrorV1("non-production expression packaged")
    _unique(expressions, "expression_id", "expression ID")
    _unique(surfaces, "surface_id", "surface ID")
    _unique(families, "family_id", "family ID")
    _unique(terms, "term_id", "term ID")
    _unique(devices, "device_id", "device ID")
    _unique(signatures, "signature_id", "signature ID")
    source_authority_ids = _tuple(data, "source_authority_ids")
    expression_ids = {record.expression_id for record in expressions}
    valid_sources = expression_ids | set(source_authority_ids)
    device_ids = {record.device_id for record in devices}
    if any(surface.source_expression_id not in valid_sources for surface in surfaces):
        raise ExpressionCatalogErrorV1("preferred surface has unknown expression link")
    if any(not family.members for family in families):
        raise ExpressionCatalogErrorV1("productive family has no members")
    if any(
        source not in valid_sources
        for device in devices
        for source in device.source_expression_ids
    ):
        raise ExpressionCatalogErrorV1("device has unknown expression source")
    if any(signature.device_id not in device_ids for signature in signatures):
        raise ExpressionCatalogErrorV1("signature has unknown device link")
    expected = data.get("counts")
    actual = {
        "expressions": len(expressions),
        "preferred_surfaces": len(surfaces),
        "productive_families": len(families),
        "controlled_terms": len(terms),
        "comedy_devices": len(devices),
        "signature_devices": len(signatures),
    }
    if expected != actual:
        raise ExpressionCatalogErrorV1("catalog count integrity failure")
    return ExpressionCatalogV1(
        bundle_version=data["bundle_version"],
        content_sha256=digest,
        expressions=expressions,
        preferred_surfaces=surfaces,
        productive_families=families,
        controlled_terms=terms,
        comedy_devices=devices,
        signature_devices=signatures,
        source_authority_ids=source_authority_ids,
    )
