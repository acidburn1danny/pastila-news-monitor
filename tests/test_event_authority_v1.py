from types import SimpleNamespace

import pastila_scout.event_authority_v1 as authority
from pastila_scout.editor.generation.controlled_generator import _event_approved_facts
from pastila_scout.editor.generation.state import EpisodeGenerationState
from pastila_scout.editor.generation.validation import validate_closing
from pastila_scout.event_authority_v1 import build_event_authority_bundle


def _article(
    article_id,
    source_id,
    summary,
    *,
    title="Titlu factual",
    source_name=None,
    published_at="2026-08-21T10:00:00+00:00",
):
    return SimpleNamespace(
        id=article_id,
        source_id=source_id,
        source_name=source_name or source_id.upper(),
        url=f"https://example.test/{article_id}",
        title=title,
        summary=summary,
        published_at=published_at,
    )


def test_one_source_cleans_html_entities_boilerplate_and_marks_truncation():
    bundle = build_event_authority_bundle(
        event_id=7,
        canonical_article_id=11,
        articles=(
            _article(
                11,
                "sursa",
                "<p>Reţeaua are aproape 100 de ani. &#8222;Lucrările continuă [&#8230;]</p><p>&copy; Exemplu.ro.</p>",
            ),
        ),
    )

    assert len(bundle.segments) == 1
    assert bundle.segments[0].canonical is True
    assert bundle.segments[0].truncated is True
    assert "<p>" not in bundle.segments[0].summary
    assert "&#8222;" not in bundle.segments[0].summary
    assert "Exemplu.ro" not in bundle.segments[0].summary


def test_romaniatv_feed_footer_is_removed_without_changing_factual_text():
    factual = "Filmul a câștigat Leopardul de Aur la Festivalul de la Locarno."
    bundle = build_event_authority_bundle(
        event_id=2346,
        canonical_article_id=11,
        articles=(
            _article(
                11,
                "romaniatv",
                factual
                + " Articolul Florin Șerban a câștigat Leopardul de Aur apare prima dată în Romania TV .",
                source_name="RomaniaTV",
            ),
        ),
    )

    assert bundle.segments[0].summary == factual
    assert bundle.segments[0].truncated is False


def test_romaniatv_phrase_inside_factual_text_is_not_removed():
    factual = "Articolul apare prima dată în arhiva instituției, potrivit Romania TV."
    bundle = build_event_authority_bundle(
        event_id=2347,
        canonical_article_id=12,
        articles=(_article(12, "romaniatv", factual, source_name="RomaniaTV"),),
    )

    assert bundle.segments[0].summary == factual


def test_repeated_source_and_exact_duplicate_authority_are_not_repeated():
    bundle = build_event_authority_bundle(
        event_id=7,
        canonical_article_id=11,
        articles=(
            _article(11, "a", "Acelaşi fapt."),
            _article(12, "a", "Alt articol al aceleiaşi surse."),
            _article(13, "b", "Acelaşi fapt."),
        ),
    )

    assert tuple(item.source_id for item in bundle.segments) == ("a",)
    assert bundle.omitted_source_ids == ("b",)


def test_complementary_and_conflicting_qualifications_remain_separate():
    bundle = build_event_authority_bundle(
        event_id=7,
        canonical_article_id=11,
        articles=(
            _article(11, "a", "Instituţia a anunţat măsura."),
            _article(12, "b", "Lucrările sunt programate pentru luni."),
            _article(13, "c", "Lucrările ar putea începe luni."),
        ),
    )

    assert tuple(item.source_id for item in bundle.segments) == ("a", "b", "c")
    assert bundle.segments[1].summary != bundle.segments[2].summary


def test_budget_omits_whole_supporting_segment_without_truncating_unique_text(
    monkeypatch,
):
    monkeypatch.setattr(authority, "MAX_MODEL_VISIBLE_AUTHORITY_CHARACTERS", 45)
    canonical = _article(11, "a", "Fapt canonic complet.", title="Titlu")
    supporting = _article(
        12, "b", "Fapt suplimentar unic şi complet.", title="Alt titlu"
    )

    bundle = build_event_authority_bundle(
        event_id=7,
        canonical_article_id=11,
        articles=(canonical, supporting),
    )

    assert bundle.segments[0].summary == "Fapt canonic complet."
    assert bundle.omitted_source_ids == ("b",)


def test_closing_gate_rejects_mechanical_story_stitch_but_accepts_new_sentence():
    state = EpisodeGenerationState().accept_story(
        "story-01",
        SimpleNamespace(
            story_id=2238,
            factual_summary="Primăria Capitalei modernizează reţeaua de canalizare",
            ending="o vechime de aproape 100 de ani.",
            generated_callback_anchors=(),
            used_humor_mechanisms=(),
            used_expression_families=(),
            used_reference_families=(),
            used_vocatives=0,
            profanity_usage=0,
            rhetorical_question_functions=(),
            ending_type="completed",
            warnings=(),
        ),
    )
    context = SimpleNamespace(available_callback_anchors=())
    malformed = SimpleNamespace(
        text="Primăria Capitalei modernizează reţeaua de canalizare o vechime de aproape 100 de ani.",
        callback_executions=(),
    )
    valid = SimpleNamespace(
        text="Lucrările vizează o reţea veche de aproape 100 de ani.",
        callback_executions=(),
    )

    assert (
        "closing_mechanical_story_stitch"
        in validate_closing(malformed, context, state).errors
    )
    assert validate_closing(valid, context, state).accepted is True


def test_bundle_becomes_separate_source_facts_and_category_stays_sidecar_only():
    bundle = build_event_authority_bundle(
        event_id=7,
        canonical_article_id=11,
        articles=(
            _article(11, "a", "Fapt canonic."),
            _article(12, "b", "Fapt complementar."),
        ),
    )
    event = SimpleNamespace(
        event_id=7,
        canonical_title="Titlu",
        canonical_summary="Rezumat",
        categories=("Politica",),
        event_authority_bundle=bundle,
    )

    facts = _event_approved_facts(event)

    assert len(facts) == 2
    assert {item.field for item in facts} == {"event_source_authority"}
    assert "Sursa: A" in facts[0].value
    assert "Sursa: B" in facts[1].value
    assert all("Politica" not in item.value for item in facts)


def test_historical_handoff_falls_back_to_canonical_authority_without_category():
    event = SimpleNamespace(
        event_id=7,
        canonical_title="Titlu",
        canonical_summary="Rezumat",
        categories=("Politica",),
        event_authority_bundle=None,
    )

    facts = _event_approved_facts(event)

    assert tuple(item.field for item in facts) == (
        "canonical_title",
        "canonical_summary",
    )
