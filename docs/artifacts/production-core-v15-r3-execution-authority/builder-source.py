"""Build and sign an R3 authority without claiming or executing an attempt."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_execution_bound_preflight_r2 as r2_issuer
import preflight_production_core_candidate_qualification_v15 as legacy
import project_production_core_candidate_qualification_v15_r3 as projection
from pastila_scout import production_core_successor_contract_v15_r3 as contract

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v15-r3-execution-authority"
R2_COMMIT = "2a45477249da4105e5c563dc090457ca05190a85"
R2_TREE = "5ba5cc8e4493252e5d949275baaaed58fc1d1016"
R2_AUTHORITY = "b19342109055faf172afe1d3296f42143501acf06dcf1c53b85a024065c24d0b"
R2_ATTEMPT = "30747ad2a52d1d64a0ad29933eb51385a2cebd9a6efecfcc77993140c5542bdd"
R2_ATTEMPT_SHA256 = "189f0905ca0973cf7fc78c2fbf7af308a95f1caa90957a0ce19e875a0fa30efe"
R2_INNER_PREFLIGHT = "e2f7c54e30f4bda75e8c95b1558f5f59c52245c0cfbfd64b00f5a1abf3d0029c"
R2_INVENTORY_ROOT = "ccb42322be83de8a1dbfa846dd8ae9b7fce34c44082caac30a774d9516864d9d"
R2_OUTPUT = Path("/root/pf9-v15-preconsumption-output")
R3_OUTPUT = Path("/root/pf9-v15-r3-preconsumption-output")
V14_TERMINAL_SHA256 = "fabc58e6a886e310d6f6473f0e25b181dbc293fe78adab06ba5db4976bea45fa"
BRANCH = "successor/core-v2-v12-runner-binding-remediation"
NEW_SOURCES = (
    "docs/production-core-v15-r2-forensics-and-r3-contract.md",
    "scripts/project_production_core_candidate_qualification_v15_r3.py",
    "src/pastila_scout/production_core_successor_contract_v15_r3.py",
    "tests/test_production_core_successor_contract_v15_r3.py",
    "scripts/materialize_production_core_v15_r3_execution_authority.py",
    "scripts/audit_production_core_v15_r3_execution_authority.py",
    "scripts/preflight_production_core_candidate_qualification_v15_r3.py",
    "scripts/execute_production_core_candidate_qualification_v15_r3.py",
    "tests/test_production_core_v15_r3_execution_authority.py",
)
ARTIFACT_NAMES = ("authority.json", "binding.json", "binding.sig", "builder-source.py")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def historical_r2() -> dict:
    """Verify R2 signature and consumed evidence without rerunning its empty-output audit."""
    head = git("rev-parse", "HEAD")
    if (head != R2_COMMIT and git("show", "-s", "--format=%P", head) != R2_COMMIT):
        raise ValueError("R3 HEAD is not the direct successor of consumed R2")
    remote = git("rev-parse", f"refs/remotes/origin/{BRANCH}")
    if (git("rev-parse", f"{R2_COMMIT}^{{tree}}") != R2_TREE
            or remote not in (R2_COMMIT, head)):
        raise ValueError("published R2 source checkpoint drift")
    artifact_root = ROOT / "docs/artifacts/production-core-v15-execution-bound-preflight-r2"
    paths = {name: artifact_root / name for name in ARTIFACT_NAMES}
    if any(path.is_symlink() or not path.is_file() or
           path.read_bytes() != subprocess.check_output(
               ["git", "show", f"{R2_COMMIT}:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT)
           for path in paths.values()):
        raise ValueError("historical R2 signed artifact drift")
    authority = json.loads(paths["authority.json"].read_bytes())
    core = dict(authority)
    claimed = core.pop("authority_identity", None)
    if (claimed != R2_AUTHORITY or claimed != digest(canonical(core))
            or paths["binding.json"].read_bytes() != r2_issuer.canonical(
                r2_issuer.binding_for(authority, paths["authority.json"].read_bytes()))
            or paths["builder-source.py"].read_bytes() !=
            (ROOT / "scripts/materialize_production_core_v15_execution_bound_preflight_r2.py").read_bytes()):
        raise ValueError("historical R2 authority or binding drift")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey",
                    str(signing.PUBLIC_KEY), "-rawin", "-in", str(paths["binding.json"]),
                    "-sigfile", str(paths["binding.sig"])], check=True, capture_output=True)
    attempt_path = R2_OUTPUT / "attempt.json"
    consumed = json.loads(attempt_path.read_bytes())
    if (attempt_path.is_symlink() or digest(attempt_path.read_bytes()) != R2_ATTEMPT_SHA256
            or consumed.get("attempt_identity") != R2_ATTEMPT
            or consumed.get("preflight_identity") != R2_INNER_PREFLIGHT
            or (R2_OUTPUT / "terminal-failure.json").exists()
            or (R2_OUTPUT / "completion.json").exists()):
        raise ValueError("consumed R2 attempt evidence drift")
    inventory = [(str(path.relative_to(R2_OUTPUT)), digest(path.read_bytes()))
                 for path in sorted(R2_OUTPUT.rglob("*")) if path.is_file()]
    root = digest(json.dumps(inventory, separators=(",", ":")).encode())
    if (len(inventory) != 806 or root != R2_INVENTORY_ROOT
            or sum(path.endswith(".raw") for path, _ in inventory) != 200
            or sum(path.endswith(".observation.json") for path, _ in inventory) != 200
            or any(path.endswith(".receipt.json") for path, _ in inventory)):
        raise ValueError("consumed R2 evidence inventory drift")
    v14 = Path("/root/pf9-v14-preconsumption-output/terminal-failure.json")
    if v14.is_symlink() or digest(v14.read_bytes()) != V14_TERMINAL_SHA256:
        raise ValueError("V14 terminal evidence drift")
    return {
        "published_commit": R2_COMMIT, "published_tree": R2_TREE,
        "authority_identity": R2_AUTHORITY,
        "binding_identity": digest(paths["binding.json"].read_bytes()),
        "signature_identity": digest(paths["binding.sig"].read_bytes()),
        "attempt_identity": R2_ATTEMPT, "attempt_sha256": R2_ATTEMPT_SHA256,
        "inner_preflight_identity": R2_INNER_PREFLIGHT,
        "evidence_inventory_root": root, "terminal_failure": "ABSENT_HISTORICAL",
        "v14_terminal_failure_sha256": V14_TERMINAL_SHA256,
    }


def source_closure(r2_authority: dict) -> dict[str, str]:
    inherited = r2_authority.get("source_sha256")
    if not isinstance(inherited, dict) or set(NEW_SOURCES) & set(inherited):
        raise ValueError("R3 source inheritance invalid")
    sources = dict(inherited)
    for name, expected in inherited.items():
        path = ROOT / name
        if (path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected
                or digest(subprocess.check_output(["git", "show", f"{R2_COMMIT}:{name}"], cwd=ROOT)) != expected):
            raise ValueError(f"published R2 source drift: {name}")
    for name in NEW_SOURCES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"R3 source missing: {name}")
        sources[name] = digest(path.read_bytes())
    if set(sources) != set(inherited) | set(NEW_SOURCES):
        raise ValueError("R3 source closure mismatch")
    return dict(sorted(sources.items()))


def build(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
          output: Path) -> dict:
    historical = historical_r2()
    r2_authority = json.loads((ROOT / "docs/artifacts/production-core-v15-execution-bound-preflight-r2/authority.json").read_bytes())
    sources = source_closure(r2_authority)
    if output != R3_OUTPUT or output == R2_OUTPUT:
        raise ValueError("R3 output must be distinct and canonical")
    old = legacy.preflight(recovery, private, backup, v13_terminal, terminal,
                           rootfs, snapshot, unicode_root, output)
    if old.get("verdict") != "PASS + 0 BLOCKERS" or old.get("output", {}).get("entries") != 0:
        raise ValueError("R3 runtime or output preflight rejected")
    request_manifest = json.loads((ROOT / "docs/artifacts/production-core-candidate-request-manifest-v2.json").read_bytes())
    if len(contract.validate_manifest_contract(request_manifest)) != 200:
        raise ValueError("R3 semantic request contract rejected")
    projected = projection.projected_mechanics()
    syntax = ast.parse(projected)
    commands = [node.value for node in ast.walk(syntax)
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.List)
                and any(isinstance(target, ast.Name) and target.id == "command"
                        for target in node.targets)]
    if len(commands) != 1:
        raise ValueError("R3 shell projection missing")
    arguments = commands[0].elts
    marker = next((index for index, node in enumerate(arguments)
                   if isinstance(node, ast.Constant) and node.value == "--"), None)
    if marker is None or len(arguments[marker + 1:]) != 16:
        raise ValueError("R3 16-argument shell projection mismatch")
    if (projected.count("successor_cases = validate_manifest_contract(requests)") != 1
            or projected.count("case = case_for_row(successor_cases, row)") != 1
            or projected.count("close_post_claim_failure(") != 1):
        raise ValueError("R3 consuming mechanics projection rejected")
    if source_closure(r2_authority) != sources or historical_r2() != historical:
        raise ValueError("R3 source or historical evidence changed during build")
    core = {
        "schema": "pastila-production-core-v15-r3-execution-authority",
        "schema_version": 1, "status": "SIGNED_NO_CANDIDATE_NO_ATTEMPT",
        "publication_parent_commit": R2_COMMIT, "publication_parent_tree": R2_TREE,
        "historical_r2": historical,
        "base_v15_authority_identity": r2_authority["v15_authority_identity"],
        "base_v15_binding_identity": r2_authority["v15_binding_identity"],
        "base_v15_signature_identity": r2_authority["v15_signature_identity"],
        "published_preflight_commit": r2_authority["published_preflight_commit"],
        "published_preflight_source_sha256": r2_authority["published_preflight_source_sha256"],
        "legacy_preflight_identity": old["preflight_identity"],
        "qualification_generation_identity": r2_authority["qualification_generation_identity"],
        "qualification_identity": r2_authority["qualification_identity"],
        "schedule_sha256": r2_authority["schedule_sha256"],
        "alias_secret_commitment": r2_authority["alias_secret_commitment"],
        "runtime_object_authority_identity": r2_authority["runtime_object_authority_identity"],
        "rootfs_sha256": r2_authority["rootfs_sha256"],
        "driver_snapshot": r2_authority["driver_snapshot"],
        "v14_terminal_evidence": r2_authority["v14_terminal_evidence"],
        "output": old["output"],
        "runner_sha256": r2_authority["runner_sha256"],
        "shell_sha256": r2_authority["shell_sha256"],
        "validator_sha256": r2_authority["validator_sha256"],
        "mechanics_executor_sha256": r2_authority["mechanics_executor_sha256"],
        "r3_projected_mechanics_sha256": digest(projected.encode()),
        "bound_executor_sha256": sources["scripts/execute_production_core_candidate_qualification_v15_r3.py"],
        "bound_preflight_sha256": sources["scripts/preflight_production_core_candidate_qualification_v15_r3.py"],
        "contract_sha256": sources["src/pastila_scout/production_core_successor_contract_v15_r3.py"],
        "projection_sha256": sources["scripts/project_production_core_candidate_qualification_v15_r3.py"],
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
        "candidate_execution_authorized": False,
        "attempt_consumption_authorized": False,
        "adjudication": False, "promotion": False,
    }
    return {**core, "authority_identity": digest(canonical(core))}


def binding_for(authority: dict, raw: bytes) -> dict:
    return {
        "schema": "pastila-production-core-v15-r3-execution-binding",
        "schema_version": 1, "algorithm": "Ed25519",
        "authority_identity": authority["authority_identity"],
        "authority_sha256": digest(raw),
        "publication_parent_commit": R2_COMMIT,
        "historical_r2": authority["historical_r2"],
        "bound_executor_sha256": authority["bound_executor_sha256"],
        "bound_preflight_sha256": authority["bound_preflight_sha256"],
        "contract_sha256": authority["contract_sha256"],
        "projection_sha256": authority["projection_sha256"],
        "r3_projected_mechanics_sha256": authority["r3_projected_mechanics_sha256"],
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
        raise ValueError("R3 authority already materialized")
    signing.verify_key(key)
    authority = build(recovery, private, backup, v13_terminal, terminal,
                      rootfs, snapshot, unicode_root, output)
    raw = json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    bound = canonical(binding_for(authority, raw))
    with tempfile.TemporaryDirectory(prefix=".v15-r3-", dir=OUTPUT.parent) as temporary:
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
            raise ValueError("R3 signature length invalid")
        result = {"authority_identity": authority["authority_identity"],
                  "binding_identity": digest(bound),
                  "signature_identity": digest((staging / "binding.sig").read_bytes())}
        os.replace(staging, OUTPUT)
    return result


def main() -> int:
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
