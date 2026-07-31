"""Extract the initial editorial knowledge base from frozen experiment evidence."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pastila_scout.editor.generation.controlled_revision_quality.editorial_knowledge import (
    CONTRACT_VERSION,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    Confidence,
    EditorialKnowledgeBase,
    EvidenceReference,
    FindingType,
    KnowledgeEntry,
    KnowledgeRelationship,
    KnowledgeStatus,
    RelationshipType,
    entry_fingerprint,
    knowledge_base_fingerprint,
    serialize_knowledge_base,
    validate_knowledge_base,
)

KNOWLEDGE_PATH = Path("docs/artifacts/editorial-knowledge-base.json")
INDEX_PATH = Path("docs/artifacts/editorial-knowledge-index.json")
MANIFEST_PATH = "docs/artifacts/experiments/part-7h-2/experiment-manifest.json"
TRADEOFF_PATH = "docs/artifacts/causal-editorial-tradeoff-analysis.json"
MATRIX_PATH = "docs/artifacts/editorial-tradeoff-matrix.json"
H1_PATH = "docs/artifacts/controlled-prompt-effectiveness-experiment.json"
H2_PATH = "docs/artifacts/controlled-second-prompt-hypothesis-experiment.json"
H3_PATH = "docs/artifacts/h3-experiment.json"
H3_PREDICTION_PATH = "docs/artifacts/prediction-validation.json"


def _entry(**values) -> KnowledgeEntry:
    preliminary = KnowledgeEntry(entry_fingerprint="0" * 64, **values)
    return preliminary.model_copy(
        update={"entry_fingerprint": entry_fingerprint(preliminary)}
    )


def build_knowledge_base(repository_root: Path) -> EditorialKnowledgeBase:
    """Extract seven reusable findings without speculation or provider execution."""

    manifest = json.loads((repository_root / MANIFEST_PATH).read_text(encoding="utf-8"))
    tradeoff = json.loads((repository_root / TRADEOFF_PATH).read_text(encoding="utf-8"))
    if tradeoff["root_conclusion"] != "EDITORIAL_TRADE_OFFS_CHARACTERIZED":
        raise RuntimeError("trade-off analysis is not authoritative")
    experiment_id = manifest["experiment"]["experiment_id"]
    manifest_fingerprint = manifest["manifest"]["manifest_fingerprint"]
    created_at = manifest["experiment"]["completed_at"]

    def evidence(*artifacts: str, scenarios: tuple[str, ...] = ()):
        return (
            EvidenceReference(
                experiment_id=experiment_id,
                manifest_path=MANIFEST_PATH,
                manifest_fingerprint=manifest_fingerprint,
                artifact_paths=artifacts,
                scenario_ids=scenarios,
            ),
        )

    entries = [
        _entry(
            knowledge_id="EK-001",
            entry_version=1,
            title="Quote-specific preservation reduced quote mutation",
            description="The H2 quote-specific instruction removed both observed primary QUOTE_MUTATION failures.",
            finding_type=FindingType.PROMPT_BEHAVIOR,
            status=KnowledgeStatus.ACTIVE,
            confidence=Confidence.MEDIUM,
            confidence_justification="Both paired targeted scenarios improved, but one run cannot exclude provider stochasticity.",
            source_experiments=(experiment_id,),
            supporting_evidence=evidence(
                H2_PATH, TRADEOFF_PATH, scenarios=("SYN-10", "SYN-23")
            ),
            affected_categories=("QUOTE_MUTATION", "quote_preservation"),
            affected_scenarios=("SYN-10", "SYN-23"),
            observed_behavior="QUOTE_MUTATION decreased from two scenarios to zero.",
            causal_explanation="The only intended variable was one quote-specific instruction; paired evidence is consistent with a prompt effect.",
            net_editorial_utility=2,
            side_effects=("Both scenarios remained editorially rejected.",),
            recommended_usage="Retain as evidence that quote handling is prompt-responsive, not as proof of production suitability.",
            reusable=True,
            deprecated=False,
            superseded_by=None,
            created_at=created_at,
        ),
        _entry(
            knowledge_id="EK-002",
            entry_version=1,
            title="Narrow target improvement can have negative net editorial utility",
            description="H2 resolved two criterion failures but introduced four, producing net utility minus two.",
            finding_type=FindingType.TRADE_OFF,
            status=KnowledgeStatus.ACTIVE,
            confidence=Confidence.MEDIUM,
            confidence_justification="The transition counts are deterministic; causal attribution of the new failures remains lower confidence.",
            source_experiments=(experiment_id,),
            supporting_evidence=evidence(
                TRADEOFF_PATH,
                MATRIX_PATH,
                scenarios=("SYN-10", "SYN-20", "SYN-23"),
            ),
            affected_categories=(
                "quote_preservation",
                "instruction_compliance",
                "meaning_preservation",
                "source_authority_preservation",
            ),
            affected_scenarios=("SYN-10", "SYN-20", "SYN-23"),
            observed_behavior="Two resolved scenario-criterion failures were offset by four introduced failures.",
            causal_explanation="The paired treatment improved its target but SYN-20 regressed across four criteria; prompt interaction and stochasticity remain alternatives.",
            net_editorial_utility=-2,
            side_effects=("Editorial acceptance decreased from one pass to zero.",),
            recommended_usage="Require multi-criterion trade-off review before promoting a targeted prompt improvement.",
            reusable=True,
            deprecated=False,
            superseded_by=None,
            created_at=created_at,
        ),
        _entry(
            knowledge_id="EK-003",
            entry_version=1,
            title="Removing quote failure exposed pre-existing authority failure",
            description="SOURCE_AUTHORITY_DRIFT replaced QUOTE_MUTATION as primary in two scenarios without introducing the underlying authority criteria.",
            finding_type=FindingType.PROMPT_INTERACTION,
            status=KnowledgeStatus.ACTIVE,
            confidence=Confidence.LOW,
            confidence_justification="Primary-category substitution is observed, but its causal mechanism was not independently tested.",
            source_experiments=(experiment_id,),
            supporting_evidence=evidence(TRADEOFF_PATH, scenarios=("SYN-10", "SYN-23")),
            affected_categories=("QUOTE_MUTATION", "SOURCE_AUTHORITY_DRIFT"),
            affected_scenarios=("SYN-10", "SYN-23"),
            observed_behavior="Resolving quote preservation changed the primary failure label while the scenarios remained rejected.",
            causal_explanation="Failure prioritization exposed authority failures already present in control evidence; H2 did not cure them.",
            net_editorial_utility=2,
            side_effects=(
                "Primary-category frequency can obscure unchanged secondary failures.",
            ),
            recommended_usage="Inspect criterion-level transitions whenever a primary failure category disappears.",
            reusable=True,
            deprecated=False,
            superseded_by=None,
            created_at=created_at,
        ),
        _entry(
            knowledge_id="EK-004",
            entry_version=1,
            title="Editorial acceptance requires criterion-level explanation",
            description="Aggregate acceptance alone cannot identify resolved, substituted, or introduced editorial failures.",
            finding_type=FindingType.BEST_PRACTICE,
            status=KnowledgeStatus.ACTIVE,
            confidence=Confidence.HIGH,
            confidence_justification="The frozen H2 evidence contains the same zero treatment passes alongside both improvements and regressions.",
            source_experiments=(experiment_id,),
            supporting_evidence=evidence(H2_PATH, TRADEOFF_PATH),
            affected_categories=("editorial_acceptance",),
            affected_scenarios=("SYN-10", "SYN-20", "SYN-23"),
            observed_behavior="One aggregate acceptance value coexisted with two resolved and four introduced criterion failures.",
            causal_explanation="Acceptance is a terminal judgment rather than a diagnostic decomposition.",
            net_editorial_utility=-2,
            side_effects=(),
            recommended_usage="Always retain criterion and transition diagnostics beside acceptance counts.",
            reusable=True,
            deprecated=False,
            superseded_by=None,
            created_at=created_at,
        ),
        _entry(
            knowledge_id="EK-005",
            entry_version=1,
            title="Net Editorial Utility supplements editorial acceptance",
            description="Scenario-criterion resolutions minus introductions exposes compensating changes hidden by acceptance.",
            finding_type=FindingType.BEST_PRACTICE,
            status=KnowledgeStatus.ACTIVE,
            confidence=Confidence.HIGH,
            confidence_justification="The metric is deterministically reconstructed from all 24 paired criterion transitions.",
            source_experiments=(experiment_id,),
            supporting_evidence=evidence(TRADEOFF_PATH, MATRIX_PATH),
            affected_categories=("editorial_acceptance", "Net Editorial Utility"),
            affected_scenarios=("SYN-10", "SYN-20", "SYN-23"),
            observed_behavior="Net Editorial Utility was minus two while targeted quote behavior improved.",
            causal_explanation="The metric counts compensating criterion changes without replacing the frozen acceptance gate.",
            net_editorial_utility=-2,
            side_effects=("It must not replace editorial acceptance.",),
            recommended_usage="Use as a diagnostic paired metric alongside, never instead of, acceptance.",
            reusable=True,
            deprecated=False,
            superseded_by=None,
            created_at=created_at,
        ),
        _entry(
            knowledge_id="EK-006",
            entry_version=1,
            title="Single-mechanism prompt budgets bound causal interpretation",
            description="H2 changed one documented behavioral mechanism and preserved all technical contracts.",
            finding_type=FindingType.BEST_PRACTICE,
            status=KnowledgeStatus.ACTIVE,
            confidence=Confidence.MEDIUM,
            confidence_justification="The manifest verifies a one-of-one budget and frozen technical variables; provider stochasticity still limits attribution.",
            source_experiments=(experiment_id,),
            supporting_evidence=evidence(
                "docs/artifacts/prompt-delta-budget.json", MANIFEST_PATH
            ),
            affected_categories=("Prompt Delta Budget",),
            affected_scenarios=tuple(f"SYN-{number:02d}" for number in range(1, 25)),
            observed_behavior="One prompt mechanism was evaluated with 24/24 technical and reference preservation.",
            causal_explanation="Restricting the intended variable makes claims narrower, though it does not eliminate stochastic uncertainty.",
            net_editorial_utility=-2,
            side_effects=("A narrow mechanism may optimize only one criterion.",),
            recommended_usage="Keep future prompt experiments within a precommitted semantic delta budget.",
            reusable=True,
            deprecated=False,
            superseded_by=None,
            created_at=created_at,
        ),
        _entry(
            knowledge_id="EK-007",
            entry_version=1,
            title="Canonical manifests make experiment conclusions reproducible",
            description="The Part 7H.2 manifest validates identity, lineage, gates, results, decision, and nine supporting artifacts.",
            finding_type=FindingType.BEST_PRACTICE,
            status=KnowledgeStatus.ACTIVE,
            confidence=Confidence.HIGH,
            confidence_justification="Deterministic fingerprint and artifact validation are enforced by executable contracts and tests.",
            source_experiments=(experiment_id,),
            supporting_evidence=evidence(MANIFEST_PATH),
            affected_categories=("Experiment reproducibility",),
            affected_scenarios=tuple(f"SYN-{number:02d}" for number in range(1, 25)),
            observed_behavior="One canonical manifest reconstructs and validates the complete H2 experiment state.",
            causal_explanation="Typed invariants and raw-byte artifact fingerprints detect inconsistent reconstruction.",
            net_editorial_utility=None,
            side_effects=(),
            recommended_usage="Create and validate a canonical manifest before extracting reusable knowledge.",
            reusable=True,
            deprecated=False,
            superseded_by=None,
            created_at=created_at,
        ),
    ]
    relationships = [
        KnowledgeRelationship(
            source_id="EK-002",
            target_id="EK-001",
            relationship_type=RelationshipType.DEPENDS_ON,
            explanation="The trade-off calculation depends on the targeted quote resolution.",
        ),
        KnowledgeRelationship(
            source_id="EK-003",
            target_id="EK-001",
            relationship_type=RelationshipType.REFINES,
            explanation="Criterion evidence refines what the primary quote-category reduction means.",
        ),
        KnowledgeRelationship(
            source_id="EK-005",
            target_id="EK-004",
            relationship_type=RelationshipType.REFINES,
            explanation="Net utility supplies the diagnostic decomposition acceptance lacks.",
        ),
        KnowledgeRelationship(
            source_id="EK-006",
            target_id="EK-001",
            relationship_type=RelationshipType.RELATED_TO,
            explanation="The bounded prompt delta supports narrow interpretation of the quote finding.",
        ),
        KnowledgeRelationship(
            source_id="EK-007",
            target_id="EK-006",
            relationship_type=RelationshipType.SUPPORTS,
            explanation="Manifest validation preserves the frozen variables required by the delta budget.",
        ),
    ]
    h3_path = repository_root / H3_PATH
    if h3_path.is_file():
        h3 = json.loads(h3_path.read_text(encoding="utf-8"))
        prediction = json.loads(
            (repository_root / H3_PREDICTION_PATH).read_text(encoding="utf-8")
        )
        entries.append(
            _entry(
                knowledge_id="EK-008",
                entry_version=1,
                title="Balanced preservation produced positive multi-criterion utility",
                description="H3 increased editorial acceptance and produced Net Editorial Utility +8 while preserving technical and reference contracts.",
                finding_type=FindingType.PROMPT_BEHAVIOR,
                status=KnowledgeStatus.ACTIVE,
                confidence=Confidence.MEDIUM,
                confidence_justification="The paired 24-scenario experiment is technically complete, while the predicted causal mechanism was only partially confirmed.",
                source_experiments=(h3["experiment_id"],),
                supporting_evidence=(
                    EvidenceReference(
                        experiment_id=h3["experiment_id"],
                        manifest_path=MANIFEST_PATH,
                        manifest_fingerprint=manifest_fingerprint,
                        artifact_paths=(H3_PATH, H3_PREDICTION_PATH),
                        scenario_ids=tuple(prediction["observed_affected_scenarios"]),
                    ),
                ),
                affected_categories=(
                    "editorial_acceptance",
                    "instruction_compliance",
                    "meaning_preservation",
                    "quote_preservation",
                    "source_authority_preservation",
                ),
                affected_scenarios=tuple(prediction["observed_affected_scenarios"]),
                observed_behavior="H3 resolved 13 scenario-criterion failures, introduced five, and increased acceptance from one to three passes.",
                causal_explanation="A single balanced-preservation rule was the intended variable; its broader scenario effect and remaining regressions make the exact mechanism only partially confirmed.",
                net_editorial_utility=h3["net_editorial_utility"]["value"],
                side_effects=(
                    "Five criterion failures were introduced.",
                    "One control pass still became a treatment failure.",
                ),
                recommended_usage="Use as evidence for balanced multi-criterion preservation and retain predictive uncertainty in future experiments.",
                reusable=True,
                deprecated=False,
                superseded_by=None,
                created_at=h3["created_at"],
            )
        )
        relationships.append(
            KnowledgeRelationship(
                source_id="EK-008",
                target_id="EK-002",
                relationship_type=RelationshipType.REFINES,
                explanation="H3 validates that the H2 trade-off can be improved while retaining residual regressions and broader-than-predicted effects.",
            )
        )
    preliminary = EditorialKnowledgeBase(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        contract_version=CONTRACT_VERSION,
        generated_at=created_at,
        generator="scripts.build_editorial_knowledge_base",
        entries=tuple(entries),
        relationships=tuple(relationships),
        knowledge_base_fingerprint="0" * 64,
    )
    return preliminary.model_copy(
        update={"knowledge_base_fingerprint": knowledge_base_fingerprint(preliminary)}
    )


def build_index(base: EditorialKnowledgeBase) -> dict:
    """Create a compact deterministic future-query index without search behavior."""

    indexes: dict[str, defaultdict[str, list[str]]] = {
        name: defaultdict(list)
        for name in (
            "by_category",
            "by_confidence",
            "by_finding_type",
            "by_experiment",
            "by_scenario",
        )
    }
    for entry in base.entries:
        for value in entry.affected_categories:
            indexes["by_category"][value].append(entry.knowledge_id)
        indexes["by_confidence"][entry.confidence.value].append(entry.knowledge_id)
        indexes["by_finding_type"][entry.finding_type.value].append(entry.knowledge_id)
        for value in entry.source_experiments:
            indexes["by_experiment"][value].append(entry.knowledge_id)
        for value in entry.affected_scenarios:
            indexes["by_scenario"][value].append(entry.knowledge_id)
    return {
        "schema_version": 1,
        "knowledge_base_fingerprint": base.knowledge_base_fingerprint,
        "entry_count": len(base.entries),
        **{
            name: {key: sorted(set(value)) for key, value in sorted(index.items())}
            for name, index in indexes.items()
        },
    }


def write_knowledge_base(repository_root: Path) -> EditorialKnowledgeBase:
    base = build_knowledge_base(repository_root)
    diagnostics = validate_knowledge_base(base, repository_root)
    if not diagnostics.valid:
        raise RuntimeError(f"knowledge validation failed: {diagnostics.errors}")
    serialize_knowledge_base(repository_root / KNOWLEDGE_PATH, base)
    (repository_root / INDEX_PATH).write_text(
        json.dumps(build_index(base), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return base


if __name__ == "__main__":
    knowledge = write_knowledge_base(Path.cwd())
    print(f"Knowledge entries: {len(knowledge.entries)}")
    print("Provider requests: 0")
