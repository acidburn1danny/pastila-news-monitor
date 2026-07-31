"""Order-normalized semantic fingerprints for decision artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from pastila_scout.editor.decision.models import (
    EditorialCore,
    EditorialDecisionPlan,
    EditorialMaterial,
)


def _hash(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _material_payload(material: EditorialMaterial) -> dict:
    payload = material.model_dump(mode="json")
    payload["related_material_ids"] = sorted(payload["related_material_ids"])
    payload["metadata"] = sorted(
        payload["metadata"], key=lambda item: (item["key"], item["value"])
    )
    payload["transformation_evidence"] = sorted(payload["transformation_evidence"])
    return payload


def source_material_fingerprint(materials: Sequence[EditorialMaterial]) -> str:
    """Fingerprint material independent of collection and metadata ordering."""

    return _hash(
        sorted(
            (_material_payload(item) for item in materials),
            key=lambda x: x["material_id"],
        )
    )


def editorial_core_fingerprint(core: EditorialCore) -> str:
    """Fingerprint a core after normalizing evidence-reference collections."""

    payload = core.model_dump(mode="json")
    for field in (
        "what_happened",
        "involved_parties",
        "why_it_matters",
        "consequence",
        "central_tension",
    ):
        payload[field]["material_ids"] = sorted(payload[field]["material_ids"])
    for collection in ("factual_boundaries", "secondary_angles"):
        for item in payload[collection]:
            item["material_ids"] = sorted(item["material_ids"])
        payload[collection] = sorted(
            payload[collection],
            key=lambda item: (item["statement"], item["material_ids"]),
        )
    payload["unresolved_questions"] = sorted(payload["unresolved_questions"])
    return _hash(payload)


def decision_plan_fingerprint(plan: EditorialDecisionPlan) -> str:
    """Fingerprint all semantically meaningful decision-plan content."""

    payload = plan.model_dump(mode="json")
    payload["source_material"] = sorted(
        (_material_payload(item) for item in plan.source_material),
        key=lambda item: item["material_id"],
    )
    for decision in payload["decisions"]:
        for field in (
            "material_ids",
            "evidence",
            "principle_ids",
            "tension_ids",
            "unresolved_dependencies",
        ):
            decision[field] = sorted(decision[field])
    payload["decisions"] = sorted(
        payload["decisions"],
        key=lambda item: (item["stage"], item["rank"], item["decision_id"]),
    )
    for risk in payload["risks"]:
        risk["affected_material_ids"] = sorted(risk["affected_material_ids"])
    payload["risks"] = sorted(payload["risks"], key=lambda item: item["risk_id"])
    for field in (
        "unresolved_questions",
        "blocking_issues",
        "advisory_issues",
    ):
        payload[field] = sorted(payload[field])
    return _hash(payload)
