"""Deterministic normal-release installer planning, separate from qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


class ReleaseOrchestrationError(ValueError):
    """A normal-release input or output boundary is invalid."""


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _safe_external(path: Path, repository: Path) -> Path:
    value = path.resolve()
    if (
        value == repository
        or repository in value.parents
        or value in repository.parents
    ):
        raise ReleaseOrchestrationError("work and output roots must be external")
    return value


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ReleaseOrchestrationError("repository identity cannot be resolved")
    return result.stdout.strip()


def _inventory(bundle: Path) -> tuple[dict[str, object], ...]:
    entries = []
    normalized: set[str] = set()
    for path in sorted(
        bundle.rglob("*"), key=lambda item: item.relative_to(bundle).as_posix()
    ):
        if path.is_symlink():
            raise ReleaseOrchestrationError("payload cannot contain links")
        if sys.platform == "win32" and path.stat().st_file_attributes & 0x400:
            raise ReleaseOrchestrationError("payload cannot contain reparse points")
        if not path.is_file():
            continue
        relative = path.relative_to(bundle).as_posix()
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            raise ReleaseOrchestrationError("unsafe payload path")
        identity = relative.casefold()
        if identity in normalized:
            raise ReleaseOrchestrationError("payload paths collide on Windows")
        normalized.add(identity)
        before = path.stat()
        digest = _hash(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ReleaseOrchestrationError("payload changed during inventory")
        entries.append({"path": relative, "size": after.st_size, "sha256": digest})
    if not entries:
        raise ReleaseOrchestrationError("payload is empty")
    return tuple(entries)


def _bundle_source_wheel(bundle: Path) -> tuple[Path, str]:
    direct_urls = tuple(bundle.glob("pastila_news_monitor-*.dist-info/direct_url.json"))
    if len(direct_urls) != 1:
        raise ReleaseOrchestrationError("bundle source provenance is missing")
    try:
        value = json.loads(direct_urls[0].read_text(encoding="utf-8"))
        parsed = urlparse(value["url"])
        expected = value["archive_info"]["hashes"]["sha256"].upper()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ReleaseOrchestrationError(
            "bundle source provenance is malformed"
        ) from error
    if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
        raise ReleaseOrchestrationError("bundle source wheel must be local")
    raw = unquote(parsed.path)
    if os.name == "nt" and raw.startswith("/") and len(raw) > 2 and raw[2] == ":":
        raw = raw[1:]
    wheel = Path(raw).resolve()
    if not wheel.is_file() or _hash(wheel) != expected:
        raise ReleaseOrchestrationError("bundle source wheel identity is invalid")
    return wheel, expected


def _verify_bundle_source(repository: Path, bundle: Path) -> dict[str, object]:
    """Bind the packaged application wheel byte-for-byte to accepted HEAD."""
    wheel, wheel_sha = _bundle_source_wheel(bundle)
    tracked = tuple(
        path
        for path in _git(
            repository, "ls-tree", "-r", "--name-only", "HEAD"
        ).splitlines()
        if path.startswith("src/pastila_scout/") and path.endswith(".py")
    )
    expected = {path.removeprefix("src/"): path for path in tracked}
    try:
        with zipfile.ZipFile(wheel) as archive:
            actual = {
                name: archive.read(name)
                for name in archive.namelist()
                if name.startswith("pastila_scout/") and name.endswith(".py")
            }
    except (OSError, zipfile.BadZipFile) as error:
        raise ReleaseOrchestrationError("bundle source wheel is unreadable") from error
    if set(actual) != set(expected):
        raise ReleaseOrchestrationError("bundle application sources do not match HEAD")
    for archive_path, repository_path in expected.items():
        if (repository / repository_path).read_bytes() != actual[archive_path]:
            raise ReleaseOrchestrationError(
                "bundle application sources do not match HEAD"
            )
    bundled_sources = bundle / "config" / "sources.yaml"
    if (
        bundled_sources.read_bytes()
        != (repository / "config" / "sources.yaml").read_bytes()
    ):
        raise ReleaseOrchestrationError(
            "bundle source configuration does not match HEAD"
        )
    return {"application_wheel_path": str(wheel), "application_wheel_sha256": wheel_sha}


def _write_includes(
    *, bundle: Path, entries: tuple[dict[str, object], ...], work: Path
) -> tuple[Path, Path]:
    files = work / "payload-files.generated.iss"
    verify = work / "payload-verify.generated.iss"
    file_lines: list[str] = []
    unlock = []
    restart = []
    hashes = []
    for index, entry in enumerate(entries):
        relative = str(entry["path"]).replace("/", "\\")
        escaped = relative.replace("'", "''")
        source = str(bundle / Path(str(entry["path"]))).replace('"', '""')
        parent = str(Path(relative).parent)
        destination = "{app}\\{code:StageDirectory}"
        if parent != ".":
            destination += f"\\{parent.replace('"', '""')}"
        line = f'Source: "{source}"; DestDir: "{destination}"; Flags: ignoreversion'
        if index == len(entries) - 1:
            line += "; AfterInstall: ActivateStagedPayload"
        file_lines.append(line)
        unlock.append(f"  if not FileIsUnlocked(Root + '\\{escaped}') then exit;")
        restart.append(
            "  RegisterRestartManagerResource(SessionHandle, "
            f"ExpandConstant('{{localappdata}}\\Programs\\PastilaScout\\app\\{escaped}'));"
        )
        hashes.append(
            f"  {{ expected size {entry['size']} }}; "
            f"if CompareText(GetSHA256OfFile(Root + '\\{escaped}'), "
            f"'{entry['sha256']}') <> 0 then exit;"
        )
    verify_lines = [
        "function FileIsUnlocked(const Path: String): Boolean;",
        "var",
        "  Stream: TFileStream;",
        "begin",
        "  Result := False;",
        "  try",
        "    Stream := TFileStream.Create(Path, fmOpenReadWrite or fmShareExclusive);",
        "    try Result := True; finally Stream.Free; end;",
        "  except",
        "    Result := False;",
        "  end;",
        "end;",
        "",
        "function VerifyInstalledPayloadUnlocked(const Root: String): Boolean;",
        "begin",
        "  Result := False;",
        *unlock,
        "  Result := True;",
        "end;",
        "",
        "procedure RegisterRestartManagerResources(const SessionHandle: LongWord);",
        "begin",
        *restart,
        "end;",
        "",
        "function VerifyStagedPayload(const Root: String): Boolean;",
        "begin",
        "  Result := False;",
        *hashes,
        "  Result := True;",
        "end;",
        "",
        "function StageDirectory(Param: String): String;",
        "begin",
        "  Result := StageName;",
        "end;",
    ]
    files.write_text("\n".join(file_lines) + "\n", encoding="utf-8")
    verify.write_text("\n".join(verify_lines) + "\n", encoding="utf-8")
    return files, verify


def create_release_plan(
    *,
    repository: Path,
    bundle: Path,
    work_root: Path,
    output_root: Path,
    iscc: Path,
    app_version: str,
    source_head: str,
    python_version: str | None = None,
    pyinstaller_version: str | None = None,
    inno_setup_version: str | None = None,
) -> dict[str, object]:
    repository = repository.resolve()
    bundle = _safe_external(bundle, repository)
    work_root = _safe_external(work_root, repository)
    output_root = _safe_external(output_root, repository)
    iscc = iscc.resolve()
    if not bundle.is_dir() or not iscc.is_file():
        raise ReleaseOrchestrationError("bundle or ISCC is missing")
    if work_root.exists() or (output_root.exists() and any(output_root.iterdir())):
        raise ReleaseOrchestrationError("work must be absent and output empty")
    actual_head = _git(repository, "rev-parse", "HEAD")
    if source_head != actual_head:
        raise ReleaseOrchestrationError("source HEAD mismatch")
    tracked = _git(repository, "status", "--porcelain", "--untracked-files=no")
    if tracked:
        raise ReleaseOrchestrationError("tracked tree must be clean")
    if app_version != "0.1.0":
        raise ReleaseOrchestrationError("owner rebuild version must remain 0.1.0")
    required = (
        bundle / "PastilaScout.exe",
        bundle / "pastila-scout.exe",
        bundle / "config" / "sources.yaml",
        bundle / "desktop_v1" / "default-settings-v1.json",
        bundle / "resources" / "trust" / "bootstrap-root-v1.json",
        bundle / "resources" / "trust" / "pastila-root-1.pub",
        bundle / "THIRD-PARTY-NOTICES.txt",
    )
    if not all(item.is_file() for item in required):
        raise ReleaseOrchestrationError("required payload resource is missing")
    provenance = _verify_bundle_source(repository, bundle)
    entries = _inventory(bundle)
    work_root.mkdir(parents=True)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = work_root / "payload-manifest-v1.json"
    manifest_value = {
        "schema": "pastila-scout-release-payload",
        "schema_version": 1,
        "files": entries,
    }
    manifest.write_text(
        json.dumps(manifest_value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    files, verify = _write_includes(bundle=bundle, entries=entries, work=work_root)
    definition = repository / "packaging" / "inno" / "PastilaScout.iss"
    icon = repository / "packaging" / "resources" / "PastilaScout.ico"
    payload_bytes = sum(int(entry["size"]) for entry in entries)
    command = (
        str(iscc),
        "/Q",
        f"/DPayloadFilesInclude={files}",
        f"/DPayloadVerifyInclude={verify}",
        f"/DPayloadBytes={payload_bytes}",
        f"/DAppVersion={app_version}",
        f"/DOutputDir={output_root}",
        f"/DFrozenIcon={icon}",
        str(definition),
    )
    return {
        "schema": "pastila-scout-release-orchestration",
        "schema_version": 1,
        "source_branch": _git(repository, "branch", "--show-current"),
        "source_head": actual_head,
        "source_subject": _git(repository, "show", "-s", "--format=%s", "HEAD"),
        "tracked_tree_status": "clean",
        "excluded_untracked_paths": _git(
            repository, "status", "--porcelain", "--untracked-files=all"
        ).splitlines(),
        "app_version": app_version,
        "python_version": python_version,
        "pyinstaller_version": pyinstaller_version,
        "inno_setup_version": inno_setup_version,
        "inno_executable_sha256": _hash(iscc),
        "packaged_bundle_root": str(bundle),
        "payload_file_count": len(entries),
        "payload_manifest_sha256": _hash(manifest),
        "payload_files_include_sha256": _hash(files),
        "payload_verify_include_sha256": _hash(verify),
        "gui_exe_sha256": _hash(required[0]),
        "cli_exe_sha256": _hash(required[1]),
        "sources_yaml_sha256": _hash(required[2]),
        "inno_definition_sha256": _hash(definition),
        "icon_sha256": _hash(icon),
        **provenance,
        "exact_iscc_command": list(command),
        "output_installer_path": str(
            output_root / f"PastilaScout-{app_version}-Setup.exe"
        ),
        "installer_sha256": None,
        "installer_size": None,
        "authenticode_state": None,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "orchestration_result": "planned",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("repository", "bundle", "work-root", "output-root", "iscc"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--python-version")
    parser.add_argument("--pyinstaller-version")
    parser.add_argument("--inno-setup-version")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    receipt = _safe_external(args.receipt, args.repository.resolve())
    plan = create_release_plan(
        repository=args.repository,
        bundle=args.bundle,
        work_root=args.work_root,
        output_root=args.output_root,
        iscc=args.iscc,
        app_version=args.app_version,
        source_head=args.source_head,
        python_version=args.python_version or os.sys.version.split()[0],
        pyinstaller_version=args.pyinstaller_version,
        inno_setup_version=args.inno_setup_version,
    )
    if not args.plan_only:
        bundle = Path(str(plan["packaged_bundle_root"]))
        if _git(Path(args.repository).resolve(), "rev-parse", "HEAD") != plan[
            "source_head"
        ] or _git(
            Path(args.repository).resolve(),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ):
            raise ReleaseOrchestrationError("source tree changed before compilation")
        work = Path(args.work_root)
        for filename, field in (
            ("payload-manifest-v1.json", "payload_manifest_sha256"),
            ("payload-files.generated.iss", "payload_files_include_sha256"),
            ("payload-verify.generated.iss", "payload_verify_include_sha256"),
        ):
            if _hash(work / filename) != plan[field]:
                raise ReleaseOrchestrationError("generated release input changed")
        before_compile = _inventory(bundle)
        manifest_value = json.loads(
            (Path(args.work_root) / "payload-manifest-v1.json").read_text(
                encoding="utf-8"
            )
        )
        if list(before_compile) != manifest_value["files"]:
            raise ReleaseOrchestrationError("payload changed before compilation")
        completed = subprocess.run(plan["exact_iscc_command"], check=False)
        if completed.returncode:
            raise ReleaseOrchestrationError("ISCC compilation failed")
        installer = Path(str(plan["output_installer_path"]))
        if not installer.is_file():
            raise ReleaseOrchestrationError("expected installer was not produced")
        if _inventory(bundle) != before_compile:
            raise ReleaseOrchestrationError("payload changed during compilation")
        plan["installer_sha256"] = _hash(installer)
        plan["installer_size"] = installer.stat().st_size
        signature = subprocess.run(
            (
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"(Get-AuthenticodeSignature -LiteralPath '{str(installer).replace("'", "''")}').Status",
            ),
            check=False,
            capture_output=True,
            text=True,
        )
        plan["authenticode_state"] = (
            signature.stdout.strip() if signature.returncode == 0 else "Unknown"
        )
        plan["orchestration_result"] = "completed"
    _atomic_json(receipt, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
