from pathlib import Path

import pytest

from pastila_scout.config import (
    ConfigError,
    SourceCategory,
    SourceConfig,
    load_application_config,
    load_config,
    load_configuration,
    load_sources_config,
)


def test_ai_configuration_loads_only_from_application_config(tmp_path: Path) -> None:
    application = write_config(
        tmp_path / "config.yaml",
        """ai:
  provider: openai
  model: test-model
  temperature: 0.2
  max_retries: 1
  retry_delay: 0.0
  prompt_version: test-v2
  enable_ai: true
cache:
  ai_verification_directory: cache/ai
""",
    )
    write_config(tmp_path / "sources.yaml", "sources: []\n")

    config = load_configuration(application)

    assert config.ai.model == "test-model"
    assert config.ai.prompt_version == "test-v2"
    assert config.cache.ai_verification_directory == Path("cache/ai")
    assert config.sources == ()


def test_sources_reject_misplaced_ai_configuration(tmp_path: Path) -> None:
    sources = write_config(
        tmp_path / "sources.yaml",
        """ai:
  enable_ai: true
sources: []
""",
    )

    with pytest.raises(ConfigError, match="AI settings.*config/config.yaml"):
        load_sources_config(sources)
    with pytest.raises(ConfigError, match="AI settings.*config/config.yaml"):
        load_config(sources)


def test_missing_application_config_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Could not read configuration file"):
        load_application_config(tmp_path / "config.yaml")


def test_source_alias_metadata_is_available_after_composition(tmp_path: Path) -> None:
    application = write_config(tmp_path / "config.yaml", "sources_file: sources.yaml\n")
    write_config(
        tmp_path / "sources.yaml",
        """sources:
  - id: stiri
    name: Știri România
    adapter: rss
    url: https://example.com/feed
    enabled: true
    prioritate: 2
    source_category: [Politica, Social]
""",
    )

    source = load_configuration(application).sources[0]

    assert source.type == "rss"
    assert source.priority == 2
    assert source.categories == (SourceCategory.POLITICA, SourceCategory.SOCIAL)


def write_config(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_valid_configuration(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        """
sources:
  - id: local-news
    name: Local News
    type: rss
    url: https://example.com/feed.xml
    enabled: true
    categories: [Politica, Social]
  - id: local-site
    name: Local Site
    type: html
    url: https://example.com/news
    enabled: false
    categories: [Diverse]
""",
    )

    config = load_config(config_path)

    assert len(config.sources) == 2
    assert config.sources[0].id == "local-news"
    assert config.sources[0].type == "rss"
    assert config.sources[0].enabled is True
    assert config.sources[1].type == "html"


def test_rejects_unsupported_source_type(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        """
sources:
  - id: unsupported
    name: Unsupported source
    type: api
    url: https://example.com/api
    enabled: false
""",
    )

    with pytest.raises(ConfigError, match="type"):
        load_config(config_path)


def test_rejects_missing_required_field(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        """
sources:
  - id: missing-url
    name: Missing URL
    type: html
    enabled: false
""",
    )

    with pytest.raises(ConfigError, match="url"):
        load_config(config_path)


def test_enabled_html_source_requires_selectors() -> None:
    with pytest.raises(ValueError, match="list_selector.*link_selector"):
        SourceConfig(
            id="site",
            name="Site",
            type="html",
            url="https://example.com/news",
            enabled=True,
            categories=["Diverse"],
        )


def test_html_source_accepts_selectors_and_positive_max_items() -> None:
    source = SourceConfig(
        id="site",
        name="Site",
        type="html",
        url="https://example.com/news",
        enabled=True,
        categories=["Social"],
        list_selector="article",
        link_selector="a",
        max_items=10,
    )

    assert source.list_selector == "article"
    assert source.max_items == 10

    with pytest.raises(ValueError, match="greater than 0"):
        SourceConfig.model_validate({**source.model_dump(), "max_items": 0})


def test_rss_source_remains_valid_without_html_fields() -> None:
    source = SourceConfig(
        id="feed",
        name="Feed",
        type="rss",
        url="https://example.com/feed.xml",
        enabled=True,
        categories=["Diverse"],
    )

    assert source.list_selector is None


def test_checked_in_config_contains_small_real_rss_source_set() -> None:
    config = load_config(Path("config/sources.yaml"))

    assert len(config.sources) == 21
    assert len({source.id for source in config.sources}) == len(config.sources)
    assert all(source.categories for source in config.sources)
    assert {source.id for source in config.sources} == {
        "digi24",
        "hotnews",
        "g4media",
        "newsro",
        "adevarul",
        "libertatea",
        "observatornews",
        "antena3",
        "europalibera",
        "rfi",
        "recorder",
        "pressone",
        "economica",
        "profit",
        "ziare",
        "reuters",
        "ap",
        "bbc_world",
        "politico_europe",
        "cnn",
        "msnow",
    }
    assert all("example.com" not in source.url for source in config.sources)
    assert config.polling.max_article_age_hours == 168
    assert config.sources[0].max_articles_per_poll == 60
    assert config.polling.concurrency == 3

    international = {
        source.id: source
        for source in config.sources
        if SourceCategory.EXTERNE in source.categories
    }
    assert set(international) == {
        "reuters",
        "ap",
        "bbc_world",
        "politico_europe",
        "cnn",
        "msnow",
    }
    assert all(source.max_articles_per_poll == 50 for source in international.values())
    assert {source.id for source in international.values() if source.enabled} == {
        "bbc_world",
        "politico_europe",
        "msnow",
    }
    assert all(
        source.disabled_reason
        for source in international.values()
        if not source.enabled
    )


def test_global_polling_defaults_are_applied_to_legacy_configuration(
    tmp_path: Path,
) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        """sources:
  - id: feed
    name: Feed
    type: rss
    url: https://example.com/feed
    enabled: true
    categories: [Diverse]
""",
    )

    config = load_config(config_path)

    assert config.polling.max_article_age_hours == 168
    assert config.polling.max_articles_per_source == 100
    assert config.polling.accept_articles_without_date is True
    assert config.polling.future_date_tolerance_minutes == 60
    assert config.event_matching.enabled is True
    assert config.event_matching.lookback_hours == 168
    assert config.event_matching.similarity_threshold == 0.72


def test_event_matching_configuration_and_invalid_values(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        """event_matching:
  enabled: false
  lookback_hours: 24
  similarity_threshold: 0.9
sources: []
""",
    )
    config = load_config(config_path)
    assert config.event_matching.enabled is False
    assert config.event_matching.lookback_hours == 24
    assert config.event_matching.similarity_threshold == 0.9

    config_path.write_text(
        "event_matching:\n  lookback_hours: 0\n  similarity_threshold: 1.2\nsources: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="event_matching"):
        load_config(config_path)


def test_source_polling_overrides_are_loaded(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        """polling:
  max_article_age_hours: 120
  max_articles_per_source: 50
  accept_articles_without_date: true
  future_date_tolerance_minutes: 30
sources:
  - id: feed
    name: Feed
    type: rss
    url: https://example.com/feed
    enabled: true
    categories: [Economie]
    max_article_age_hours: 24
    max_articles_per_poll: 5
    accept_articles_without_date: false
""",
    )

    source = load_config(config_path).sources[0]

    assert source.max_article_age_hours == 24
    assert source.max_articles_per_poll == 5
    assert source.accept_articles_without_date is False


@pytest.mark.parametrize(
    "field_value",
    [
        "max_article_age_hours: 0",
        "max_articles_per_source: 0",
        "future_date_tolerance_minutes: -1",
    ],
)
def test_rejects_invalid_global_polling_values(
    tmp_path: Path, field_value: str
) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        f"""polling:
  {field_value}
sources: []
""",
    )

    with pytest.raises(ConfigError, match=field_value.split(":")[0]):
        load_config(config_path)


@pytest.mark.parametrize(
    "override",
    ["max_article_age_hours: 0", "max_articles_per_poll: 0"],
)
def test_rejects_invalid_source_polling_overrides(
    tmp_path: Path, override: str
) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        f"""sources:
  - id: feed
    name: Feed
    type: rss
    url: https://example.com/feed
    enabled: true
    categories: [Diverse]
    {override}
""",
    )

    with pytest.raises(ConfigError, match=override.split(":")[0]):
        load_config(config_path)


def test_valid_multiple_romanian_categories() -> None:
    source = SourceConfig(
        id="news",
        name="News",
        type="rss",
        url="https://example.com/feed",
        enabled=True,
        categories=[
            "Politica",
            "Social",
            "Conspiratii",
            "Economie",
            "CanCan",
            "Externe",
            "Diverse",
        ],
    )

    assert source.categories == tuple(SourceCategory)


@pytest.mark.parametrize(
    ("categories", "message"),
    [
        (None, "categories"),
        ([], "at least 1"),
        (["politica"], "categories"),
        (["Unknown"], "categories"),
        (["Social", "Social"], "duplicates"),
        ([1], "categories"),
    ],
)
def test_rejects_invalid_source_categories(categories: object, message: str) -> None:
    values: dict[str, object] = {
        "id": "news",
        "name": "News",
        "type": "rss",
        "url": "https://example.com/feed",
        "enabled": True,
    }
    if categories is not None:
        values["categories"] = categories

    with pytest.raises(ValueError, match=message):
        SourceConfig.model_validate(values)


@pytest.mark.parametrize("concurrency", [1, 3, 10])
def test_accepts_bounded_concurrency(tmp_path: Path, concurrency: int) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        f"polling:\n  concurrency: {concurrency}\nsources: []\n",
    )

    assert load_config(config_path).polling.concurrency == concurrency


def test_default_concurrency_is_three(tmp_path: Path) -> None:
    config_path = write_config(tmp_path / "sources.yaml", "sources: []\n")

    assert load_config(config_path).polling.concurrency == 3


@pytest.mark.parametrize("concurrency", ["0", "11", "2.5"])
def test_rejects_invalid_concurrency(tmp_path: Path, concurrency: str) -> None:
    config_path = write_config(
        tmp_path / "sources.yaml",
        f"polling:\n  concurrency: {concurrency}\nsources: []\n",
    )

    with pytest.raises(ConfigError, match="concurrency"):
        load_config(config_path)
