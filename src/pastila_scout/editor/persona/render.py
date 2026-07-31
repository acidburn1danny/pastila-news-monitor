"""Canonical rendering and semantic identity for Editorial Persona."""

from __future__ import annotations

import hashlib
import json

from pastila_scout.editor.persona.models import EditorialPersona
from pastila_scout.editor.persona.validator import validate_persona


def _canonical_payload(persona: EditorialPersona) -> dict:
    payload = persona.model_dump(mode="json")
    payload["authority_hierarchy"] = sorted(
        payload["authority_hierarchy"], key=lambda item: item["rank"]
    )
    payload["responsibilities"] = sorted(payload["responsibilities"])
    payload["boundaries"] = sorted(payload["boundaries"], key=lambda item: item["kind"])
    payload["identity"]["capabilities"] = sorted(payload["identity"]["capabilities"])
    payload["identity"]["excluded_identities"] = sorted(
        payload["identity"]["excluded_identities"]
    )
    payload["mission"]["objectives"] = sorted(payload["mission"]["objectives"])
    philosophy = payload["philosophy"]
    philosophy["principles"] = sorted(
        philosophy["principles"], key=lambda item: item["order"]
    )
    for principle in philosophy["principles"]:
        principle["required_behaviors"] = sorted(principle["required_behaviors"])
        principle["prohibited_behaviors"] = sorted(principle["prohibited_behaviors"])
    philosophy["tensions"] = sorted(
        philosophy["tensions"], key=lambda item: item["order"]
    )
    return payload


def persona_fingerprint(persona: EditorialPersona) -> str:
    """Return an order-normalized SHA-256 fingerprint of Persona semantics."""

    validate_persona(persona)
    data = json.dumps(
        _canonical_payload(persona),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values]


def render_persona(persona: EditorialPersona) -> str:
    """Render stable, prompt-ready Persona identity without style instructions."""

    validate_persona(persona)
    payload = _canonical_payload(persona)
    identity = payload["identity"]
    mission = payload["mission"]
    philosophy = payload["philosophy"]
    philosophy_lines = [
        f"Philosophy ID: {philosophy['philosophy_id']}",
        f"Version: {philosophy['version']}",
        "Principles:",
    ]
    for principle in philosophy["principles"]:
        philosophy_lines.extend(
            (
                (
                    f"{principle['order']}. {principle['title']} "
                    f"[{principle['priority']}]"
                ),
                f"   Statement: {principle['statement']}",
                f"   Rationale: {principle['rationale']}",
                "   Required behaviors:",
                *[f"   - {item}" for item in principle["required_behaviors"]],
                "   Prohibited behaviors:",
                *[f"   - {item}" for item in principle["prohibited_behaviors"]],
            )
        )
    philosophy_lines.append("Editorial tensions:")
    for tension in philosophy["tensions"]:
        philosophy_lines.extend(
            (
                (
                    f"{tension['order']}. {tension['first_value']} versus "
                    f"{tension['second_value']} ({tension['tension_id']})"
                ),
                f"   Default: {tension['default_resolution']}",
                f"   Hard boundary: {tension['hard_boundary']}",
                f"   Override authority: {tension['override_authority']}",
            )
        )
    lines = [
        "[Editorial Persona]",
        "",
        "Identity",
        f"Persona ID: {payload['persona_id']}",
        f"Version: {payload['version']}",
        f"Title: {payload['title']}",
        f"Jurisdiction: {payload['jurisdiction']}",
        f"Project: {payload['project']}",
        f"Role: {identity['professional_role']}",
        f"Context: {identity['editorial_context']}",
        "Capabilities:",
        *_bullets(identity["capabilities"]),
        "Excluded identities:",
        *_bullets(identity["excluded_identities"]),
        "",
        "Mission",
        mission["statement"],
        "Objectives:",
        *_bullets(mission["objectives"]),
        "",
        "Editorial Philosophy",
        *philosophy_lines,
        "",
        "Authority",
        *[
            f"{item['rank']}. {item['authority']}: {item['description']}"
            for item in payload["authority_hierarchy"]
        ],
        "",
        "Responsibilities",
        *_bullets(payload["responsibilities"]),
        "",
        "Boundaries",
        *_bullets([item["statement"] for item in payload["boundaries"]]),
        "",
        "Relationship with Editor-in-Chief",
        payload["editor_in_chief_relationship"]["statement"],
        "",
        "Relationship with Editorial Memory",
        payload["editorial_memory_relationship"]["statement"],
        "",
        "Relationship with Editorial Profile",
        payload["editorial_profile_relationship"]["statement"],
    ]
    return "\n".join(lines) + "\n"
