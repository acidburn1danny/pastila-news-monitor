# Phase 5.5F permanent PyInstaller specification.
# All PASTILA_SPEC_* values are set internally by build.ps1 after its public inputs pass.
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


def required_path(name: str) -> str:
    value = os.environ.get(name)
    if not value or not Path(value).is_absolute():
        raise SystemExit(f"missing governed build input: {name}")
    return value


gui_wrapper = required_path("PASTILA_SPEC_GUI_WRAPPER")
cli_wrapper = required_path("PASTILA_SPEC_CLI_WRAPPER")
resource_root = Path(required_path("PASTILA_SPEC_RESOURCE_ROOT"))
gui_version_info = required_path("PASTILA_SPEC_GUI_VERSION_INFO")
cli_version_info = required_path("PASTILA_SPEC_CLI_VERSION_INFO")
icon = required_path("PASTILA_SPEC_ICON")

hidden_imports = [
    "httpx",
    "openai",
    "pastila_scout.editor_generation_authority_v1",
    "pastila_scout.editor_generation_runtime_v1.composition",
    "pastila_scout.provider_execution_ollama_v1",
    "pastila_scout.provider_execution_openai_sdk_bridge_v2.bootstrap",
    "pastila_scout.provider_execution_openai_sdk_v2",
    "pastila_scout.provider_execution_openai_sdk_v2.client",
    "pastila_scout.provider_execution_openai_sdk_v2.mapping",
    "pastila_scout.provider_execution_openai_sdk_v2.models",
    "pastila_scout.provider_runtime_openai_bridged_v2",
    "pastila_scout.provider_runtime_openai_bridged_v2.composition",
    "pastila_scout.provider_runtime_openai_v2.production",
    "pastila_scout.wsl_execution_v1",
    "pastila_scout.wsl_execution_v1.boundary",
    "pastila_scout.wsl_execution_v1_1",
    "pastila_scout.wsl_execution_v1_1.boundary",
]

datas = [
    (str(resource_root / "config" / "config.yaml"), "config"),
    (str(resource_root / "config" / "sources.yaml"), "config"),
    (
        str(resource_root / "desktop_v1" / "default-settings-v1.json"),
        "desktop_v1",
    ),
    (str(resource_root / "resources" / "trust" / "pastila-root-1.pub"), "resources/trust"),
    (
        str(resource_root / "resources" / "trust" / "bootstrap-root-v1.json"),
        "resources/trust",
    ),
    (
        str(
            resource_root
            / "pastila_scout"
            / "resources"
            / "expression_retrieval_v1"
            / "catalog.json"
        ),
        "pastila_scout/resources/expression_retrieval_v1",
    ),
    (
        str(
            resource_root
            / "pastila_scout"
            / "resources"
            / "expression_catalog_v2"
            / "catalog-overlay.json"
        ),
        "pastila_scout/resources/expression_catalog_v2",
    ),
    (
        str(
            resource_root
            / "pastila_scout"
            / "resources"
            / "branding"
            / "pastila-scout-investigator.png"
        ),
        "pastila_scout/resources/branding",
    ),
    (
        str(
            resource_root
            / "pastila_scout"
            / "resources"
            / "branding"
            / "pastila-scout-investigator-sidebar.png"
        ),
        "pastila_scout/resources/branding",
    ),
    (
        str(
            Path(SPECPATH).parents[1]
            / "src"
            / "pastila_scout"
            / "experimental_core_v1_2_runner.py"
        ),
        "src/pastila_scout",
    ),
    (
        str(
            Path(SPECPATH).parents[1]
            / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence"
            / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"
        ),
        ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence",
    ),
    (str(resource_root / "resources" / "THIRD-PARTY-NOTICES.txt"), "."),
] + copy_metadata("pastila-news-monitor") + collect_data_files("certifi")

common = dict(
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

gui_analysis = Analysis([gui_wrapper], **common)
cli_analysis = Analysis([cli_wrapper], **common)
gui_pyz = PYZ(gui_analysis.pure)
cli_pyz = PYZ(cli_analysis.pure)

gui_exe = EXE(
    gui_pyz,
    gui_analysis.scripts,
    [],
    exclude_binaries=True,
    name="PastilaScout",
    console=False,
    icon=icon,
    version=gui_version_info,
    upx=False,
    contents_directory=".",
)
cli_exe = EXE(
    cli_pyz,
    cli_analysis.scripts,
    [],
    exclude_binaries=True,
    name="pastila-scout",
    console=True,
    icon=icon,
    version=cli_version_info,
    upx=False,
    contents_directory=".",
)

bundle = COLLECT(
    gui_exe,
    cli_exe,
    gui_analysis.binaries,
    gui_analysis.datas,
    cli_analysis.binaries,
    cli_analysis.datas,
    strip=False,
    upx=False,
    name="app",
)
