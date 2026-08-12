from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "packaging" / "pyinstaller" / "PastilaScout.spec"
BUILD = ROOT / "packaging" / "pyinstaller" / "build.ps1"
PRODUCTION = {
    "packaging/pyinstaller/PastilaScout.spec",
    "packaging/pyinstaller/version_info.txt.in",
    "packaging/pyinstaller/build.ps1",
    "packaging/resources/PastilaScout.ico",
    "packaging/resources/THIRD-PARTY-NOTICES.txt",
}
TESTS = {
    "tests/packaging/test_frozen_application_v1.py",
    "tests/packaging/test_version_parity_v1.py",
    "tests/packaging/test_build_mode_v1.py",
}
OWNERSHIP_AUTHORITY = (
    ROOT
    / "docs"
    / "windows-application"
    / "phase-5.6b-r7-r8-installer-test-ownership-refresh-r2.json"
)
OWNERSHIP_AUTHORITY_SHA256 = (
    "63E8E773C5F049C224D1E0C51C7F36E36E5232A7AD6219FE2F3F18AFE1F32933"
)
OWNERSHIP_AUTHORITY_SCHEMA = (
    "pastila-scout-phase-5.6b-installer-test-ownership-refresh-v2"
)


def external_ownership(authority: Path = OWNERSHIP_AUTHORITY) -> dict[str, str]:
    raw = authority.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != OWNERSHIP_AUTHORITY_SHA256:
        raise ValueError("installer-test ownership authority identity mismatch")
    record = json.loads(raw)
    if (
        record.get("schema") != OWNERSHIP_AUTHORITY_SCHEMA
        or record.get("status") != "CANDIDATE_READY_FOR_SEPARATE_FORMAL_FREEZE"
        or record.get("decision") != "R7_R8_TEST_OWNERSHIP_SCOPE_VALID"
    ):
        raise ValueError("installer-test ownership authority is malformed")
    binding = record.get("ownership_binding")
    candidates = record.get("candidate_set")
    if not isinstance(binding, dict) or not isinstance(candidates, dict):
        raise TypeError("installer-test ownership binding is absent")
    path = binding.get("path")
    expected = binding.get("refreshed_sha256")
    if (
        path != "tests/packaging/test_inno_installer_v1.py"
        or not isinstance(expected, str)
        or candidates.get(path) != expected
    ):
        raise ValueError("installer-test ownership binding is inconsistent")
    return {path: expected}


def has_external_ownership(root: Path, relative_path: str) -> bool:
    expected = external_ownership().get(relative_path)
    if expected is None:
        return False
    return (
        hashlib.sha256((root / relative_path).read_bytes()).hexdigest().upper()
        == expected
    )


def phase_candidate_files(root: Path) -> set[str]:
    owned_roots = (
        root / "packaging" / "pyinstaller",
        root / "packaging" / "resources",
        root / "tests" / "packaging",
    )
    return {
        path.relative_to(root).as_posix()
        for owned_root in owned_roots
        for path in owned_root.rglob("*")
        if path.is_file()
        and not (path.suffix == ".pyc" and "__pycache__" in path.parts)
        and not has_external_ownership(root, path.relative_to(root).as_posix())
    }


def assignment(tree: ast.Module, name: str) -> ast.AST:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return node.value
    raise AssertionError(f"missing assignment {name}")


def test_spec_is_valid_python_and_defines_two_analysis_exe_shared_collect() -> None:
    tree = ast.parse(SPEC.read_text(encoding="utf-8"), filename=str(SPEC))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    names = [node.func.id for node in calls if isinstance(node.func, ast.Name)]
    assert names.count("Analysis") == 2
    assert names.count("EXE") == 2
    assert names.count("COLLECT") == 1
    assert "BUNDLE" not in names


def test_spec_has_exact_launcher_names_and_subsystems() -> None:
    tree = ast.parse(SPEC.read_text(encoding="utf-8"))
    exe_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "EXE"
    ]
    observed = {}
    for call in exe_calls:
        values = {
            kw.arg: ast.literal_eval(kw.value)
            for kw in call.keywords
            if kw.arg in {"name", "console"}
        }
        observed[values["name"]] = values["console"]
    assert observed == {"PastilaScout": False, "pastila-scout": True}


def test_spec_resource_and_provider_inventories_are_closed() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert text.count('"default-settings-v1.json"') == 1
    assert text.count('"desktop_v1/default-settings-v1.json"') == 0
    assert text.count('"desktop_v1",') == 1
    assert text.count('"pastila_scout/desktop_v1"') == 0
    assert text.count("pastila-root-1.pub") == 1
    assert text.count("bootstrap-root-v1.json") == 1
    assert "THIRD-PARTY-NOTICES.txt" in text
    assert 'collect_data_files("certifi")' in text
    assert 'copy_metadata("pastila-news-monitor")' in text
    assert "provider_execution_ollama_v1" in text
    assert "provider_runtime_openai_bridged_v2" in text
    assert "editor_generation_authority_v1" in text
    forbidden = (
        "claude",
        "gemini",
        "private_key",
        "provenance",
        "receipt_id",
        "verifier_id",
    )
    assert all(value not in text.lower() for value in forbidden)


def test_production_trust_pair_is_exact_and_cross_bound() -> None:
    trust = ROOT / "resources" / "trust"
    key = (trust / "pastila-root-1.pub").read_bytes()
    bootstrap = json.loads((trust / "bootstrap-root-v1.json").read_bytes())
    assert len(key) == 32
    assert set(bootstrap) == {
        "algorithm",
        "key_id",
        "public_key_filename",
        "public_key_sha256",
        "schema",
        "schema_version",
    }
    assert bootstrap["algorithm"] == "Ed25519"
    assert bootstrap["key_id"] == "pastila-root-1"
    assert bootstrap["public_key_filename"] == "pastila-root-1.pub"
    assert bootstrap["public_key_sha256"] == hashlib.sha256(key).hexdigest()


def test_build_script_governs_exact_wrapper_bytes_and_tool_hash() -> None:
    text = BUILD.read_text(encoding="utf-8")
    gui = re.search(r'\$GuiWrapperText = "([^"]+)"', text)
    cli = re.search(r'\$CliWrapperText = "([^"]+)"', text)
    assert gui and cli
    decode = lambda value: value.replace("`n", "\n")
    assert (
        decode(gui.group(1))
        == "from pastila_scout.desktop_v1.entrypoint import main\n\nraise SystemExit(main())\n"
    )
    assert (
        decode(cli.group(1))
        == "from pastila_scout.cli import main\n\nraise SystemExit(main())\n"
    )
    assert decode(gui.group(1)).encode("utf-8") == (
        b"from pastila_scout.desktop_v1.entrypoint import main\n\n"
        b"raise SystemExit(main())\n"
    )
    assert decode(cli.group(1)).encode("utf-8") == (
        b"from pastila_scout.cli import main\n\nraise SystemExit(main())\n"
    )
    assert "pyinstaller-6.22.0-py3-none-win_amd64.whl" in text
    assert "6E5F3656DE100954BF5DB25536C43E097E46D482843A96D03A0852BF266E4853" in text
    assert "--no-index" in text
    assert "--find-links" in text
    assert "--dry-run" in text and "--report" in text
    assert "Compare-Object $availableFiles $selectedFiles" in text
    assert "production trust resources do not cross-bind exactly" in text
    assert "installed modules or sys.path leak" in text
    assert "installed distribution inventory diverges" in text
    assert "pth_external" in text
    assert "bad_origins" in text
    assert 'for name in ("pastila_scout", "openai", "httpx")' in text


def test_each_launcher_has_its_own_rendered_version_identity() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    build = BUILD.read_text(encoding="utf-8")
    assert "PASTILA_SPEC_GUI_VERSION_INFO" in spec
    assert "PASTILA_SPEC_CLI_VERSION_INFO" in spec
    assert "version-info-gui.txt" in build
    assert "version-info-cli.txt" in build
    assert "Pastila Scout Console" in build


def test_external_resources_have_exact_final_identity_and_are_never_generated() -> None:
    icon = (ROOT / "packaging" / "resources" / "PastilaScout.ico").read_bytes()
    notices = (
        ROOT / "packaging" / "resources" / "THIRD-PARTY-NOTICES.txt"
    ).read_bytes()
    assert len(icon) == 176_052
    assert hashlib.sha256(icon).hexdigest().upper() == (
        "605B76E16C442C97E0268A8203B7F898EE2DE5B17A1654DC043D1F7718B3D947"
    )
    assert len(notices) == 165_124
    notices_sha = hashlib.sha256(notices).hexdigest().upper()
    assert notices_sha == (
        "20DA9DC9E2B66EF7C1774D83A777F4593DB531BC48E6CB4ED4E74604AF096686"
    )
    assert notices_sha != (
        "F1E626E7C1641431598FDFEBC2D6F8C35F1F69C4C679B9105FECBCC64CD02AA3"
    )
    assert notices.count(b"\n") == 3_176
    assert not notices.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in notices
    assert notices.endswith(b"\n")
    text = BUILD.read_text(encoding="utf-8")
    assert "New-Item -ItemType File" not in text
    assert "Copy-Item -LiteralPath $Icon" not in text
    assert "invalid ICO header" in text
    assert "trailing non-ICO payload" in text
    assert "no decodable Windows image entry" in text
    assert "Pastila Scout Third-Party Notices`n`n" in text
    assert "must be UTF-8 without BOM and LF-terminated" in text


def test_exact_final_ownership_and_complete_eight_path_state() -> None:
    assert len(PRODUCTION) == 5 and len(TESTS) == 3
    assert phase_candidate_files(ROOT) == PRODUCTION | TESTS


def test_ownership_ignores_only_real_python_cache_bytecode(tmp_path: Path) -> None:
    cache = tmp_path / "tests" / "packaging" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "test_module.cpython-314.pyc").write_bytes(b"cache")
    rogue = cache / "rogue.py"
    rogue.write_text("not a cache artifact", encoding="utf-8")
    assert phase_candidate_files(tmp_path) == {rogue.relative_to(tmp_path).as_posix()}


def test_external_ownership_requires_exact_path_and_identity(tmp_path: Path) -> None:
    relative = "tests/packaging/test_inno_installer_v1.py"
    authorized = tmp_path / relative
    authorized.parent.mkdir(parents=True)
    authorized.write_bytes((ROOT / relative).read_bytes())
    assert phase_candidate_files(tmp_path) == set()

    authorized.write_bytes(b"wrong identity")
    assert phase_candidate_files(tmp_path) == {relative}


def test_external_ownership_does_not_hide_similar_or_arbitrary_paths(
    tmp_path: Path,
) -> None:
    packaging = tmp_path / "tests" / "packaging"
    packaging.mkdir(parents=True)
    similar = packaging / "test_inno_installer_v2.py"
    ignored = packaging / "ignored-arbitrary.py"
    similar.write_bytes(
        (ROOT / "tests/packaging/test_inno_installer_v1.py").read_bytes()
    )
    ignored.write_text("ignored by Git is not ownership", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("ignored-arbitrary.py\n", encoding="utf-8")
    assert phase_candidate_files(tmp_path) == {
        "tests/packaging/ignored-arbitrary.py",
        "tests/packaging/test_inno_installer_v2.py",
    }


def test_external_ownership_consumes_exact_frozen_r2_authority() -> None:
    assert external_ownership() == {
        "tests/packaging/test_inno_installer_v1.py": (
            "831B730ABD0F8C876C48D50FB0D29DF0E47A4568B6A35C9C6F7E4599272F99CE"
        )
    }


def test_external_ownership_authority_fails_closed(tmp_path: Path) -> None:
    authority = tmp_path / "authority.json"
    try:
        external_ownership(authority)
    except OSError:
        pass
    else:
        raise AssertionError("missing ownership authority was accepted")
    for raw in (
        b"{}",
        b"not json",
        OWNERSHIP_AUTHORITY.read_bytes().replace(
            b"831B730ABD0F8C876C48D50FB0D29DF0E47A4568B6A35C9C6F7E4599272F99CE",
            b"39BD76109D598D1295E2E9E3611D221FD433A30EC8D8442E66F29CF1FFD8E89F",
        ),
    ):
        authority.write_bytes(raw)
        try:
            external_ownership(authority)
        except (ValueError, json.JSONDecodeError):
            pass
        else:
            raise AssertionError("invalid ownership authority was accepted")
