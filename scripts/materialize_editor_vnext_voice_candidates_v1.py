"""Materialize and verify the bounded VNext VOICE candidate dependency closure."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


EXPECTED_FREE = 74_017_955_312
PRODUCT = Path("/root/pastila-vnext/v1")
RELATIVE_DESTINATION = Path("components/voice-candidates-v1")
FORBIDDEN = (b"/root/pf9", b"/mnt/c/pf9", b"F:\\pt", b"F:/pt", b"pastila-news-monitor")
CANDIDATES = (
    {
        "candidate_id": "V1_QWEN3_8B_NON_THINKING", "layout": "qwen3-8b",
        "source_candidate_id": "C1_QWEN3_8B",
        "repo_id": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218",
        "snapshot_identity": "be259728abcc2c864bdf4d035267a8fcf8ccc57e4e277f8bd5d0934f1963fbc7",
        "expected_bytes": 16_397_461_266,
    },
    {
        "candidate_id": "V2_QWEN25_7B_INSTRUCT", "layout": "qwen2.5-7b-instruct",
        "source_candidate_id": "C2_QWEN25_7B",
        "repo_id": "Qwen/Qwen2.5-7B-Instruct", "revision": "a09a35458c702b33eeacc393d103063234e8bc28",
        "snapshot_identity": "5fe636f259ab71443c94837b3c19420e0b796c3d9edcd371332b8ff88577e8fd",
        "expected_bytes": 15_242_807_270,
    },
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identify(value: dict, field: str) -> dict:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: hashlib.sha256(canonical(body)).hexdigest()}


def git_blob_oid(path: Path) -> str:
    size = path.stat().st_size
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {size}\0".encode())
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_and_scan(path: Path) -> tuple[str, tuple[str, ...]]:
    digest = hashlib.sha256(); hits: set[str] = set(); carry = b""
    maximum = max(map(len, FORBIDDEN)) - 1
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
            window = carry + chunk
            hits.update(token.decode(errors="replace") for token in FORBIDDEN if token in window)
            carry = window[-maximum:]
    return digest.hexdigest(), tuple(sorted(hits))


def load_source_manifest(repo: Path) -> dict:
    return json.loads((repo / "docs/artifacts/editor-core-text-realizer-model-acquisition-v1-snapshots.json").read_text(encoding="utf-8"))


def verify_source(repo: Path, source_store: Path) -> list[dict]:
    manifest = load_source_manifest(repo); by_revision = {item["revision"]: item for item in manifest["models"]}; results = []
    for expected in CANDIDATES:
        declared = by_revision.get(expected["revision"])
        if declared is None or any(declared[key] != expected[key] for key in ("repo_id", "revision", "snapshot_identity")) or declared["total_bytes"] != expected["expected_bytes"]:
            raise ValueError("published source manifest binding mismatch")
        root = source_store / expected["snapshot_identity"]
        if not root.is_dir() or root.is_symlink():
            raise ValueError("source snapshot root missing or linked")
        all_paths = sorted(str(path.relative_to(root)).replace("\\", "/") for path in root.rglob("*") if path.is_file())
        if [path for path in all_paths if path not in {"receipt.json", *[item["path"] for item in declared["files"]]}]:
            raise ValueError(f"unexpected source administration file: {expected['candidate_id']}")
        receipt_path = root / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if identify(receipt, "receipt_identity")["receipt_identity"] != receipt.get("receipt_identity"):
            raise ValueError("source receipt identity mismatch")
        receipt_expected = {
            "candidate_id": expected["source_candidate_id"], "files": len(declared["files"]),
            "revision": expected["revision"], "snapshot_identity": expected["snapshot_identity"],
            "total_bytes": expected["expected_bytes"],
        }
        if any(receipt.get(key) != value for key, value in receipt_expected.items()):
            raise ValueError("source receipt binding mismatch")
        actual_paths = sorted(path for path in all_paths if path != "receipt.json")
        declared_paths = sorted(item["path"] for item in declared["files"])
        if actual_paths != declared_paths:
            raise ValueError(f"source inventory mismatch: {expected['candidate_id']}")
        files = []; total = 0
        for item in sorted(declared["files"], key=lambda row: row["path"]):
            path = root / item["path"]
            if path.is_symlink() or path.stat().st_size != item["size"]:
                raise ValueError(f"source file size/link mismatch: {item['path']}")
            sha, _ = sha256_and_scan(path)
            if item.get("sha256"):
                if sha != item["sha256"]:
                    raise ValueError(f"source sha256 mismatch: {item['path']}")
            elif git_blob_oid(path) != item["git_oid"]:
                raise ValueError(f"source git oid mismatch: {item['path']}")
            files.append({"path": item["path"], "size": item["size"], "sha256": sha, "git_oid": item["git_oid"]})
            total += item["size"]
        if total != expected["expected_bytes"]:
            raise ValueError("source total bytes mismatch")
        results.append({**expected, "source_root": str(root), "files": files, "verified_bytes": total})
    return results


def verify_closure(root: Path, *, require_independent_from: Path | None = None) -> dict:
    lock_path = root / "dependency-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if identify(lock, "lock_identity")["lock_identity"] != lock.get("lock_identity"):
        raise ValueError("dependency lock identity mismatch")
    seen_inodes = set(); hardlinks = 0; symlinks = 0; path_hits: list[str] = []; total = 0; files = 0
    for candidate in lock["candidates"]:
        candidate_root = root / candidate["layout"]
        for item in candidate["files"]:
            path = candidate_root / item["path"]
            if path.is_symlink(): symlinks += 1; continue
            stat = path.stat(); files += 1; total += stat.st_size
            if stat.st_nlink != 1: hardlinks += 1
            inode = (stat.st_dev, stat.st_ino)
            if inode in seen_inodes: hardlinks += 1
            seen_inodes.add(inode)
            sha, hits = sha256_and_scan(path)
            if stat.st_size != item["size"] or sha != item["sha256"]:
                raise ValueError(f"closure content mismatch: {candidate['candidate_id']}:{item['path']}")
            path_hits.extend(f"{candidate['candidate_id']}:{item['path']}:{hit}" for hit in hits)
            if require_independent_from is not None:
                source = require_independent_from / candidate["snapshot_identity"] / item["path"]
                source_stat = source.stat()
                if (source_stat.st_dev, source_stat.st_ino) == inode:
                    raise ValueError("destination is a hardlink to source")
    if symlinks or hardlinks or path_hits or total != lock["snapshot_bytes"]:
        raise ValueError({"symlinks": symlinks, "hardlinks": hardlinks, "path_hits": path_hits, "bytes": total})
    return {"status": "PASS", "lock_identity": lock["lock_identity"], "files": files, "snapshot_bytes": total, "symlinks": 0, "hardlinks": 0, "legacy_path_hits": 0}


def materialize(repo: Path, product: Path, source_store: Path) -> dict:
    if product != PRODUCT:
        raise ValueError("unexpected persistent product root")
    destination = product / RELATIVE_DESTINATION; stage = destination.parent / ".voice-candidates-v1.stage"
    if destination.exists() or stage.exists():
        raise ValueError("destination or stage already exists")
    free = shutil.disk_usage(product).free
    if free < EXPECTED_FREE:
        raise ValueError(f"free-space gate failed: {free} < {EXPECTED_FREE}")
    verified = verify_source(repo, source_store)
    stage.mkdir(parents=True)
    try:
        locked_candidates = []
        for candidate in verified:
            target = stage / candidate["layout"]; target.mkdir()
            source_root = Path(candidate["source_root"])
            for item in candidate["files"]:
                output = target / item["path"]; output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_root / item["path"], output)
            locked_candidates.append({key: value for key, value in candidate.items() if key != "source_root"})
        lock = identify({
            "schema": "editor-vnext-voice-candidates-dependency-lock", "schema_version": 1,
            "product_root": str(PRODUCT), "relative_root": str(RELATIVE_DESTINATION),
            "plan_identity": "2ddc49ed46d0e891aef7b69b4874de5305c32346b8ec0962f296c50859faaa61",
            "candidates": locked_candidates, "snapshot_bytes": sum(item["verified_bytes"] for item in verified),
            "physical_copy": True, "runtime_dependency_on_source": False, "legacy_dependency_count": 0,
        }, "lock_identity")
        (stage / "dependency-lock.json").write_bytes(json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
        stage.replace(destination)
        verification = verify_closure(destination, require_independent_from=source_store)
        closure = identify({
            "schema": "editor-vnext-voice-candidates-dependency-closure", "schema_version": 1,
            "status": "PASS_DEPENDENCY_ONLY_NO_MODEL_LOAD", "product_root": str(PRODUCT),
            "relative_root": str(RELATIVE_DESTINATION), "lock_identity": lock["lock_identity"],
            "candidates": len(lock["candidates"]), "files": verification["files"],
            "snapshot_bytes": verification["snapshot_bytes"], "hardlinks": 0, "symlinks": 0,
            "legacy_path_hits": 0, "legacy_dependency_count": 0,
            "model_loaded": False, "inference_performed": False, "download_performed": False,
            "training_performed": False, "optimizer_created": False,
        }, "closure_identity")
        artifact = repo / "docs/artifacts/editor-vnext-voice-candidates-dependency-closure-v1.json"
        artifact.write_bytes(json.dumps(closure, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
        return closure
    except Exception:
        if stage.exists(): shutil.rmtree(stage)
        raise


def restore_proof(source: Path, temporary_root: Path) -> dict:
    if not str(temporary_root).startswith("/tmp/editor-vnext-voice-candidates-cleanroom-"):
        raise ValueError("restore proof root must be the bounded temporary clean-room")
    if temporary_root.exists():
        raise ValueError("restore proof root must be new")
    try:
        shutil.copytree(source, temporary_root, symlinks=True)
        result = verify_closure(temporary_root)
        result.update({"cleanroom_root": str(temporary_root), "source": "VNEXT_CLOSURE_ONLY", "legacy_available_to_resolver": False})
        return result
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source-store", type=Path); parser.add_argument("--product-root", type=Path, default=PRODUCT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight-only", action="store_true"); group.add_argument("--materialize", action="store_true"); group.add_argument("--verify-root", type=Path); group.add_argument("--restore-proof", type=Path)
    args = parser.parse_args(); repo = args.repo.resolve()
    if args.preflight_only:
        if args.source_store is None: raise ValueError("source store required")
        verified = verify_source(repo, args.source_store.resolve()); free = shutil.disk_usage(args.product_root).free
        if free < EXPECTED_FREE: raise ValueError("free-space gate failed")
        print(json.dumps({"status": "PASS_SOURCE_AND_SPACE_PREFLIGHT", "candidates": len(verified), "bytes": sum(item["verified_bytes"] for item in verified), "free_bytes": free}, sort_keys=True)); return
    if args.materialize:
        if args.source_store is None: raise ValueError("source store required")
        print(json.dumps(materialize(repo, args.product_root.resolve(), args.source_store.resolve()), sort_keys=True)); return
    if args.restore_proof:
        print(json.dumps(restore_proof(args.product_root.resolve() / RELATIVE_DESTINATION, args.restore_proof), sort_keys=True)); return
    print(json.dumps(verify_closure(args.verify_root.resolve()), sort_keys=True))


if __name__ == "__main__": main()
