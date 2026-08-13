from pathlib import Path

import pytest

import pastila_scout.desktop_scout_v1 as package
from pastila_scout.desktop_application_v1 import (
    DesktopApplicationExecutionError,
    DesktopOperationStatusV1,
    DesktopReportReferenceV1,
    ScoutDesktopCategoryV1,
    ScoutDesktopRequestV1,
)
from pastila_scout.desktop_report_v1.models import _DesktopScoutReportInputV1
from pastila_scout.desktop_report_v1.service import _DesktopReportFacadeV1
from pastila_scout.desktop_scout_v1.service import _ScoutDesktopOperationV1
from pastila_scout.poller import PollResult


def _opener(path: Path) -> None:
    del path


class _ReportFacadeFake:
    def __init__(self):
        self.calls = []

    def generate_report(
        self, *, result: _DesktopScoutReportInputV1
    ) -> DesktopReportReferenceV1:
        self.calls.append(result)
        return DesktopReportReferenceV1(report_reference="fake-report")

    def open_report(self, *, reference: str) -> None:
        del reference


def _request() -> ScoutDesktopRequestV1:
    return ScoutDesktopRequestV1(
        operation_reference="operation-1",
        period_days=7,
        category=ScoutDesktopCategoryV1.POLITICA,
    )


@pytest.mark.parametrize("period", (1, 3, 7))
def test_targeted_request_always_uses_exact_48_hour_window(monkeypatch, period):
    operation = _ScoutDesktopOperationV1(
        config_path=Path("config.yaml"),
        sources_path=Path("sources.yaml"),
        database_path=Path("scout.db"),
        report_facade=_ReportFacadeFake(),
    )
    calls = []
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.poll_once",
        lambda *args, **kwargs: calls.append((args, kwargs)) or _poll(),
    )

    result = operation.run_scout(
        request=ScoutDesktopRequestV1(
            operation_reference="targeted-operation",
            period_days=period,
            category=ScoutDesktopCategoryV1.POLITICA,
            targeted_query="Donald Trump Iran",
        )
    )

    assert calls[0][1]["max_article_age_hours_override"] == 48.0
    assert calls[0][1]["category"] == "Politica"
    assert result.targeted_candidate_ids == ()


def test_normal_request_retains_selected_period_and_global_projection_marker(
    monkeypatch,
):
    operation = _ScoutDesktopOperationV1(
        config_path=Path("config.yaml"),
        sources_path=Path("sources.yaml"),
        database_path=Path("scout.db"),
        report_facade=_ReportFacadeFake(),
    )
    calls = []
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.poll_once",
        lambda *args, **kwargs: calls.append((args, kwargs)) or _poll(),
    )

    result = operation.run_scout(request=_request())

    assert calls[0][1]["max_article_age_hours_override"] == 168.0
    assert result.targeted_candidate_ids is None


def test_targeted_source_failure_retains_empty_scope(monkeypatch):
    operation = _ScoutDesktopOperationV1(
        config_path=Path("config.yaml"),
        sources_path=Path("sources.yaml"),
        database_path=Path("scout.db"),
        report_facade=_ReportFacadeFake(),
    )
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.poll_once",
        lambda *args, **kwargs: _poll("failed", 0, ("unavailable",)),
    )

    result = operation.run_scout(
        request=ScoutDesktopRequestV1(
            operation_reference="targeted-failure",
            period_days=1,
            category=ScoutDesktopCategoryV1.ALL,
            targeted_query="breaking topic",
        )
    )

    assert result.status is DesktopOperationStatusV1.FAILED
    assert result.targeted_candidate_ids == ()


def test_targeted_projection_ids_are_carried_and_uses_same_window_time(monkeypatch):
    operation = _ScoutDesktopOperationV1(
        config_path=Path("config.yaml"),
        sources_path=Path("sources.yaml"),
        database_path=Path("scout.db"),
        report_facade=_ReportFacadeFake(),
    )
    calls = []
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.poll_once",
        lambda *args, **kwargs: calls.append(("poll", kwargs)) or _poll(),
    )
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.project_targeted_event_ids",
        lambda **kwargs: calls.append(("project", kwargs)) or (9, 4),
    )

    result = operation.run_scout(
        request=ScoutDesktopRequestV1(
            operation_reference="targeted-projection",
            period_days=7,
            category=ScoutDesktopCategoryV1.ALL,
            targeted_query="Donald Trump Iran",
        )
    )

    assert result.targeted_candidate_ids == (9, 4)
    assert calls[0][1]["now"] is calls[1][1]["now"]
    assert calls[1][1]["database_path"] == Path("scout.db")
    assert calls[1][1]["excluded_source_ids"] == ()


def test_targeted_projection_exception_fails_closed(monkeypatch):
    operation = _ScoutDesktopOperationV1(
        config_path=Path("config.yaml"),
        sources_path=Path("sources.yaml"),
        database_path=Path("scout.db"),
        report_facade=_ReportFacadeFake(),
    )
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.poll_once",
        lambda *args, **kwargs: _poll(),
    )
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.project_targeted_event_ids",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("projection failed")),
    )

    result = operation.run_scout(
        request=ScoutDesktopRequestV1(
            operation_reference="targeted-projection-failure",
            period_days=3,
            category=ScoutDesktopCategoryV1.ALL,
            targeted_query="Donald Trump Iran",
        )
    )

    assert result.targeted_candidate_ids == ()


def _poll(status="success", succeeded=2, failed_ids=()):
    failed = len(failed_ids)
    return PollResult(
        run_id=1,
        status=status,
        sources_checked=succeeded + failed,
        sources_succeeded=succeeded,
        sources_failed=failed,
        articles_found=3,
        articles_inserted=2,
        duplicates_skipped=1,
        error_message=None,
        failed_source_ids=failed_ids,
    )


def test_private_exports_and_exact_projection(tmp_path, monkeypatch):
    assert package.__all__ == ()
    reports = tmp_path / "reports"
    reports.mkdir()
    facade = _DesktopReportFacadeV1(report_directory=reports, opener=_opener)
    operation = _ScoutDesktopOperationV1(
        config_path=Path("config.yaml"),
        sources_path=Path("sources.yaml"),
        database_path=Path("scout.db"),
        report_facade=facade,
    )
    calls = []

    def fake_poll(*args, **kwargs):
        calls.append((args, kwargs))
        return _poll()

    monkeypatch.setattr("pastila_scout.desktop_scout_v1.service.poll_once", fake_poll)
    result = operation.run_scout(request=_request())
    assert result.status is DesktopOperationStatusV1.COMPLETED
    assert calls == [
        (
            (Path("config.yaml"), Path("scout.db")),
            {
                "sources_path": Path("sources.yaml"),
                "max_article_age_hours_override": 168.0,
                "category": "Politica",
            },
        )
    ]
    assert result.report_reference is not None


def test_structural_report_facade_is_accepted(monkeypatch):
    facade = _ReportFacadeFake()
    operation = _ScoutDesktopOperationV1(
        config_path=Path("config.yaml"),
        sources_path=Path("sources.yaml"),
        database_path=Path("scout.db"),
        report_facade=facade,
    )
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.poll_once",
        lambda *args, **kwargs: _poll(),
    )
    result = operation.run_scout(request=_request())
    assert result.report_reference.report_reference == "fake-report"
    assert len(facade.calls) == 1


@pytest.mark.parametrize(
    "failed_ids",
    [
        ("zeta", "alpha"),
        ("same", "same"),
        ("with space", "a:b", "a::b", "a/b", "a\\b", "punct.!", "Știre"),
    ],
)
def test_failed_source_identity_is_unchanged(tmp_path, monkeypatch, failed_ids):
    reports = tmp_path / "reports"
    reports.mkdir()
    operation = _ScoutDesktopOperationV1(
        config_path=Path("c"),
        sources_path=Path("s"),
        database_path=Path("d"),
        report_facade=_DesktopReportFacadeV1(report_directory=reports, opener=_opener),
    )
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.poll_once",
        lambda *a, **k: _poll("partial", 1, failed_ids),
    )
    result = operation.run_scout(request=_request())
    assert result.status is DesktopOperationStatusV1.PARTIAL
    assert result.failed_source_ids is failed_ids


def test_failed_value_has_no_report(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    reports.mkdir()
    operation = _ScoutDesktopOperationV1(
        config_path=Path("c"),
        sources_path=Path("s"),
        database_path=Path("d"),
        report_facade=_DesktopReportFacadeV1(report_directory=reports, opener=_opener),
    )
    monkeypatch.setattr(
        "pastila_scout.desktop_scout_v1.service.poll_once",
        lambda *a, **k: _poll("failed", 0, ("bad",)),
    )
    result = operation.run_scout(request=_request())
    assert result.status is DesktopOperationStatusV1.FAILED
    assert result.report_reference is None
    assert not tuple(reports.iterdir())


def test_lower_exception_is_safely_reduced(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    reports.mkdir()
    operation = _ScoutDesktopOperationV1(
        config_path=Path("c"),
        sources_path=Path("s"),
        database_path=Path("d"),
        report_facade=_DesktopReportFacadeV1(report_directory=reports, opener=_opener),
    )

    def fail(*args, **kwargs):
        raise RuntimeError("secret")

    monkeypatch.setattr("pastila_scout.desktop_scout_v1.service.poll_once", fail)
    with pytest.raises(DesktopApplicationExecutionError) as caught:
        operation.run_scout(request=_request())
    assert caught.value.__cause__ is None
    assert "secret" not in str(caught.value)
