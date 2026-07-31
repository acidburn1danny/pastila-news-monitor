"""Semantic SHA-256 fingerprints for Satirical Voice contracts."""

from __future__ import annotations

import hashlib
import json

from pastila_scout.editor.voice.models import (
    SatiricalOpportunity,
    SatiricalRisk,
    SatiricalVoice,
    SatiricalVoiceCalibration,
)


def _hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _calibration_payload(calibration: SatiricalVoiceCalibration) -> dict:
    payload = calibration.model_dump(mode="json")
    for field in (
        "allowed_mechanisms",
        "disallowed_mechanisms",
        "valid_targets",
        "protected_subjects",
        "required_factual_prerequisites",
        "tonal_constraints",
        "escalation_conditions",
        "editor_review_conditions",
    ):
        payload[field] = sorted(payload[field])
    return payload


def calibration_fingerprint(calibration: SatiricalVoiceCalibration) -> str:
    return _hash(_calibration_payload(calibration))


def voice_fingerprint(voice: SatiricalVoice) -> str:
    payload = voice.model_dump(mode="json")
    payload["characteristics"] = sorted(payload["characteristics"])
    payload["excluded_identities"] = sorted(payload["excluded_identities"])
    payload["fixed_boundaries"] = sorted(payload["fixed_boundaries"])
    payload["principles"] = sorted(payload["principles"], key=lambda x: x["order"])
    for item in payload["principles"]:
        item["required_behaviors"] = sorted(item["required_behaviors"])
        item["prohibited_behaviors"] = sorted(item["prohibited_behaviors"])
    payload["mechanisms"] = sorted(payload["mechanisms"], key=lambda x: x["order"])
    for item in payload["mechanisms"]:
        for field in (
            "appropriate_uses",
            "misuse_risks",
            "factual_prerequisites",
            "tonal_constraints",
        ):
            item[field] = sorted(item[field])
    payload["calibration"] = _calibration_payload(voice.calibration)
    return _hash(payload)


def opportunity_fingerprint(opportunity: SatiricalOpportunity) -> str:
    payload = opportunity.model_dump(mode="json")
    for field in (
        "supported_material_ids",
        "editorial_core_element_ids",
        "decision_ids",
        "risk_ids",
        "supported_mechanisms",
        "factual_basis",
        "prohibited_interpretations",
    ):
        payload[field] = sorted(payload[field])
    return _hash(payload)


def risk_collection_fingerprint(risks: tuple[SatiricalRisk, ...]) -> str:
    payload = []
    for risk in risks:
        item = risk.model_dump(mode="json")
        item["affected_opportunity_ids"] = sorted(item["affected_opportunity_ids"])
        item["affected_material_ids"] = sorted(item["affected_material_ids"])
        payload.append(item)
    return _hash(sorted(payload, key=lambda item: item["risk_id"]))
