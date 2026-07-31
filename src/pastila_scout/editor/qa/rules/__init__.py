"""Private deterministic editorial rules subsystem (M6C.5B)."""

from pastila_scout.editor.qa.rules.concrete import build_supported_rules
from pastila_scout.editor.qa.rules.context import RuleContext, TextMetrics
from pastila_scout.editor.qa.rules.engine import RuleEngine
from pastila_scout.editor.qa.rules.policy import DeterministicEditorialRulePolicy
from pastila_scout.editor.qa.rules.registry import RuleRegistry, RuleSet
from pastila_scout.editor.qa.rules.reviewer import DeterministicRulesReviewer

__all__ = [
    "DeterministicEditorialRulePolicy",
    "DeterministicRulesReviewer",
    "RuleContext",
    "RuleEngine",
    "RuleRegistry",
    "RuleSet",
    "TextMetrics",
    "build_supported_rules",
]
