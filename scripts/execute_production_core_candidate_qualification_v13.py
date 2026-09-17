"""WSL-native V13 adapter around byte-pinned execution mechanics."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import audit_production_core_v13_launcher_boundary as audit_launcher
import preflight_production_core_candidate_qualification_v13 as preflight

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pastila_scout import production_core_candidate_execution_authority_v13 as validator  # noqa: E402
from pastila_scout import production_core_checkpoint_resume_v6 as checkpoint  # noqa: E402
from pastila_scout import production_core_semantic_authority_v2 as semantic  # noqa: E402

MECHANICS = ROOT / "scripts/execute_production_core_candidate_qualification_v3.py"
MECHANICS_SHA256 = "9869bfcb65da5a189013f1b56ca3f914c86872bad59c2997d1d4c59ab97239f7"
SOURCE_KEYS = (
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "scripts/execute_production_core_candidate_qualification_v13.py",
    "scripts/launch_production_core_candidate_qualification_v13.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "scripts/run_production_core_candidate_qualification_v11.sh",
    "scripts/smoke_production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v13.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v12.py",
    "src/pastila_scout/production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_semantic_authority_v2.py",
)
NAMES = (
    "production-core-successor-comparative-qualification-generation-v13.json",
    "production-core-candidate-request-manifest-v2.json",
    "production-core-successor-candidate-object-manifest-v10.json",
    "production-core-successor-candidate-generation-qualification-v13.json",
)
PROMPTS = {
    "pastila-editor-core-v1.1-json-successor-v2": ROOT / "docs/artifacts/pastila-editor-core-v1.1-json-successor-v10-system-prompt.txt",
    "pastila-editor-core-v1.2-json-successor": ROOT / "docs/artifacts/pastila-editor-core-v1.2-json-successor-v10-system-prompt.txt",
}
PROMPT_SHA256 = {
    "pastila-editor-core-v1.1-json-successor-v2": "91c84e9ab10cbecdfdd7e255b133c56263feb546d55d7e1ea01362f9be5567bb",
    "pastila-editor-core-v1.2-json-successor": "70e125c8fa6e58f3864419bec34f6685a95bcb7bbfb9455838aaf593d01fac36",
}


def projected_mechanics() -> str:
    raw = MECHANICS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MECHANICS_SHA256:
        raise ValueError("pinned V3 execution mechanics changed")
    source = raw.decode("utf-8")
    old_command = '''        command = [
            "wsl.exe",
            "-d",
            "Ubuntu-24.04",
            "-u",
            "root",
            "--",
            "bash",
            "--noprofile",
            "--norc",
            "-s",
            "--",'''
    new_command = '''        command = [
            "bash",
            "--noprofile",
            "--norc",
            "-s",
            "--",'''
    if source.count(old_command) != 1:
        raise ValueError("WSL-native command projection witness mismatch")
    source = source.replace(old_command, new_command)
    old_key = '"scripts/execute_production_core_candidate_qualification_v3.py"'
    if source.count(old_key) != 1:
        raise ValueError("V13 executor source-key witness mismatch")
    source = source.replace(old_key, '"scripts/execute_production_core_candidate_qualification_v13.py"')
    old_except = "except OSError, ValueError, json.JSONDecodeError, SystemExit:"
    if source.count(old_except) != 1:
        raise ValueError("V13 executor syntax repair witness mismatch")
    source = source.replace(old_except, "except (OSError, ValueError, json.JSONDecodeError, SystemExit):")
    old_independence = 'if len(set(ids)) != len(ids) or seen.intersection(ids):\n            raise SystemExit("materialization independence mismatch")\n        seen.update(ids)'
    new_independence = 'if len(set(ids)) != len(ids) or seen.intersection(ids[1:]):\n            raise SystemExit("materialization independence mismatch")\n        seen.update(ids[1:])'
    if source.count(old_independence) != 1:
        raise ValueError("V13 shared-rootfs projection witness mismatch")
    return source.replace(old_independence, new_independence)


def object_authority(path: str, kind: str, helper: bytes) -> dict:
    raw = subprocess.run(["bash", "--noprofile", "--norc", "-s", "--", path, kind],
                         input=helper, check=True, capture_output=True).stdout
    value = json.loads(raw)
    if tuple(value) != ("physical_identity", "content_identity"):
        raise ValueError("V13 object authority response rejected")
    return value


def linux_path(path: Path) -> str:
    if path.is_symlink() or not path.exists() or not path.is_absolute():
        raise ValueError("V13 Linux path rejected")
    return str(path)


def validate_and_map(generation: dict, requests: dict, candidates: dict, qualification: dict):
    rows = validator.validate_preflight(generation, requests, candidates, qualification)
    adapters = candidates["adapter_manifest_sha256"]
    if tuple(adapters) != ("pastila-editor-core-v1.1-json-successor-v10", "pastila-editor-core-v1.2-json-successor-v10"):
        raise ValueError("V13 candidate manifest mapping mismatch")
    candidates["adapter_manifest_sha256"] = {
        "pastila-editor-core-v1.1-json-successor-v2": adapters["pastila-editor-core-v1.1-json-successor-v10"],
        "pastila-editor-core-v1.2-json-successor": adapters["pastila-editor-core-v1.2-json-successor-v10"],
    }
    return rows


def terminal_validator(snapshots: dict[str, bytes]) -> None:
    if tuple(snapshots) != NAMES:
        raise ValueError("V13 public snapshot set mismatch")
    for name, raw in snapshots.items():
        committed = subprocess.check_output(["git", "show", f"{preflight.COMMIT}:docs/artifacts/{name}"], cwd=ROOT)
        if raw != committed:
            raise ValueError(f"V13 public snapshot drift: {name}")
    validator.validate_preflight(*(json.loads(snapshots[name]) for name in NAMES))


def build_namespace() -> dict:
    audit_launcher.audit()
    preflight.published_source_closure()
    source_hashes = audit_launcher.launcher_boundary.build()["source_sha256"]
    if any(name not in source_hashes for name in SOURCE_KEYS):
        raise ValueError("V13 executable source closure incomplete")
    mechanism = {"execution_authority_identity": audit_launcher.launcher_boundary.AUTHORITY_ID,
                 "source_sha256": {name: source_hashes[name] for name in SOURCE_KEYS}}
    namespace = {
        "__builtins__": __builtins__,
        "__file__": str(Path(__file__).resolve()),
        "__name__": "v13_pinned_mechanics",
        "PINNED_ENTRY_EXECUTOR_SHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "PINNED_TERMINAL_VALIDATOR": terminal_validator,
        "PINNED_EXECUTION_MECHANISM": mechanism,
        "PINNED_ROOTFS_SHA256": validator.EXPECTED_OBJECTS[0][2],
        "PINNED_UNICODE_AUTHORITY_SHA256": validator.UNICODE_AUTHORITY_SHA256,
        "Unicode16SentenceAuthority": semantic.Unicode16SentenceAuthority,
        "validate_response_v2": semantic.validate_response_v2,
        "build_checkpoint_receipt": checkpoint.build_receipt,
        "validate_checkpoint_chain": checkpoint.validate_chain,
        "write_checkpoint_receipt": checkpoint.write_receipt,
    }
    for name in ("GENERATION_IDENTITY", "MATRIX_ROWS", "build_attempt", "build_terminal_failure", "canonical",
                 "identity", "materialize_batches", "result_status", "validate_attempt", "validate_boundary_logs",
                 "validate_case_receipt", "validate_completion", "validate_observation", "validate_terminal_failure"):
        namespace[name] = getattr(validator, name)
    source = projected_mechanics()
    exec(compile(source, str(MECHANICS), "exec"), namespace, namespace)  # noqa: S102 - pinned mechanics
    namespace.update({
        "RUNNER": ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v12.py",
        "LAUNCHER": ROOT / "scripts/run_production_core_candidate_qualification_v11.sh",
        "NAMES": NAMES,
        "PROMPTS": PROMPTS,
        "PROMPT_SHA256": PROMPT_SHA256,
        "object_authority": object_authority,
        "wsl": linux_path,
        "validate_preflight": validate_and_map,
    })
    return namespace


def main() -> int:
    namespace = build_namespace()
    return namespace["main"]()


if __name__ == "__main__":
    raise SystemExit(main())
