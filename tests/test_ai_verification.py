"""Focused tests for provider-neutral AI verification and its cache."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.ai.cache import FileVerificationCache, verification_cache_key
from pastila_scout.ai.provider import (
    ProviderError,
    StructuredAIResponse,
    resolve_openai_api_key,
)
from pastila_scout.ai.verification import EventVerifier, confirms_same_event
from pastila_scout.cli import main
from pastila_scout.config import AIConfig
from pastila_scout.core.event_verification import run_event_verification
from pastila_scout.database import initialize_database, open_database
from pastila_scout.models.ai import EventVerificationRequest, VerificationArticle
from pastila_scout.models.reconciliation import ReconciliationSnapshot
from pastila_scout.reporting.verification import (
    render_verification_console,
    write_verification_reports,
)


class FakeProvider:
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = responses

    def verify(self, request: EventVerificationRequest) -> str:
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class DiagnosticProvider:
    def verify_with_diagnostics(
        self, request: EventVerificationRequest
    ) -> StructuredAIResponse:
        return StructuredAIResponse(_decision(), 120, 30, 150)


def _article(article_id: int, title: str = "știre românească") -> VerificationArticle:
    return VerificationArticle(
        article_id=article_id,
        event_id=article_id,
        normalized_title=title,
        summary="Descriere confirmată",
        published_at="2026-07-26T10:00:00+00:00",
        source_id=f"source-{article_id}",
        source_name=f"Sursa {article_id}",
        url=f"https://example.com/{article_id}",
        categories=("Social",),
    )


def _request() -> EventVerificationRequest:
    return EventVerificationRequest(
        left=_article(1), right=_article(2), deterministic_similarity=0.9
    )


def _decision(**updates: object) -> str:
    payload = {
        "same_event": True,
        "ai_similarity_score": 91,
        "same_people": None,
        "same_institution": True,
        "same_location": None,
        "same_context": True,
        "reasoning": "Aceeași știre și același context.",
    }
    payload.update(updates)
    return json.dumps(payload, ensure_ascii=False)


def _config(tmp_path: Path, **updates: object) -> AIConfig:
    return AIConfig(
        enable_ai=True,
        retry_delay=0.0,
        **updates,
    )


def test_valid_structured_response_and_threshold(tmp_path: Path) -> None:
    config = _config(tmp_path)
    verifier = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "cache"),
        FakeProvider([_decision()]),
        api_key_available=True,
    )
    result = verifier.verify(_request())
    assert result.status == "success"
    assert confirms_same_event(result)
    assert result.reasoning.endswith("context.")


def test_verification_decision_usage_and_cache_diagnostics(tmp_path: Path) -> None:
    config = _config(tmp_path)
    verifier = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "cache"),
        DiagnosticProvider(),
        api_key_available=True,
        input_cost_per_million_tokens=1.0,
        output_cost_per_million_tokens=2.0,
    )
    report = run_event_verification(
        (_request(),), verifier, database_path="readonly.db"
    )
    record = report.records[0]
    assert record.confirmed_same_event is True
    assert record.decision is not None
    assert record.decision.reason == "verified"
    assert record.decision.threshold == 85
    assert record.result.usage.total_tokens == 150
    assert record.result.usage.provider_latency_ms is not None
    assert record.result.usage.estimated_cost == 0.00018
    assert record.result.cache_diagnostics is not None
    assert record.result.cache_diagnostics.fingerprint_version == "verification-v1"
    assert report.usage.total_tokens == 150


def test_malformed_response_is_rejected(tmp_path: Path) -> None:
    config = _config(tmp_path)
    verifier = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "cache"),
        FakeProvider(['{"same_event": true}']),
        api_key_available=True,
    )
    assert verifier.verify(_request()).status == "invalid_response"


def test_missing_key_and_disabled_fallbacks(tmp_path: Path) -> None:
    config = _config(tmp_path)
    missing = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "cache"),
        None,
        api_key_available=False,
    ).verify(_request())
    disabled_config = config.model_copy(update={"enable_ai": False})
    disabled = EventVerifier(
        disabled_config,
        FileVerificationCache(tmp_path / "other"),
        None,
        api_key_available=True,
    ).verify(_request())
    assert missing.status == "missing_api_key"
    assert disabled.status == "disabled"
    assert not confirms_same_event(disabled)


def test_retry_success_and_exhaustion(tmp_path: Path) -> None:
    config = _config(tmp_path, max_retries=2)
    success = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "success"),
        FakeProvider([ProviderError("temporary"), _decision()]),
        api_key_available=True,
        sleep=lambda _: None,
    ).verify(_request())
    exhausted = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "failed"),
        FakeProvider([ProviderError("down")] * 3),
        api_key_available=True,
        sleep=lambda _: None,
    ).verify(_request())
    assert success.retry_count == 1
    assert exhausted.status == "retry_exhausted"
    assert exhausted.retry_count == 2


def test_cache_key_order_and_invalidation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    request = _request()
    reversed_request = request.model_copy(
        update={"left": request.right, "right": request.left}
    )
    assert verification_cache_key(request, config) == verification_cache_key(
        reversed_request, config
    )
    assert verification_cache_key(request, config) != verification_cache_key(
        request, config.model_copy(update={"model": "another-model"})
    )
    assert verification_cache_key(request, config) != verification_cache_key(
        request, config.model_copy(update={"prompt_version": "v2"})
    )
    changed = request.model_copy(
        update={"left": request.left.model_copy(update={"summary": "Alt conținut"})}
    )
    assert verification_cache_key(request, config) != verification_cache_key(
        changed, config
    )


def test_corrupt_cache_is_regenerated_as_utf8(tmp_path: Path) -> None:
    config = _config(tmp_path)
    key = verification_cache_key(_request(), config)
    cache_directory = tmp_path / "cache"
    cache_directory.mkdir()
    (cache_directory / f"{key}.json").write_text("{bad", encoding="utf-8")
    verifier = EventVerifier(
        config,
        FileVerificationCache(cache_directory),
        FakeProvider([_decision()]),
        api_key_available=True,
    )
    assert verifier.verify(_request()).status == "success"
    content = (cache_directory / f"{key}.json").read_text(encoding="utf-8")
    assert "Aceeași știre" in content


def test_cached_result_prevents_second_provider_request(tmp_path: Path) -> None:
    config = _config(tmp_path)
    provider = FakeProvider([_decision()])
    verifier = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "cache"),
        provider,
        api_key_available=True,
    )
    assert verifier.verify(_request()).status == "success"
    assert verifier.verify(_request()).status == "cache_hit"
    assert verifier.ai_requests == 1


def test_threshold_rejects_false_dimension(tmp_path: Path) -> None:
    config = _config(tmp_path)
    verifier = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "cache"),
        FakeProvider([_decision(same_location=False)]),
        api_key_available=True,
    )
    assert not confirms_same_event(verifier.verify(_request()))


def test_compact_detailed_and_utf8_reports(tmp_path: Path) -> None:
    config = _config(tmp_path)
    verifier = EventVerifier(
        config,
        FileVerificationCache(tmp_path / "cache"),
        FakeProvider([_decision()]),
        api_key_available=True,
        now=lambda: datetime(2026, 7, 26, tzinfo=UTC),
    )
    report = run_event_verification((_request(),), verifier, database_path="știri.db")
    compact = render_verification_console(report, details=False)
    detailed = render_verification_console(report, details=True)
    assert not any(line.startswith("Events ") for line in compact)
    assert any(line.startswith("Events ") for line in detailed)
    json_path, text_path = write_verification_reports(report, tmp_path / "reports")
    json_text = json_path.read_text(encoding="utf-8")
    text_report = text_path.read_text(encoding="utf-8")
    assert "românească" in json_text
    assert '"decision"' in json_text
    assert "Aceeași știre" in text_report
    assert "Verification fields" in text_report


def test_environment_key_precedes_dotenv(tmp_path: Path, monkeypatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("OPENAI_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    assert resolve_openai_api_key(str(dotenv)) == "environment-key"


def test_cli_is_read_only_and_writes_compact_reports(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    database = tmp_path / "scout.db"
    with open_database(database) as connection:
        initialize_database(connection)
    before = database.read_bytes()
    config = tmp_path / "config.yaml"
    config.write_text(
        """
ai:
  enable_ai: false
""",
        encoding="utf-8",
    )
    (tmp_path / "sources.yaml").write_text(
        """sources:
  - id: romanian-source
    name: Știri România
    adapter: rss
    url: https://example.com/feed
    enabled: true
    prioritate: 2
    source_category: [Politica, Social]
""",
        encoding="utf-8",
    )
    captured_metadata: dict[str, tuple[tuple[str, ...], int]] = {}

    def capture_snapshot(connection, source_metadata):
        captured_metadata.update(source_metadata)
        return ReconciliationSnapshot(events=(), articles=())

    monkeypatch.setattr(
        "pastila_scout.cli.load_reconciliation_snapshot", capture_snapshot
    )
    reports = tmp_path / "reports"
    exit_code = main(
        [
            "verify-event-candidates",
            "--database",
            str(database),
            "--config",
            str(config),
            "--output-directory",
            str(reports),
            "--no-ai",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Candidate pairs: 0" in output
    assert "Events " not in output
    assert len(list(reports.glob("*.json"))) == 1
    assert len(list(reports.glob("*.txt"))) == 1
    assert captured_metadata == {"romanian-source": (("Politica", "Social"), 2)}
    assert database.read_bytes() == before
