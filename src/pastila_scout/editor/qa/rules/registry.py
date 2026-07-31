"""Side-effect-free immutable rule registry and selected rule sets."""

from pydantic import Field, field_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint
from pastila_scout.editor.qa.rules.base import EditorialRule
from pastila_scout.editor.qa.rules.models import RuleCategory


class RuleRegistrationError(ValueError):
    pass


class RuleSet(FrozenModel):
    name: str
    rule_keys: tuple[str, ...] = Field(min_length=1)
    categories: tuple[RuleCategory, ...]
    rule_set_fingerprint: str

    @field_validator("rule_keys")
    @classmethod
    def unique_rules(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("rule set contains duplicate rules")
        return value


class RuleRegistry:
    """Read-only registry with deterministic order and explicit construction."""

    def __init__(self, rules: tuple[EditorialRule, ...]):
        keys = tuple(_key(rule) for rule in rules)
        if len(keys) != len(set(keys)):
            raise RuleRegistrationError("rule ID/version pairs must be unique")
        ids = tuple(rule.rule_id for rule in rules)
        if len(ids) != len(set(ids)):
            raise RuleRegistrationError("rule IDs must be unique")
        self._rules = tuple(
            sorted(rules, key=lambda rule: (rule.category.value, rule.rule_id))
        )

    @property
    def rules(self) -> tuple[EditorialRule, ...]:
        return self._rules

    @property
    def registry_fingerprint(self) -> str:
        return fingerprint(tuple(_descriptor(rule) for rule in self._rules))

    def get(self, rule_id: str) -> EditorialRule:
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        raise KeyError(f"unknown editorial rule: {rule_id}")

    def select(
        self, *, name: str = "m6c.5b-default", rule_ids: tuple[str, ...] | None = None
    ) -> RuleSet:
        if rule_ids is None:
            selected = self._rules
        else:
            if len(rule_ids) != len(set(rule_ids)):
                raise RuleRegistrationError("selected rule IDs must be unique")
            requested = set(rule_ids)
            selected = tuple(rule for rule in self._rules if rule.rule_id in requested)
            unknown = requested - {rule.rule_id for rule in selected}
            if unknown:
                raise RuleRegistrationError(
                    f"rule set references unknown rules: {','.join(sorted(unknown))}"
                )
        keys = tuple(_key(rule) for rule in selected)
        categories = tuple(dict.fromkeys(rule.category for rule in selected))
        return RuleSet(
            name=name,
            rule_keys=keys,
            categories=categories,
            rule_set_fingerprint=fingerprint(
                {"name": name, "rules": tuple(_descriptor(rule) for rule in selected)}
            ),
        )

    def resolve(self, rule_set: RuleSet) -> tuple[EditorialRule, ...]:
        by_key = {_key(rule): rule for rule in self._rules}
        try:
            return tuple(by_key[key] for key in rule_set.rule_keys)
        except KeyError as error:
            raise RuleRegistrationError(
                f"rule set references unknown rule: {error.args[0]}"
            ) from error


def _key(rule: EditorialRule) -> str:
    return f"{rule.rule_id}@{rule.rule_version}"


def _descriptor(rule: EditorialRule):
    return {
        "rule_id": rule.rule_id,
        "rule_version": rule.rule_version,
        "category": rule.category,
        "description": rule.description,
        "default_severity": rule.default_severity,
        "default_blocking": rule.blocking,
        "default_enabled": getattr(rule, "default_enabled", True),
        "operational_status": getattr(rule, "operational_status", None),
        "supported_scopes": tuple(
            sorted(rule.supported_scopes, key=lambda item: item.value)
        ),
        "capabilities": tuple(sorted(rule.capabilities, key=lambda item: item.value)),
        "implementation_key": getattr(rule, "check", None),
    }
