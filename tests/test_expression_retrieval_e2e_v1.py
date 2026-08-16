from __future__ import annotations

import re

from pastila_scout.expression_retrieval_v1 import (
    EditorialRetrievalContextV1,
    load_catalog_v1,
    retrieve_story_voice_palette_v1,
)
from pastila_scout.expression_retrieval_v1.editor_adapter import (
    serialize_story_voice_palette_v1,
)
from pastila_scout.expression_retrieval_v1.usage import (
    derive_episode_voice_state_v1,
    detect_usage_receipt_v1,
)


def _realize(value: str) -> str:
    return re.sub(r"\{[^{}]+\}", "exemplu", value)


def test_eight_story_offline_composition_chain_and_state_evolution() -> None:
    catalog = load_catalog_v1()
    contexts = (
        EditorialRetrievalContextV1(
            event_id="1",
            title="Primaria cere alt aviz pentru acelasi permis",
            bureaucracy=True,
            topic_tags=("bureaucracy", "absurdity"),
            humor_intensity=3,
        ),
        EditorialRetrievalContextV1(
            event_id="2",
            title="O funcție obținută prin clientelism",
            patronage=True,
            political_context=True,
            keywords=("patronaj", "clientelism"),
        ),
        EditorialRetrievalContextV1(
            event_id="3",
            title="Autoritățile demontează fake news",
            disinformation=True,
            keywords=("fake news", "dezinformare"),
        ),
        EditorialRetrievalContextV1(
            event_id="4",
            title="La Cluj proiectul e fain",
            region="Ardeal",
            keywords=("fain",),
        ),
        EditorialRetrievalContextV1(
            event_id="5",
            title="Șantierul neterminat devine poveste fără sfârșit",
            unfinished_project=True,
            topic_tags=("unfinished_project", "bureaucracy"),
        ),
        EditorialRetrievalContextV1(
            event_id="6",
            title="Scandalul vedetei are un vibe-ul straniu",
            entertainment=True,
            meme_context=True,
            keywords=("vibe-ul", "entertainment"),
        ),
        EditorialRetrievalContextV1(
            event_id="7",
            title="Victime după un accident grav",
            victim_sensitive=True,
            tragedy_sensitive=True,
            raw_eligible=False,
            topic_tags=("tragedy",),
        ),
        EditorialRetrievalContextV1(
            event_id="8",
            title="Un lider suveranist răspunde cu aroganță",
            political_context=True,
            keywords=("suveranist", "arrogance"),
        ),
    )
    receipts = []
    for index, context in enumerate(contexts, 1):
        state = derive_episode_voice_state_v1(receipts)
        palette = retrieve_story_voice_palette_v1(
            catalog=catalog, context=context, episode_state=state
        )
        toolkit = serialize_story_voice_palette_v1(palette)
        assert palette.total_count <= 5
        assert toolkit["usage_instruction"]["optional"] is True
        offered = (
            *palette.expressions,
            *palette.controlled_terms,
            *palette.comedy_devices,
            *palette.signature_devices,
        )
        if index == 7 or not offered:
            output = "Text factual validat fără folosirea instrumentelor oferite."
        else:
            output = _realize(offered[0].display_text)
        receipt = detect_usage_receipt_v1(
            catalog=catalog, palette=palette, validated_story_text=output
        )
        receipts.append(receipt)
        if index == 7:
            assert receipt.raw_usage_count == 0
            assert receipt.expression_ids_used == ()
            assert receipt.controlled_term_ids_used == ()
            assert receipt.device_ids_used == ()
    final_state = derive_episode_voice_state_v1(receipts)
    assert final_state != derive_episode_voice_state_v1(())
    assert len({(item.event_id, item.output_sha256) for item in receipts}) == 8
