from __future__ import annotations

import importlib.metadata
import re
from pathlib import Path

import pastila_scout

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "packaging" / "pyinstaller" / "version_info.txt.in"


def render(version: str, executable: str) -> str:
    assert re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version)
    parts = version.split(".")
    return (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("{FILE_VERSION}", f"{parts[0]}, {parts[1]}, {parts[2]}, 0")
        .replace("{PRODUCT_VERSION}", f"{parts[0]}, {parts[1]}, {parts[2]}, 0")
        .replace("{CANONICAL_VERSION}", version)
        .replace("{FILE_DESCRIPTION}", "Pastila Scout")
        .replace("{INTERNAL_NAME}", Path(executable).stem)
        .replace("{ORIGINAL_FILENAME}", executable)
    )


def test_installed_metadata_is_runtime_version_authority() -> None:
    assert pastila_scout.__version__ == importlib.metadata.version(
        "pastila-news-monitor"
    )
    assert pastila_scout.__version__ != "0.0.0-dev"


def test_template_renders_stable_four_part_projection_deterministically() -> None:
    first = render("12.34.56", "PastilaScout.exe")
    second = render("12.34.56", "PastilaScout.exe")
    assert first == second
    assert "filevers=(12, 34, 56, 0)" in first
    assert "prodvers=(12, 34, 56, 0)" in first
    assert "StringStruct('ProductVersion', '12.34.56')" in first
    assert "StringStruct('OriginalFilename', 'PastilaScout.exe')" in first
    assert "{" not in first and "}" not in first


def test_gui_and_console_render_distinct_governed_file_identities() -> None:
    gui = render("1.2.3", "PastilaScout.exe")
    cli = render("1.2.3", "pastila-scout.exe")
    assert "StringStruct('OriginalFilename', 'PastilaScout.exe')" in gui
    assert "StringStruct('OriginalFilename', 'pastila-scout.exe')" in cli
    assert gui != cli


def test_optional_legal_fields_are_omitted_without_fabrication() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    forbidden = ("CompanyName", "LegalCopyright", "TODO", "UNKNOWN", "Your Company")
    assert all(value not in text for value in forbidden)


def test_development_or_noncanonical_versions_cannot_render() -> None:
    for value in ("0.0.0-dev", "1.2", "1.2.3+local", "01.2.3"):
        try:
            render(value, "PastilaScout.exe")
        except AssertionError:
            continue
        raise AssertionError(f"invalid stable version rendered: {value}")
