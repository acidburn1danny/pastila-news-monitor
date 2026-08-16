from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.expression_retrieval_v1 import (
    EditorialRetrievalContextV1,
    EpisodeVoiceStateV1,
    load_catalog_v1,
    retrieve_story_voice_palette_v1,
)
from pastila_scout.expression_retrieval_v1.models import (
    PaletteItemReasonV1,
    PaletteItemV1,
    StoryVoicePaletteV1,
)
from pastila_scout.expression_retrieval_v1.usage import (
    UsageReceiptV1,
    derive_episode_voice_state_v1,
    detect_usage_receipt_v1,
    load_committed_usage_receipts_v1,
    output_sha256_v1,
    palette_fingerprint_v1,
)


def _item(identity: str, text: str, family: str) -> PaletteItemV1:
    return PaletteItemV1(
        identity,
        text,
        family,
        PaletteItemReasonV1(("test",), (("test", 1),), 1),
    )


def _receipt(**changes: object) -> UsageReceiptV1:
    values = {
        "event_id": "1",
        "output_sha256": "sha256:" + "1" * 64,
        "catalog_bundle_sha256": load_catalog_v1().content_sha256,
        "palette_fingerprint": "sha256:" + "2" * 64,
    }
    values.update(changes)
    return UsageReceiptV1(**values)


def test_exact_expression_use_is_detected_but_offered_absence_is_not() -> None:
    catalog = load_catalog_v1()
    record = next(
        item for item in catalog.expressions if not item.raw and not item.regionalism
    )
    surface = next(
        (
            item.surface
            for item in catalog.preferred_surfaces
            if item.source_expression_id == record.expression_id
        ),
        record.preferred_surface or record.text,
    )
    palette = StoryVoicePaletteV1(
        "1",
        expressions=(
            _item(record.expression_id, surface, record.semantic_families[0]),
        ),
    )
    used = detect_usage_receipt_v1(
        catalog=catalog,
        palette=palette,
        validated_story_text=f"Context. {surface} Final.",
    )
    absent = detect_usage_receipt_v1(
        catalog=catalog,
        palette=palette,
        validated_story_text="Text fara expresia oferita.",
    )
    assert used.expression_ids_used == (record.expression_id,)
    assert used.expression_family_ids_used == tuple(sorted(record.semantic_families))
    assert absent.expression_ids_used == ()


def test_controlled_term_requires_exact_offered_occurrence() -> None:
    catalog = load_catalog_v1()
    term = next(item for item in catalog.controlled_terms if item.term == "fake news")
    palette = StoryVoicePaletteV1(
        "2", controlled_terms=(_item(term.term_id, term.term, term.domains[0]),)
    )
    assert detect_usage_receipt_v1(
        catalog=catalog,
        palette=palette,
        validated_story_text="Este fake news, explicit.",
    ).controlled_term_ids_used == (term.term_id,)
    assert (
        detect_usage_receipt_v1(
            catalog=catalog,
            palette=palette,
            validated_story_text="Este o informatie falsa.",
        ).controlled_term_ids_used
        == ()
    )


def test_device_and_signature_templates_are_local_and_conservative() -> None:
    catalog = load_catalog_v1()
    legend = next(
        item
        for item in catalog.comedy_devices
        if item.device_id.endswith("legenda-spune")
    )
    signature = next(
        item
        for item in catalog.comedy_devices
        if item.device_id.endswith("mare-clasic")
    )
    closing = next(
        item
        for item in catalog.comedy_devices
        if item.device_id.endswith("s-a-terminat")
    )
    palette = StoryVoicePaletteV1(
        "3",
        comedy_devices=(
            _item(legend.device_id, legend.structure, legend.family),
            _item(closing.device_id, closing.structure, closing.family),
        ),
        signature_devices=(
            _item(signature.device_id, signature.structure, signature.family),
        ),
    )
    receipt = detect_usage_receipt_v1(
        catalog=catalog,
        palette=palette,
        validated_story_text=(
            "Legenda spune ca birocratia doarme. Cum zicea un mare clasic in viata... "
            "Aici se termina ideea, dar nu cu formula oferita."
        ),
    )
    assert (
        legend.device_id not in receipt.device_ids_used
    )  # diacritics are not invented
    assert signature.device_id not in receipt.signature_device_ids_used
    assert closing.device_id not in receipt.device_ids_used
    exact = detect_usage_receipt_v1(
        catalog=catalog,
        palette=palette,
        validated_story_text="Legenda spune că povestea continuă. Cum zicea un mare clasic în viață...",
    )
    assert legend.device_id in exact.device_ids_used
    assert signature.device_id in exact.signature_device_ids_used


def test_raw_meme_and_regional_counts_require_verified_use() -> None:
    catalog = load_catalog_v1()
    records = (
        next(item for item in catalog.expressions if item.raw),
        next(item for item in catalog.expressions if item.meme),
        next(item for item in catalog.expressions if item.regionalism),
    )
    palette = StoryVoicePaletteV1(
        "4",
        expressions=tuple(
            _item(
                item.expression_id,
                item.preferred_surface or item.text,
                item.semantic_families[0],
            )
            for item in records
        ),
    )
    text = " ".join(item.preferred_surface or item.text for item in records)
    receipt = detect_usage_receipt_v1(
        catalog=catalog, palette=palette, validated_story_text=text
    )
    assert receipt.raw_usage_count >= 1
    assert receipt.meme_usage_count >= 1
    assert receipt.regional_items_used == (records[2].expression_id,)


def test_hashes_and_receipt_json_are_deterministic() -> None:
    catalog = load_catalog_v1()
    palette = StoryVoicePaletteV1.empty("5")
    assert output_sha256_v1("text") == output_sha256_v1("text")
    assert output_sha256_v1("text") != output_sha256_v1("text\n")
    assert palette_fingerprint_v1(
        catalog=catalog, palette=palette
    ) == palette_fingerprint_v1(catalog=catalog, palette=palette)
    receipt = detect_usage_receipt_v1(
        catalog=catalog, palette=palette, validated_story_text="text"
    )
    assert (
        UsageReceiptV1.model_validate_json(receipt.model_dump_json(), strict=True)
        == receipt
    )


def test_state_fold_deduplicates_and_skips_malformed_legacy_values() -> None:
    first = _receipt(
        expression_ids_used=("expression:a",),
        expression_family_ids_used=("family:a",),
        controlled_term_ids_used=("term:a",),
        raw_usage_count=1,
    )
    second = _receipt(
        event_id="2",
        output_sha256="sha256:" + "3" * 64,
        device_ids_used=("device:a",),
        device_family_ids_used=("device-family:a",),
        signature_family_ids_used=("signature:a",),
        meme_usage_count=1,
        regional_items_used=("expression:regional",),
    )
    state = derive_episode_voice_state_v1((first, first, {"bad": "legacy"}, second))
    assert state.used_expression_ids == ("expression:a",)
    assert state.used_device_ids == ("device:a",)
    assert state.raw_usage_count == state.meme_usage_count == 1
    assert state.controlled_term_usage == (("term:a", 1),)


def test_six_story_episode_state_evolves_only_after_committed_receipts() -> None:
    receipts = tuple(
        _receipt(
            event_id=str(index),
            output_sha256="sha256:" + f"{index:x}" * 64,
            expression_ids_used=((f"expression:{index}",) if index in {1, 5} else ()),
            expression_family_ids_used=(("idiom",) if index in {1, 5} else ()),
            device_ids_used=((f"device:{index}",) if index in {3, 4} else ()),
            device_family_ids_used=(("hagism",) if index in {3, 4} else ()),
            signature_family_ids_used=(("signature",) if index == 6 else ()),
            raw_usage_count=int(index == 5),
            meme_usage_count=int(index == 6),
        )
        for index in range(1, 7)
    )
    states = tuple(
        derive_episode_voice_state_v1(receipts[:count]) for count in range(7)
    )
    assert states[0] == EpisodeVoiceStateV1()
    assert states[1].used_expression_ids == ("expression:1",)
    assert states[2] == states[1]
    assert states[3].used_device_families == ("hagism",)
    assert states[4].used_device_ids == ("device:3", "device:4")
    assert states[5].raw_usage_count == 1
    assert states[6].meme_usage_count == 1
    assert states[6].used_signature_families == ("signature",)


def test_committed_artifact_loader_checks_payload_hash_and_legacy(
    tmp_path: Path,
) -> None:
    receipt = _receipt()
    envelope = {
        "operational_result": {
            "draft": {"usage_receipts": [receipt.model_dump(mode="json")]}
        },
        "payload_sha256": "",
    }
    canonical = (
        json.dumps(
            envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        + b"\n"
    )
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    envelope["payload_sha256"] = digest
    payload = (
        json.dumps(
            envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        + b"\n"
    )
    path = tmp_path / "material.json"
    path.write_bytes(payload)
    assert load_committed_usage_receipts_v1(((str(path), digest),)) == (receipt,)
    assert load_committed_usage_receipts_v1(((str(path), "sha256:" + "0" * 64),)) == ()
    legacy = tmp_path / "legacy.json"
    legacy_envelope = {"operational_result": {"draft": {}}, "payload_sha256": ""}
    legacy_canonical = (
        json.dumps(legacy_envelope, sort_keys=True, separators=(",", ":")).encode()
        + b"\n"
    )
    legacy_hash = "sha256:" + hashlib.sha256(legacy_canonical).hexdigest()
    legacy_envelope["payload_sha256"] = legacy_hash
    legacy_payload = (
        json.dumps(legacy_envelope, sort_keys=True, separators=(",", ":")).encode()
        + b"\n"
    )
    legacy.write_bytes(legacy_payload)
    assert load_committed_usage_receipts_v1(((str(legacy), legacy_hash),)) == ()


def test_actual_use_changes_next_story_retrieval_but_offering_does_not() -> None:
    catalog = load_catalog_v1()
    record = next(
        item for item in catalog.expressions if not item.raw and not item.regionalism
    )
    context = EditorialRetrievalContextV1(
        event_id="next",
        title=record.text,
        keywords=record.semantic_families,
    )
    offered = retrieve_story_voice_palette_v1(
        catalog=catalog, context=context, episode_state=EpisodeVoiceStateV1()
    )
    if record.expression_id not in {item.authority_id for item in offered.expressions}:
        record = next(
            item
            for item in catalog.expressions
            if item.expression_id == offered.expressions[0].authority_id
        )
    surface = record.preferred_surface or record.text
    palette = StoryVoicePaletteV1(
        "prior",
        expressions=(
            _item(record.expression_id, surface, record.semantic_families[0]),
        ),
    )
    used = detect_usage_receipt_v1(
        catalog=catalog, palette=palette, validated_story_text=surface
    )
    absent = detect_usage_receipt_v1(
        catalog=catalog, palette=palette, validated_story_text="nimic"
    )
    used_state = derive_episode_voice_state_v1((used,))
    absent_state = derive_episode_voice_state_v1((absent,))
    used_next = retrieve_story_voice_palette_v1(
        catalog=catalog, context=context, episode_state=used_state
    )
    absent_next = retrieve_story_voice_palette_v1(
        catalog=catalog, context=context, episode_state=absent_state
    )
    assert record.expression_id not in {
        item.authority_id for item in used_next.expressions
    }
    assert record.expression_id in {
        item.authority_id for item in absent_next.expressions
    }
