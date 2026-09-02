import base64
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout import semantic_authority_cosign_v2_3_7 as subject


def _manifest():
    value = {
        "schema": "SEMANTIC_AUTHORITY_PUBLIC_ATTESTATION_DEPLOYMENT_V2_3_7",
        "v2_3_6_governance_identity": "a" * 64,
        "v2_3_6_deployment_identity": "f" * 64,
        "repository_slug": "owner/repository",
        "repository_id": "123",
        "owner_id": "456",
        "workflow_commit": "b" * 40,
        "workflow_blob_sha256": "c" * 64,
        "schedule_precommit_identity": "d" * 64,
        "cosign_sha256": subject.COSIGN_LINUX_SHA256,
        "launcher_sha256": "e" * 64,
        "wsl_sha256": subject.WSL_SHA256,
        "containment_dependency_root": subject.CONTAINMENT_DEPENDENCY_ROOT,
        "trusted_root_sha256": subject.TRUSTED_ROOT_SHA256,
        "tuf_root_version": 1,
        "tuf_snapshot_version": 165,
        "tuf_targets_version": 14,
    }
    value["deployment_identity"] = subject.identity(value, "deployment_identity")
    return value


def test_deployment_manifest_is_exact_and_identity_closed(monkeypatch):
    value = _manifest()
    governance = {"governance_identity": "a" * 64}
    deployment = {key: value[key] for key in ("repository_slug", "repository_id", "owner_id", "workflow_commit", "workflow_blob_sha256")}
    deployment["deployment_identity"] = "f" * 64
    monkeypatch.setattr(subject.v236, "validate_deployment", lambda d, g: None)
    subject.validate_deployment_manifest(value, v236_governance=governance, v236_deployment=deployment)
    for mutation in (
        lambda v: v.update(extra=True),
        lambda v: v.update(repository_id="0"),
        lambda v: v.update(workflow_commit="main"),
        lambda v: v.update(cosign_sha256="0" * 64),
        lambda v: v.update(tuf_targets_version=13),
        lambda v: v.update(deployment_identity="0" * 64),
    ):
        altered = dict(value)
        mutation(altered)
        with pytest.raises(ValueError):
            subject.validate_deployment_manifest(altered, v236_governance=governance, v236_deployment=deployment)


def test_dsse_statement_is_decoded_but_not_treated_as_crypto_proof():
    statement = {"_type": "https://in-toto.io/Statement/v1", "subject": []}
    envelope = {
        "dsseEnvelope": {
            "payload": base64.b64encode(json.dumps(statement).encode()).decode(),
            "payloadType": "application/vnd.in-toto+json",
            "signatures": [{"sig": "not-a-proof"}],
        }
    }
    assert subject.decode_dsse_statement(json.dumps(envelope).encode()) == statement
    envelope["dsseEnvelope"]["payload"] = "%%%"
    with pytest.raises(ValueError):
        subject.decode_dsse_statement(json.dumps(envelope).encode())


def test_contained_runner_hashes_launcher_and_closes_environment(tmp_path, monkeypatch):
    launcher = tmp_path / "launcher.sh"
    launcher.write_bytes(b"launcher")
    wsl = tmp_path / "wsl.exe"
    wsl.write_bytes(b"wsl")
    launcher_hash = hashlib.sha256(b"launcher").hexdigest()
    wsl_hash = hashlib.sha256(b"wsl").hexdigest()
    seen = {}

    def fake_run(command, **kwargs):
        seen.update(command=command, kwargs=kwargs)
        return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b"Verified OK"})()

    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    monkeypatch.setattr(subject, "WSL_SHA256", wsl_hash)
    subject.run_contained(
        wsl=wsl, distribution="Ubuntu-24.04",
        launcher_host=launcher, launcher_linux="/mnt/c/repo/launcher.sh",
        launcher_sha256=launcher_hash, cosign_linux="/mnt/c/tools/cosign", args=["version"],
    )
    assert seen["kwargs"]["env"] == {"SystemRoot": r"C:\Windows", "WINDIR": r"C:\Windows"}
    assert seen["command"][seen["command"].index("--launcher-sha256") + 1] == launcher_hash
    assert seen["command"][-1] == "version"
    launcher.write_bytes(b"changed")
    with pytest.raises(ValueError, match="launcher hash"):
        subject.run_contained(
            wsl=wsl, distribution="Ubuntu-24.04", launcher_host=launcher,
            launcher_linux="/mnt/c/repo/launcher.sh", launcher_sha256=launcher_hash,
            cosign_linux="/mnt/c/tools/cosign", args=["version"],
        )


def test_attestation_adapter_requires_complete_github_claim_tuple(tmp_path, monkeypatch):
    launcher = tmp_path / "launcher.sh"
    launcher.write_bytes(b"x")
    pin = hashlib.sha256(b"x").hexdigest()
    monkeypatch.setattr(subject, "run_contained", lambda **kwargs: type("R", (), {"returncode": 0, "stdout": b"Verified OK", "stderr": b""})())
    with pytest.raises(ValueError, match="partial GitHub"):
        subject.verify_blob_attestation(
            wsl=Path("wsl.exe"), distribution="Ubuntu-24.04", launcher_host=launcher,
            launcher_linux="/mnt/c/l", launcher_sha256=pin, cosign_linux="/mnt/c/c",
            bundle_linux="/mnt/c/b", trusted_root_linux="/mnt/c/r", digest="0" * 64,
            certificate_identity="id", oidc_issuer="issuer", github_repository="owner/repo",
        )


def test_launcher_uses_kernel_network_namespace_and_closed_environment():
    text = Path("scripts/run_cosign_offline_v2_3_7.sh").read_text(encoding="utf-8")
    for required in ("${BASH_SOURCE[0]}", "launcher_actual", "sha256sum", "realpath --canonicalize-existing", "unshare --user --map-root-user --net", "env -i"):
        assert required in text
    for forbidden in ("http_proxy", "https_proxy", "NO_PROXY", "curl ", "wget "):
        assert forbidden not in text


def test_frozen_zero_network_qualification_is_identity_closed():
    path = Path("docs/artifacts/semantic-contract-v2-3-7-cosign-zero-network-qualification.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["qualification_identity"] == subject.identity(value, "qualification_identity")
    assert value["implementation"]["module_sha256"] == subject.sha(Path(subject.__file__).read_bytes())
    assert value["implementation"]["test_sha256"] == subject.sha(Path(__file__).read_bytes())
    assert value["implementation"]["launcher_sha256"] == subject.sha(Path("scripts/run_cosign_offline_v2_3_7.sh").read_bytes())
    assert value["implementation"]["wsl_sha256"] == subject.WSL_SHA256
    assert value["implementation"]["containment_dependency_root"] == subject.CONTAINMENT_DEPENDENCY_ROOT
    assert value["activity_boundary"] == {
        "authority_bases_created_or_admitted": 0,
        "blind_or_future_family_access": False,
        "curriculum_population": False,
        "pilot15_executed": False,
        "registry_metadata_acquired": False,
        "registry_snapshots_acquired": False,
        "workflow_deployed": False,
    }
    assert value["remaining_blockers"] == [
        "PUBLIC_WORKFLOW_AND_IMMUTABLE_DEPLOYMENT_MANIFEST_NOT_YET_DEPLOYED_OR_FROZEN"
    ]
