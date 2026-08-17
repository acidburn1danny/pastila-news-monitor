from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.expression_retrieval_v1 import (
    ControlledTermUsageRoleV1,
    EditorialRetrievalContextV1,
    EpisodeVoiceStateV1,
    ExpressionCatalogErrorV1,
    StoryComedyBudgetV1,
    controlled_term_usage_role_v1,
    load_catalog_v1,
    reset_catalog_cache_v1,
    retrieve_story_voice_palette_v1,
    retrieve_story_voice_palette_with_trace_v1,
    story_comedy_budget_v1,
)
from pastila_scout.expression_retrieval_v1.editor_adapter import (
    serialize_story_voice_palette_v1,
)
from pastila_scout.expression_retrieval_v1.models import (
    ExpressionCatalogV1,
    PaletteItemReasonV1,
    PaletteItemV1,
    StoryVoicePaletteV1,
)
from pastila_scout.expression_retrieval_v1.usage import detect_usage_receipt_v1

CATALOG_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "pastila_scout"
    / "resources"
    / "expression_retrieval_v1"
    / "catalog.json"
)


def _catalog_json() -> dict[str, object]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _write_catalog(tmp_path: Path, data: dict[str, object]) -> Path:
    data.pop("bundle_content_sha256", None)
    canonical = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    data["bundle_content_sha256"] = hashlib.sha256(canonical).hexdigest()
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _context(**changes: object) -> EditorialRetrievalContextV1:
    values = {"event_id": "event-1", "title": ""}
    values.update(changes)
    return EditorialRetrievalContextV1(**values)  # type: ignore[arg-type]


def _ids(palette: object) -> set[str]:
    return {
        item.authority_id
        for section in (
            palette.expressions,
            palette.controlled_terms,
            palette.comedy_devices,
            palette.signature_devices,
        )
        for item in section
    }


def test_template_device_projection_exposes_semantics_without_brace_placeholder() -> (
    None
):
    reason = PaletteItemReasonV1((), (), 0)
    palette = StoryVoicePaletteV1(
        event_id="event-1",
        comedy_devices=(
            PaletteItemV1(
                "promotion-v2:device:dus-rece",
                "{AȘTEPTARE}; realitatea: duș rece.",
                "dus-rece",
                reason,
            ),
        ),
    )

    projected = serialize_story_voice_palette_v1(palette)
    device = projected["comedy_devices"][0]

    assert "text" not in device
    assert device["template_parts"] == ("", "; realitatea: duș rece.")
    assert device["slots"] == ("AȘTEPTARE",)
    assert "{AȘTEPTARE}" not in json.dumps(device, ensure_ascii=False)
    assert all("{" not in part and "}" not in part for part in device["template_parts"])
    assert device["affordance"] == "dus-rece"


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"comedy_disabled": True}, StoryComedyBudgetV1.DISABLED),
        ({"victim_sensitive": True}, StoryComedyBudgetV1.DISABLED),
        ({"humor_intensity": 1}, StoryComedyBudgetV1.LOW),
        ({"humor_intensity": 2}, StoryComedyBudgetV1.NORMAL),
        ({"humor_intensity": 3}, StoryComedyBudgetV1.HIGH),
    ],
)
def test_story_comedy_budget_is_derived_from_authoritative_context(
    changes: dict[str, object], expected: StoryComedyBudgetV1
) -> None:
    assert story_comedy_budget_v1(_context(**changes)) is expected


def test_sparse_policy_returns_no_weak_match_and_one_strong_primary() -> None:
    catalog = load_catalog_v1()
    weak = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title="Biblioteca prelungeste programul de weekend",
            summary="Programul creste cu doua ore.",
            humor_intensity=1,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )
    strong_record = next(
        item for item in catalog.expressions if not item.raw and not item.regionalism
    )
    strong = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title=strong_record.text, humor_intensity=2),
        episode_state=EpisodeVoiceStateV1(),
    )

    assert weak.total_count == 0
    assert len(strong.expressions) == 1
    assert strong.total_count == 1


def test_disabled_budget_hides_comedy_but_keeps_factual_controlled_term() -> None:
    catalog = load_catalog_v1()
    palette = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title="Autoritatea dezminte fake news",
            disinformation=True,
            comedy_disabled=True,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )

    assert palette.expressions == ()
    assert palette.comedy_devices == ()
    assert palette.signature_devices == ()
    assert tuple(item.display_text for item in palette.controlled_terms) == (
        "fake news",
    )


def test_only_primary_comedy_tool_is_visible_and_alternates_remain_in_trace() -> None:
    catalog = load_catalog_v1()
    context = _context(
        title="Santier neterminat, o poveste fara sfarsit",
        topic_tags=("unfinished_project", "bureaucracy"),
        unfinished_project=True,
        humor_intensity=3,
    )
    palette, trace = retrieve_story_voice_palette_with_trace_v1(
        catalog=catalog,
        context=context,
        episode_state=EpisodeVoiceStateV1(),
    )
    visible_comedy = (
        *palette.expressions,
        *palette.comedy_devices,
        *palette.signature_devices,
    )

    assert len(visible_comedy) == 1
    assert len(tuple(item for item in trace.items if item.selected)) > 1


def test_controlled_term_roles_derive_from_frozen_metadata() -> None:
    catalog = load_catalog_v1()
    roles = {
        item.term: controlled_term_usage_role_v1(item)
        for item in catalog.controlled_terms
    }

    assert roles["vibe-ul"] is ControlledTermUsageRoleV1.DECORATIVE_CONTEXT
    assert roles["fake news"] is ControlledTermUsageRoleV1.FACTUAL_CONTEXT
    assert all(
        roles[term] is ControlledTermUsageRoleV1.FACTUAL_CONTEXT
        for term in ("suveranist", "pesedaurii", "pesedizat")
    )


def test_entertainment_device_suppresses_decorative_vibe_from_visible_palette() -> None:
    catalog = load_catalog_v1()
    palette, trace = retrieve_story_voice_palette_with_trace_v1(
        catalog=catalog,
        context=_context(
            title="Influencerul transforma despartirea in promovare",
            categories=("CanCan",),
            entertainment=True,
            meme_context=True,
            humor_intensity=3,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )

    assert tuple(item.display_text for item in palette.comedy_devices) == (
        "Absolut {cadru/eveniment}.",
    )
    assert palette.controlled_terms == ()
    vibe_trace = next(
        item for item in trace.items if item.authority_id.endswith("vibe-ul")
    )
    assert vibe_trace.selected is False
    assert vibe_trace.reason_codes == (
        "decorative_controlled_term_mutually_exclusive_with_comedy_tool",
    )


def test_decorative_vibe_is_visible_alone_but_suppressed_by_expression_or_signature() -> (
    None
):
    catalog = load_catalog_v1()
    vibe_only_catalog = replace(catalog, comedy_devices=(), signature_devices=())
    vibe_only = retrieve_story_voice_palette_v1(
        catalog=vibe_only_catalog,
        context=_context(title="vibe-ul", meme_context=True, humor_intensity=1),
        episode_state=EpisodeVoiceStateV1(),
    )
    expression = next(
        item for item in catalog.expressions if not item.raw and not item.regionalism
    )
    expression_catalog = replace(catalog, comedy_devices=(), signature_devices=())
    with_expression = retrieve_story_voice_palette_v1(
        catalog=expression_catalog,
        context=_context(
            title=f"{expression.text} vibe-ul",
            meme_context=True,
            humor_intensity=2,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )
    signature = next(item for item in catalog.comedy_devices if item.signature_capable)
    signature_catalog = replace(catalog, comedy_devices=(signature,))
    with_signature = retrieve_story_voice_palette_v1(
        catalog=signature_catalog,
        context=_context(
            title="vibe-ul",
            topic_tags=("signature_context",),
            meme_context=True,
            humor_intensity=2,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )

    assert tuple(item.display_text for item in vibe_only.controlled_terms) == (
        "vibe-ul",
    )
    assert len(with_expression.expressions) == 1
    assert with_expression.controlled_terms == ()
    assert len(with_signature.signature_devices) == 1
    assert with_signature.controlled_terms == ()


@pytest.mark.parametrize(
    ("term", "changes"),
    [
        ("fake news", {"disinformation": True}),
    ],
)
def test_factual_controlled_term_may_coexist_with_comedy_device(
    term: str, changes: dict[str, object]
) -> None:
    catalog = load_catalog_v1()
    palette = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title=term,
            topic_tags=("unfinished_project",),
            unfinished_project=True,
            humor_intensity=3,
            **changes,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )

    assert len(palette.comedy_devices) == 1
    assert tuple(item.display_text for item in palette.controlled_terms) == (term,)


def test_suppressed_decorative_term_is_not_offered_or_receipted() -> None:
    catalog = load_catalog_v1()
    palette = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title="Influencerul are vibe-ul unei reclame",
            entertainment=True,
            meme_context=True,
            humor_intensity=3,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )
    receipt = detect_usage_receipt_v1(
        catalog=catalog,
        palette=palette,
        validated_story_text="Vibe-ul exista doar coincidental in text.",
    )

    assert palette.controlled_terms == ()
    assert receipt.controlled_term_ids_used == ()


def test_catalog_loads_as_packaged_resource_and_is_cached() -> None:
    reset_catalog_cache_v1()
    first = load_catalog_v1()
    second = load_catalog_v1()
    assert first is second
    assert len(first.expressions) == 102
    assert len(first.preferred_surfaces) == 11
    assert len(first.productive_families) == 4
    assert len(first.controlled_terms) == 5
    assert len(first.comedy_devices) == 14
    assert len(first.signature_devices) == 3


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.__setitem__("corpus_schema_version", 2), "unsupported"),
        (lambda data: data["expressions"][0].pop("text"), "invalid catalog field"),
        (
            lambda data: data["expressions"].append(dict(data["expressions"][0])),
            "duplicate expression ID",
        ),
        (
            lambda data: data["preferred_surfaces"][0].__setitem__(
                "source_expression_id", "missing"
            ),
            "unknown expression link",
        ),
        (
            lambda data: data["productive_families"][0].__setitem__("members", []),
            "no members",
        ),
        (
            lambda data: data["comedy_devices"][0].__setitem__(
                "source_expression_ids", ["missing"]
            ),
            "unknown expression source",
        ),
        (
            lambda data: data["expressions"][0].__setitem__(
                "owner_class", "REJECT_EDITOR"
            ),
            "non-production expression",
        ),
        (
            lambda data: data["expressions"][0].__setitem__(
                "owner_class", "DEFER_PROMOTION"
            ),
            "non-production expression",
        ),
    ],
)
def test_catalog_rejects_invalid_content(
    tmp_path: Path, mutation: object, message: str
) -> None:
    data = _catalog_json()
    mutation(data)  # type: ignore[operator]
    counts = data["counts"]
    counts["expressions"] = len(data["expressions"])
    path = _write_catalog(tmp_path, data)
    with pytest.raises(ExpressionCatalogErrorV1, match=message):
        load_catalog_v1(path, use_cache=False)


def test_catalog_rejects_bad_integrity(tmp_path: Path) -> None:
    data = _catalog_json()
    data["bundle_content_sha256"] = "0" * 64
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ExpressionCatalogErrorV1, match="integrity"):
        load_catalog_v1(path, use_cache=False)


def test_no_match_returns_empty_palette() -> None:
    palette = retrieve_story_voice_palette_v1(
        catalog=load_catalog_v1(),
        context=_context(title="qzxw unknown token"),
        episode_state=EpisodeVoiceStateV1(),
    )
    assert palette.total_count == 0


def test_semantic_and_keyword_matching_is_deterministic() -> None:
    catalog = load_catalog_v1()
    context = _context(
        title="Un proiect terminat cu un duș rece", topic_tags=("contrast",)
    )
    first = retrieve_story_voice_palette_v1(
        catalog=catalog, context=context, episode_state=EpisodeVoiceStateV1()
    )
    second = retrieve_story_voice_palette_v1(
        catalog=catalog, context=context, episode_state=EpisodeVoiceStateV1()
    )
    assert first == second
    assert first.total_count <= 5
    assert len(first.expressions) <= 3
    assert (
        len(first.controlled_terms)
        + len(first.comedy_devices)
        + len(first.signature_devices)
        <= 2
    )


def test_preferred_surface_is_returned() -> None:
    catalog = load_catalog_v1()
    surface = next(
        item
        for item in catalog.preferred_surfaces
        if any(
            expression.expression_id == item.source_expression_id
            for expression in catalog.expressions
        )
    )
    source_id = surface.source_expression_id
    source = next(
        item for item in catalog.expressions if item.expression_id == source_id
    )
    palette = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title=source.text, keywords=source.semantic_families),
        episode_state=EpisodeVoiceStateV1(),
    )
    selected = {item.authority_id: item.display_text for item in palette.expressions}
    assert selected.get(source_id) == surface.surface


def test_regional_expression_requires_explicit_region() -> None:
    catalog = load_catalog_v1()
    regional = next(item for item in catalog.expressions if item.regionalism)
    wrong = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title=regional.text, region="București"),
        episode_state=EpisodeVoiceStateV1(),
    )
    right = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title=regional.text, region="Ardeal"),
        episode_state=EpisodeVoiceStateV1(),
    )
    assert regional.expression_id not in _ids(wrong)
    assert regional.expression_id in _ids(right)


def test_raw_gate_and_victim_suppression() -> None:
    catalog = load_catalog_v1()
    raw = next(item for item in catalog.expressions if item.raw)
    allowed = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title=raw.text, raw_eligible=True, profanity_ceiling=2, humor_intensity=3
        ),
        episode_state=EpisodeVoiceStateV1(),
    )
    blocked = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title=raw.text,
            raw_eligible=True,
            profanity_ceiling=2,
            victim_sensitive=True,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )
    assert raw.expression_id in _ids(allowed)
    assert raw.expression_id not in _ids(blocked)


def test_victim_tragedy_context_suppresses_all_expressions() -> None:
    catalog = load_catalog_v1()
    tragedy = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title="Victime dupa prabusirea unei pasarele",
            summary="Ancheta verifica responsabilitatea institutionala.",
            humor_intensity=3,
            victim_sensitive=True,
            tragedy_sensitive=True,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )

    assert tragedy.expressions == ()


@pytest.mark.parametrize(
    ("term", "blocked_context", "allowed_context"),
    [
        ("fake news", {}, {"disinformation": True}),
        ("suveranist", {}, {"political_context": True}),
        ("pesedaurii", {}, {"political_context": True}),
        ("pesedizat", {}, {"political_context": True}),
        ("vibe-ul", {}, {"meme_context": True}),
    ],
)
def test_controlled_term_context_gates(
    term: str, blocked_context: dict[str, object], allowed_context: dict[str, object]
) -> None:
    catalog = load_catalog_v1()
    record = next(item for item in catalog.controlled_terms if item.term == term)
    if term == "vibe-ul":
        catalog = replace(catalog, comedy_devices=(), signature_devices=())
    blocked = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title=term, **blocked_context),
        episode_state=EpisodeVoiceStateV1(),
    )
    allowed = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title=term, **allowed_context),
        episode_state=EpisodeVoiceStateV1(),
    )
    assert record.term_id not in _ids(blocked)
    assert record.term_id in _ids(allowed)


def test_retired_sinecura_family_is_absent_and_patronage_is_not_padded() -> None:
    catalog = load_catalog_v1()
    serialized = json.dumps(_catalog_json(), ensure_ascii=False).casefold()
    assert "promotion-v2:controlled:sinecura" not in serialized
    assert all(
        form not in serialized for form in ("sinecură", "sinecuri", "sinecurele")
    )

    palette = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title="Numire prin clientelism",
            summary="O funcție obținută prin pile și patronaj politic.",
            patronage=True,
            political_context=True,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )
    assert palette.controlled_terms == ()
    assert palette.total_count == 0


def test_temporal_disabled_term_is_suppressed() -> None:
    catalog = load_catalog_v1()
    target = next(
        item for item in catalog.controlled_terms if item.term == "suveranist"
    )
    modified = replace(
        catalog,
        controlled_terms=tuple(
            replace(item, enabled=False) if item.term_id == target.term_id else item
            for item in catalog.controlled_terms
        ),
    )
    palette = retrieve_story_voice_palette_v1(
        catalog=modified,
        context=_context(title="suveranist", political_context=True),
        episode_state=EpisodeVoiceStateV1(),
        now=datetime(2026, 8, 16, tzinfo=UTC),
    )
    assert target.term_id not in _ids(palette)


def test_expression_and_family_repetition() -> None:
    catalog = load_catalog_v1()
    expression = next(item for item in catalog.expressions if item.semantic_families)
    context = _context(title=expression.text, keywords=expression.semantic_families)
    used = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=context,
        episode_state=EpisodeVoiceStateV1(
            used_expression_ids=(expression.expression_id,)
        ),
    )
    penalized, trace = retrieve_story_voice_palette_with_trace_v1(
        catalog=catalog,
        context=context,
        episode_state=EpisodeVoiceStateV1(
            used_expression_families=expression.semantic_families
        ),
    )
    assert expression.expression_id not in _ids(used)
    assert any(
        item.authority_id == expression.expression_id
        and "repetition_penalty" in item.reason_codes
        for item in trace.items
    ) or expression.expression_id not in _ids(penalized)


def test_controlled_max_per_episode_gate() -> None:
    catalog = load_catalog_v1()
    term = next(item for item in catalog.controlled_terms if item.term == "fake news")
    palette = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title="fake news", disinformation=True),
        episode_state=EpisodeVoiceStateV1(
            controlled_term_usage=((term.term_id, term.max_per_episode),)
        ),
    )
    assert term.term_id not in _ids(palette)


def test_device_adaptation_closing_signature_and_compound() -> None:
    catalog = load_catalog_v1()
    assert any(item.compound_capable for item in catalog.comedy_devices)
    signature = next(item for item in catalog.comedy_devices if item.signature_capable)
    palette = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title="semnătură", topic_tags=("signature_context",)),
        episode_state=EpisodeVoiceStateV1(),
    )
    assert signature.device_id in _ids(palette)
    used = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(title="semnătură", topic_tags=("signature_context",)),
        episode_state=EpisodeVoiceStateV1(used_device_ids=(signature.device_id,)),
    )
    assert signature.device_id not in _ids(used)


def test_tragedy_suppresses_risky_devices() -> None:
    catalog = load_catalog_v1()
    risky = next(
        item for item in catalog.comedy_devices if "victim_targeting" in item.risk_tags
    )
    palette = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(
            title=risky.structure,
            topic_tags=risky.best_for,
            tragedy_sensitive=True,
        ),
        episode_state=EpisodeVoiceStateV1(),
    )
    assert risky.device_id not in _ids(palette)


@pytest.mark.parametrize(
    ("scenario_id", "context"),
    [
        (
            "municipal_no_permit",
            {"title": "autorizație birocratică", "bureaucracy": True},
        ),
        (
            "politician_contradiction",
            {"title": "contradicție", "political_context": True},
        ),
        ("patronage_appointment", {"title": "numire", "patronage": True}),
        ("fake_news_denial", {"title": "fake news", "disinformation": True}),
        ("cluj_regional", {"title": "fain", "region": "Ardeal"}),
        (
            "unfinished_infrastructure",
            {"title": "proiect neterminat", "unfinished_project": True},
        ),
        ("bureaucratic_delay", {"title": "întârziere", "bureaucracy": True}),
        ("celebrity_scandal", {"title": "scandal vedetă", "entertainment": True}),
        (
            "victim_tragedy",
            {"title": "victimă", "victim_sensitive": True, "tragedy_sensitive": True},
        ),
        (
            "international_politics",
            {
                "title": "politică externă",
                "international": True,
                "political_context": True,
            },
        ),
        (
            "arrogant_politician",
            {
                "title": "aroganță",
                "political_context": True,
                "topic_tags": ("arrogance",),
            },
        ),
        (
            "failed_improvised_project",
            {
                "title": "proiect improvizat",
                "topic_tags": ("improvisation", "failed_project"),
            },
        ),
        (
            "medical_harm",
            {
                "title": "prejudiciu medical",
                "victim_sensitive": True,
                "tragedy_sensitive": True,
            },
        ),
        (
            "repeated_signature",
            {"title": "semnătură", "topic_tags": ("signature_context",)},
        ),
        ("ordinary_low_comedy", {"title": "raport administrativ obișnuit"}),
        ("same_family_already_used", {"title": "absurd", "topic_tags": ("absurdity",)}),
    ],
)
def test_frozen_golden_scenarios_are_bounded_and_stable(
    scenario_id: str, context: dict[str, object]
) -> None:
    catalog = load_catalog_v1()
    state = (
        EpisodeVoiceStateV1(used_device_families=("hagism",))
        if scenario_id == "same_family_already_used"
        else EpisodeVoiceStateV1()
    )
    first = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(**context),
        episode_state=state,
        now=datetime(2026, 8, 16, tzinfo=UTC),
    )
    second = retrieve_story_voice_palette_v1(
        catalog=catalog,
        context=_context(**context),
        episode_state=state,
        now=datetime(2026, 8, 16, tzinfo=UTC),
    )
    assert first == second
    assert len(first.expressions) <= 3
    assert first.total_count <= 5
    assert (
        len(first.controlled_terms)
        + len(first.comedy_devices)
        + len(first.signature_devices)
        <= 2
    )


def test_import_boundary_does_not_import_provider_or_editor_modules() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import pastila_scout.expression_retrieval_v1; "
                "print('\\n'.join(sorted(sys.modules)))"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "pastila_scout.provider_" not in result.stdout
    assert "pastila_scout.editor_" not in result.stdout


def test_catalog_models_are_immutable() -> None:
    catalog: ExpressionCatalogV1 = load_catalog_v1()
    with pytest.raises((AttributeError, TypeError)):
        catalog.bundle_version = 2  # type: ignore[misc]
