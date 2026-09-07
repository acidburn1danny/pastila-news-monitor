import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (
    ROOT
    / "docs/artifacts/production-core-semantic-adjudicator-public-key-registry-v1.json"
)
TOP_LEVEL_FIELDS = (
    "schema",
    "schema_version",
    "status",
    "registration_basis_kit_commit",
    "registration_basis_kit_tree",
    "roles",
    "independence_assertion",
    "private_key_material_present",
    "candidate_execution_authorized",
    "candidate_promotion_effect",
    "registry_identity",
)
ROLE_FIELDS = (
    "adjudicator_id",
    "public_key_format",
    "public_key_sha256",
    "public_key_pem_base64",
)
EXPECTED_PUBLIC_KEY_SHA256 = {
    "ADJUDICATOR_A": "e30913d2a150ff6c3c5d621550c94e9559175921ca9dae49bfbe2bbabc911497",
    "ADJUDICATOR_B": "0fcc6461e3e6a0c53693ac834ae7e7264dc379a37b721eb40ace99d12c96c793",
}
ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_registry():
    return json.loads(
        REGISTRY.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicates
    )


def _identity(value):
    body = dict(value)
    body.pop("registry_identity")
    encoded = json.dumps(
        body, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def test_owner_registered_public_key_registry_is_exact_and_identity_closed():
    value = _load_registry()
    assert tuple(value) == TOP_LEVEL_FIELDS
    assert (
        value["schema"]
        == "pastila-production-core-semantic-adjudicator-public-key-registry"
    )
    assert type(value["schema_version"]) is int and value["schema_version"] == 1
    assert value["status"] == "OWNER_REGISTERED_PUBLIC_IDENTITIES"
    assert (
        value["registration_basis_kit_commit"]
        == "776e673a640b1619edbeaf9b4aa2471bcc62d77d"
    )
    assert (
        value["registration_basis_kit_tree"]
        == "44f25a7ea1a4598a75cd83bfa6560bf369a58162"
    )
    assert tuple(value["roles"]) == ("ADJUDICATOR_A", "ADJUDICATOR_B")
    assert value["registry_identity"] == _identity(value)
    assert (
        value["registry_identity"]
        == "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
    )


def test_public_key_bytes_hashes_ids_and_independence_are_closed():
    value = _load_registry()
    expected_ids = {
        "ADJUDICATOR_A": "EVALUATOR-A-01",
        "ADJUDICATOR_B": "EVALUATOR-B-01",
    }
    observed_hashes = set()
    for role, expected_id in expected_ids.items():
        record = value["roles"][role]
        assert tuple(record) == ROLE_FIELDS
        assert record["adjudicator_id"] == expected_id
        assert (
            record["public_key_format"]
            == "PEM_SUBJECT_PUBLIC_KEY_INFO_ED25519_EXACT_BYTES_BASE64"
        )
        key_bytes = base64.b64decode(record["public_key_pem_base64"], validate=True)
        assert (
            base64.b64encode(key_bytes).decode("ascii")
            == record["public_key_pem_base64"]
        )
        assert hashlib.sha256(key_bytes).hexdigest() == record["public_key_sha256"]
        assert record["public_key_sha256"] == EXPECTED_PUBLIC_KEY_SHA256[role]
        assert key_bytes.startswith(b"-----BEGIN PUBLIC KEY-----\r\n")
        assert key_bytes.endswith(b"-----END PUBLIC KEY-----\r\n")
        pem_lines = key_bytes.split(b"\r\n")
        assert len(pem_lines) == 4 and pem_lines[-1] == b""
        der = base64.b64decode(pem_lines[1], validate=True)
        assert len(der) == 44
        assert der.startswith(ED25519_SPKI_PREFIX)
        assert len(der[len(ED25519_SPKI_PREFIX) :]) == 32
        observed_hashes.add(record["public_key_sha256"])
    assert len(observed_hashes) == 2
    assert (
        value["independence_assertion"]
        == "OWNER_DESIGNATED_DISTINCT_HUMAN_EVALUATORS_WITH_DISTINCT_PUBLIC_KEYS"
    )
    assert value["private_key_material_present"] is False
    assert value["candidate_execution_authorized"] is False
    assert value["candidate_promotion_effect"] is False


def test_duplicate_json_keys_are_rejected():
    try:
        json.loads('{"schema":1,"schema":2}', object_pairs_hook=_reject_duplicates)
    except ValueError as exc:
        assert str(exc) == "duplicate JSON key: schema"
    else:
        raise AssertionError("duplicate JSON key accepted")


def test_registry_contains_no_private_key_material_or_host_paths():
    raw = REGISTRY.read_text(encoding="utf-8")
    assert "PRIVATE KEY-----" not in raw
    assert "C:\\" not in raw and "/home/" not in raw
