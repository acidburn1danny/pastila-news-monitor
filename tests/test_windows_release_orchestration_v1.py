from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path

import pytest

from pastila_scout.windows_release_orchestration_v1 import (
    ReleaseOrchestrationError,
    create_release_plan,
)

PROJECT_VERSION = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["version"]


def _bundle(root: Path, source_ref: str = "HEAD") -> Path:
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
        subprocess.check_output(["git", "show", f"{source_ref}:config/sources.yaml"])
    )
    wheel = (
        root / "wheelhouse" / f"pastila_news_monitor-{PROJECT_VERSION}-py3-none-any.whl"
    )
    wheel.parent.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", source_ref], text=True
    ).splitlines()
    with zipfile.ZipFile(wheel, "w") as archive:
        for path in tracked:
            if path.startswith("src/pastila_scout/") and path.endswith(".py"):
                archive.writestr(
                    path.removeprefix("src/"),
                    subprocess.check_output(["git", "show", f"{source_ref}:{path}"]),
                )
    digest = __import__("hashlib").sha256(wheel.read_bytes()).hexdigest()
    direct = (
        bundle / f"pastila_news_monitor-{PROJECT_VERSION}.dist-info" / "direct_url.json"
    )
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


def _plan(
    tmp_path: Path,
    monkeypatch,
    bundle: Path | None = None,
    *,
    clean_tree: bool = True,
    application_payload_source_head: str | None = None,
    app_version: str = PROJECT_VERSION,
):
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
    if clean_tree:
        real_git = __import__(
            "pastila_scout.windows_release_orchestration_v1", fromlist=["_git"]
        )._git

        def clean(repository: Path, *arguments: str) -> str:
            if arguments == ("status", "--porcelain", "--untracked-files=no"):
                return ""
            if arguments == ("status", "--porcelain", "--untracked-files=all"):
                return "?? config/settings.json\n"
            return real_git(repository, *arguments)

        monkeypatch.setattr(
            "pastila_scout.windows_release_orchestration_v1._git", clean
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
        app_version=app_version,
        application_payload_source_head=application_payload_source_head or head,
        installer_source_head=head,
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
    assert plan["app_version"] == PROJECT_VERSION == "1.1.8"
    assert plan["windows_release_revision"] == "r3"
    assert plan["output_installer_path"].endswith(
        f"PastilaScout-{PROJECT_VERSION}-Setup.exe"
    )
    assert plan["intended_release_receipt_filename"] == (
        "PastilaScout-1.1.8-Windows-r3-release-receipt.json"
    )
    verify = (tmp_path / "work" / "payload-verify.generated.iss").read_text(
        encoding="utf-8"
    )
    assert "if not FileExists(Path) then begin" in verify


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
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
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
            app_version=PROJECT_VERSION,
            application_payload_source_head=head,
            installer_source_head="0" * 40,
        )


def test_release_plan_rejects_noncanonical_product_version(
    tmp_path: Path, monkeypatch
) -> None:
    with pytest.raises(ReleaseOrchestrationError, match="canonical authority"):
        _plan(tmp_path, monkeypatch, app_version="1.0.0")


def test_release_plan_rejects_bundle_with_stale_product_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    bundle = _bundle(tmp_path)
    metadata = bundle / f"pastila_news_monitor-{PROJECT_VERSION}.dist-info"
    metadata.rename(bundle / "pastila_news_monitor-1.1.0.dist-info")
    with pytest.raises(ReleaseOrchestrationError, match="bundle product version"):
        _plan(tmp_path / "plan", monkeypatch, bundle=bundle)


def test_release_plan_rejects_bundle_built_from_different_source(
    tmp_path: Path, monkeypatch
) -> None:
    bundle = _bundle(tmp_path)
    wheel = (
        tmp_path
        / "wheelhouse"
        / f"pastila_news_monitor-{PROJECT_VERSION}-py3-none-any.whl"
    )
    with zipfile.ZipFile(wheel) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    entries["pastila_scout/__init__.py"] = b"different"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    digest = __import__("hashlib").sha256(wheel.read_bytes()).hexdigest()
    direct = (
        bundle / f"pastila_news_monitor-{PROJECT_VERSION}.dist-info" / "direct_url.json"
    )
    value = json.loads(direct.read_text(encoding="utf-8"))
    value["archive_info"]["hashes"]["sha256"] = digest
    direct.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ReleaseOrchestrationError, match="do not match payload source"):
        _plan(tmp_path / "plan", monkeypatch, bundle)


def test_release_plan_records_distinct_payload_and_installer_sources(
    tmp_path: Path, monkeypatch
) -> None:
    plan = _plan(tmp_path, monkeypatch)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    assert plan["application_payload_source_head"] == head
    assert plan["installer_source_head"] == head
    assert "source_head" not in plan


def test_release_plan_accepts_verified_older_payload_source(
    tmp_path: Path, monkeypatch
) -> None:
    payload_head = "e70d61e24a7c0a998d9cc46fb5469a636999b6b0"
    bundle = _bundle(tmp_path / "payload", payload_head)
    plan = _plan(
        tmp_path / "plan",
        monkeypatch,
        bundle,
        application_payload_source_head=payload_head,
    )
    assert plan["application_payload_source_head"] == payload_head
    assert (
        plan["installer_source_head"]
        == subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    )


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
        _plan(tmp_path, monkeypatch, clean_tree=False)


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
    assert "--application-payload-source-head" in wrapper
    assert "--installer-source-head" in wrapper
    assert "if ($PlanOnly)" in wrapper
    assert "pyproject.toml" in wrapper
    assert "'--app-version', '0.1.0'" not in wrapper
    assert "encoding='utf-8'" in wrapper
