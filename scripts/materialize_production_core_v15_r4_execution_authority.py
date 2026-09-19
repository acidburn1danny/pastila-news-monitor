"""Build a separately signed R4 boundary without executing a candidate."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_r3_execution_authority as r3
import preflight_production_core_candidate_qualification_v15 as legacy
import project_production_core_candidate_qualification_v15_r4 as projection
from pastila_scout import production_core_successor_contract_v15_r3 as contract

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v15-r4-execution-authority"
R3_COMMIT = "cb2f05909fc833ad4a1643b35753feda59017393"
R3_TREE = "6f1441fc3c1877946271e6240a16ff4b88325286"
R3_AUTHORITY = "e6e0fc4c74b29b81335048a7a71f69fe306308281ed1852b740ccc67b2e63997"
R4_OUTPUT = Path("/root/pf9-v15-r4-preconsumption-output")
BRANCH = r3.BRANCH
ARTIFACT_NAMES = r3.ARTIFACT_NAMES
NEW_SOURCES = (
    "docs/production-core-v15-r4-namespace-successor.md",
    "scripts/project_production_core_candidate_qualification_v15_r4.py",
    "scripts/materialize_production_core_v15_r4_execution_authority.py",
    "scripts/audit_production_core_v15_r4_execution_authority.py",
    "scripts/preflight_production_core_candidate_qualification_v15_r4.py",
    "scripts/execute_production_core_candidate_qualification_v15_r4.py",
    "scripts/supervise_production_core_candidate_qualification_v15_r4.py",
    "tests/test_production_core_v15_r4_execution_authority.py",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def historical_r3() -> dict:
    """Verify the published R3 snapshot and immutable R2/V14 evidence."""
    head = git("rev-parse", "HEAD")
    if head != R3_COMMIT and git("show", "-s", "--format=%P", head) != R3_COMMIT:
        raise ValueError("R4 HEAD must be R3 or its direct successor")
    if (git("rev-parse", f"{R3_COMMIT}^{{tree}}") != R3_TREE
            or git("rev-parse", f"refs/remotes/origin/{BRANCH}") not in (R3_COMMIT, head)):
        raise ValueError("R3 published checkpoint drift")
    root = r3.OUTPUT
    paths = {name: root / name for name in ARTIFACT_NAMES}
    if (root.is_symlink() or {p.name for p in root.iterdir()} != set(ARTIFACT_NAMES)
            or any(p.is_symlink() or not p.is_file() or p.read_bytes() != subprocess.check_output(
                ["git", "show", f"{R3_COMMIT}:{p.relative_to(ROOT).as_posix()}"], cwd=ROOT)
                for p in paths.values())):
        raise ValueError("R3 signed artifact publication drift")
    authority_raw = paths["authority.json"].read_bytes()
    authority = json.loads(authority_raw)
    core = dict(authority)
    claimed = core.pop("authority_identity", None)
    if (claimed != R3_AUTHORITY or claimed != digest(canonical(core))
            or paths["binding.json"].read_bytes() != r3.canonical(r3.binding_for(authority, authority_raw))
            or paths["builder-source.py"].read_bytes() !=
            (ROOT / "scripts/materialize_production_core_v15_r3_execution_authority.py").read_bytes()):
        raise ValueError("R3 signed authority drift")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey",
                    str(signing.PUBLIC_KEY), "-rawin", "-in", str(paths["binding.json"]),
                    "-sigfile", str(paths["binding.sig"])], check=True, capture_output=True)
    if authority["publication_parent_commit"] != r3.R2_COMMIT or authority["historical_r2"]["attempt_identity"] != r3.R2_ATTEMPT:
        raise ValueError("R3 historical parent binding drift")
    r2_attempt = r3.R2_OUTPUT / "attempt.json"
    if (r2_attempt.is_symlink() or digest(r2_attempt.read_bytes()) != r3.R2_ATTEMPT_SHA256
            or (r3.R2_OUTPUT / "completion.json").exists()
            or (r3.R2_OUTPUT / "terminal-failure.json").exists()):
        raise ValueError("R2 consumed attempt drift")
    inventory = [(str(p.relative_to(r3.R2_OUTPUT)), digest(p.read_bytes()))
                 for p in sorted(r3.R2_OUTPUT.rglob("*")) if p.is_file()]
    if len(inventory) != 806 or digest(json.dumps(inventory, separators=(",", ":")).encode()) != r3.R2_INVENTORY_ROOT:
        raise ValueError("R2 evidence inventory drift")
    v14 = Path("/root/pf9-v14-preconsumption-output/terminal-failure.json")
    if v14.is_symlink() or digest(v14.read_bytes()) != r3.V14_TERMINAL_SHA256:
        raise ValueError("V14 terminal evidence drift")
    if (r3.R3_OUTPUT.is_symlink() or not r3.R3_OUTPUT.is_dir()
            or list(r3.R3_OUTPUT.iterdir())
            or r3.R3_OUTPUT.stat().st_dev != authority["output"]["device"]
            or r3.R3_OUTPUT.stat().st_ino != authority["output"]["inode"]):
        raise ValueError("unconsumed historical R3 output drift")
    return {
        "published_commit": R3_COMMIT, "published_tree": R3_TREE,
        "authority_identity": claimed,
        "binding_identity": digest(paths["binding.json"].read_bytes()),
        "signature_identity": digest(paths["binding.sig"].read_bytes()),
        "historical_r2": authority["historical_r2"],
        "r3_output": authority["output"],
        "v14_terminal_failure_sha256": r3.V14_TERMINAL_SHA256,
    }


def source_closure(r3_authority: dict) -> dict[str, str]:
    inherited = r3_authority.get("source_sha256")
    if not isinstance(inherited, dict) or set(inherited) & set(NEW_SOURCES):
        raise ValueError("R4 source inheritance rejected")
    sources = dict(inherited)
    for name, expected in inherited.items():
        path = ROOT / name
        if (path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected
                or digest(subprocess.check_output(["git", "show", f"{R3_COMMIT}:{name}"], cwd=ROOT)) != expected):
            raise ValueError(f"R3 published source drift: {name}")
    for name in NEW_SOURCES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"R4 source missing: {name}")
        sources[name] = digest(path.read_bytes())
    return dict(sorted(sources.items()))


def build(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
          output: Path) -> dict:
    historical = historical_r3()
    r3_authority = json.loads((r3.OUTPUT / "authority.json").read_bytes())
    sources = source_closure(r3_authority)
    if output != R4_OUTPUT or output in (r3.R2_OUTPUT, r3.R3_OUTPUT):
        raise ValueError("R4 output substitution")
    old = legacy.preflight(recovery, private, backup, v13_terminal, terminal,
                           rootfs, snapshot, unicode_root, output)
    if old.get("verdict") != "PASS + 0 BLOCKERS" or old.get("output", {}).get("entries") != 0:
        raise ValueError("R4 runtime or output preflight rejected")
    manifest = json.loads((ROOT / "docs/artifacts/production-core-candidate-request-manifest-v2.json").read_bytes())
    if len(contract.validate_manifest_contract(manifest)) != 200:
        raise ValueError("R4 request/validator contract rejected")
    boundary = {"boundary_identity": "0" * 64, "source_sha256": sources}
    namespace = projection.build_namespace(boundary)
    projection.verify_namespace(namespace, boundary)
    projected = r3.projection.projected_mechanics()
    syntax = ast.parse(projected)
    commands = [node.value for node in ast.walk(syntax)
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.List)
                and any(isinstance(target, ast.Name) and target.id == "command"
                        for target in node.targets)]
    if len(commands) != 1:
        raise ValueError("R4 shell projection missing")
    command = commands[0].elts
    marker = next((i for i, node in enumerate(command)
                   if isinstance(node, ast.Constant) and node.value == "--"), None)
    if marker is None or len(command[marker + 1:]) != 16:
        raise ValueError("R4 16-argument shell projection mismatch")
    if source_closure(r3_authority) != sources or historical_r3() != historical:
        raise ValueError("R4 source or historical evidence changed during build")
    namespace_claim = projection.binding_claim(sources)
    core = {
        "schema": "pastila-production-core-v15-r4-execution-authority",
        "schema_version": 1, "status": "SIGNED_NO_CANDIDATE_NO_ATTEMPT",
        "publication_parent_commit": R3_COMMIT, "publication_parent_tree": R3_TREE,
        "historical_r3": historical,
        "base_v15_authority_identity": r3_authority["base_v15_authority_identity"],
        "published_preflight_commit": r3_authority["published_preflight_commit"],
        "qualification_generation_identity": r3_authority["qualification_generation_identity"],
        "qualification_identity": r3_authority["qualification_identity"],
        "schedule_sha256": r3_authority["schedule_sha256"],
        "alias_secret_commitment": r3_authority["alias_secret_commitment"],
        "runtime_object_authority_identity": r3_authority["runtime_object_authority_identity"],
        "rootfs_sha256": r3_authority["rootfs_sha256"],
        "driver_snapshot": r3_authority["driver_snapshot"],
        "v14_terminal_evidence": r3_authority["v14_terminal_evidence"],
        "output": old["output"], "legacy_preflight_identity": old["preflight_identity"],
        "runner_sha256": r3_authority["runner_sha256"],
        "shell_sha256": r3_authority["shell_sha256"],
        "validator_sha256": r3_authority["validator_sha256"],
        "mechanics_executor_sha256": r3_authority["mechanics_executor_sha256"],
        "projected_mechanics_sha256": digest(projected.encode()),
        "namespace_binding": namespace_claim,
        "namespace_binding_identity": digest(canonical(namespace_claim)),
        "bound_executor_sha256": sources["scripts/execute_production_core_candidate_qualification_v15_r4.py"],
        "bound_preflight_sha256": sources["scripts/preflight_production_core_candidate_qualification_v15_r4.py"],
        "bound_supervisor_sha256": sources["scripts/supervise_production_core_candidate_qualification_v15_r4.py"],
        "projection_sha256": sources[projection.SOURCE],
        "matrix_rows": 2400, "batch_count": 12, "rows_per_batch": 200,
        "request_count": 200, "shell_argument_count": 16,
        "input_token_cap": 1924, "max_new_tokens": 6268,
        "decoded_response_byte_cap": 6268,
        "runner_wall_ns": 600_000_000_000,
        "runner_max_rss_bytes": 16_106_127_360,
        "attempt_claim": "EXCLUSIVE_DIRECTORY_FLOCK_THEN_DURABLE_NO_CLOBBER_ATTEMPT_JSON_BEFORE_LAUNCHER",
        "candidate_execution_boundary": "FIRST_V15_SHELL_SUBPROCESS_AFTER_DURABLE_ATTEMPT_JSON",
        "resume_policy": "NO_RESTART_OR_REEXECUTION_AFTER_ATTEMPT_JSON",
        "source_sha256": sources, "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution": 0, "attempt_consumption": 0,
        "candidate_execution_authorized": False, "attempt_consumption_authorized": False,
        "adjudication": False, "promotion": False,
    }
    return {**core, "authority_identity": digest(canonical(core))}


def binding_for(authority: dict, raw: bytes) -> dict:
    return {
        "schema": "pastila-production-core-v15-r4-execution-binding",
        "schema_version": 1, "algorithm": "Ed25519",
        "authority_identity": authority["authority_identity"],
        "authority_sha256": digest(raw),
        "publication_parent_commit": R3_COMMIT,
        "historical_r3": authority["historical_r3"],
        "bound_executor_sha256": authority["bound_executor_sha256"],
        "bound_preflight_sha256": authority["bound_preflight_sha256"],
        "bound_supervisor_sha256": authority["bound_supervisor_sha256"],
        "projection_sha256": authority["projection_sha256"],
        "projected_mechanics_sha256": authority["projected_mechanics_sha256"],
        "namespace_binding_identity": authority["namespace_binding_identity"],
        "qualification_generation_identity": authority["qualification_generation_identity"],
        "driver_snapshot": authority["driver_snapshot"],
        "output": authority["output"],
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution": 0, "attempt_consumption": 0,
        "adjudication": False, "promotion": False,
    }


def materialize(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
                terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
                output: Path, key: Path) -> dict[str, str]:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError("R4 authority already materialized")
    signing.verify_key(key)
    authority = build(recovery, private, backup, v13_terminal, terminal,
                      rootfs, snapshot, unicode_root, output)
    raw = json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    bound = canonical(binding_for(authority, raw))
    with tempfile.TemporaryDirectory(prefix=".v15-r4-", dir=OUTPUT.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        (staging / "authority.json").write_bytes(raw)
        (staging / "binding.json").write_bytes(bound)
        (staging / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(key), "-rawin",
                        "-in", str(staging / "binding.json"), "-out", str(staging / "binding.sig")],
                       check=True, capture_output=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey",
                        str(signing.PUBLIC_KEY), "-rawin", "-in", str(staging / "binding.json"),
                        "-sigfile", str(staging / "binding.sig")], check=True, capture_output=True)
        if len((staging / "binding.sig").read_bytes()) != 64:
            raise ValueError("R4 signature length invalid")
        result = {"authority_identity": authority["authority_identity"],
                  "binding_identity": digest(bound),
                  "signature_identity": digest((staging / "binding.sig").read_bytes())}
        os.replace(staging, OUTPUT)
    return result


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs",
                 "snapshot", "unicode-root", "output", "private-key"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.recovery, args.private, args.backup,
                                 args.v13_terminal, args.terminal, args.rootfs,
                                 args.snapshot, args.unicode_root, args.output,
                                 args.private_key), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
