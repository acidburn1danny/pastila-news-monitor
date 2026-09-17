"""Read-only V13 pre-consumption gate; never creates an attempt or runs a candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import audit_production_core_successor_execution_authority_v13 as audit_authority
import materialize_production_core_successor_qualification_generation_v13 as generation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pastila_scout.production_core_semantic_authority_v2 import Unicode16SentenceAuthority  # noqa: E402

COMMIT = "b67b31e2e9931ecde05c2a9de5018a5e7bca7834"
TREE = "ca65b07de51138c4e2b064bd027eb17bf0d1cebc"
MIN_FREE_BYTES = 68_719_476_736
AUTHORITY = ROOT / "docs/artifacts/production-core-v13-successor-execution-authority"
PUBLIC_FILES = (
    "docs/artifacts/production-core-successor-candidate-generation-qualification-v13.json",
    "docs/artifacts/production-core-successor-comparative-qualification-generation-v13.json",
    "docs/artifacts/production-core-v13-successor-execution-authority/authority.json",
    "docs/artifacts/production-core-v13-successor-execution-authority/binding.json",
    "docs/artifacts/production-core-v13-successor-execution-authority/binding.sig",
    "docs/artifacts/production-core-v13-successor-execution-authority/builder-source.py",
    "docs/production-core-v13-successor-alias-generation.md",
    "scripts/audit_production_core_successor_execution_authority_v13.py",
    "scripts/audit_production_core_successor_qualification_generation_v13.py",
    "scripts/materialize_production_core_successor_execution_authority_v13.py",
    "scripts/materialize_production_core_successor_qualification_generation_v13.py",
    "tests/test_production_core_successor_execution_authority_v13.py",
    "tests/test_production_core_successor_qualification_generation_v13.py",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).strip().decode()


def published_source_closure() -> None:
    if git("rev-parse", f"{COMMIT}^{{tree}}") != TREE:
        raise ValueError("published V13 source tree mismatch")
    head = git("rev-parse", "HEAD")
    remote = git("rev-parse", "refs/remotes/origin/successor/core-v2-v12-runner-binding-remediation")
    for revision in (head, remote):
        if subprocess.run(["git", "merge-base", "--is-ancestor", COMMIT, revision], cwd=ROOT).returncode != 0:
            raise ValueError("published V13 commit is not an ancestor")
    for name in PUBLIC_FILES:
        path = ROOT / name
        committed = subprocess.check_output(["git", "show", f"{COMMIT}:{name}"], cwd=ROOT)
        if path.is_symlink() or not path.is_file() or path.read_bytes() != committed:
            raise ValueError(f"published V13 source drift: {name}")


def native_empty_output(path: Path, recovery_root: Path, private_root: Path) -> dict[str, object]:
    if not path.is_absolute() or str(path).startswith("/mnt/") or path.is_symlink() or not path.is_dir():
        raise ValueError("output must be an existing native Linux directory")
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise ValueError("output ancestor substitution")
        current = current.parent
    resolved = path.resolve(strict=True)
    if (resolved.is_relative_to(recovery_root.resolve(strict=True))
            or resolved.is_relative_to(private_root.resolve(strict=True))
            or resolved.is_relative_to(ROOT.resolve(strict=True))):
        raise ValueError("output overlaps a protected input")
    current = resolved
    while current != current.parent:
        if current.is_symlink() or not stat.S_ISDIR(current.stat().st_mode):
            raise ValueError("output ancestor substitution")
        current = current.parent
    if path.stat().st_uid != os.geteuid() or path.stat().st_mode & 0o077:
        raise ValueError("output ownership or permissions rejected")
    if any(path.iterdir()):
        raise ValueError("output is not empty before attempt consumption")
    filesystem = subprocess.check_output(["findmnt", "-n", "-o", "FSTYPE", "--target", str(path)], text=True).strip()
    if filesystem != "ext4":
        raise ValueError("output requires native ext4")
    free = shutil.disk_usage(path).free
    if free < MIN_FREE_BYTES:
        raise ValueError("output host capacity below frozen minimum")
    return {"path": str(resolved), "device": path.stat().st_dev, "inode": path.stat().st_ino,
            "filesystem": filesystem, "free_bytes": free, "entries": 0}


def validate_matrix() -> None:
    public = generation.read_json(generation.GENERATION)
    requests = generation.read_json(generation.REQUESTS)
    by_case = {row["case_id"]: row for row in requests["requests"]}
    rows = public["schedule"]
    if len(rows) != 2400 or len(by_case) != 200:
        raise ValueError("V13 matrix cardinality mismatch")
    for offset in range(0, 2400, 200):
        batch = rows[offset:offset + 200]
        first = batch[0]
        if (len(batch) != 200 or {r["case_id"] for r in batch} != set(by_case)
                or any(r["materialization"] != first["materialization"] or r["repetition"] != first["repetition"]
                       or r["candidate_alias"] != first["candidate_alias"] or r["batch_ordinal"] != index
                       or r["global_ordinal"] != offset + index for index, r in enumerate(batch, 1))):
            raise ValueError("V13 batch schedule mismatch")
        for row in batch:
            case = by_case[row["case_id"]]
            if hashlib.sha256(case["candidate_visible_request"].encode()).hexdigest() != case["candidate_visible_request_sha256"]:
                raise ValueError("frozen candidate-visible request changed")


def capability_probe() -> None:
    if os.name == "nt" or os.geteuid() != 0:
        raise ValueError("V13 executable boundary requires WSL root")
    for name in ("bash", "unshare", "mount", "chroot", "nvidia-smi"):
        if shutil.which(name) is None:
            raise ValueError(f"required executable unavailable: {name}")
    subprocess.run(["unshare", "--mount", "--net", "--pid", "--ipc", "--uts", "--fork", "true"], check=True, capture_output=True)
    gpu = subprocess.run(["nvidia-smi", "-L"], check=True, capture_output=True, text=True)
    if not gpu.stdout.strip():
        raise ValueError("NVIDIA GPU unavailable")


def preflight(recovery_root: Path, private_root: Path, backup_root: Path, unicode_root: Path, output: Path) -> dict[str, object]:
    from audit_production_core_v13_launcher_boundary import audit as audit_launcher_boundary

    launcher_boundary = audit_launcher_boundary()
    published_source_closure()
    output_state = native_empty_output(output, recovery_root, private_root)
    authority = audit_authority.audit(AUTHORITY, recovery_root, private_root, backup_root, recompute=True)
    validate_matrix()
    if unicode_root.is_symlink() or str(unicode_root).startswith("/mnt/"):
        raise ValueError("Unicode authority requires native ext4")
    Unicode16SentenceAuthority.load(unicode_root)
    capability_probe()
    core: dict[str, object] = {
        "schema": "pastila-production-core-v13-preconsumption-preflight",
        "schema_version": 1,
        "result": "PASS",
        "bound_published_commit": COMMIT,
        "bound_published_tree": TREE,
        "authority_identity": authority["authority_identity"],
        "launcher_boundary_identity": launcher_boundary["boundary_identity"],
        "launcher_binding_identity": launcher_boundary["binding_identity"],
        "launcher_signature_identity": launcher_boundary["signature_identity"],
        "binding_identity": authority["binding_identity"],
        "signature_identity": authority["signature_identity"],
        "source_closure": authority["source_closure"],
        "runtime_object_closure": authority["runtime_object_closure"],
        "qualification_schedule_closure": authority["qualification_schedule_closure"],
        "unicode_authority": "PASS",
        "executable_capabilities": "PASS",
        "output": output_state,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }
    raw = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {**core, "preflight_identity": hashlib.sha256(raw).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--unicode-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preflight(args.recovery_root, args.private_root, args.backup_root, args.unicode_root, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
