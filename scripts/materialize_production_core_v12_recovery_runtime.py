"""Materialize and seal the complete V12 recovery runtime from verified objects."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/artifacts/production-core-v12-clean-recovery.json"
RUNNER_PATH = ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v12.py"
PROMPTS = {
    "pastila-editor-core-v1.1-json-successor-v2": ROOT / "docs/artifacts/pastila-editor-core-v1.1-json-successor-v10-system-prompt.txt",
    "pastila-editor-core-v1.2-json-successor": ROOT / "docs/artifacts/pastila-editor-core-v1.2-json-successor-v10-system-prompt.txt",
}
EXPECTED_PROMPTS = {
    "pastila-editor-core-v1.1-json-successor-v2": "91c84e9ab10cbecdfdd7e255b133c56263feb546d55d7e1ea01362f9be5567bb",
    "pastila-editor-core-v1.2-json-successor": "70e125c8fa6e58f3864419bec34f6685a95bcb7bbfb9455838aaf593d01fac36",
}
EXPECTED_GENERATION = "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7"
EXPECTED_QUALIFICATION = "607ef6193b312c6d2e5d581c10caf9cb8a3a14a5b46166888e9bd8bddade5a45"
EXPECTED_CANDIDATE_MANIFEST = "6c3bf1d21e85a454069ccd4e80f542fa5005ea6b89b41bb0d90b4acad2533314"
EXPECTED_RUNNER = "b7073a3b75036e5be26aa4b1d9546aa9f012370168a74df552b648708e399e29"
EXPECTED_BASE = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
EXPECTED_ROOTFS = "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
EXPECTED_TOKENIZER = "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c"
EXPECTED_ADAPTERS = {
    "pastila-editor-core-v1.1-json-successor-v2": "813131dc9cae57a66f216957475479e716594c46a67f77783122ff955aa7ee32",
    "pastila-editor-core-v1.2-json-successor": "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f",
}
TOKENIZER_FILES = {
    "chat_template.jinja": "2f545122222db8bb43ca0ea0c49e9185320a8670f7d35575b0da0eb48b1e8970",
    "config.json": "b1897778395bb1795489a048ebde2e6d216eee21014ce9c18193d15f097454a6",
    "tokenizer.json": "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135",
    "tokenizer_config.json": "f59f7294e4f26383d0ea93840fe21cf197784be0842a8301a0343e8c34ed0d6d",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def flat_identity(root: Path) -> str:
    records: list[bytes] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"non-flat runtime object: {path}")
        records.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha256_file(path)))
    if not records:
        raise ValueError(f"empty runtime object: {root}")
    return hashlib.sha256(b"".join(records)).hexdigest()


def validate_flat_directory(root: Path, expected: str) -> str:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"flat runtime directory missing: {root}")
    if root.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise ValueError(f"flat runtime directory is writable: {root}")
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError(f"flat runtime directory is not read-only: {path}")
    observed = flat_identity(root)
    if observed != expected:
        raise ValueError(f"flat runtime identity mismatch: {root}")
    return observed


def safe_extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive, "r:") as handle:
        for member in handle.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise ValueError(f"unsafe archive member: {member.name}")
            destination = target.joinpath(*name.parts).resolve()
            if target.resolve() not in destination.parents and destination != target.resolve():
                raise ValueError(f"archive containment failure: {member.name}")
        handle.extractall(target)
    for path in target.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"writable or symlink runtime object: {path}")
        mode = path.stat().st_mode
        path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    target.chmod(target.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def wsl_path(path: Path) -> str:
    resolved = path.resolve()
    if os.name != "nt":
        return resolved.as_posix()
    drive = resolved.drive.rstrip(":").lower()
    if not drive:
        raise ValueError(f"WSL path requires a Windows drive: {path}")
    return "/mnt/" + drive + "/" + resolved.relative_to(resolved.anchor).as_posix()


def host_path(path: str) -> Path:
    """Map a canonical WSL drive path to the current host without UNC access."""
    parts = PurePosixPath(path).parts
    if os.name != "nt" and path.startswith("/") and ".." not in parts:
        return Path(path)
    if len(parts) < 4 or parts[:2] != ("/", "mnt") or len(parts[2]) != 1 or not parts[2].isalpha() or any(part in (".", "..") for part in parts[3:]):
        raise ValueError(f"invalid WSL drive path: {path}")
    if os.name == "nt":
        return Path(parts[2].upper() + ":\\", *parts[3:])
    return Path(path)


def require_clean_output(path: Path) -> None:
    if path.exists():
        if path.is_symlink() or any(path.iterdir()):
            raise ValueError(f"output root must be new and empty: {path}")
    else:
        path.mkdir(parents=True)


def finalize_runtime_permissions(root: Path) -> None:
    """Close writable parent directories after all artifacts have been emitted."""
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_symlink():
            raise ValueError(f"symlink in completed runtime: {path}")
        path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    root.chmod(root.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def validate_projection(value: dict[str, object]) -> None:
    if tuple(value) != ("schema", "schema_version", "materializations"):
        raise ValueError("executor projection field order mismatch")
    if value["schema"] != "pastila-production-core-local-object-resolution-v2" or value["schema_version"] != 2:
        raise ValueError("executor projection schema mismatch")
    materializations = value["materializations"]
    if not isinstance(materializations, dict) or tuple(materializations) != ("A", "B"):
        raise ValueError("executor projection materialization labels mismatch")
    for label in ("A", "B"):
        local = materializations[label]
        if not isinstance(local, dict) or tuple(local) != ("rootfs_tar", "model", "adapters"):
            raise ValueError(f"executor projection shape mismatch: {label}")
        adapters = local["adapters"]
        if not isinstance(adapters, dict) or tuple(adapters) != tuple(EXPECTED_ADAPTERS):
            raise ValueError(f"executor projection adapters mismatch: {label}")
        if any(not isinstance(path, str) or not path.startswith("/") or ".." in PurePosixPath(path).parts for path in (local["rootfs_tar"], local["model"], *adapters.values())):
            raise ValueError(f"executor projection path mismatch: {label}")


def validate_recovery_resolution(value: dict[str, object]) -> None:
    core = dict(value)
    claimed = core.pop("resolution_identity", None)
    if value.get("schema") != "pastila-production-core-v12-recovery-runtime-resolution" or value.get("schema_version") != 1:
        raise ValueError("recovery resolution schema mismatch")
    if claimed != hashlib.sha256(canonical(core)).hexdigest():
        raise ValueError("recovery resolution seal mismatch")
    if type(value.get("candidate_execution")) is not int or value["candidate_execution"] != 0 or type(value.get("successor_attempt_consumption")) is not int or value["successor_attempt_consumption"] != 0 or value.get("adjudication") is not False or value.get("promotion") is not False:
        raise ValueError("recovery resolution execution state mismatch")


def audit_recovery_resolution(recovery: dict[str, object], projection: dict[str, object]) -> None:
    """Recheck the sealed resolution and every runtime object before any execution."""
    validate_recovery_resolution(recovery)
    validate_projection(projection)
    if recovery.get("runner_identity") != EXPECTED_RUNNER or recovery.get("source_recovery_manifest_identity") != "8c064b062bd68a2c3f5cae839672a8d4e94b8ee49b8d3d3ed8f077ffc878439e":
        raise ValueError("recovery source identity mismatch")
    if recovery.get("base_model_content_identity") != EXPECTED_BASE or recovery.get("adapter_content_identities") != EXPECTED_ADAPTERS or recovery.get("tokenizer_content_identity") != EXPECTED_TOKENIZER:
        raise ValueError("recovery content claims mismatch")
    if sha256_file(RUNNER_PATH) != EXPECTED_RUNNER or recovery.get("prompt_identities") != EXPECTED_PROMPTS:
        raise ValueError("runner or prompt identity mismatch")
    for name, path in PROMPTS.items():
        source_claim = recovery.get("source_inputs", {}).get("prompts", {}).get(name, {})
        if sha256_file(path) != EXPECTED_PROMPTS[name] or source_claim.get("sha256") != EXPECTED_PROMPTS[name] or source_claim.get("source_path") != path.relative_to(ROOT).as_posix():
            raise ValueError(f"source prompt identity mismatch: {name}")
    artifacts = {
        "comparative_generation": ("production-core-successor-comparative-qualification-generation-v10.json", "qualification_generation_identity", EXPECTED_GENERATION),
        "candidate_generation_qualification": ("production-core-successor-candidate-generation-qualification-v10.json", "qualification_identity", EXPECTED_QUALIFICATION),
        "candidate_object_manifest": ("production-core-successor-candidate-object-manifest-v10.json", "manifest_identity", EXPECTED_CANDIDATE_MANIFEST),
    }
    for name, (filename, key, expected) in artifacts.items():
        source = ROOT / "docs" / "artifacts" / filename
        source_claim = recovery.get("source_inputs", {}).get("qualification_artifacts", {}).get(name, {})
        if json.loads(source.read_bytes()).get(key) != expected or source_claim.get("identity") != expected or source_claim.get("source_path") != source.relative_to(ROOT).as_posix():
            raise ValueError(f"qualification artifact identity mismatch: {name}")
    if recovery.get("materializations") != projection["materializations"]:
        raise ValueError("recovery projection path substitution")
    seen: set[tuple[int, int]] = set()
    for label in ("A", "B"):
        local = projection["materializations"][label]
        checks = [(local["model"], EXPECTED_BASE), *( (local["adapters"][name], expected) for name, expected in EXPECTED_ADAPTERS.items())]
        for linux, expected in checks:
            path = host_path(linux)
            validate_flat_directory(path, expected)
            physical = (path.stat().st_dev, path.stat().st_ino)
            if physical in seen:
                raise ValueError("A/B physical materialization overlap")
            seen.add(physical)
        rootfs = host_path(local["rootfs_tar"])
        if rootfs.is_symlink() or not rootfs.is_file() or rootfs.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH) or sha256_file(rootfs) != EXPECTED_ROOTFS:
            raise ValueError("rootfs identity or permissions mismatch")
        tokenizer = host_path(recovery["tokenizers"][label])
        if tokenizer.is_symlink() or not tokenizer.is_dir():
            raise ValueError("tokenizer materialization missing")
        for filename, expected in TOKENIZER_FILES.items():
            item = tokenizer / filename
            if item.is_symlink() or not item.is_file() or item.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH) or sha256_file(item) != expected:
                raise ValueError(f"tokenizer identity or permissions mismatch: {label}/{filename}")
    if recovery["tokenizers"]["A"] == recovery["tokenizers"]["B"] or projection["materializations"]["A"]["model"] == projection["materializations"]["B"]["model"]:
        raise ValueError("incomplete A/B materialization")


def build(options: argparse.Namespace) -> tuple[dict[str, object], dict[str, object]]:
    backup = options.backup_root.resolve(strict=True)
    object_root = backup / "objects"
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    if manifest["recovery_manifest_identity"] != "8c064b062bd68a2c3f5cae839672a8d4e94b8ee49b8d3d3ed8f077ffc878439e":
        raise ValueError("recovery manifest identity mismatch")
    require_clean_output(options.output_root)
    root = options.output_root.resolve()
    model_root = root / "models"
    adapter_root = root / "adapters"
    tokenizer_root = root / "tokenizers"
    rootfs_root = root / "rootfs"
    model_root.mkdir()
    adapter_root.mkdir()
    tokenizer_root.mkdir()
    rootfs_root.mkdir()
    objects = {item["logical_name"]: item for item in manifest["external_objects"]}
    for item in manifest["external_objects"]:
        archive = object_root / item["backup_name"]
        if not archive.is_file() or archive.is_symlink() or archive.stat().st_size != item["archive_bytes"] or sha256_file(archive) != item["archive_sha256"]:
            raise ValueError(f"external object mismatch: {item['logical_name']}")
    runner_identity = hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest()
    if runner_identity != EXPECTED_RUNNER:
        raise ValueError("V12 runner identity mismatch")
    prompt_paths: dict[str, str] = {}
    for name, path in PROMPTS.items():
        if sha256_file(path) != EXPECTED_PROMPTS[name]:
            raise ValueError(f"prompt identity mismatch: {name}")
        prompt_paths[name] = str(path.resolve())
    generation = json.loads((ROOT / "docs/artifacts/production-core-successor-comparative-qualification-generation-v10.json").read_bytes())
    if generation["qualification_generation_identity"] != EXPECTED_GENERATION:
        raise ValueError("generation identity mismatch")
    base_archive = object_root / objects["base-model"]["backup_name"]
    model_paths = {}
    for label in ("A", "B"):
        target = model_root / label
        safe_extract(base_archive, target)
        validate_flat_directory(target, EXPECTED_BASE)
        model_paths[label] = wsl_path(target)
    adapter_paths: dict[str, dict[str, str]] = {"A": {}, "B": {}}
    for label in ("A", "B"):
        for candidate, logical in (("pastila-editor-core-v1.1-json-successor-v2", "adapter-v10-v1.1"), ("pastila-editor-core-v1.2-json-successor", "adapter-v10-v1.2")):
            target = adapter_root / label / candidate
            target.parent.mkdir(parents=True, exist_ok=True)
            safe_extract(object_root / objects[logical]["backup_name"], target)
            validate_flat_directory(target, EXPECTED_ADAPTERS[candidate])
            adapter_paths[label][candidate] = wsl_path(target)
    tokenizer_paths = {}
    tokenizer_archive = object_root / objects["tokenizer"]["backup_name"]
    for label in ("A", "B"):
        target = tokenizer_root / label
        safe_extract(tokenizer_archive, target)
        for filename, expected in TOKENIZER_FILES.items():
            if sha256_file(target / filename) != expected:
                raise ValueError(f"tokenizer file identity mismatch: {label}/{filename}")
        tokenizer_paths[label] = wsl_path(target)
    rootfs_archive = object_root / objects["inference-rootfs"]["backup_name"]
    rootfs_target = rootfs_root / "inference-rootfs.tar"
    shutil.copyfile(rootfs_archive, rootfs_target)
    rootfs_target.chmod(rootfs_target.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    if sha256_file(rootfs_target) != EXPECTED_ROOTFS:
        raise ValueError("rootfs identity mismatch")
    rootfs_path = wsl_path(rootfs_target)
    artifact_paths = {
        "comparative_generation": ROOT / "docs/artifacts/production-core-successor-comparative-qualification-generation-v10.json",
        "candidate_generation_qualification": ROOT / "docs/artifacts/production-core-successor-candidate-generation-qualification-v10.json",
        "candidate_object_manifest": ROOT / "docs/artifacts/production-core-successor-candidate-object-manifest-v10.json",
    }
    artifact_identities = {
        "comparative_generation": generation["qualification_generation_identity"],
        "candidate_generation_qualification": json.loads(artifact_paths["candidate_generation_qualification"].read_bytes())["qualification_identity"],
        "candidate_object_manifest": json.loads(artifact_paths["candidate_object_manifest"].read_bytes())["manifest_identity"],
    }
    materializations = {
        label: {
            "rootfs_tar": rootfs_path,
            "model": model_paths[label],
            "adapters": adapter_paths[label],
        }
        for label in ("A", "B")
    }
    projection = {"schema": "pastila-production-core-local-object-resolution-v2", "schema_version": 2, "materializations": materializations}
    recovery_core = {
        "schema": "pastila-production-core-v12-recovery-runtime-resolution",
        "schema_version": 1,
        "source_recovery_manifest_identity": manifest["recovery_manifest_identity"],
        "runner_identity": EXPECTED_RUNNER,
        "qualification_generation_identity": EXPECTED_GENERATION,
        "qualification_identity": EXPECTED_QUALIFICATION,
        "candidate_manifest_identity": EXPECTED_CANDIDATE_MANIFEST,
        "external_object_archives": {item["logical_name"]: item["archive_sha256"] for item in manifest["external_objects"]},
        "base_model_content_identity": EXPECTED_BASE,
        "tokenizer_content_identity": EXPECTED_TOKENIZER,
        "adapter_content_identities": EXPECTED_ADAPTERS,
        "prompt_identities": EXPECTED_PROMPTS,
        "source_inputs": {
            "prompts": {name: {"source_path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_PROMPTS[name]} for name, path in PROMPTS.items()},
            "qualification_artifacts": {name: {"source_path": str(artifact_paths[name].relative_to(ROOT)).replace("\\", "/"), "identity": artifact_identities[name]} for name in artifact_paths},
        },
        "materializations": materializations,
        "tokenizers": tokenizer_paths,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }
    recovery = {**recovery_core, "resolution_identity": hashlib.sha256(canonical(recovery_core)).hexdigest()}
    validate_recovery_resolution(recovery)
    validate_projection(projection)
    return recovery, projection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--recovery-output", type=Path, required=True)
    parser.add_argument("--projection-output", type=Path, required=True)
    options = parser.parse_args()
    recovery, projection = build(options)
    options.recovery_output.write_bytes(json.dumps(recovery, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n")
    options.projection_output.write_bytes(json.dumps(projection, ensure_ascii=False, separators=(",", ":")).encode())
    finalize_runtime_permissions(options.output_root)
    print(json.dumps({"resolution_identity": recovery["resolution_identity"], "recovery_output": str(options.recovery_output), "projection_output": str(options.projection_output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
