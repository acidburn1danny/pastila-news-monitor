"""Canonical, stable decision-rule vocabulary for pre-writing judgment."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecisionRule:
    rule_id: str
    statement: str


CANONICAL_DECISION_RULES = tuple(
    DecisionRule(f"decision-rule-{number:02d}", statement)
    for number, statement in enumerate(
        (
            "Preserve indispensable facts.",
            "Attribute allegations and disputed claims explicitly.",
            "Hold materially misleading unresolved claims for verification.",
            "Do not remove context whose absence changes factual meaning.",
            "Compress detail only when meaning survives.",
            "Remove duplicated explanations.",
            "Lead with the clearest accurate account of what happened.",
            "Introduce consequence early when it establishes relevance.",
            "Delay secondary detail that interrupts initial comprehension.",
            "Separate facts from commentary.",
            "Preserve quotations only when their exact wording matters.",
            "Never mutate a quotation.",
            "Identify contradiction only from supplied evidence.",
            "Never infer motive without evidence.",
            "Never turn correlation into causation.",
            "Never present uncertainty as certainty.",
            "Protect victims and vulnerable people from gratuitous exposure.",
            "Escalate serious tonal ambiguity to the Editor-in-Chief.",
            "Escalate profile guidance that conflicts with fixed Persona boundaries.",
            "Reject pacing improvements that materially distort the story.",
            "Prefer one clear explanation over multiple partial explanations.",
            "Identify missing response, attribution, chronology, or verification.",
            "Represent source disagreement explicitly when editorially material.",
            "Do not manufacture balance where evidence is not symmetrical.",
            "Do not omit a verified response that weakens a preferred angle.",
        ),
        start=1,
    )
)
