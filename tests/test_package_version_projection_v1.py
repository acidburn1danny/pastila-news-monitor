from __future__ import annotations

import ast
import importlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from importlib import metadata
from pathlib import Path

import pytest

import pastila_scout

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "pastila_scout" / "__init__.py"


@contextmanager
def _project_with(lookup: Callable[[str], str]) -> Iterator[object]:
    original = metadata.version
    metadata.version = lookup
    try:
        yield importlib.reload(pastila_scout)
    finally:
        metadata.version = original
        importlib.reload(pastila_scout)


def test_valid_metadata_is_exposed_exactly_once_per_module_execution() -> None:
    calls: list[str] = []

    def lookup(name: str) -> str:
        calls.append(name)
        return "12.34.56"

    with _project_with(lookup) as projected:
        assert projected.__version__ == "12.34.56"
        assert type(projected.__version__) is str
        assert projected.__version__ == "12.34.56"
        assert calls == ["pastila-news-monitor"]


def test_reload_reexecutes_one_exact_lookup() -> None:
    values = iter(("1.2.3", "2.3.4"))
    calls: list[str] = []

    def lookup(name: str) -> str:
        calls.append(name)
        return next(values)

    with _project_with(lookup) as projected:
        assert projected.__version__ == "1.2.3"
        projected = importlib.reload(pastila_scout)
        assert projected.__version__ == "2.3.4"
        assert calls == ["pastila-news-monitor", "pastila-news-monitor"]


def test_exact_metadata_absence_uses_development_fallback() -> None:
    def lookup(name: str) -> str:
        assert name == "pastila-news-monitor"
        raise metadata.PackageNotFoundError(name)

    with _project_with(lookup) as projected:
        assert projected.__version__ == "0.0.0-dev"


def test_unexpected_metadata_failure_propagates_unchanged() -> None:
    failure = PermissionError("metadata unavailable")

    def lookup(name: str) -> str:
        assert name == "pastila-news-monitor"
        raise failure

    with pytest.raises(PermissionError) as captured, _project_with(lookup):
        pass
    assert captured.value is failure


@pytest.mark.parametrize(
    "candidate",
    [
        "",
        "v1.2.3",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "1.2",
        "1.2.3.0",
        " 1.2.3",
        "1.2.3 ",
        "١.٢.٣",
        "1.2.3-alpha",
        "1.2.3+build",
        "1.2.-3",
        "1.2.x",
        "1" * 129 + ".2.3",
    ],
)
def test_invalid_present_metadata_fails_without_repair_or_fallback(
    candidate: str,
) -> None:
    with (
        pytest.raises(RuntimeError, match="^invalid installed package version$"),
        _project_with(lambda name: candidate),
    ):
        pass


def test_non_string_present_metadata_fails_finitely() -> None:
    with (
        pytest.raises(RuntimeError, match="^invalid installed package version$"),
        _project_with(lambda name: None),
    ):  # type: ignore[arg-type,return-value]
        pass


@pytest.mark.parametrize("candidate", ["0.0.0", "1.2.3", "10.20.30"])
def test_stable_semver_boundaries_are_accepted(candidate: str) -> None:
    with _project_with(lambda name: candidate) as projected:
        assert projected.__version__ == candidate


def test_package_root_is_lightweight_and_has_no_second_authority() -> None:
    source = PACKAGE_ROOT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported_roots <= {"importlib", "re"}
    assert "pyproject.toml" not in source
    assert "os.environ" not in source
    assert "subprocess" not in source
    assert "git describe" not in source
    assert source.count("metadata.version(") == 1

    owner_sources = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "src/pastila_scout/__init__.py",
            "src/pastila_scout/cli.py",
            "src/pastila_scout/logging_config.py",
            "src/pastila_scout/desktop_v1/views.py",
            "src/pastila_scout/desktop_v1/resources.py",
        )
    }
    combined = "\n".join(owner_sources.values())
    assert combined.count("metadata.version(") == 1
    for path, owner_source in owner_sources.items():
        if path.endswith("__init__.py"):
            continue
        assert "pyproject.toml" not in owner_source
        assert "PackageNotFoundError" not in owner_source
        assert "importlib.metadata" not in owner_source
        assert "os.environ" not in owner_source
        assert "git describe" not in owner_source


def test_frozen_specification_and_scope_are_exact() -> None:
    specification = (
        ROOT / "docs/windows-application/VersionProjectionSpecificationV1.md"
    ).read_text(encoding="utf-8")
    assert "25 requirements" in specification
    assert "25 verification rows" in specification
    assert "phase-5.5c-version-projection-spec-v1-ready" in specification
    assert not (ROOT / "src/pastila_scout/version.py").exists()
