"""Negative tests for the V15 execution-bound receipt, without a candidate."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import execute_production_core_candidate_qualification_v15_bound_r2 as consuming  # noqa: E402
import audit_production_core_v15_execution_bound_preflight_r2 as signed  # noqa: E402
import materialize_production_core_v15_execution_bound_preflight_r2 as issuer  # noqa: E402
import preflight_production_core_candidate_qualification_v15_bound_r2 as gate  # noqa: E402


def fixture_authority() -> dict:
    return {
        "authority_identity": "a" * 64, "legacy_preflight_receipt_identity": "b" * 64,
        "alias_secret_commitment": "c" * 64, "source_sha256": {},
    }


def fixture_receipt(now: int) -> dict:
    core = {"schema": gate.SCHEMA, "authority_identity": "a" * 64,
            "legacy_preflight_identity": "b" * 64, "issuer_pid": gate.os.getpid(),
            "issued_at_ns": now, "expires_at_ns": now + gate.LIFETIME_NS,
            "published_commit": issuer.BASE_COMMIT, "published_tree": issuer.BASE_TREE,
            "output": {"path": "/tmp/fixture", "device": 1, "inode": 2, "entries": 0},
            "v13_secret_sha256": "c" * 64}
    return {**core, "receipt_identity": issuer.digest(issuer.canonical(core))}


def test_acyclic_source_graph_and_published_base() -> None:
    names = issuer.NEW_SOURCES
    assert len(names) == len(set(names))
    assert "scripts/execute_production_core_candidate_qualification_v15_bound_r2.py" in names
    assert "scripts/preflight_production_core_candidate_qualification_v15_bound_r2.py" in names
    assert "import audit_production_core_v15_execution_bound_preflight_r2" not in (ROOT / "scripts/materialize_production_core_v15_execution_bound_preflight_r2.py").read_text()
    assert "import preflight_production_core_candidate_qualification_v15_bound" not in (ROOT / "scripts/materialize_production_core_v15_execution_bound_preflight_r2.py").read_text()
    assert issuer.BASE_COMMIT == "c060df236c416dd9ef7d62c987205973da7767a9"
    assert issuer.git("rev-parse", f"{issuer.BASE_COMMIT}^") == "f1cf2967705d29e53fb2e5eccc7459aecc2b43fc"
    assert issuer.PUBLICATION_PARENT == "46fa435afc93831104bb68e03599fcba9fd3c718"
    assert issuer.git("show", "-s", "--format=%P", issuer.PUBLICATION_PARENT) == issuer.BASE_COMMIT
    assert set(issuer.CORRECTIVE_SOURCES) <= set(issuer.NEW_SOURCES)


def test_complete_minimal_consuming_source_closure() -> None:
    a1, a2 = issuer.inherited_maps()
    required = set(issuer.execution_source_keys())
    missing = required - set(a2)
    assert missing == {
        "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
        "scripts/preflight_production_core_candidate_qualification_v15.py",
        "scripts/resolve_production_core_object_authority_v2.sh",
        "scripts/run_production_core_candidate_qualification_v15.sh",
        "scripts/smoke_production_core_checkpoint_resume_v6.py",
        "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
        "src/pastila_scout/production_core_checkpoint_resume_v6.py",
        "src/pastila_scout/production_core_semantic_authority_v2.py",
    }
    assert missing <= set(a1)
    sources = issuer.source_closure()
    assert set(sources) == set(a1) | set(a2) | set(issuer.NEW_SOURCES)
    assert required <= set(sources)
    assert all(sources[name] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
               for name in sources)


def test_every_consuming_source_omission_and_drift_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    a1, a2 = issuer.inherited_maps()
    original_maps = issuer.inherited_maps
    for name in issuer.execution_source_keys():
        left = dict(a1)
        right = dict(a2)
        left.pop(name, None)
        right.pop(name, None)
        with monkeypatch.context() as patch:
            patch.setattr(issuer, "published_base", lambda: ())
            patch.setattr(issuer, "inherited_maps", lambda: (left, right))
            with pytest.raises(ValueError, match="source closure incomplete"):
                issuer.source_closure()
        with monkeypatch.context() as patch:
            altered = dict(a1)
            altered[name] = "0" * 64
            patch.setattr(issuer, "published_base", lambda: ())
            patch.setattr(issuer, "inherited_maps", lambda: (altered, dict(a2)))
            with pytest.raises(ValueError, match="conflict|source drift"):
                issuer.source_closure()
    assert issuer.inherited_maps == original_maps


def test_fixture_consuming_gate_passes_the_previous_failure_without_claim(tmp_path: Path) -> None:
    sources = issuer.source_closure()
    namespace = consuming.mechanics.build_namespace({
        "boundary_identity": "f" * 64, "source_sha256": sources,
    })
    assert callable(namespace["main"])
    assert namespace["atomic"].__name__ == "atomic_no_replace"
    assert list(tmp_path.iterdir()) == []


def test_predecessor_publication_and_signed_artifacts_rejected(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    authority = {"source_sha256": {}, "publication_parent_commit": issuer.PUBLICATION_PARENT}
    ref = f"refs/heads/{issuer.BRANCH}"
    original_git = issuer.git
    # Before push, the old remote ref must fail at the publication/ref gate.
    with monkeypatch.context() as patch:
        patch.setattr(issuer, "git", lambda *args: (
            f"{issuer.BASE_COMMIT}\t{ref}" if args[0] == "ls-remote" else original_git(*args)))
        with pytest.raises(ValueError, match="^execution-bound publication/ref drift$"):
            gate.current_publication(authority)
    # An old R2 ref that matches local HEAD still fails the exact parent gate.
    with monkeypatch.context() as patch:
        patch.setattr(issuer, "git", lambda *args: (
            f"{issuer.PUBLICATION_PARENT}\t{ref}" if args[0] == "ls-remote"
            else issuer.PUBLICATION_PARENT if args == ("rev-parse", "HEAD")
            else original_git(*args)))
        with pytest.raises(ValueError, match="^execution-bound publication parent drift$"):
            gate.current_publication(authority)
    # The predecessor ref cannot masquerade as the corrective successor.
    with monkeypatch.context() as patch:
        patch.setattr(issuer, "git", lambda *args: (
            f"{issuer.BASE_COMMIT}\t{ref}" if args[0] == "ls-remote"
            else issuer.BASE_COMMIT if args == ("rev-parse", "HEAD")
            else original_git(*args)))
        with pytest.raises(ValueError, match="^execution-bound checkpoint ancestry drift$"):
            gate.current_publication(authority)
    old = ROOT / "docs/artifacts/production-core-v15-execution-bound-preflight"
    copied = tmp_path / "old-authority"
    shutil.copytree(old, copied)
    with monkeypatch.context() as patch:
        patch.setattr(issuer, "OUTPUT", copied)
        with pytest.raises(ValueError, match="authority identity rejected"):
            signed.audit(*(tmp_path for _ in range(8)))


def test_old_receipt_and_tampering_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = 1_000_000_000_000
    receipt = fixture_receipt(now)
    secret = tmp_path / "candidate-alias-secret-v13.json"
    secret.write_bytes(b"fixture")
    authority = fixture_authority()
    authority["alias_secret_commitment"] = hashlib.sha256(b"fixture").hexdigest()
    receipt["v13_secret_sha256"] = authority["alias_secret_commitment"]
    core = dict(receipt)
    core.pop("receipt_identity")
    receipt["receipt_identity"] = issuer.digest(issuer.canonical(core))
    monkeypatch.setattr(gate.time, "time_ns", lambda: now + 1)
    monkeypatch.setattr(gate, "current_publication", lambda _: (issuer.BASE_COMMIT, issuer.BASE_TREE))
    monkeypatch.setattr(gate.legacy, "empty_output", lambda *args: receipt["output"])
    gate.verify_receipt(receipt, authority, receipt, tmp_path, tmp_path, ())
    with pytest.raises(ValueError, match="receipt substitution"):
        gate.verify_receipt({"preflight_identity": "b" * 64}, authority, receipt, tmp_path, tmp_path, ())
    wrong = {**receipt, "authority_identity": issuer.BASE_AUTHORITY}
    with pytest.raises(ValueError, match="receipt substitution"):
        gate.verify_receipt(wrong, authority, receipt, tmp_path, tmp_path, ())
    wrong = {**receipt, "receipt_identity": "0" * 64}
    with pytest.raises(ValueError, match="receipt substitution"):
        gate.verify_receipt(wrong, authority, receipt, tmp_path, tmp_path, ())
    monkeypatch.setattr(gate.time, "time_ns", lambda: now + gate.LIFETIME_NS + 1)
    with pytest.raises(ValueError, match="stale"):
        gate.verify_receipt(receipt, authority, receipt, tmp_path, tmp_path, ())


def test_publication_and_runtime_drift_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = 2_000_000_000_000
    receipt = fixture_receipt(now)
    secret = tmp_path / "candidate-alias-secret-v13.json"
    secret.write_bytes(b"fixture")
    authority = fixture_authority()
    authority["alias_secret_commitment"] = hashlib.sha256(b"fixture").hexdigest()
    receipt["v13_secret_sha256"] = authority["alias_secret_commitment"]
    core = dict(receipt)
    core.pop("receipt_identity")
    receipt["receipt_identity"] = issuer.digest(issuer.canonical(core))
    monkeypatch.setattr(gate.time, "time_ns", lambda: now + 1)
    monkeypatch.setattr(gate, "current_publication", lambda _: ("f" * 40, "e" * 40))
    with pytest.raises(ValueError, match="publication changed"):
        gate.verify_receipt(receipt, authority, receipt, tmp_path, tmp_path, ())
    monkeypatch.setattr(gate, "current_publication", lambda _: (issuer.BASE_COMMIT, issuer.BASE_TREE))
    monkeypatch.setattr(gate.legacy, "empty_output", lambda *args: {"entries": 1})
    with pytest.raises(ValueError, match="output changed"):
        gate.verify_receipt(receipt, authority, receipt, tmp_path, tmp_path, ())
    monkeypatch.setattr(gate.legacy, "empty_output", lambda *args: receipt["output"])
    secret.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="V13 secret changed"):
        gate.verify_receipt(receipt, authority, receipt, tmp_path, tmp_path, ())


def test_no_attempt_without_explicit_owner_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "issue", lambda *args: (_ for _ in ()).throw(AssertionError("should not issue")))
    with pytest.raises(ValueError, match="separate owner"):
        consuming.run(*(Path("/tmp/fixture") for _ in range(9)), owner_authorized=False)


def test_noncanonical_output_cannot_bypass_atomic_guard(tmp_path: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "output"
    output.mkdir()
    alias = tmp_path / "output" / ".." / "output"
    monkeypatch.setattr(gate.signed, "audit", lambda *args: (_ for _ in ()).throw(AssertionError("audit reached")))
    with pytest.raises(ValueError, match="canonical"):
        gate.issue(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path, tmp_path,
                   tmp_path, tmp_path, alias)
    with pytest.raises(ValueError, match="canonical"):
        consuming.run(*(tmp_path for _ in range(8)), alias, owner_authorized=True)


def test_fixture_receipt_issuance_without_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    private = tmp_path / "private"
    private.mkdir()
    secret = private / "candidate-alias-secret-v13.json"
    secret.write_bytes(b"fixture-only")
    output = tmp_path / "output"
    output.mkdir()
    state = {"path": str(output), "device": 1, "inode": 2, "filesystem": "ext4", "entries": 0}
    authority = {
        "authority_identity": "a" * 64, "legacy_preflight_receipt_identity": "b" * 64,
        "alias_secret_commitment": hashlib.sha256(b"fixture-only").hexdigest(),
        "output": state, "bound_executor_sha256": "c" * 64,
        "mechanics_executor_sha256": "d" * 64, "validator_sha256": "e" * 64,
        "shell_sha256": "f" * 64, "qualification_generation_identity": "1" * 64,
        "qualification_identity": "2" * 64, "schedule_sha256": "3" * 64,
        "driver_snapshot": {"manifest_identity": "4" * 64},
        "runtime_object_authority_identity": "5" * 64, "rootfs_sha256": "6" * 64,
        "v14_terminal_evidence": {"terminal_failure_sha256": "7" * 64},
        "runner_wall_ns": 600_000_000_000, "runner_max_rss_bytes": 16_106_127_360,
    }
    report = {"authority": authority, "authority_identity": "a" * 64,
              "binding_identity": "8" * 64, "signature_identity": "9" * 64}
    monkeypatch.setattr(gate.signed, "audit", lambda *args: report)
    monkeypatch.setattr(gate, "current_publication", lambda _: (issuer.BASE_COMMIT, issuer.BASE_TREE))
    monkeypatch.setattr(gate, "frozen_mechanics", lambda _: None)
    monkeypatch.setattr(gate.legacy, "preflight", lambda *args: {"preflight_identity": "b" * 64})
    monkeypatch.setattr(gate.legacy, "empty_output", lambda *args: state)
    receipt = gate.issue(tmp_path, private, tmp_path, tmp_path, tmp_path, tmp_path,
                         tmp_path, tmp_path, output)
    assert receipt["schema"] == gate.SCHEMA
    assert receipt["authority_identity"] == "a" * 64
    assert receipt["attempt_consumption"] == 0
    assert receipt["candidate_execution"] == 0
    assert list(output.iterdir()) == []
    gate.verify_receipt(receipt, authority, receipt, private, output, ())


def test_source_and_signature_drift_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    assert issuer.BASE_COMMIT == "c060df236c416dd9ef7d62c987205973da7767a9"
    assert issuer.BASE_TREE == "9f2bd9a0fbddb954ed04f951988adfdf7021180f"
    assert len(issuer.NEW_SOURCES) == 7
    assert consuming.mechanics.atomic_no_replace.__name__ == "atomic_no_replace"
    source = (ROOT / "scripts/execute_production_core_candidate_qualification_v15_bound_r2.py").read_text()
    assert "gate.verify_receipt" in source and "namespace[\"atomic\"] = guarded_atomic" in source
    assert "signed.audit" in source and "attempt.json" in source
    with pytest.raises(ValueError):
        gate.frozen_mechanics({"shell_argument_count": 15, "runner_sha256": "0" * 64})


def test_detached_signature_and_binding_tampering_rejected(tmp_path: Path,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "artifact"
    shutil.copytree(issuer.OUTPUT, artifact)
    monkeypatch.setattr(issuer, "OUTPUT", artifact)
    signature = artifact / "binding.sig"
    original = signature.read_bytes()
    signature.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    with pytest.raises(subprocess.CalledProcessError):
        signed.audit(*(tmp_path for _ in range(8)))
    signature.write_bytes(original)
    binding = artifact / "binding.json"
    binding.write_bytes(binding.read_bytes() + b" ")
    with pytest.raises(ValueError, match="binding"):
        signed.audit(*(tmp_path for _ in range(8)))


def test_v14_launcher_and_runner_drift_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate.mechanics, "LAUNCHER", ROOT / "scripts/run_production_core_candidate_qualification_v14.sh")
    with pytest.raises(ValueError, match="V14 shell"):
        gate.frozen_mechanics({"shell_argument_count": 16, "runner_sha256": "0" * 64,
                               "input_token_cap": 1924, "max_new_tokens": 6268,
                               "decoded_response_byte_cap": 6268, "runner_wall_ns": 600_000_000_000,
                               "runner_max_rss_bytes": 16_106_127_360, "matrix_rows": 2400,
                               "batch_count": 12, "rows_per_batch": 200})
