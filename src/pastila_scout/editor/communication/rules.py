"""Declarative fixed rules for language-neutral spoken communication."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommunicationRule:
    rule_id: str
    statement: str
    blocking: bool


CANONICAL_COMMUNICATION_RULES = (
    CommunicationRule(
        "language-neutral",
        "Communication policies contain no language-specific realization.",
        True,
    ),
    CommunicationRule(
        "no-generation",
        "Communication policies never generate wording or scripts.",
        True,
    ),
    CommunicationRule(
        "story-lineage",
        "Assessments retain exact Story Architecture Plan lineage.",
        True,
    ),
    CommunicationRule(
        "orientation-preserved",
        "Communication never silently loses listener orientation.",
        True,
    ),
    CommunicationRule(
        "dependencies-local", "Required dependencies remain close to their use.", False
    ),
    CommunicationRule(
        "payoff-prepared", "Payoffs follow sufficient recognized setup.", True
    ),
    CommunicationRule(
        "profile-bounded",
        "Profile tuning cannot override upstream or fixed boundaries.",
        True,
    ),
    CommunicationRule(
        "readiness-derived", "Assessment readiness is deterministic.", True
    ),
)
