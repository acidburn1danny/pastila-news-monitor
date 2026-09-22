"""Read-only, non-consuming pre-ablation gate for the editorial Bridge.

The gate cannot authorize training: it proves only the published dataset,
tokenizer, runtime and experimental protocol. It fails closed while the
independent naturalistic corpus is not frozen and bound.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
BOUNDARY_PATH = ART / "editor-core-editorial-bridge-v1-boundary.json"
TOKEN_PATH = ART / "editor-core-editorial-bridge-v1-token-audit.json"
DATASET_COMMIT = "94880823ac060539f21b1df4b8374b04a484ad78"
DATASET_TREE = "ff2ec5bcf306e81710c3dd25fff1e9234ef48d6c"
UPSTREAM = "origin/successor/core-v2-v12-runner-binding-remediation"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"module missing: {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def boundary() -> dict:
    value = json.loads(BOUNDARY_PATH.read_bytes())
    identity = value.pop("boundary_identity", None)
    if identity != sha(canonical(value)):
        raise ValueError("boundary identity mismatch")
    value["boundary_identity"] = identity
    if value["status"] != "LOCAL_PREFLIGHT_ONLY_NO_ABLATION_AUTHORITY" or value["training_authorized"] is not False:
        raise ValueError("training authority substitution")
    if (value["published_dataset_commit"], value["published_dataset_tree"]) != (DATASET_COMMIT, DATASET_TREE):
        raise ValueError("published dataset substitution")
    for relative, expected in value["source_hashes"].items():
        path = ROOT / relative
        if not path.is_file() or sha(path.read_bytes()) != expected:
            raise ValueError(f"gate source drift: {relative}")
    token = json.loads(TOKEN_PATH.read_bytes())
    token_identity = token.pop("receipt_identity", None)
    if token_identity != sha(canonical(token)) or token_identity != value["token_audit_receipt_identity"]:
        raise ValueError("token receipt identity")
    if sha(TOKEN_PATH.read_bytes()) != value["token_audit_blob_sha256"]:
        raise ValueError("token receipt blob")
    return value


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-c", f"safe.directory={ROOT}", *args], cwd=ROOT, text=True).strip()


def publication(value: dict) -> dict:
    if git("rev-parse", f"{DATASET_COMMIT}^{{tree}}") != DATASET_TREE:
        raise ValueError("published tree drift")
    if subprocess.run(["git", "-c", f"safe.directory={ROOT}", "merge-base", "--is-ancestor", DATASET_COMMIT, "HEAD"], cwd=ROOT).returncode:
        raise ValueError("dataset commit not ancestor")
    if git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}") != UPSTREAM:
        raise ValueError("upstream ref substitution")
    remote = subprocess.check_output(["git", "-c", f"safe.directory={ROOT}", "ls-remote", "--heads",
                                      "origin", UPSTREAM.split("origin/", 1)[1]], cwd=ROOT, text=True).strip()
    if len(remote.split()) != 2 or remote.split()[1] != "refs/heads/" + UPSTREAM.split("origin/", 1)[1]:
        raise ValueError("remote publication missing")
    remote_sha = remote.split()[0]
    if remote_sha != git("rev-parse", UPSTREAM):
        raise ValueError("remote tracking drift")
    if subprocess.run(["git", "-c", f"safe.directory={ROOT}", "merge-base", "--is-ancestor", DATASET_COMMIT, remote_sha], cwd=ROOT).returncode:
        raise ValueError("remote dataset ancestry")
    files = git("diff-tree", "--no-commit-id", "--name-only", "-r", DATASET_COMMIT).splitlines()
    if len(files) != 17:
        raise ValueError("published 17-file closure")
    for relative in files:
        if not relative.startswith(("docs/artifacts/editor-core-editorial-mechanics-bridge-v1-",
                                    "docs/editor-core-editorial-mechanics-bridge-v1.md",
                                    "scripts/audit_editor_core_editorial_mechanics_bridge.py",
                                    "scripts/build_editor_core_editorial_mechanics_bridge.py",
                                    "tests/test_editor_core_editorial_mechanics_bridge.py")):
            raise ValueError("published file scope")
        if subprocess.check_output(["git", "-c", f"safe.directory={ROOT}", "show", f"{DATASET_COMMIT}:{relative}"], cwd=ROOT) != (ROOT / relative).read_bytes():
            raise ValueError("published blob drift")
    if value["published_dataset_commit"] != DATASET_COMMIT:
        raise ValueError("boundary dataset commit")
    return {"remote_head": remote_sha, "published_tree": DATASET_TREE, "published_blobs": 17}


def local_audits(value: dict) -> dict:
    corpus = load_module(ROOT / "scripts/audit_editor_core_editorial_mechanics_bridge.py", "bridge_corpus")
    result = corpus.audit()
    if result["verdict"] != "PASS" or result["blockers"] or result["manifest_identity"] != value["published_manifest_identity"] or result["plan_identity"] != value["published_plan_identity"]:
        raise ValueError("published corpus audit")
    projector = load_module(ROOT / "scripts/project_editor_core_editorial_bridge_arms.py", "bridge_projection")
    arms = projector.projection()
    if arms["projection_identity"] != value["arm_projection_identity"] or {key: item["sha256"] for key, item in arms["arms"].items()} != value["arm_corpus_sha256"]:
        raise ValueError("arm projection drift")
    return {"corpus": result, "arm_projection_identity": arms["projection_identity"]}


def preflight(model: Path, checkpoint: Path, rootfs: Path, snapshot: Path, output: Path) -> dict:
    value = boundary()
    r6 = load_module(ROOT / "scripts/launch_editor_core_v10_v12_targeted_r6_zero_step.py", "frozen_r6")
    before = r6.output_snapshot(output)
    published = publication(value)
    audits = local_audits(value)
    if r6.flat_manifest(model) != value["base_model_identity"]:
        raise ValueError("base model identity")
    parent = r6.validate_parent(checkpoint)
    if (parent["adapter_identity"], parent["checkpoint_identity"]) != (value["parent_adapter_identity"], value["parent_checkpoint_identity"]):
        raise ValueError("R2 parent substitution")
    if r6.sha_file(rootfs) != value["rootfs_sha256"]:
        raise ValueError("rootfs identity")
    helper = load_module(ROOT / "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py", "snapshot_helper")
    snap = helper.manifest(snapshot)
    if snap.get("manifest_identity") != value["driver_snapshot_manifest_identity"]:
        raise ValueError("driver snapshot identity")
    token = json.loads(TOKEN_PATH.read_bytes())
    command = ["bash", str(ROOT / "scripts/run_editor_core_editorial_bridge_token_audit.sh"),
               str(rootfs), str(model), str(ROOT)]
    fresh = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
    if fresh != token:
        raise ValueError("fresh tokenizer receipt drift")
    runtime = r6.run_runtime_probe(rootfs, snapshot)
    after = r6.output_snapshot(output)
    if before != after:
        raise ValueError("output identity or emptiness drift")
    core = {"schema": "editor-core-editorial-bridge-preflight-receipt", "schema_version": 1,
            "status": "PASS_LOCAL_TECHNICAL_PREFLIGHT_ABLATIONS_STILL_BLOCKED",
            "boundary_identity": value["boundary_identity"], "published": published,
            "manifest_identity": audits["corpus"]["manifest_identity"], "plan_identity": audits["corpus"]["plan_identity"],
            "arm_projection_identity": audits["arm_projection_identity"],
            "token_receipt_identity": value["token_audit_receipt_identity"],
            "parent_adapter_identity": parent["adapter_identity"], "parent_checkpoint_identity": parent["checkpoint_identity"],
            "base_model_identity": value["base_model_identity"], "rootfs_sha256": value["rootfs_sha256"],
            "driver_snapshot_manifest_identity": value["driver_snapshot_manifest_identity"],
            "cuda_available": runtime["cuda_available"], "output_entries_before": 0, "output_entries_after": 0,
            "naturalistic_corpus_frozen": False, "gate_published": False,
            "ablation_training_authorized": False, "model_loaded": False, "inference_performed": False,
            "optimizer_created": False, "optimizer_steps": 0, "training_performed": False,
            "adjudication_performed": False, "promotion": False}
    return {**core, "receipt_identity": sha(canonical(core)),
            "output_runtime_observation": {"device": before[0], "inode": before[1]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--driver-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preflight(args.model, args.parent_checkpoint, args.rootfs, args.driver_snapshot, args.output),
                     ensure_ascii=False, sort_keys=True))
