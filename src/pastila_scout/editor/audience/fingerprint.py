"""Semantic SHA-256 fingerprints for Audience Model artifacts."""

from __future__ import annotations

import hashlib
import json

from pastila_scout.editor.audience.models import (
    AudienceAssessment,
    AudienceCalibration,
    AudienceModel,
    AudienceProfileGuidance,
)


def _hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _normalize(value: object) -> object:
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        normalized = [_normalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        )
    return value


def _sort_fields(payload: dict, fields: tuple[str, ...]) -> None:
    for field in fields:
        payload[field] = sorted(payload[field])


def audience_model_fingerprint(model: AudienceModel) -> str:
    payload = model.model_dump(mode="json")
    _sort_fields(
        payload,
        (
            "audience_assumptions",
            "excluded_assumptions",
            "default_emotional_policy",
            "fatigue_policy",
            "attention_policy",
            "fixed_boundaries",
        ),
    )
    payload["principles"] = sorted(
        payload["principles"], key=lambda item: item["order"]
    )
    for item in payload["principles"]:
        _sort_fields(item, ("required_behaviors", "prohibited_behaviors"))
    for section in ("knowledge_profile", "cognitive_profile", "trust_profile"):
        for key, value in payload[section].items():
            if isinstance(value, list):
                payload[section][key] = sorted(value)
    return _hash(_normalize(payload))


def calibration_fingerprint(calibration: AudienceCalibration) -> str:
    payload = calibration.model_dump(mode="json")
    _sort_fields(
        payload,
        (
            "attention_priorities",
            "trust_safeguards",
            "fatigue_constraints",
            "episode_specific_overrides",
        ),
    )
    payload["established_profile_guidance"] = sorted(
        payload["established_profile_guidance"], key=lambda item: item["guidance_id"]
    )
    return _hash(_normalize(payload))


def assessment_fingerprint(assessment: AudienceAssessment) -> str:
    payload = assessment.model_dump(mode="json")
    for field in ("attention_risks", "trust_risks", "fatigue_assessments"):
        payload[field] = sorted(
            payload[field], key=lambda item: item.get("risk_id", item.get("fatigue_id"))
        )
    _sort_fields(
        payload,
        ("unresolved_audience_questions", "blocking_issues", "advisory_issues"),
    )
    return _hash(_normalize(payload))


def risk_collection_fingerprint(risks: tuple[object, ...]) -> str:
    payload = [risk.model_dump(mode="json") for risk in risks]
    return _hash(_normalize(payload))


def guidance_collection_fingerprint(
    guidance: tuple[AudienceProfileGuidance, ...],
) -> str:
    payload = [item.model_dump(mode="json") for item in guidance]
    return _hash(_normalize(payload))
