import copy
import hashlib
import pickle
from pathlib import Path

import pytest

import pastila_scout.desktop_report_v1 as package
from pastila_scout.desktop_application_v1 import (
    DesktopApplicationExecutionError,
    DesktopOperationStatusV1,
    ScoutDesktopCategoryV1,
)
from pastila_scout.desktop_report_v1.html import _render_report_html_v1
from pastila_scout.desktop_report_v1.models import _DesktopScoutReportInputV1
from pastila_scout.desktop_report_v1.service import _DesktopReportFacadeV1


def _report(**changes):
    values = {
        "operation_reference": "operation<&>",
        "status": DesktopOperationStatusV1.PARTIAL,
        "sources_checked": 2,
        "sources_succeeded": 1,
        "sources_failed": 1,
        "articles_found": 3,
        "articles_inserted": 2,
        "duplicates_skipped": 1,
        "failed_source_ids": ("source<&>",),
        "executed_period_days": 7,
        "executed_category": ScoutDesktopCategoryV1.POLITICA,
    }
    values.update(changes)
    return _DesktopScoutReportInputV1(**values)


def test_models_and_deterministic_escaped_html():
    value = _report()
    assert package.__all__ == ()
    assert copy.copy(value) == value and copy.deepcopy(value) == value
    assert "operation<&>" not in repr(value) and "source<&>" not in repr(value)
    with pytest.raises(TypeError):
        pickle.dumps(value)
    first = _render_report_html_v1(report=value)
    assert first == _render_report_html_v1(report=_report())
    assert "operation&lt;&amp;&gt;" in first and "source&lt;&amp;&gt;" in first


def test_reference_atomic_catalog_and_open(tmp_path):
    opened = []

    def opener(path: Path) -> None:
        opened.append(path)

    facade = _DesktopReportFacadeV1(report_directory=tmp_path, opener=opener)
    reference = facade.generate_report(result=_report())
    digest = hashlib.sha256(b"operation<&>").hexdigest()
    assert reference.report_reference == "scout-report-v1:" + digest
    expected = (tmp_path / f"{digest}.html").resolve()
    assert expected.is_file()
    facade.open_report(reference=reference.report_reference)
    assert opened == [expected]
    with pytest.raises(DesktopApplicationExecutionError):
        facade.generate_report(result=_report())
    with pytest.raises(DesktopApplicationExecutionError):
        facade.open_report(reference="unknown")


def test_existing_destination_is_not_replaced(tmp_path):
    def opener(path: Path) -> None:
        del path

    value = _report(operation_reference="same")
    digest = hashlib.sha256(b"same").hexdigest()
    target = tmp_path / f"{digest}.html"
    target.write_text("existing", encoding="utf-8")
    facade = _DesktopReportFacadeV1(report_directory=tmp_path, opener=opener)
    with pytest.raises(DesktopApplicationExecutionError):
        facade.generate_report(result=value)
    assert target.read_text(encoding="utf-8") == "existing"


def test_report_failures_have_no_retained_context(tmp_path):
    def opener(path: Path) -> None:
        raise RuntimeError(path)

    facade = _DesktopReportFacadeV1(report_directory=tmp_path, opener=opener)
    reference = facade.generate_report(result=_report())
    with pytest.raises(DesktopApplicationExecutionError) as caught:
        facade.open_report(reference=reference.report_reference)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
