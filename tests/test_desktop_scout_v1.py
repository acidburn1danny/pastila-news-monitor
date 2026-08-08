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
