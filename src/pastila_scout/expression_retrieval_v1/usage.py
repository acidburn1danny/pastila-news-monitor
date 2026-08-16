"""Deterministic local usage receipts and episode-state folding."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import EpisodeVoiceStateV1, ExpressionCatalogV1, StoryVoicePaletteV1

_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_SLOT = re.compile(r"\{[^{}]+\}")


class UsageReceiptV1(BaseModel):
    """Locally verified usage attached to one successfully validated story."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: int = Field(default=1, ge=1, le=1)
    event_id: str = Field(min_length=1)
    output_sha256: str
    catalog_bundle_sha256: str = Field(min_length=1)
    palette_fingerprint: str
    expression_ids_used: tuple[str, ...] = ()
    expression_family_ids_used: tuple[str, ...] = ()
    controlled_term_ids_used: tuple[str, ...] = ()
    device_ids_used: tuple[str, ...] = ()
    device_family_ids_used: tuple[str, ...] = ()
    signature_device_ids_used: tuple[str, ...] = ()
    signature_family_ids_used: tuple[str, ...] = ()
    raw_usage_count: int = Field(default=0, ge=0)
    meme_usage_count: int = Field(default=0, ge=0)
    regional_items_used: tuple[str, ...] = ()
    created_from_successful_output: bool = True

    @field_validator(
        "expression_ids_used",
        "expression_family_ids_used",
        "controlled_term_ids_used",
        "device_ids_used",
        "device_family_ids_used",
        "signature_device_ids_used",
        "signature_family_ids_used",
        "regional_items_used",
    )
    @classmethod
    def stable_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(not item for item in value):
            raise ValueError("usage IDs must be sorted and unique")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> UsageReceiptV1:
        if (
            not _HASH.fullmatch(self.output_sha256)
            or not _HASH.fullmatch(self.palette_fingerprint)
            or self.created_from_successful_output is not True
        ):
            raise ValueError("invalid usage receipt identity")
        return self


def output_sha256_v1(text: str) -> str:
    if type(text) is not str or not text:
        raise ValueError("validated story text is required")
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def palette_fingerprint_v1(
    *, catalog: ExpressionCatalogV1, palette: StoryVoicePaletteV1
) -> str:
    sections = {
        name: [
            {"id": item.authority_id, "text": item.display_text, "family": item.family}
            for item in getattr(palette, name)
        ]
        for name in (
            "expressions",
            "controlled_terms",
            "comedy_devices",
            "signature_devices",
        )
    }
    canonical = json.dumps(
        {
            "catalog": catalog.content_sha256,
            "event_id": palette.event_id,
            "sections": sections,
            "constraints": {
                "optional": True,
                "may_use_none": True,
                "never_force": True,
            },
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _offered(palette: StoryVoicePaletteV1) -> set[str]:
    return {
        item.authority_id
        for values in (
            palette.expressions,
            palette.controlled_terms,
            palette.comedy_devices,
            palette.signature_devices,
        )
        for item in values
    }


def _template_used(template: str, text: str) -> bool:
    template = _normalized(template)
    text = _normalized(text)
    if template == "s-a terminat.":
        return text.rstrip().endswith("s-a terminat.")
    literals = tuple(
        value.strip(" .,;:!?")
        for value in _SLOT.split(template)
        if value.strip(" .,;:!?")
    )
    if not literals:
        return False
    position = 0
    for literal in literals:
        found = text.find(literal, position)
        if found < 0:
            return False
        position = found + len(literal)
    return "{reversal}" not in template or position < len(text.rstrip(" ."))


def detect_usage_receipt_v1(
    *,
    catalog: ExpressionCatalogV1,
    palette: StoryVoicePaletteV1,
    validated_story_text: str,
) -> UsageReceiptV1:
    """Detect only locally verifiable use among tools offered to this story."""
    text = _normalized(validated_story_text)
    offered = _offered(palette)
    expressions = {
        x.expression_id: x for x in catalog.expressions if x.expression_id in offered
    }
    surfaces = {x.source_expression_id: x.surface for x in catalog.preferred_surfaces}
    used_expressions = {
        identity
        for identity, record in expressions.items()
        if _normalized(
            surfaces.get(identity) or record.preferred_surface or record.text
        )
        in text
    }
    controlled = {
        x.term_id: x for x in catalog.controlled_terms if x.term_id in offered
    }
    used_controlled = {
        identity
        for identity, record in controlled.items()
        if _normalized(record.term) in text
    }
    devices = {x.device_id: x for x in catalog.comedy_devices if x.device_id in offered}
    used_devices = {
        identity
        for identity, record in devices.items()
        if _template_used(record.structure, validated_story_text)
    }
    signatures = {
        x.device_id: x for x in catalog.signature_devices if x.device_id in offered
    }
    used_signatures = used_devices & signatures.keys()
    return UsageReceiptV1(
        event_id=palette.event_id,
        output_sha256=output_sha256_v1(validated_story_text),
        catalog_bundle_sha256=catalog.content_sha256,
        palette_fingerprint=palette_fingerprint_v1(catalog=catalog, palette=palette),
        expression_ids_used=tuple(sorted(used_expressions)),
        expression_family_ids_used=tuple(
            sorted(
                {f for i in used_expressions for f in expressions[i].semantic_families}
            )
        ),
        controlled_term_ids_used=tuple(sorted(used_controlled)),
        device_ids_used=tuple(sorted(used_devices)),
        device_family_ids_used=tuple(sorted({devices[i].family for i in used_devices})),
        signature_device_ids_used=tuple(sorted(used_signatures)),
        signature_family_ids_used=tuple(
            sorted({signatures[i].family for i in used_signatures})
        ),
        raw_usage_count=sum(expressions[i].raw for i in used_expressions),
        meme_usage_count=sum(expressions[i].meme for i in used_expressions),
        regional_items_used=tuple(
            sorted(i for i in used_expressions if expressions[i].regionalism)
        ),
    )


def derive_episode_voice_state_v1(
    receipts: Iterable[UsageReceiptV1 | dict[str, object]],
) -> EpisodeVoiceStateV1:
    accepted: list[UsageReceiptV1] = []
    seen: set[tuple[str, str]] = set()
    for value in receipts:
        try:
            receipt = (
                value
                if type(value) is UsageReceiptV1
                else UsageReceiptV1.model_validate_json(
                    json.dumps(value, ensure_ascii=False), strict=True
                )
            )
        except TypeError, ValueError:
            continue
        identity = (receipt.event_id, receipt.output_sha256)
        if identity in seen:
            continue
        seen.add(identity)
        accepted.append(receipt)
    controlled: dict[str, int] = {}
    for receipt in accepted:
        for identity in receipt.controlled_term_ids_used:
            controlled[identity] = controlled.get(identity, 0) + 1
    unique = lambda values: tuple(dict.fromkeys(values))
    return EpisodeVoiceStateV1(
        used_expression_ids=unique(i for r in accepted for i in r.expression_ids_used),
        used_expression_families=unique(
            i for r in accepted for i in r.expression_family_ids_used
        ),
        used_device_ids=unique(i for r in accepted for i in r.device_ids_used),
        used_device_families=unique(
            i for r in accepted for i in r.device_family_ids_used
        ),
        used_signature_families=unique(
            i for r in accepted for i in r.signature_family_ids_used
        ),
        raw_usage_count=sum(r.raw_usage_count for r in accepted),
        meme_usage_count=sum(r.meme_usage_count for r in accepted),
        regional_usage=unique(i for r in accepted for i in r.regional_items_used),
        controlled_term_usage=tuple(sorted(controlled.items())),
    )


def load_committed_usage_receipts_v1(
    materials: Iterable[tuple[str | None, str | None]],
) -> tuple[UsageReceiptV1, ...]:
    """Read trusted receipts from atomically committed Editor artifacts."""
    result: list[UsageReceiptV1] = []
    for path_value, expected_hash in materials:
        try:
            if type(path_value) is not str or type(expected_hash) is not str:
                continue
            payload = Path(path_value).read_bytes()
            envelope = json.loads(payload.decode("utf-8"))
            if envelope.get("payload_sha256") != expected_hash:
                continue
            envelope["payload_sha256"] = ""
            canonical = (
                json.dumps(
                    envelope,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n"
            )
            if "sha256:" + hashlib.sha256(canonical).hexdigest() != expected_hash:
                continue
            values = envelope["operational_result"]["draft"].get("usage_receipts", ())
            result.extend(
                UsageReceiptV1.model_validate_json(
                    json.dumps(item, ensure_ascii=False), strict=True
                )
                for item in values
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            continue
    return tuple(result)


__all__ = (
    "UsageReceiptV1",
    "derive_episode_voice_state_v1",
    "detect_usage_receipt_v1",
    "load_committed_usage_receipts_v1",
    "output_sha256_v1",
    "palette_fingerprint_v1",
)
