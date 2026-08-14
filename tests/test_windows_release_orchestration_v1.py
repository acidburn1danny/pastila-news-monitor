from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from pastila_scout.windows_release_orchestration_v1 import (
    ReleaseOrchestrationError,
    create_release_plan,
)


def _bundle(root: Path) -> Path:
    bundle = root / "bundle"
    for relative in (
        "PastilaScout.exe",
        "pastila-scout.exe",
        "config/sources.yaml",
        "desktop_v1/default-settings-v1.json",
        "resources/trust/bootstrap-root-v1.json",
        "resources/trust/pastila-root-1.pub",
        "THIRD-PARTY-NOTICES.txt",
    ):
        path = bundle / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(relative.encode())
    (bundle / "config" / "sources.yaml").write_bytes(
        subprocess.check_output(["git", "show", "HEAD:config/sources.yaml"])
    )
    wheel = root / "wheelhouse" / "pastila_news_monitor-0.1.0-py3-none-any.whl"
    wheel.parent.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"], text=True
    ).splitlines()
    with zipfile.ZipFile(wheel, "w") as archive:
        for path in tracked:
            if path.startswith("src/pastila_scout/") and path.endswith(".py"):
                archive.writestr(
                    path.removeprefix("src/"),
                    Path(path).read_bytes(),
                )
    digest = __import__("hashlib").sha256(wheel.read_bytes()).hexdigest()
    direct = bundle / "pastila_news_monitor-0.1.0.dist-info" / "direct_url.json"
    direct.parent.mkdir()
    direct.write_text(
        json.dumps(
            {
                "url": wheel.as_uri(),
                "archive_info": {"hashes": {"sha256": digest}},
            }
        ),
        encoding="utf-8",
    )
    return bundle


def _plan(tmp_path: Path, monkeypatch, bundle: Path | None = None):
    monkeypatch.setattr(
        "pastila_scout.windows_release_orchestration_v1._safe_external",
        lambda path, _repository: path.resolve(),
    )
    repository = Path.cwd().resolve()
    head = (
        __import__("subprocess")
        .check_output(["git", "rev-parse", "HEAD"], text=True)
        .strip()
    )
    iscc = tmp_path / "ISCC.exe"
    iscc.parent.mkdir(parents=True, exist_ok=True)
    iscc.write_bytes(b"compiler")
    return create_release_plan(
        repository=repository,
        bundle=bundle or _bundle(tmp_path),
        work_root=tmp_path / "work",
        output_root=tmp_path / "output",
        iscc=iscc,
        app_version="0.1.0",
        source_head=head,
        python_version="3.14.3",
        pyinstaller_version="6.22.0",
    )


def test_plan_only_generates_deterministic_manifest_and_no_installer(
    tmp_path: Path, monkeypatch
) -> None:
    plan = _plan(tmp_path, monkeypatch)
    manifest = tmp_path / "work" / "payload-manifest-v1.json"
    content = json.loads(manifest.read_text(encoding="utf-8"))

    assert plan["orchestration_result"] == "planned"
    assert plan["payload_file_count"] == 8
    assert [item["path"] for item in content["files"]] == sorted(
        item["path"] for item in content["files"]
    )
    assert not tuple((tmp_path / "output").glob("*.exe"))
    assert "build-installer.ps1" not in " ".join(plan["exact_iscc_command"])
    assert any(
        "config/settings.json" in item for item in plan["excluded_untracked_paths"]
    )
    assert plan["application_wheel_sha256"]


def test_manifest_is_reproducible_across_external_roots(
    tmp_path: Path, monkeypatch
) -> None:
    first_bundle = _bundle(tmp_path / "first")
    first = _plan(tmp_path / "first-plan", monkeypatch, first_bundle)
    second_bundle = tmp_path / "second" / "bundle"
    shutil.copytree(first_bundle, second_bundle)
    second = _plan(tmp_path / "second-plan", monkeypatch, second_bundle)
    assert first["payload_manifest_sha256"] == second["payload_manifest_sha256"]


def test_release_plan_rejects_missing_launcher_and_wrong_head(
    tmp_path: Path, monkeypatch
) -> None:
    bundle = _bundle(tmp_path)
    (bundle / "PastilaScout.exe").unlink()
    with pytest.raises(ReleaseOrchestrationError, match="required payload"):
        _plan(tmp_path / "missing", monkeypatch, bundle)

    bundle = _bundle(tmp_path / "head")
    repository = Path.cwd().resolve()
    iscc = tmp_path / "head" / "ISCC.exe"
    iscc.write_bytes(b"compiler")
    monkeypatch.setattr(
        "pastila_scout.windows_release_orchestration_v1._safe_external",
        lambda path, _repository: path.resolve(),
    )
    with pytest.raises(ReleaseOrchestrationError, match="HEAD mismatch"):
        create_release_plan(
            repository=repository,
            bundle=bundle,
            work_root=tmp_path / "head-work",
            output_root=tmp_path / "head-output",
            iscc=iscc,
            app_version="0.1.0",
            source_head="0" * 40,
        )


def test_release_plan_rejects_bundle_built_from_different_source(
    tmp_path: Path, monkeypatch
) -> None:
    bundle = _bundle(tmp_path)
    wheel = tmp_path / "wheelhouse" / "pastila_news_monitor-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    entries["pastila_scout/__init__.py"] = b"different"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    digest = __import__("hashlib").sha256(wheel.read_bytes()).hexdigest()
    direct = bundle / "pastila_news_monitor-0.1.0.dist-info" / "direct_url.json"
    value = json.loads(direct.read_text(encoding="utf-8"))
    value["archive_info"]["hashes"]["sha256"] = digest
    direct.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ReleaseOrchestrationError, match="do not match HEAD"):
        _plan(tmp_path / "plan", monkeypatch, bundle)


def test_release_plan_rejects_tracked_or_staged_changes(
    tmp_path: Path, monkeypatch
) -> None:
    real_git = __import__(
        "pastila_scout.windows_release_orchestration_v1", fromlist=["_git"]
    )._git

    def dirty(repository: Path, *arguments: str) -> str:
        if arguments == ("status", "--porcelain", "--untracked-files=no"):
            return "M  src/pastila_scout/example.py"
        return real_git(repository, *arguments)

    monkeypatch.setattr("pastila_scout.windows_release_orchestration_v1._git", dirty)
    with pytest.raises(ReleaseOrchestrationError, match="tracked tree"):
        _plan(tmp_path, monkeypatch)


def test_qualification_wrapper_remains_frozen() -> None:
    wrapper = Path("packaging/inno/build-installer.ps1").read_text(encoding="utf-8")
    assert "repositoryHead -ne $wrapperAuthorityHead" in wrapper
    assert "phase-5.6b-wrapper-accounting-consumer-refresh-r1-verified" in wrapper


def test_normal_release_wrapper_is_separate_and_records_tool_versions() -> None:
    wrapper = Path("packaging/inno/build-release-installer.ps1").read_text(
        encoding="utf-8"
    )
    assert "pastila_scout.windows_release_orchestration_v1" in wrapper
    assert "build-installer.ps1" not in wrapper
    assert "--pyinstaller-version" in wrapper
    assert "--inno-setup-version" in wrapper
    assert "if ($PlanOnly)" in wrapper
