from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "packaging" / "pyinstaller" / "build.ps1"


def run_build(
    tmp_path: Path, mode: str, *, work: Path | None = None
) -> subprocess.CompletedProcess[str]:
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir(exist_ok=True)
    work_root = work or (tmp_path / "work")
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-BuildMode",
            mode,
            "-PythonExecutable",
            sys.executable,
            "-Wheelhouse",
            str(wheelhouse),
            "-WorkRoot",
            str(work_root),
            "-DistRoot",
            str(tmp_path / "dist"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("mode", ["development", "Stable", "unknown", ""])
def test_nonstable_modes_fail_before_mutation(tmp_path: Path, mode: str) -> None:
    result = run_build(tmp_path, mode)
    assert result.returncode != 0
    if mode:
        assert "BuildMode must be exactly stable" in result.stderr
    else:
        assert "BuildMode" in result.stderr and "EmptyStringNotAllowed" in result.stderr
    assert not (tmp_path / "work").exists()
    assert not (tmp_path / "dist").exists()


def test_stable_passes_final_resource_gates_before_mutation(tmp_path: Path) -> None:
    result = run_build(tmp_path, "stable")
    assert result.returncode != 0
    assert any(
        boundary in result.stderr
        for boundary in (
            "Python must be Windows AMD64 CPython 3.14 with functional Tcl/Tk",
            "wheelhouse must contain the single exact PyInstaller wheel",
        )
    )
    assert "name 'implementation' is not defined" not in result.stderr
    assert "PastilaScout.ico is required" not in result.stderr
    assert "THIRD-PARTY-NOTICES.txt is required" not in result.stderr
    assert not (tmp_path / "work").exists()
    assert not (tmp_path / "dist").exists()


def test_missing_ico_fails_without_generating_placeholder(tmp_path: Path) -> None:
    fake_repo = tmp_path / "candidate"
    fake_script = fake_repo / "packaging" / "pyinstaller" / "build.ps1"
    fake_script.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, fake_script)
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    work = tmp_path / "work"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(fake_script),
            "-BuildMode",
            "stable",
            "-PythonExecutable",
            sys.executable,
            "-Wheelhouse",
            str(wheelhouse),
            "-WorkRoot",
            str(work),
            "-DistRoot",
            str(tmp_path / "dist"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "final owner-approved PastilaScout.ico is required" in result.stderr
    assert not (fake_repo / "packaging" / "resources").exists()
    assert not work.exists()


def test_omitted_build_mode_is_rejected_by_mandatory_interface(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-PythonExecutable",
            sys.executable,
            "-Wheelhouse",
            str(wheelhouse),
            "-WorkRoot",
            str(tmp_path / "work"),
            "-DistRoot",
            str(tmp_path / "dist"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "BuildMode" in result.stderr
    assert not (tmp_path / "work").exists()


def test_missing_notices_fails_without_generating_placeholder(tmp_path: Path) -> None:
    fake_repo = tmp_path / "candidate"
    fake_script = fake_repo / "packaging" / "pyinstaller" / "build.ps1"
    fake_script.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, fake_script)
    resources = fake_repo / "packaging" / "resources"
    resources.mkdir()
    (resources / "PastilaScout.ico").write_bytes(b"unit-test-only")
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    work = tmp_path / "work"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(fake_script),
            "-BuildMode",
            "stable",
            "-PythonExecutable",
            sys.executable,
            "-Wheelhouse",
            str(wheelhouse),
            "-WorkRoot",
            str(work),
            "-DistRoot",
            str(tmp_path / "dist"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "owner-approved THIRD-PARTY-NOTICES.txt is required" in result.stderr
    assert not (resources / "THIRD-PARTY-NOTICES.txt").exists()
    assert not work.exists()


def test_relative_paths_fail_before_mutation(tmp_path: Path) -> None:
    result = run_build(tmp_path, "stable", work=Path("relative-work"))
    assert result.returncode != 0
    assert "WorkRoot must be an absolute path" in result.stderr
    assert not (ROOT / "relative-work").exists()


def test_output_may_not_overlap_read_only_wheelhouse(tmp_path: Path) -> None:
    work = tmp_path / "wheels" / "nested-work"
    result = run_build(tmp_path, "stable", work=work)
    assert result.returncode != 0
    assert "output and protected input paths must not overlap" in result.stderr
    assert not work.exists()


def test_interface_has_exactly_five_mandatory_parameters() -> None:
    command = (
        "$e=$null;$t=$null;"
        f"$a=[Management.Automation.Language.Parser]::ParseFile('{SCRIPT}',[ref]$t,[ref]$e);"
        "$a.ParamBlock.Parameters|%{($_.Name.VariablePath.UserPath)+':' + "
        "[bool]($_.Attributes|?{$_.TypeName.Name-eq'Parameter'-and$_.NamedArguments.ArgumentName-eq'Mandatory'})}"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.splitlines() == [
        "BuildMode:True",
        "PythonExecutable:True",
        "Wheelhouse:True",
        "WorkRoot:True",
        "DistRoot:True",
    ]


def test_interface_rejects_positional_binding_before_mutation(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "stable",
            sys.executable,
            str(wheelhouse),
            str(tmp_path / "work"),
            str(tmp_path / "dist"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not (tmp_path / "work").exists()


def test_environment_and_wheel_metadata_are_fail_closed() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"system": platform.system()' in text
    assert "$pythonInfo.system -ne 'Windows'" in text
    assert "$pythonCheck | & $PythonExecutable -I - 2>&1" in text
    assert "$pythonOutput.Count -ne 1" in text
    assert "$wheelAudit | & $PythonExecutable -I - $Wheelhouse 2>&1" in text
    assert "$isolationCheck | & $VenvPython -I - $RepositoryRoot 2>&1" in text
    assert "$versionCheck | & $VenvPython -I - 2>&1" in text
    assert "-c $wheelAudit" not in text
    assert "-c $isolationCheck" not in text
    assert text.count("ConvertFrom-Json | ForEach-Object { $_ }") == 2
    assert "(Join-Path $ResourceRoot 'resources\\trust')" in text
    assert (
        "(Join-Path $ResourceRoot "
        "'pastila_scout\\resources\\expression_retrieval_v1')" in text
    )
    assert text.count("-m pip --isolated") == 6
    assert "duplicate normalized distribution identity" in text
    assert "direct URL requirement is forbidden" in text


def wheel_audit() -> str:
    text = SCRIPT.read_text(encoding="utf-8")
    match = re.search(r"\$wheelAudit = @'\n(.*?)\n'@", text, re.DOTALL)
    assert match
    return match.group(1)


def make_wheel(
    path: Path,
    name: str,
    version: str,
    requirement: str = "",
    *,
    vendored_metadata: bool = False,
    top_level_metadata: bool = True,
    second_top_level: bool = False,
    metadata_name: str | None = None,
) -> None:
    declared_name = metadata_name or name
    metadata = f"Metadata-Version: 2.1\nName: {declared_name}\nVersion: {version}\n"
    if requirement:
        metadata += f"Requires-Dist: {requirement}\n"
    with zipfile.ZipFile(path, "w") as archive:
        if top_level_metadata:
            archive.writestr(f"{name}-{version}.dist-info/METADATA", metadata)
        if second_top_level:
            archive.writestr("second-1.dist-info/METADATA", metadata)
        if vendored_metadata:
            archive.writestr(
                "package/_vendor/example-9.dist-info/METADATA",
                "Metadata-Version: 2.1\nName: vendored-example\nVersion: 9\n",
            )


def test_wheel_audit_accepts_vendored_distribution_metadata(tmp_path: Path) -> None:
    make_wheel(
        tmp_path / "example-1-py3-none-any.whl",
        "example",
        "1",
        vendored_metadata=True,
    )
    result = subprocess.run(
        [sys.executable, "-c", wheel_audit(), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_wheel_audit_accepts_multiple_vendored_identities(tmp_path: Path) -> None:
    path = tmp_path / "example-1-py3-none-any.whl"
    make_wheel(path, "example", "1", vendored_metadata=True)
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr(
            "package/_vendor/second-2.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: second\nVersion: 2\n",
        )
    result = subprocess.run(
        [sys.executable, "-c", wheel_audit(), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"top_level_metadata": False}, "exactly one METADATA"),
        ({"second_top_level": True}, "exactly one METADATA"),
        ({"metadata_name": "different"}, "identity mismatch"),
    ],
)
def test_wheel_audit_rejects_invalid_top_level_identity(
    tmp_path: Path, options: dict[str, object], message: str
) -> None:
    make_wheel(tmp_path / "example-1-py3-none-any.whl", "example", "1", **options)
    result = subprocess.run(
        [sys.executable, "-c", wheel_audit(), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert message in result.stderr


def test_wheel_audit_rejects_filename_identity_mismatch(tmp_path: Path) -> None:
    make_wheel(tmp_path / "renamed-1-py3-none-any.whl", "example", "1")
    result = subprocess.run(
        [sys.executable, "-c", wheel_audit(), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "identity mismatch" in result.stderr


def test_wheel_audit_rejects_duplicate_normalized_identity(tmp_path: Path) -> None:
    make_wheel(tmp_path / "example_package-1-py3-none-any.whl", "Example_Package", "1")
    make_wheel(tmp_path / "example_package-2-py3-none-any.whl", "example.package", "2")
    result = subprocess.run(
        [sys.executable, "-c", wheel_audit(), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "duplicate normalized distribution identity" in result.stderr


@pytest.mark.parametrize(
    "requirement",
    [
        "dependency @ https://example.invalid/dependency.whl",
        "dependency@ https://example.invalid/dependency.whl",
        "dependency\t@\thttps://example.invalid/dependency.whl",
        'dependency[extra] @ HTTPS://example.invalid/dependency.whl; python_version > "3"',
    ],
)
def test_wheel_audit_rejects_direct_url_requirement(
    tmp_path: Path, requirement: str
) -> None:
    make_wheel(
        tmp_path / "example-1-py3-none-any.whl",
        "example",
        "1",
        requirement,
    )
    result = subprocess.run(
        [sys.executable, "-c", wheel_audit(), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "direct URL requirement is forbidden" in result.stderr


def test_wheel_audit_does_not_treat_marker_text_as_direct_url(tmp_path: Path) -> None:
    make_wheel(
        tmp_path / "example-1-py3-none-any.whl",
        "example",
        "1",
        'dependency; os_name == "x@y:https:"',
    )
    result = subprocess.run(
        [sys.executable, "-c", wheel_audit(), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
