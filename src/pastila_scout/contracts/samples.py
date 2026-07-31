"""Realistic, deterministic sample documents for the frozen v1 contracts."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.contracts.editor_output import EditorAgentOutputV1
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import (
    assign_scout_input_identity,
    canonical_json_bytes,
)
from pastila_scout.contracts.io import write_contract
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1


def _component(
    raw: float, normalized: float, contribution: float, maximum: float, explanation: str
) -> dict[str, object]:
    return {
        "raw_input": raw,
        "normalized_value": normalized,
        "weighted_contribution": contribution,
        "maximum_contribution": maximum,
        "explanation": explanation,
    }


def sample_scout_input(*, ai_enabled: bool = True) -> ScoutEditorInputV1:
    """Return a small Romanian Scout report with a valid stable identity."""

    data: dict[str, object] = {
        "contract_version": "scout-editor-input-v1",
        "editorial_contract_version": "scout-editorial-semantics-v1",
        "generated_at": datetime(2026, 7, 26, 18, 0, tzinfo=UTC),
        "report_id": "",
        "content_fingerprint": "",
        "scout_version": "0.1.0",
        "ranking_schema_version": "event-ranking-v1",
        "source_run_id": f"snapshot:sha256:{'1' * 64}",
        "ranking_parameters": {
            "days": 7,
            "category_filter": None,
            "limit": 100,
            "top": 10,
            "minimum_score": 55.0,
            "ai_enabled": ai_enabled,
        },
        "event_counts": {"eligible": 30, "processed": 30, "reported": 1},
        "ranked_events": [
            {
                "rank": 1,
                "score_rank": 1,
                "event_id": 44,
                "canonical_title": "Guvernul anunță o nouă măsură fiscală",
                "canonical_summary": "Măsura urmează să fie discutată în ședința de guvern.",
                "publication_bounds": {
                    "first_published_at": datetime(2026, 7, 25, 9, 15, tzinfo=UTC),
                    "last_published_at": datetime(2026, 7, 25, 10, 5, tzinfo=UTC),
                },
                "categories": ["Politica", "Economie"],
                "source_count": 2,
                "article_count": 2,
                "source_provenance": [
                    {
                        "source_id": "digi24",
                        "source_name": "Digi24",
                        "url": "https://example.ro/masura-fiscala",
                        "title": "Guvernul anunță o nouă măsură fiscală",
                        "published_at": datetime(2026, 7, 25, 9, 15, tzinfo=UTC),
                    },
                    {
                        "source_id": "hotnews",
                        "source_name": "HotNews",
                        "url": "https://example.net/masuri-guvern",
                        "title": "Noile măsuri discutate de Guvern",
                        "published_at": datetime(2026, 7, 25, 10, 5, tzinfo=UTC),
                    },
                ],
                "provenance_truncated": False,
                "deterministic_score": {
                    "score": 81.4,
                    "schema_version": "deterministic-event-score-v1",
                    "components": {
                        "supporting_articles": _component(
                            2, 0.2, 3, 15, "Two supporting articles."
                        ),
                        "source_diversity": _component(
                            2, 0.4, 6, 15, "Two distinct sources."
                        ),
                        "source_credibility": _component(
                            2, 1, 15, 15, "Priority-two sources."
                        ),
                        "recency": _component(12, 0.95, 19, 20, "Published recently."),
                        "national_relevance": _component(
                            1, 1, 15, 15, "National government action."
                        ),
                        "category_weight": _component(
                            1, 0.8, 8, 10, "Politics and economy."
                        ),
                        "title_strength": _component(
                            1, 0.77, 7.4, 10, "Specific active title."
                        ),
                    },
                },
                "ai_editorial_score": (
                    {
                        "score": 90.0,
                        "dimensions": {
                            "importance": 9,
                            "virality": 8,
                            "absurdity": 6,
                            "satirical_potential": 9,
                            "public_interest": 10,
                            "emotional_impact": 8,
                            "originality": 7,
                        },
                    }
                    if ai_enabled
                    else None
                ),
                "final_score": 85.27 if ai_enabled else 81.4,
                "recommendation": "STRONG_PICK" if ai_enabled else "POSSIBLE_PICK",
                "scout_recommendation_reason": (
                    "High public relevance and satirical potential."
                    if ai_enabled
                    else "Scout produced a deterministic-only ranking."
                ),
                "editorial_risks": (
                    ["Confirm implementation details before publication."]
                    if ai_enabled
                    else []
                ),
                "score_basis": (
                    "deterministic_and_ai" if ai_enabled else "deterministic_only"
                ),
                "extensions": {},
            }
        ],
        "extensions": {},
    }
    return assign_scout_input_identity(data)


def sample_selection_profile() -> SelectionProfileV1:
    return SelectionProfileV1.model_validate_json(
        canonical_json_bytes(
            {
                "contract_version": "editor-selection-profile-v1",
                "profile_name": "pastila-weekly",
                "profile_version": "1.0.0",
                "target_story_count": 1,
                "backup_count": 0,
                "category_constraints": {
                    "Politica": {
                        "minimum": 0,
                        "preferred": 1,
                        "maximum": 1,
                        "minimum_policy": "soft",
                        "extensions": {},
                    }
                },
                "maximum_stories_from_one_category": 1,
                "minimum_source_diversity": 2,
                "avoid_semantic_redundancy": True,
                "opening_story_preference": "high-impact national story",
                "closing_story_preference": "lighter story",
                "provider_policy": "optional",
                "extensions": {},
            }
        )
    )


def sample_episode_context() -> EpisodeContextV1:
    return EpisodeContextV1.model_validate_json(
        canonical_json_bytes(
            {
                "contract_version": "episode-context-v1",
                "episode_format": "weekly_satirical_news",
                "platform": "YouTube",
                "language": "ro",
                "target_runtime": {"unit": "seconds", "value": 180},
                "target_story_count": 1,
                "audience": "Public român general",
                "pacing": "varied",
                "tone": ["satirical", "factual"],
                "humor_style": ["ironic", "absurdist"],
                "factual_strictness": "high",
                "political_balance": "balanced",
                "opening_preference": "high-impact national story",
                "closing_preference": "lighter story",
                "presenter_notes": [],
                "mandatory_event_ids": [],
                "excluded_event_ids": [],
                "theme": None,
                "episode_objective": "A concise, varied Romanian news episode.",
                "previous_episode_reference": "pastila-2026-07-19",
                "avoid_recent_event_ids": [201, 244],
                "extensions": {},
            }
        )
    )


def sample_editor_output(
    source: ScoutEditorInputV1 | None = None,
) -> EditorAgentOutputV1:
    source = source or sample_scout_input()
    event = source.ranked_events[0]
    inherited = {
        "deterministic_score": event.deterministic_score.score,
        "ai_editorial_score": (
            event.ai_editorial_score.score if event.ai_editorial_score else None
        ),
        "final_score": event.final_score,
        "recommendation": event.recommendation,
    }
    return EditorAgentOutputV1.model_validate_json(
        canonical_json_bytes(
            {
                "contract_version": "editor-agent-output-v1",
                "editorial_contract_version": "scout-editorial-semantics-v1",
                "generated_at": datetime(2026, 7, 26, 18, 30, tzinfo=UTC),
                "editor_agent_version": "sample-only-1.0.0",
                "source_report_id": source.report_id,
                "source_contract_version": source.contract_version,
                "source_content_fingerprint": source.content_fingerprint,
                "selection_profile": {
                    "name": "pastila-weekly",
                    "version": "1.0.0",
                    "extensions": {},
                },
                "requested_episode_size": 1,
                "status": "success",
                "episode_proposal": {
                    "episode_title_suggestion": "Promisiuni și alte certitudini temporare",
                    "editorial_angle": "Deciziile instituționale și efectele lor cotidiene.",
                    "estimated_total_runtime": {"unit": "seconds", "value": 180},
                    "selected_stories": [
                        {
                            "position": 1,
                            "event_id": event.event_id,
                            "canonical_title": event.canonical_title,
                            "episode_role": "opening",
                            "selection_reason": "Strong national relevance and a clear premise.",
                            "transition_reason": None,
                            "tone_recommendation": "Direct factual setup followed by restrained irony.",
                            "factual_editorial_risks": list(event.editorial_risks),
                            "suggested_treatment_length": {
                                "unit": "seconds",
                                "value": 180,
                            },
                            "editorial_confidence": 92,
                            "source_references": [
                                item.model_dump() for item in event.source_provenance
                            ],
                            "inherited_scout_scores": inherited,
                            "extensions": {},
                        }
                    ],
                    "backup_stories": [],
                    "episode_flow": [
                        {
                            "position": 1,
                            "event_id": event.event_id,
                            "role": "opening",
                            "placement_reason": "Provides the strongest immediate national hook.",
                            "expected_transition_type": None,
                            "extensions": {},
                        }
                    ],
                    "rejection_summary": {
                        "total_candidates": 1,
                        "selected": 1,
                        "backups": 0,
                        "excluded_by_constraints": 0,
                        "semantically_redundant": 0,
                        "otherwise_not_selected": 0,
                        "notable_exclusions": [],
                        "unused_strong_candidates": [],
                        "extensions": {},
                    },
                    "warnings": [],
                    "editorial_notes": ["Keep the factual setup concise."],
                    "overall_selection_reasoning": "One strong candidate fits the sample episode.",
                    "extensions": {},
                },
                "errors": [],
                "extensions": {},
            }
        )
    )


def sample_editor_partial_output(
    source: ScoutEditorInputV1 | None = None,
) -> EditorAgentOutputV1:
    """Return a valid partial-success envelope without adding selection logic."""

    output = sample_editor_output(source)
    assert output.episode_proposal is not None
    proposal_data = output.episode_proposal.model_dump(mode="json")
    proposal_data["warnings"] = [
        {
            "code": "provider_unavailable",
            "message": "Optional editorial provider was unavailable; deterministic data remains valid.",
            "event_id": None,
            "recoverable": True,
        }
    ]
    data = output.model_dump(mode="json")
    data["status"] = "partial_success"
    data["episode_proposal"] = proposal_data
    return EditorAgentOutputV1.model_validate_json(json.dumps(data, ensure_ascii=False))


def write_sample_contracts(output_directory: Path) -> tuple[Path, ...]:
    """Write all four frozen sample contracts."""

    scout_ai = sample_scout_input(ai_enabled=True)
    scout_deterministic = sample_scout_input(ai_enabled=False)
    samples = (
        ("scout-editor-input-ai-v1.sample.json", scout_ai),
        ("scout-editor-input-deterministic-v1.sample.json", scout_deterministic),
        ("editor-selection-profile-v1.sample.json", sample_selection_profile()),
        ("episode-context-v1.sample.json", sample_episode_context()),
        ("editor-agent-output-success-v1.sample.json", sample_editor_output(scout_ai)),
        (
            "editor-agent-output-partial-success-v1.sample.json",
            sample_editor_partial_output(scout_ai),
        ),
    )
    return tuple(
        write_contract(value, output_directory / name) for name, value in samples
    )
