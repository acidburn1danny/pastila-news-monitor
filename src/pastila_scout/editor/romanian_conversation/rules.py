"""Declarative Romanian conversational invariants."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RomanianConversationRule:
    rule_id: str
    statement: str
    blocking: bool


_STATEMENTS = (
    ("romanian-language", "Language identity is Romanian ro-RO."),
    (
        "communication-downstream",
        "Romanian realization remains downstream of Spoken Communication.",
    ),
    ("no-prose-generation", "The engine never generates prose."),
    ("no-learning", "The engine never learns or persists corrections."),
    ("clarity-before-naturalness", "Naturalness never overrides clarity."),
    ("factuality-before-naturalness", "Naturalness never overrides factuality."),
    ("attribution-preserved", "Naturalness never overrides attribution."),
    ("legal-status-preserved", "Naturalness never overrides legal status."),
    ("sensitivity-preserved", "Naturalness never overrides sensitivity."),
    ("grammar-not-authenticity", "Correct grammar does not guarantee authenticity."),
    ("authenticity-not-incoherence", "Authenticity cannot excuse incoherence."),
    ("inversion-clear", "Inversion requires immediate comprehension."),
    ("ellipsis-recoverable", "Ellipsis requires recoverable meaning."),
    ("fragments-functional", "Fragments require a spoken function."),
    ("repetition-functional", "Repetition requires an editorial function."),
    ("slang-contextual", "Slang requires contextual compatibility."),
    ("jargon-justified", "Jargon requires precision or audience justification."),
    ("borrowings-contextual", "Borrowings are not automatically rejected."),
    ("calques-reviewed", "Calques are not automatically accepted."),
    ("press-not-default", "Press formulas are not default speech."),
    ("bureaucracy-shows-agency", "Bureaucratic formulas cannot hide agency."),
    ("academic-not-default", "Academic framing is not default explanation."),
    ("legal-precision-binding", "Legal precision remains binding."),
    ("entity-identity", "Entity shortening preserves identity."),
    ("demonstratives-resolvable", "Demonstratives remain resolvable."),
    ("colloquial-dignity", "Colloquial references preserve dignity."),
    ("satire-upstream-owned", "Satire remains attached to validated opportunities."),
    ("no-payoff-explanation", "Payoff explanation is never added automatically."),
    ("indicators-not-authorship", "AI-likeness indicators do not claim authorship."),
    ("bounded-examples", "Canonical examples remain short and bounded."),
    ("guidance-lineage", "Profile guidance retains evidence lineage."),
    (
        "active-guidance-status",
        "Only established or explicit editor guidance tunes assessments.",
    ),
    ("local-corrections-local", "Local corrections remain local."),
    ("permanence-explicit", "Permanent editor rules require explicit permanence."),
    ("guidance-bounded", "Guidance cannot mutate canonical safeguards."),
    ("upstream-block-propagates", "Upstream blocked readiness propagates."),
    ("upstream-review-propagates", "Relevant upstream review propagates."),
    ("readiness-derived", "Assessment readiness is derived."),
    ("rendering-deterministic", "Renderer output is deterministic."),
    ("editor-final-authority", "Editor-in-Chief retains final authority."),
)

CANONICAL_ROMANIAN_CONVERSATION_RULES = tuple(
    RomanianConversationRule(identifier, statement, index not in {10, 18, 19, 30, 39})
    for index, (identifier, statement) in enumerate(_STATEMENTS, start=1)
)
