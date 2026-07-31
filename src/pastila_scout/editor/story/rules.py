"""Stable declarative rules for Story Architecture validation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoryArchitectureRule:
    """A named architecture invariant and its failure consequence."""

    rule_id: str
    statement: str
    blocking: bool


CANONICAL_STORY_ARCHITECTURE_RULES = (
    StoryArchitectureRule(
        "single-primary-spine", "Exactly one primary narrative spine is required.", True
    ),
    StoryArchitectureRule(
        "evidence-linked-units",
        "Every unit must retain valid upstream evidence links.",
        True,
    ),
    StoryArchitectureRule(
        "core-appears-early",
        "The primary editorial core must appear in the first two spine units.",
        True,
    ),
    StoryArchitectureRule(
        "prerequisites-before-use",
        "Every prerequisite must precede its dependent unit.",
        True,
    ),
    StoryArchitectureRule(
        "context-before-dependency",
        "Required context must precede dependent interpretation.",
        True,
    ),
    StoryArchitectureRule(
        "no-held-or-removed-material",
        "Held or removed material cannot re-enter architecture.",
        True,
    ),
    StoryArchitectureRule(
        "indispensable-material-retained",
        "Indispensable material remains represented.",
        True,
    ),
    StoryArchitectureRule(
        "attribution-preserved",
        "Allegations and disputed claims preserve attribution.",
        True,
    ),
    StoryArchitectureRule(
        "causality-evidenced", "Causal transitions require evidence.", True
    ),
    StoryArchitectureRule(
        "chronology-undistorted",
        "Sequence changes must not distort factual chronology.",
        True,
    ),
    StoryArchitectureRule(
        "consequence-evidenced",
        "Consequences retain supporting material or core links.",
        True,
    ),
    StoryArchitectureRule(
        "satire-after-setup",
        "Satire follows validated opportunity and factual setup.",
        True,
    ),
    StoryArchitectureRule(
        "protected-subjects", "Protected subjects never become satirical targets.", True
    ),
    StoryArchitectureRule(
        "payoff-after-setup", "Every payoff resolves an earlier setup.", True
    ),
    StoryArchitectureRule(
        "takeaway-evidenced", "Audience takeaway remains evidence-linked.", True
    ),
    StoryArchitectureRule(
        "secondary-angles-subordinate",
        "Secondary angles cannot compete with the primary spine.",
        False,
    ),
    StoryArchitectureRule(
        "profile-guidance-bounded",
        "Profile guidance cannot override fixed safeguards.",
        True,
    ),
    StoryArchitectureRule(
        "no-upstream-mutation",
        "Architecture cannot change upstream editorial judgments.",
        True,
    ),
    StoryArchitectureRule(
        "no-generated-language",
        "Architecture contains references and functions, not prose.",
        True,
    ),
    StoryArchitectureRule(
        "readiness-derived",
        "Readiness is derived from upstream state and architecture findings.",
        True,
    ),
)
