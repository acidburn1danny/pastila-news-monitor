"""Explicit static discovery used to verify the checked-in consumer inventory."""

from __future__ import annotations

import ast
from pathlib import Path

_FROZEN_PREFIXES = (
    "editor/script_composer/",
    "provider_adapters_v2/",
    "provider_execution_",
    "provider_runtime_openai_",
    "provider_smoke_request_authority_v2/",
    "provider_v2/",
)
_FROZEN_FILES = ("provider_composition_v2.py",)


def _consumer_package(relative_path: str) -> str:
    if relative_path.startswith("editor/generation/ai_provider_adapter/openai/"):
        return "pastila_scout.editor.generation.ai_provider_adapter.openai"
    module_path = relative_path.removesuffix(".py")
    if module_path.endswith("/__init__"):
        module_path = module_path.removesuffix("/__init__")
    return "pastila_scout." + module_path.replace("/", ".")


def _has_direct_openai_runtime_import(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = tuple(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules = (node.module or "",)
        else:
            continue
        if any(
            module == "openai"
            or module.startswith("openai.")
            or module == "pastila_scout.ai.openai_provider"
            or (module.startswith("pastila_scout.provider_") and "openai" in module)
            for module in modules
        ):
            return True
    return False


def discover_direct_runtime_consumers(source_root: Path) -> tuple[str, ...]:
    """Return application-owned direct OpenAI runtime consumers in path order."""

    discovered: set[str] = set()
    for path in sorted(source_root.rglob("*.py")):
        relative_path = path.relative_to(source_root).as_posix()
        if relative_path in _FROZEN_FILES or relative_path.startswith(_FROZEN_PREFIXES):
            continue
        package = _consumer_package(relative_path)
        if not package:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _has_direct_openai_runtime_import(tree):
            discovered.add(package)
    return tuple(sorted(discovered))


__all__: tuple[str, ...] = ()
