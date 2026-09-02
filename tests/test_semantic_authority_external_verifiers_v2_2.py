import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_authority_external_verifiers_v2_2 import (
    qualify_rekor_executable,
    sha256_file,
    verify_quicknet_offline,
)


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tool-downloads" / "v2-2-verifiers"
NODE_ROOT = TOOLS / "node-v22.23.2-win-x64"
CLIENT_RUNTIME = TOOLS / "drand-client-runtime"
CLIENT = CLIENT_RUNTIME / "node_modules" / "drand-client"
LAUNCHER = ROOT / "src" / "pastila_scout" / "drand_quicknet_verify_v2_2.cjs"


def pins():
    if not (TOOLS / "installation.json").is_file():
        pytest.skip("repository-scoped verifier installation is intentionally uncommitted")
    return json.loads((TOOLS / "installation.json").read_text(encoding="utf-8"))


def drand_args(info, beacon):
    p = pins()
    return dict(
        node=NODE_ROOT / "node.exe", node_sha256=p["node_executable_sha256"],
        node_tree_sha256=p["node_runtime_tree_sha256"],
        launcher=LAUNCHER, launcher_sha256=p["drand_launcher_sha256"],
        client_root=CLIENT, client_lock=CLIENT_RUNTIME / "package-lock.json",
        client_lock_sha256=p["drand_client_lock_sha256"], chain_info=info,
        client_tree_sha256=p["drand_client_tree_sha256"],
        beacon=beacon, expected_round=1,
    )


def test_rekor_binary_is_official_hash_pinned_and_launches_without_network():
    p = pins()
    assert qualify_rekor_executable(
        TOOLS / "rekor-cli-windows-amd64.exe",
        expected_sha256=p["rekor_executable_sha256"],
    ) == "v1.5.1/windows-amd64"


def test_quicknet_bls_valid_upstream_vector_and_tamper_fail_closed(monkeypatch):
    info = json.loads((TOOLS / "quicknet-info.json").read_text(encoding="utf-8"))
    beacon = json.loads((TOOLS / "quicknet-round-1.json").read_text(encoding="utf-8"))
    monkeypatch.setenv("NODE_OPTIONS", "--require=C:\\attacker-controlled-preload.cjs")
    monkeypatch.setenv("NODE_PATH", "C:\\attacker-controlled-modules")
    verify_quicknet_offline(**drand_args(info, beacon))
    bad = dict(beacon, signature="00" + beacon["signature"][2:])
    with pytest.raises(ValueError):
        verify_quicknet_offline(**drand_args(info, bad))
    wrong = dict(info, hash="0" * 64)
    with pytest.raises(ValueError):
        verify_quicknet_offline(**drand_args(wrong, beacon))
    wrong_key = dict(info, public_key="0" * len(info["public_key"]))
    with pytest.raises(ValueError):
        verify_quicknet_offline(**drand_args(wrong_key, beacon))


def test_pins_reject_component_and_lockfile_skew(tmp_path):
    info = json.loads((TOOLS / "quicknet-info.json").read_text(encoding="utf-8"))
    beacon = json.loads((TOOLS / "quicknet-round-1.json").read_text(encoding="utf-8"))
    args = drand_args(info, beacon)
    args["node_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        verify_quicknet_offline(**args)
    fake = tmp_path / "lock.json"; fake.write_text("{}", encoding="utf-8")
    args = drand_args(info, beacon); args["client_lock"] = fake
    with pytest.raises(ValueError):
        verify_quicknet_offline(**args)


def test_local_installation_record_is_content_closed():
    p = pins()
    assert sha256_file(TOOLS / "quicknet-info.json") == p["drand"]["quicknet_info_fixture_sha256"]
    assert sha256_file(TOOLS / "quicknet-round-1.json") == p["drand"]["quicknet_round_1_fixture_sha256"]
    assert sha256_file(TOOLS / "rekor-checksums.txt") == p["rekor"]["checksums_sha256"]


def test_qualification_record_is_identity_closed_without_local_installation():
    record_path = ROOT / "docs" / "artifacts" / "semantic-contract-v2-2-external-verifiers-zero-network-qualification.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    identity = record.pop("qualification_identity")
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    assert hashlib.sha256(canonical).hexdigest() == identity
    assert record["network_during_qualification"] is False
    assert record["registry_snapshots_acquired"] == 0
    assert record["real_frame_executed"] is False
