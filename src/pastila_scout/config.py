"""Configuration models and YAML loading for Scout sources."""

from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)


class SourceCategory(StrEnum):
    """Controlled Romanian vocabulary for broad source coverage."""

    POLITICA = "Politica"
    SOCIAL = "Social"
    CONSPIRATII = "Conspiratii"
    ECONOMIE = "Economie"
    CANCAN = "CanCan"
    EXTERNE = "Externe"
    DIVERSE = "Diverse"


class SourceConfig(BaseModel):
    """A validated news source definition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    type: Literal["rss", "html"] = Field(
        validation_alias=AliasChoices("type", "adapter")
    )
    url: str
    enabled: bool
    disabled_reason: str | None = None
    categories: tuple[SourceCategory, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("categories", "source_category"),
    )
    list_selector: str | None = None
    link_selector: str | None = None
    title_selector: str | None = None
    summary_selector: str | None = None
    date_selector: str | None = None
    base_url: str | None = None
    max_items: int | None = Field(default=None, gt=0, strict=True)
    max_article_age_hours: float | None = Field(default=None, gt=0, strict=True)
    max_articles_per_poll: int | None = Field(default=None, gt=0, strict=True)
    accept_articles_without_date: bool | None = None
    priority: int = Field(
        default=1,
        ge=1,
        strict=True,
        validation_alias=AliasChoices("prioritate", "priority"),
    )

    @model_validator(mode="after")
    def validate_enabled_html_selectors(self) -> SourceConfig:
        """Require selectors and unique categories where applicable."""

        if self.type == "html" and self.enabled:
            missing = [
                field
                for field in ("list_selector", "link_selector")
                if not getattr(self, field) or not getattr(self, field).strip()
            ]
            if missing:
                raise ValueError(
                    "enabled HTML sources require " + " and ".join(missing)
                )
        if len(self.categories) != len(set(self.categories)):
            raise ValueError("source categories must not contain duplicates")
        return self


class PollingConfig(BaseModel):
    """Global freshness and per-run intake defaults."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_article_age_hours: float = Field(default=168, gt=0, strict=True)
    max_articles_per_source: int = Field(default=100, gt=0, strict=True)
    accept_articles_without_date: bool = True
    future_date_tolerance_minutes: float = Field(default=60, ge=0, strict=True)
    concurrency: int = Field(default=3, ge=1, le=10, strict=True)


class EventMatchingConfig(BaseModel):
    """Deterministic local event matching settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True
    lookback_hours: float = Field(default=168, gt=0, strict=True)
    similarity_threshold: float = Field(default=0.72, ge=0, le=1, strict=True)


class AIConfig(BaseModel):
    """Provider-neutral settings for advisory event verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["openai", "ollama"] = "openai"
    model: str = "gpt-4.1-mini"
    ollama_base_url: str = "http://localhost:11434"
    temperature: float = Field(default=0.0, ge=0, le=2, strict=True)
    max_retries: int = Field(default=2, ge=0, le=2, strict=True)
    retry_delay: float = Field(default=3.0, ge=0, strict=True)
    prompt_version: str = "event-verification-v1"
    enable_ai: bool = False


class CacheConfig(BaseModel):
    """Persistent application cache settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ai_verification_directory: Path = Path("data/ai_cache")
    ai_editorial_directory: Path = Path("data/ai_cache/editorial")


class ScoringConfig(BaseModel):
    """Deterministic and advisory editorial ranking settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    deterministic_schema_version: str = "event-score-v1"
    editorial_schema_version: str = "editorial-score-v1"
    editorial_prompt_version: str = "editorial-ranking-v1"
    deterministic_weight: float = Field(default=0.55, ge=0, le=1, strict=True)
    ai_weight: float = Field(default=0.45, ge=0, le=1, strict=True)
    input_cost_per_million_tokens: float | None = Field(default=None, ge=0)
    output_cost_per_million_tokens: float | None = Field(default=None, ge=0)
    category_weights: dict[SourceCategory, float] = Field(
        default_factory=lambda: {
            SourceCategory.POLITICA: 1.0,
            SourceCategory.SOCIAL: 0.9,
            SourceCategory.CONSPIRATII: 0.95,
            SourceCategory.ECONOMIE: 0.85,
            SourceCategory.CANCAN: 0.75,
            SourceCategory.EXTERNE: 0.8,
            SourceCategory.DIVERSE: 0.6,
        }
    )

    @model_validator(mode="after")
    def validate_score_weights(self) -> ScoringConfig:
        if abs((self.deterministic_weight + self.ai_weight) - 1.0) > 1e-9:
            raise ValueError("deterministic_weight and ai_weight must total 1")
        if any(value < 0 or value > 1 for value in self.category_weights.values()):
            raise ValueError("category weights must be between 0 and 1")
        return self


class ApplicationConfig(BaseModel):
    """Application settings loaded exclusively from config/config.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    polling: PollingConfig = PollingConfig()
    event_matching: EventMatchingConfig = EventMatchingConfig()
    ai: AIConfig = AIConfig()
    cache: CacheConfig = CacheConfig()
    scoring: ScoringConfig = ScoringConfig()
    sources_file: Path = Path("sources.yaml")


class SourcesConfig(BaseModel):
    """Strict source-only configuration document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sources: tuple[SourceConfig, ...]


class ScoutConfig(ApplicationConfig):
    """Resolved runtime configuration composed from application and sources."""

    sources: tuple[SourceConfig, ...]


class ConfigError(ValueError):
    """Raised when a Scout configuration file cannot be loaded or validated."""


def _read_yaml(path: Path) -> object:
    """Read one UTF-8 YAML document with consistent errors."""

    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read configuration file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in configuration file {path}: {exc}") from exc


def load_application_config(path: Path) -> ApplicationConfig:
    """Load application and AI settings from config.yaml."""

    raw_config = _read_yaml(path)
    try:
        return ApplicationConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise ConfigError(
            f"Invalid application configuration in {path}: {exc}"
        ) from exc


def load_sources_config(path: Path) -> SourcesConfig:
    """Load a strict source-only document and reject misplaced AI settings."""

    raw_config = _read_yaml(path)
    if isinstance(raw_config, dict) and "ai" in raw_config:
        raise ConfigError(
            f"Invalid source configuration in {path}: AI settings are not allowed "
            "in sources.yaml; move them to config/config.yaml"
        )
    try:
        return SourcesConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise ConfigError(f"Invalid source configuration in {path}: {exc}") from exc


def load_configuration(
    application_path: Path,
    *,
    sources_path: Path | None = None,
) -> ScoutConfig:
    """Compose application settings and source metadata through one manager."""

    application = load_application_config(application_path)
    source_file = sources_path or application.sources_file
    if sources_path is None and not source_file.is_absolute():
        source_file = application_path.parent / source_file
    sources = load_sources_config(source_file)
    return ScoutConfig(
        **application.model_dump(exclude={"sources_file"}),
        sources_file=source_file,
        sources=sources.sources,
    )


def load_config(path: Path) -> ScoutConfig:
    """Load runtime configuration with compatibility for legacy combined files.

    If ``path`` is config.yaml, the strict split manager is used. A legacy
    combined source document remains supported unless it contains misplaced AI
    settings. The checked-in sources.yaml automatically discovers its sibling
    config.yaml.

    Args:
        path: Path to a YAML configuration file.

    Raises:
        ConfigError: If the file cannot be read, contains invalid YAML, or does
            not match the expected configuration schema.
    """

    if path.name.casefold() == "config.yaml":
        return load_configuration(path)
    if (
        path.name.casefold() == "sources.yaml"
        and (path.parent / "config.yaml").is_file()
    ):
        return load_configuration(path.parent / "config.yaml", sources_path=path)

    raw_config = _read_yaml(path)
    if isinstance(raw_config, dict) and "ai" in raw_config:
        raise ConfigError(
            f"Invalid source configuration in {path}: AI settings are not allowed "
            "in sources.yaml; move them to config/config.yaml"
        )

    try:
        return ScoutConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration in {path}: {exc}") from exc
