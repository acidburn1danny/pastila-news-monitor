"""Backfill immutable editorial-knowledge histories and evolution statistics."""

from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.editor.generation.controlled_revision_quality.editorial_knowledge import (
    deserialize_knowledge_base,
)
from pastila_scout.editor.generation.controlled_revision_quality.knowledge_evolution import (
    CONTRACT_VERSION,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    EntryHistory,
    EvolutionEvent,
    EvolutionState,
    EvolutionTrigger,
    KnowledgeEvolutionHistory,
    LifecycleState,
    RelationshipEvolutionEvent,
    event_fingerprint,
    evolution_history_fingerprint,
    history_fingerprint,
    relationship_event_fingerprint,
    serialize_history,
    statistics,
    validate_evolution_history,
)
from scripts.run_controlled_provider_quality_baseline import write_artifact_atomic

KNOWLEDGE_PATH = Path("docs/artifacts/editorial-knowledge-base.json")
HISTORY_PATH = Path("docs/artifacts/editorial-knowledge-history.json")
TIMELINE_PATH = Path("docs/artifacts/editorial-knowledge-timeline.json")
STATISTICS_PATH = Path("docs/artifacts/editorial-knowledge-statistics.json")
H3_KNOWLEDGE_VALIDATION_PATH = "docs/artifacts/knowledge-validation.json"


def _evidence_count(entry) -> int:
    experiments = set(entry.source_experiments)
    manifests: set[str] = set()
    artifacts: set[str] = set()
    scenarios: set[str] = set()
    for evidence in entry.supporting_evidence:
        manifests.add(evidence.manifest_path)
        artifacts.update(evidence.artifact_paths)
        scenarios.update(evidence.scenario_ids)
    return len(experiments) + len(manifests) + len(artifacts) + len(scenarios)


def _event(**values) -> EvolutionEvent:
    preliminary = EvolutionEvent(event_fingerprint="0" * 64, **values)
    return preliminary.model_copy(
        update={"event_fingerprint": event_fingerprint(preliminary)}
    )


def _relationship_event(**values) -> RelationshipEvolutionEvent:
    preliminary = RelationshipEvolutionEvent(event_fingerprint="0" * 64, **values)
    return preliminary.model_copy(
        update={"event_fingerprint": relationship_event_fingerprint(preliminary)}
    )


def _entry_history(entry) -> EntryHistory:
    evidence_count = _evidence_count(entry)
    proposed = EvolutionState(
        status=LifecycleState.PROPOSED,
        confidence=entry.confidence.value,
        entry_version=entry.entry_version,
        evolution_version=0,
        cumulative_evidence_count=0,
    )
    active = proposed.model_copy(
        update={
            "status": LifecycleState.ACTIVE,
            "evolution_version": 1,
            "cumulative_evidence_count": evidence_count,
        }
    )
    evidence = entry.supporting_evidence[0]
    events = [
        _event(
            event_id=f"EVE-{entry.knowledge_id}-001",
            knowledge_id=entry.knowledge_id,
            timestamp=entry.created_at,
            previous_state=proposed,
            new_state=active,
            trigger=EvolutionTrigger.STATUS_TRANSITION,
            supporting_experiments=entry.source_experiments,
            supporting_manifests=(evidence.manifest_path,),
            supporting_artifacts=evidence.artifact_paths,
            reason="Backfilled creation from the immutable knowledge entry and its original repository evidence.",
            confidence_before=entry.confidence.value,
            confidence_after=entry.confidence.value,
        )
    ]
    current = active
    refinements = 0
    if entry.knowledge_id == "EK-002":
        h3 = json.loads(
            Path("docs/artifacts/h3-experiment.json").read_text(encoding="utf-8")
        )
        refined = active.model_copy(
            update={
                "status": LifecycleState.REFINED,
                "evolution_version": 2,
                "cumulative_evidence_count": evidence_count + 3,
            }
        )
        events.append(
            _event(
                event_id="EVE-EK-002-002",
                knowledge_id="EK-002",
                timestamp=h3["created_at"],
                previous_state=active,
                new_state=refined,
                trigger=EvolutionTrigger.EXPERIMENT_REFINED,
                supporting_experiments=(h3["experiment_id"],),
                supporting_manifests=(evidence.manifest_path,),
                supporting_artifacts=(
                    "docs/artifacts/h3-experiment.json",
                    "docs/artifacts/prediction-validation.json",
                    H3_KNOWLEDGE_VALIDATION_PATH,
                ),
                reason="H3 produced positive utility but only partially confirmed EK-002's predicted mechanism and breadth.",
                confidence_before=entry.confidence.value,
                confidence_after=entry.confidence.value,
            )
        )
        current = refined
        refinements = 1
    preliminary = EntryHistory(
        knowledge_id=entry.knowledge_id,
        entry_version=entry.entry_version,
        evolution_schema_version=SCHEMA_VERSION,
        events=tuple(events),
        current_state=current,
        confirmations=0,
        refinements=refinements,
        contradictions=0,
        supersessions=0,
        deprecations=0,
        history_fingerprint="0" * 64,
    )
    return preliminary.model_copy(
        update={"history_fingerprint": history_fingerprint(preliminary)}
    )


def build_evolution_history(repository_root: Path) -> KnowledgeEvolutionHistory:
    """Backfill all current entries and the one explicit H3 refinement."""

    base = deserialize_knowledge_base(repository_root / KNOWLEDGE_PATH)
    histories = tuple(_entry_history(entry) for entry in base.entries)
    entries_by_id = {entry.knowledge_id: entry for entry in base.entries}
    relationship_history = []
    for number, relationship in enumerate(base.relationships, 1):
        timestamp = max(
            entries_by_id[relationship.source_id].created_at,
            entries_by_id[relationship.target_id].created_at,
        )
        relationship_history.append(
            _relationship_event(
                relationship_event_id=f"REL-{number:03d}",
                timestamp=timestamp,
                action="ADDED",
                source_id=relationship.source_id,
                target_id=relationship.target_id,
                relationship_type=relationship.relationship_type.value,
                supporting_artifact=KNOWLEDGE_PATH.as_posix(),
            )
        )
    generated_at = max(
        event.timestamp for history in histories for event in history.events
    )
    preliminary = KnowledgeEvolutionHistory(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        contract_version=CONTRACT_VERSION,
        generated_at=generated_at,
        source_knowledge_base_fingerprint=base.knowledge_base_fingerprint,
        histories=histories,
        relationship_history=tuple(relationship_history),
        history_fingerprint="0" * 64,
    )
    return preliminary.model_copy(
        update={"history_fingerprint": evolution_history_fingerprint(preliminary)}
    )


def build_timeline(history: KnowledgeEvolutionHistory) -> dict:
    events = [
        {
            **event.model_dump(mode="json"),
            "event_type": "KNOWLEDGE_EVOLUTION",
        }
        for item in history.histories
        for event in item.events
    ] + [
        {
            **event.model_dump(mode="json"),
            "event_type": "RELATIONSHIP_EVOLUTION",
        }
        for event in history.relationship_history
    ]
    events.sort(
        key=lambda item: (
            item["timestamp"],
            item.get("event_id", item.get("relationship_event_id")),
        )
    )
    return {
        "schema_version": 1,
        "history_fingerprint": history.history_fingerprint,
        "event_count": len(events),
        "events": events,
    }


def write_evolution(repository_root: Path) -> KnowledgeEvolutionHistory:
    history = build_evolution_history(repository_root)
    diagnostics = validate_evolution_history(history, repository_root)
    if not diagnostics.valid:
        raise RuntimeError(f"evolution validation failed: {diagnostics.errors}")
    serialize_history(repository_root / HISTORY_PATH, history)
    write_artifact_atomic(repository_root / TIMELINE_PATH, build_timeline(history))
    write_artifact_atomic(repository_root / STATISTICS_PATH, statistics(history))
    return history


if __name__ == "__main__":
    result = write_evolution(Path.cwd())
    print(f"Entries backfilled: {len(result.histories)}")
    print("Provider requests: 0")
