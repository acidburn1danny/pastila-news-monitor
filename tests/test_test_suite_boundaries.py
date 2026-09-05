"""Regression coverage for the explicit optional evidence-suite boundaries."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "foundation_test_boundaries", ROOT / "tests" / "conftest.py"
)
assert SPEC is not None and SPEC.loader is not None
BOUNDARIES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARIES)


class _Config:
    def __init__(self, enabled: set[str]) -> None:
        self.enabled = enabled

    def getoption(self, name: str) -> bool:
        return name in self.enabled


class _Item:
    def __init__(self, module_name: str) -> None:
        self.path = ROOT / "tests" / module_name
        self.markers: list[object] = []

    def add_marker(self, marker: object) -> None:
        self.markers.append(marker)


def _marker_names(item: _Item) -> tuple[str, ...]:
    return tuple(marker.name for marker in item.markers)  # type: ignore[attr-defined]


def test_optional_boundaries_are_closed_exact_and_flag_controlled() -> None:
    historical = BOUNDARIES._HISTORICAL_IDENTITY_MODULES
    owner = BOUNDARIES._OWNER_EVIDENCE_PREREQUISITES
    assert len(historical) == 27
    assert len(owner) == 14
    assert historical.isdisjoint(owner)
    files = tuple((ROOT / "tests").glob("test_*.py"))
    assert all(sum(path.name == name for path in files) == 1 for name in historical)
    assert all(sum(path.name == name for path in files) == 1 for name in owner)

    historical_name = next(iter(historical))
    owner_name = next(iter(owner))
    mandatory_name = "test_test_suite_boundaries.py"
    cases = (
        (set(), historical_name, ("historical_identity", "skip")),
        ({"--run-historical-evidence"}, historical_name, ("historical_identity",)),
        (set(), owner_name, ("owner_evidence", "skip")),
        ({"--run-owner-evidence"}, owner_name, ("owner_evidence",)),
        (set(), mandatory_name, ()),
    )
    for enabled, module_name, expected in cases:
        item = _Item(module_name)
        BOUNDARIES.pytest_collection_modifyitems(_Config(enabled), [item])
        assert _marker_names(item) == expected
