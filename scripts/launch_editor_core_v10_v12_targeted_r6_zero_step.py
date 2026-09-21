"""Zero-step launcher validation for the Editor Core targeted R6 round.

This command validates the published dataset boundary, the selected R2 step-9
development parent, and the physical runtime inputs that a later training
execution would consume. It never imports model classes, creates an optimizer,
writes the output directory, or starts training.
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
ARTIFACTS = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r6"
ACTIVE_COMMIT = "9a164a9d6585836fd9ba83245cb978557896a518"
ACTIVE_TREE = "bd105dea728f08c398fc042e2b5ec607d7d5c2f6"
PARENT_ADAPTER = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
PARENT_CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"
SEMANTIC_RESULT = "6b91d41397fddfc3dcdd31c6d738f892e4ed38007907c0ec561043df20d17229"
R4_REJECTION_SHA256 = "03b33499ef7ccef7ada194f0f45a1af304e6913d789ba2af3402fc055af28bb5"
R5_REJECTION_SHA256 = "6b20fea067a0e25a90827077577833aeddf9eacea0c4887c925db12f35ba9eed"
R5_REJECTION_IDENTITY = "25d4be0fce305808f3170b59dec09d6c1194e3052c74c9b56ab7cdd9b08272c7"
DATASET_MANIFEST = "73102c19815fe1e908883cb84ea5957e2923044097411ea6c2580b929fba7369"
TRAINING_CONFIG = "93efdcfb28a94db22f72d800245970dfe47a76609a30afc7bb92bc6afda0ed2b"
BASE_MODEL = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
ROOTFS = "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
SNAPSHOT = "f2074e618ba99a03e327ef2462a814b5a9503bbe5994692805ff8c4f11375126"
HELPER = "7026fe0ea99d54d0fc6caefd5ac4b6c1119e488b1cdc96336ce14387b7ffb433"
PUBLISHED_FILES = (
    "docs/artifacts/editor-core-v10-v12-targeted-continuation-r6-holdout-answer-key.jsonl",
    "docs/artifacts/editor-core-v10-v12-targeted-continuation-r6-holdout-requests.jsonl",
    "docs/artifacts/editor-core-v10-v12-targeted-continuation-r6-manifest.json",
    "docs/artifacts/editor-core-v10-v12-targeted-continuation-r6-new-train.jsonl",
    "docs/artifacts/editor-core-v10-v12-targeted-continuation-r6-replay-anchors.jsonl",
    "docs/artifacts/editor-core-v10-v12-targeted-continuation-r6-token-audit.json",
    "docs/artifacts/editor-core-v10-v12-targeted-continuation-r6-training-config.json",
    "docs/artifacts/editor-core-v10-v12-targeted-continuation-r6-training.jsonl",
    "docs/editor-core-v10-v12-targeted-r6-development-pack.md",
    "scripts/audit_editor_core_v10_v12_targeted_r6_pack.py",
    "scripts/audit_editor_core_v10_v12_targeted_r6_token_lengths.py",
    "scripts/build_editor_core_v10_v12_targeted_r6_pack.py",
    "scripts/run_editor_core_v10_v12_targeted_r6_token_audit.sh",
    "tests/test_editor_core_v10_v12_targeted_r6_pack.py",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def flat_manifest(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("materialization root mismatch")
    rows: list[bytes] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("materialization closure mismatch")
        rows.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha_file(path)))
    if not rows:
        raise ValueError("materialization closure empty")
    return hashlib.sha256(b"".join(rows)).hexdigest()


def load_script(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def output_snapshot(output: Path) -> tuple[int, int]:
    if not output.is_absolute() or str(output).startswith("/mnt/") or output.is_symlink() or not output.is_dir():
        raise ValueError("output must be an existing native directory")
    current = output
    while current != current.parent:
        if current.is_symlink() or not current.is_dir():
            raise ValueError("output ancestor substitution")
        current = current.parent
    filesystem = subprocess.check_output(["findmnt", "-n", "-o", "FSTYPE", "--target", str(output)], text=True).strip()
    if filesystem != "ext4":
        raise ValueError("output requires ext4")
    if list(output.iterdir()):
        raise ValueError("zero-step output is not empty")
    return output.stat().st_dev, output.stat().st_ino


def validate_public_inputs() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    selection = json.loads((ARTIFACTS / "editor-core-v10-v12-targeted-r3-semantic-result.json").read_bytes())
    selection_identity = selection.pop("result_identity")
    if selection_identity != hashlib.sha256(canonical(selection)).hexdigest() or selection_identity != SEMANTIC_RESULT:
        raise ValueError("semantic selection identity mismatch")
    if (
        selection["selection"]["scope"] != "DEVELOPMENT_ONLY"
        or selection["selection"]["retained_parent"] != "R2_STEP_9"
        or selection["selection"]["retained_adapter_identity"] != PARENT_ADAPTER
        or selection["selection"]["rejected_candidate"] != "R3_STEP_6"
        or selection["r2_parent"]["checkpoint_identity"] != PARENT_CHECKPOINT
        or selection["selection"]["promotion"] is not False
        or selection["selection"]["release"] is not False
    ):
        raise ValueError("active development parent selection mismatch")
    rejection_path = ARTIFACTS / "editor-core-v10-v12-targeted-r4-semantic-result.json"
    rejection = json.loads(rejection_path.read_bytes())
    if (
        sha_file(rejection_path) != R4_REJECTION_SHA256
        or rejection.get("development_parent_decision") != "REJECT_R4_KEEP_R2"
        or rejection.get("parent_adapter_sha256") != PARENT_ADAPTER
        or rejection.get("promotion") is not False
        or rejection.get("release") is not False
    ):
        raise ValueError("R4 rejection closure mismatch")
    r5_path = ARTIFACTS / "editor-core-v10-v12-targeted-r5-semantic-result.json"
    r5 = json.loads(r5_path.read_bytes())
    r5_identity = r5.pop("result_identity", None)
    if (
        sha_file(r5_path) != R5_REJECTION_SHA256
        or r5_identity != R5_REJECTION_IDENTITY
        or r5_identity != hashlib.sha256(canonical(r5)).hexdigest()
        or r5.get("selection", {}).get("rejected_candidate") != "R5_STEP_6"
        or r5["selection"].get("retained_parent") != "R2_STEP_9"
        or r5["selection"].get("retained_adapter_identity") != PARENT_ADAPTER
        or r5.get("r2_parent", {}).get("checkpoint_identity") != PARENT_CHECKPOINT
        or r5["selection"].get("promotion") is not False
        or r5["selection"].get("release") is not False
    ):
        raise ValueError("R5 rejection closure mismatch")
    git = ["git", "-c", f"safe.directory={ROOT}"]
    tree = subprocess.check_output([*git, "rev-parse", f"{ACTIVE_COMMIT}^{{tree}}"], cwd=ROOT, text=True).strip()
    if tree != ACTIVE_TREE:
        raise ValueError("active source tree mismatch")
    if subprocess.run([*git, "merge-base", "--is-ancestor", ACTIVE_COMMIT, "HEAD"], cwd=ROOT).returncode:
        raise ValueError("active source ancestry mismatch")
    upstream = subprocess.check_output([*git, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], cwd=ROOT, text=True).strip()
    if upstream != "origin/successor/core-v2-v12-runner-binding-remediation":
        raise ValueError("published upstream mismatch")
    if subprocess.run([*git, "merge-base", "--is-ancestor", ACTIVE_COMMIT, upstream], cwd=ROOT).returncode:
        raise ValueError("published source ancestry mismatch")
    names = subprocess.check_output([*git, "show", "--format=", "--name-only", ACTIVE_COMMIT], cwd=ROOT, text=True).splitlines()
    if tuple(names) != PUBLISHED_FILES:
        raise ValueError("published file scope mismatch")
    for name in PUBLISHED_FILES:
        if subprocess.check_output([*git, "show", f"{ACTIVE_COMMIT}:{name}"], cwd=ROOT) != (ROOT / name).read_bytes():
            raise ValueError("published blob/worktree mismatch")
    audit_module = load_script(ROOT / "scripts" / "audit_editor_core_v10_v12_targeted_r6_pack.py", "targeted_r6_audit")
    dataset_audit = audit_module.audit()
    manifest = json.loads((ARTIFACTS / f"{PREFIX}-manifest.json").read_bytes())
    config = json.loads((ARTIFACTS / f"{PREFIX}-training-config.json").read_bytes())
    if dataset_audit.get("verdict") != "PASS" or dataset_audit.get("blockers") != 0:
        raise ValueError("targeted continuation audit failed")
    if (
        manifest.get("parent_adapter_content_identity") != PARENT_ADAPTER
        or manifest.get("parent_checkpoint_identity") != PARENT_CHECKPOINT
        or manifest.get("manifest_identity") != DATASET_MANIFEST
        or config.get("training_config_identity") != TRAINING_CONFIG
        or config.get("parent_adapter_content_identity") != PARENT_ADAPTER
        or config.get("parent_checkpoint_identity") != PARENT_CHECKPOINT
        or config.get("training_authorized") is not False
        or config.get("training_performed") is not False
        or config.get("rejected_r3_r4_r5_adapter_training_use") is not False
        or config.get("r2_r3_r4_r5_holdout_training_use") is not False
    ):
        raise ValueError("zero-step authorization mismatch")
    return manifest, config, dataset_audit


def validate_parent(checkpoint: Path) -> dict[str, object]:
    if checkpoint.is_symlink() or not checkpoint.is_dir():
        raise ValueError("parent checkpoint root mismatch")
    adapter = checkpoint / "adapter"
    identity = flat_manifest(adapter)
    if identity != PARENT_ADAPTER:
        raise ValueError("parent adapter identity mismatch")
    receipt = json.loads((checkpoint / "checkpoint.json").read_bytes())
    identity_value = receipt.pop("checkpoint_identity", None)
    if identity_value != hashlib.sha256(canonical(receipt)).hexdigest():
        raise ValueError("parent checkpoint identity derivation mismatch")
    if identity_value != PARENT_CHECKPOINT or receipt.get("model_sha256") != BASE_MODEL or receipt.get("optimizer_steps") != 9:
        raise ValueError("parent checkpoint closure mismatch")
    return {"adapter_identity": identity, "checkpoint_identity": PARENT_CHECKPOINT}


def run_runtime_probe(rootfs: Path, snapshot: Path) -> dict[str, object]:
    helper = ROOT / "src" / "pastila_scout" / "production_core_wsl_driver_snapshot_v15.py"
    probe = ROOT / "scripts" / "probe_production_core_isolated_gpu_v15.sh"
    if sha_file(rootfs) != ROOTFS or sha_file(helper) != HELPER:
        raise ValueError("runtime source identity mismatch")
    result = subprocess.run(
        ["bash", str(probe), str(rootfs), "production-snapshot", str(snapshot), str(helper), HELPER],
        check=True, capture_output=True, text=True,
    )
    value = json.loads(result.stdout)
    if (
        value.get("rootfs_sha256") != ROOTFS
        or value.get("wsl_lib_source") != "production-snapshot"
        or value.get("cuda_available") is not True
        or value.get("network_isolated") is not True
        or value.get("pid_isolated") is not True
        or value.get("libcuda_load") != "PASS"
        or value.get("cu_init_result") != 0
        or value.get("cu_device_count") != 1
    ):
        raise ValueError("isolated runtime probe mismatch")
    return value


def zero_step(model: Path, checkpoint: Path, rootfs: Path, snapshot: Path, output: Path) -> dict[str, object]:
    before = output_snapshot(output)
    manifest, config, dataset_audit = validate_public_inputs()
    model_identity = flat_manifest(model)
    if model_identity != BASE_MODEL:
        raise ValueError("base model identity mismatch")
    parent = validate_parent(checkpoint)
    snapshot_module = load_script(ROOT / "src" / "pastila_scout" / "production_core_wsl_driver_snapshot_v15.py", "driver_snapshot")
    snapshot_result = snapshot_module.manifest(snapshot)
    if snapshot_result.get("manifest_identity") != SNAPSHOT:
        raise ValueError("driver snapshot identity mismatch")
    runtime = run_runtime_probe(rootfs, snapshot)
    after = output_snapshot(output)
    if before != after:
        raise ValueError("zero-step output identity changed")
    core = {
        "schema": "pastila-editor-core-targeted-r6-zero-step-receipt",
        "schema_version": 2,
        "status": "PASS_ZERO_STEP_ZERO_TRAINING",
        "active_source_commit": ACTIVE_COMMIT,
        "active_source_tree": ACTIVE_TREE,
        "semantic_rejection_identity": SEMANTIC_RESULT,
        "r4_rejection_sha256": R4_REJECTION_SHA256,
        "r5_rejection_sha256": R5_REJECTION_SHA256,
        "r5_rejection_identity": R5_REJECTION_IDENTITY,
        "dataset_manifest_identity": manifest["manifest_identity"],
        "training_config_identity": config["training_config_identity"],
        "training_corpus_sha256": config["training_corpus_sha256"],
        "parent_adapter_content_identity": parent["adapter_identity"],
        "parent_checkpoint_identity": parent["checkpoint_identity"],
        "base_model_manifest_sha256": model_identity,
        "rootfs_sha256": runtime["rootfs_sha256"],
        "driver_snapshot_manifest_identity": snapshot_result["manifest_identity"],
        "launcher_sha256": sha_file(Path(__file__)),
        "runtime_probe_sha256": sha_file(ROOT / "scripts" / "probe_production_core_isolated_gpu_v15.sh"),
        "driver_manifest_helper_sha256": HELPER,
        "isolated_cuda_available": runtime["cuda_available"],
        "runtime_versions": runtime["versions"],
        "new_training_rows": dataset_audit["new_rows"],
        "replay_rows": dataset_audit["replay_rows"],
        "independent_holdout_rows": dataset_audit["holdout_rows"],
        "output_entries_before": 0,
        "output_entries_after": 0,
        "model_loaded": False,
        "inference_performed": False,
        "forward_backward_performed": False,
        "optimizer_created": False,
        "optimizer_steps": 0,
        "training_output_created": False,
        "training_performed": False,
        "adjudication_performed": False,
        "promotion": False,
    }
    return {
        **core,
        "receipt_identity": hashlib.sha256(canonical(core)).hexdigest(),
        "output_runtime_observation": {"device": before[0], "inode": before[1]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--driver-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = zero_step(args.model, args.parent_checkpoint, args.rootfs, args.driver_snapshot, args.output)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
