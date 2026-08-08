from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TRUST_DIR = ROOT / "resources" / "trust"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "windows-trust"
PRODUCTION_KEY = TRUST_DIR / "pastila-root-1.pub"
PRODUCTION_BOOTSTRAP = TRUST_DIR / "bootstrap-root-v1.json"
DEVELOPMENT_KEY = FIXTURE_DIR / "development-pastila-root-1.pub"
DEVELOPMENT_BOOTSTRAP = FIXTURE_DIR / "development-bootstrap-root-v1.json"
SPECIFICATION = (
    ROOT / "docs" / "windows-application" / "TrustBootstrapSpecificationV1.md"
)

PRODUCTION_KEY_SHA256 = (
    "938d9b808fbbfeac58a8e8991814907bafdd191ff84c065442d690b353edb757"
)
DEVELOPMENT_KEY_HEX = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
DEVELOPMENT_KEY_SHA256 = (
    "21fe31dfa154a261626bf854046fd2271b7bed4b6abe45aa58877ef47f9721b9"
)
DEVELOPMENT_BOOTSTRAP_SHA256 = (
    "e39d301d0c3edf1ab3e93e438a2ed7b59f28eb55d81189d75e1e3453433e5ea6"
)
EXPECTED_KEYS = {
    "schema",
    "schema_version",
    "key_id",
    "algorithm",
    "public_key_filename",
    "public_key_sha256",
}


class InvalidBootstrap(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidBootstrap("duplicate member")
        result[key] = value
    return result


def _parse_canonical(data: bytes) -> dict[str, object]:
    if data.startswith(b"\xef\xbb\xbf") or data != data.strip() or data.endswith(b"\n"):
        raise InvalidBootstrap("noncanonical envelope")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, InvalidBootstrap) as exc:
        raise InvalidBootstrap("invalid metadata") from exc
    if not isinstance(value, dict) or _canonical(value) != data:
        raise InvalidBootstrap("non-JCS metadata")
    return value


def _validate_pair(
    key_bytes: bytes,
    bootstrap_bytes: bytes,
    *,
    filename: str,
    stable: bool,
) -> dict[str, object]:
    if len(key_bytes) != 32:
        raise InvalidBootstrap("invalid key length")
    if key_bytes.startswith((b"-----BEGIN", b"ssh-", b"0" * 16)):
        raise InvalidBootstrap("encoded key")
    value = _parse_canonical(bootstrap_bytes)
    if set(value) != EXPECTED_KEYS:
        raise InvalidBootstrap("wrong member set")
    expected = {
        "schema": "pastila-scout-bootstrap-root",
        "schema_version": 1,
        "key_id": "pastila-root-1",
        "algorithm": "Ed25519",
        "public_key_filename": filename,
        "public_key_sha256": _sha256(key_bytes),
    }
    if value != expected or isinstance(value["schema_version"], bool):
        raise InvalidBootstrap("wrong identity or binding")
    digest = value["public_key_sha256"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise InvalidBootstrap("invalid digest")
    if stable and (
        filename != "pastila-root-1.pub"
        or key_bytes == bytes.fromhex(DEVELOPMENT_KEY_HEX)
        or digest == DEVELOPMENT_KEY_SHA256
        or _sha256(bootstrap_bytes) == DEVELOPMENT_BOOTSTRAP_SHA256
    ):
        raise InvalidBootstrap("development trust in production")
    return value


def _production_pair() -> tuple[bytes, bytes]:
    return PRODUCTION_KEY.read_bytes(), PRODUCTION_BOOTSTRAP.read_bytes()


def _development_pair() -> tuple[bytes, bytes]:
    return DEVELOPMENT_KEY.read_bytes(), DEVELOPMENT_BOOTSTRAP.read_bytes()


def test_trust_v001_maintained_authority_chain() -> None:
    text = SPECIFICATION.read_text(encoding="utf-8")
    assert "phase-5.5a-trust-bootstrap-spec-v1-ready" in text
    assert (
        "phase-5-productization-single-owner-trust-policy-maintenance-r1-verified"
        in text
    )
    assert "1F19D796BFAC4E87E897C27E999B6251986A207141BB01BC27183923DA476693" in text


def test_trust_v002_exact_path_ownership() -> None:
    assert {path.name for path in TRUST_DIR.iterdir()} == {
        "pastila-root-1.pub",
        "bootstrap-root-v1.json",
    }
    assert {path.name for path in FIXTURE_DIR.iterdir()} == {
        "development-pastila-root-1.pub",
        "development-bootstrap-root-v1.json",
    }
    assert not (TRUST_DIR / "bootstrap-root-provenance-v1.json").exists()


def test_trust_v003_private_material_exclusion() -> None:
    inspected = [*TRUST_DIR.iterdir(), *FIXTURE_DIR.iterdir()]
    assert all(
        "private" not in path.name.lower() and "seed" not in path.name.lower()
        for path in inspected
    )
    assert all(b"PRIVATE KEY" not in path.read_bytes() for path in inspected)


def test_trust_v004_phase_exclusions() -> None:
    assert not (ROOT / "src" / "pastila_scout" / "windows_trust_v1").exists()
    assert not (ROOT / "resources" / "trust" / "manifest.json").exists()


def test_trust_v005_exact_root_identity() -> None:
    value = _parse_canonical(PRODUCTION_BOOTSTRAP.read_bytes())
    assert value["key_id"] == "pastila-root-1"


@pytest.mark.parametrize(
    "key", [b"x" * 31, b"x" * 33, b"-----BEGIN PUBLIC KEY-----", b"00" * 32]
)
def test_trust_v006_raw_key_boundaries(key: bytes) -> None:
    with pytest.raises(InvalidBootstrap):
        _validate_pair(
            key,
            PRODUCTION_BOOTSTRAP.read_bytes(),
            filename="pastila-root-1.pub",
            stable=True,
        )


def test_trust_v007_production_raw_sha256() -> None:
    key = PRODUCTION_KEY.read_bytes()
    assert len(key) == 32
    assert _sha256(key) == PRODUCTION_KEY_SHA256
    assert b"\n" not in key and not key.startswith(b"\xef\xbb\xbf")


def test_trust_v008_owner_public_input_only() -> None:
    assert PRODUCTION_KEY.is_file()
    assert all(path.suffix != ".pem" for path in TRUST_DIR.iterdir())


def test_trust_v009_exact_six_member_schema() -> None:
    value = _validate_pair(
        *_production_pair(), filename="pastila-root-1.pub", stable=True
    )
    assert set(value) == EXPECTED_KEYS
    assert value["schema_version"] == 1 and type(value["schema_version"]) is int
    assert "provenance_filename" not in value and "provenance_sha256" not in value


def test_trust_v010_strict_jcs() -> None:
    for path in (PRODUCTION_BOOTSTRAP, DEVELOPMENT_BOOTSTRAP):
        data = path.read_bytes()
        assert data == _canonical(_parse_canonical(data))


@pytest.mark.parametrize(
    "field",
    ["schema", "schema_version", "key_id", "public_key_filename", "public_key_sha256"],
)
def test_trust_v011_pair_binding_mutations(field: str) -> None:
    key, data = _production_pair()
    value = _parse_canonical(data)
    value[field] = False if field == "schema_version" else "wrong"
    with pytest.raises(InvalidBootstrap):
        _validate_pair(
            key, _canonical(value), filename="pastila-root-1.pub", stable=True
        )


@pytest.mark.parametrize(
    "field,value", [("algorithm", "ed25519"), ("algorithm", "EdDSA")]
)
def test_trust_v012_algorithm_and_fallback_rejection(field: str, value: str) -> None:
    key, data = _production_pair()
    document = _parse_canonical(data)
    document[field] = value
    with pytest.raises(InvalidBootstrap):
        _validate_pair(
            key, _canonical(document), filename="pastila-root-1.pub", stable=True
        )


def test_trust_v013_exact_development_vector() -> None:
    key, bootstrap = _development_pair()
    assert key == bytes.fromhex(DEVELOPMENT_KEY_HEX)
    assert _sha256(key) == DEVELOPMENT_KEY_SHA256
    assert len(bootstrap) == 250
    assert _sha256(bootstrap) == DEVELOPMENT_BOOTSTRAP_SHA256
    _validate_pair(
        key, bootstrap, filename="development-pastila-root-1.pub", stable=False
    )


@pytest.mark.parametrize(
    "key,filename",
    [
        (bytes.fromhex(DEVELOPMENT_KEY_HEX), "pastila-root-1.pub"),
        (bytes.fromhex(DEVELOPMENT_KEY_HEX), "development-pastila-root-1.pub"),
    ],
)
def test_trust_v014_stable_development_rejection(key: bytes, filename: str) -> None:
    value = {
        "schema": "pastila-scout-bootstrap-root",
        "schema_version": 1,
        "key_id": "pastila-root-1",
        "algorithm": "Ed25519",
        "public_key_filename": filename,
        "public_key_sha256": _sha256(key),
    }
    with pytest.raises(InvalidBootstrap):
        _validate_pair(key, _canonical(value), filename=filename, stable=True)


def test_trust_v015_literal_safe_paths() -> None:
    for value in (
        _parse_canonical(PRODUCTION_BOOTSTRAP.read_bytes()),
        _parse_canonical(DEVELOPMENT_BOOTSTRAP.read_bytes()),
    ):
        filename = value["public_key_filename"]
        assert isinstance(filename, str)
        assert (
            filename == Path(filename).name
            and "/" not in filename
            and "\\" not in filename
        )


def test_trust_v016_no_mutable_copy_or_repair() -> None:
    assert not (ROOT / "data" / "trust").exists()
    assert not (ROOT / "config" / "trust").exists()


def test_trust_v017_resource_test_only_delta() -> None:
    owned = {
        path.relative_to(ROOT).as_posix()
        for directory in (TRUST_DIR, FIXTURE_DIR)
        for path in directory.rglob("*")
        if path.is_file()
    }
    owned.add(Path(__file__).resolve().relative_to(ROOT).as_posix())
    assert owned == {
        "resources/trust/pastila-root-1.pub",
        "resources/trust/bootstrap-root-v1.json",
        "tests/fixtures/windows-trust/development-pastila-root-1.pub",
        "tests/fixtures/windows-trust/development-bootstrap-root-v1.json",
        "tests/test_trust_bootstrap_resource_v1.py",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        b"\xef\xbb\xbf{}",
        b"{}\n",
        b'{"schema":"x", "schema_version":1}',
        b'{"schema":"x","schema":"y"}',
        b"[]",
    ],
)
def test_trust_v018_invalid_metadata_fail_closed(mutation: bytes) -> None:
    with pytest.raises(InvalidBootstrap):
        _validate_pair(
            PRODUCTION_KEY.read_bytes(),
            mutation,
            filename="pastila-root-1.pub",
            stable=True,
        )


def test_trust_v019_diagnostics_are_bounded() -> None:
    with pytest.raises(InvalidBootstrap, match="invalid metadata") as captured:
        _parse_canonical(b"not-json")
    assert str(ROOT) not in str(captured.value)


def test_trust_v020_no_runtime_types_or_locators() -> None:
    assert not (ROOT / "src" / "pastila_scout" / "trust_bootstrap_v1.py").exists()
    assert not (ROOT / "src" / "pastila_scout" / "windows_trust_v1").exists()


def test_trust_v021_downstream_technical_inputs_only() -> None:
    value = _parse_canonical(PRODUCTION_BOOTSTRAP.read_bytes())
    assert set(value) == EXPECTED_KEYS
    assert not (
        {"operator", "receipt", "timestamp", "witness", "custody", "provenance"}
        & set(value)
    )


def test_trust_v022_no_lifecycle_or_optional_verification() -> None:
    text = SPECIFICATION.read_text(encoding="utf-8")
    assert "Nothing here makes signature verification optional" in text
    assert "Operational rotation and recovery remain excluded" in text


def test_trust_v023_exact_owners_no_hidden_sixth_path() -> None:
    assert len(list(TRUST_DIR.iterdir())) == 2
    assert len(list(FIXTURE_DIR.iterdir())) == 2
    assert Path(__file__).name == "test_trust_bootstrap_resource_v1.py"


def test_trust_v024_determinism_and_history() -> None:
    for key_path, bootstrap_path, filename in (
        (PRODUCTION_KEY, PRODUCTION_BOOTSTRAP, "pastila-root-1.pub"),
        (DEVELOPMENT_KEY, DEVELOPMENT_BOOTSTRAP, "development-pastila-root-1.pub"),
    ):
        key = key_path.read_bytes()
        expected = {
            "schema": "pastila-scout-bootstrap-root",
            "schema_version": 1,
            "key_id": "pastila-root-1",
            "algorithm": "Ed25519",
            "public_key_filename": filename,
            "public_key_sha256": _sha256(key),
        }
        assert bootstrap_path.read_bytes() == _canonical(expected)
    assert (
        subprocess.run(
            [
                "git",
                "rev-parse",
                "phase-5.5a-single-owner-trust-maintenance-r1-verified^{}",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "e5b9bbb382d31dc3a16aa3927868fa3b9e724234"
    )
