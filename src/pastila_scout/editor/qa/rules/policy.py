"""Validated objective thresholds shared by deterministic rules."""

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import ReviewScope, fingerprint


class LiteralPhraseRule(FrozenModel):
    phrase: str = Field(min_length=1, max_length=200)
    scopes: tuple[ReviewScope, ...] = (ReviewScope.EPISODE,)

    @field_validator("scopes")
    @classmethod
    def canonical_scopes(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("phrase scopes must be unique")
        return tuple(sorted(value, key=lambda item: item.value))


class ScopeLimit(FrozenModel):
    scope: ReviewScope
    maximum: int = Field(ge=0)


class DeterministicEditorialRulePolicy(FrozenModel):
    opening_max_words: int = Field(default=120, gt=0)
    opening_max_characters: int = Field(default=900, gt=0)
    closing_max_words: int = Field(default=120, gt=0)
    closing_max_characters: int = Field(default=900, gt=0)
    story_max_words: int = Field(default=450, gt=0)
    story_max_characters: int = Field(default=3200, gt=0)
    transition_max_words: int = Field(default=80, gt=0)
    transition_max_characters: int = Field(default=600, gt=0)
    episode_max_words: int = Field(default=2500, gt=0)
    episode_max_characters: int = Field(default=18000, gt=0)
    minimum_story_count: int = Field(default=1, gt=0)
    maximum_story_count: int = Field(default=12, gt=0)
    maximum_identical_sentence_occurrences: int = Field(default=1, gt=0)
    maximum_repeated_phrase_occurrences: int = Field(default=2, gt=0)
    repeated_phrase_minimum_words: int = Field(default=4, ge=2)
    repeated_phrase_maximum_words: int = Field(default=8, ge=2)
    maximum_consecutive_punctuation: int = Field(default=3, gt=0)
    maximum_blank_lines: int = Field(default=2, ge=0)
    maximum_line_length: int = Field(default=160, gt=10)
    maximum_placeholder_count: int = Field(default=0, ge=0)
    maximum_findings_per_rule: int = Field(default=50, gt=0, le=500)
    maximum_total_findings: int = Field(default=500, gt=0, le=5000)
    maximum_occurrences_per_finding: int = Field(default=10, gt=0, le=100)
    maximum_evidence_items: int = Field(default=5, gt=0, le=10)
    maximum_excerpt_characters: int = Field(default=200, gt=0, le=300)
    required_rhetorical_question_scopes: tuple[ReviewScope, ...] = ()
    required_phrase_rules: tuple[LiteralPhraseRule, ...] = ()
    forbidden_phrase_rules: tuple[LiteralPhraseRule, ...] = ()
    maximum_profanity_count_by_scope: tuple[ScopeLimit, ...] = ()
    profanity_literals: tuple[str, ...] = ()

    @field_validator("profanity_literals")
    @classmethod
    def unique_literals(cls, value):
        cleaned = tuple(
            sorted({item.casefold().strip() for item in value if item.strip()})
        )
        if len(cleaned) != len(value):
            raise ValueError("profanity literals must be nonempty and unique")
        return cleaned

    @field_validator("required_rhetorical_question_scopes")
    @classmethod
    def canonical_question_scopes(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("rhetorical question scopes must be unique")
        return tuple(sorted(value, key=lambda item: item.value))

    @field_validator("required_phrase_rules", "forbidden_phrase_rules")
    @classmethod
    def canonical_phrase_rules(cls, value):
        keys = tuple(
            (item.phrase.casefold(), tuple(scope.value for scope in item.scopes))
            for item in value
        )
        if len(keys) != len(set(keys)):
            raise ValueError("phrase rules must be unique")
        return tuple(item for _, item in sorted(zip(keys, value, strict=True)))

    @field_validator("maximum_profanity_count_by_scope")
    @classmethod
    def canonical_scope_limits(cls, value):
        if len(value) != len({item.scope for item in value}):
            raise ValueError("profanity scope limits must be unique")
        return tuple(sorted(value, key=lambda item: item.scope.value))

    @model_validator(mode="after")
    def phrase_size_bounds_are_ordered(self):
        if self.repeated_phrase_minimum_words > self.repeated_phrase_maximum_words:
            raise ValueError("repeated phrase minimum cannot exceed maximum")
        return self

    @property
    def policy_fingerprint(self) -> str:
        return fingerprint(self)
