"""Non-circular terminal entry: snapshot all project Python before execution."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import types
from pathlib import Path

ENTRY = Path(__file__).absolute()
if ENTRY.is_symlink() or not ENTRY.is_file():
    raise SystemExit("entry path authority rejected")
ROOT = ENTRY.parent.parent
EXECUTOR = ROOT / "scripts" / "execute_production_core_candidate_qualification_v1.py"
CORE = ROOT / "src" / "pastila_scout" / "production_core_candidate_qualification_v1.py"
ENVELOPE = ROOT / "src" / "pastila_scout" / "production_core_technical_output_envelope_v1.py"
EXPECTED_EXECUTOR_SHA256 = "e10c87b6315c038a30c29843c1cee7ee951b2b3dfaddb1d0ca0fd3a1b2bdabf9"
EXPECTED_CORE_SHA256 = "fdd1707eaae8979e3aa85d7bc681af7370752628cc287c364bb45ff92993cd07"
EXPECTED_ENVELOPE_SHA256 = "e3ac013360a239713c0da02b59359c6cfc87579e93a6721892af0bb96184bf01"
EXPECTED_ARTIFACT_SHA256 = {
    "production-core-candidate-object-manifest-v1.json": "551e6c2983e6d71664298432aa9b20e45b1677e3a45b8c6458a563cb913e83bf",
    "production-core-comparative-qualification-generation-v1.json": "8ee6a0dd4b246f930e718a8f32cf0ad880c000f82a82d1b7be34abc97797b5c4",
    "production-core-candidate-qualification-mechanism-v1.json": "40cb957fb238929deda82d9057205e434e5062e98fd3fa6c836fa0e6c75aac3a",
}
EXPECTED_IDENTITIES = {
    "manifest_identity": "51cae2453234d19fef6cd6bb1505beb7ae9bb8a27fcd152a61a6a7bb181a0420",
    "qualification_generation_identity": "cfa6c00b96430246755c7cdce4c59b52d67946b91c1635077890c317b9afcadf",
    "qualification_identity": "f6d1d3d5f30918be6676a1f7f80e7f99d7d96afceaf766a195b22a68aee25540",
}


def _read_pinned(path: Path, expected: str) -> bytes:
    if path.is_symlink():
        raise SystemExit("Python authority symlink rejected")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise SystemExit("Python authority is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read()
    finally:
        os.close(descriptor)
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit("Python authority byte mismatch")
    return data


def _terminal_validator(artifacts: dict[str, bytes]) -> str:
    if set(artifacts) != set(EXPECTED_ARTIFACT_SHA256):
        raise SystemExit("terminal artifact set mismatch")
    values = {}
    for name, expected in EXPECTED_ARTIFACT_SHA256.items():
        raw = artifacts[name]
        if hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit("terminal artifact byte mismatch")
        values[name] = json.loads(raw)
    manifest = values["production-core-candidate-object-manifest-v1.json"]
    generation = values["production-core-comparative-qualification-generation-v1.json"]
    qualification = values["production-core-candidate-qualification-mechanism-v1.json"]
    if (
        manifest.get("manifest_identity") != EXPECTED_IDENTITIES["manifest_identity"]
        or generation.get("qualification_generation_identity") != EXPECTED_IDENTITIES["qualification_generation_identity"]
        or qualification.get("qualification_identity") != EXPECTED_IDENTITIES["qualification_identity"]
    ):
        raise SystemExit("terminal artifact semantic identity mismatch")
    return EXPECTED_IDENTITIES["qualification_generation_identity"]


def _load_core() -> types.ModuleType:
    envelope_source = _read_pinned(ENVELOPE, EXPECTED_ENVELOPE_SHA256)
    envelope_name = "pastila_scout.production_core_technical_output_envelope_v1"
    envelope_module = types.ModuleType(envelope_name)
    envelope_module.__file__ = str(ENVELOPE)
    package = types.ModuleType("pastila_scout")
    package.__path__ = []  # type: ignore[attr-defined]
    sys.modules["pastila_scout"] = package
    sys.modules[envelope_name] = envelope_module
    exec(compile(envelope_source, str(ENVELOPE), "exec"), envelope_module.__dict__, envelope_module.__dict__)  # noqa: S102
    core_source = _read_pinned(CORE, EXPECTED_CORE_SHA256)
    core_module = types.ModuleType("pinned_production_core_candidate_qualification_v1")
    core_module.__file__ = str(CORE)
    exec(compile(core_source, str(CORE), "exec"), core_module.__dict__, core_module.__dict__)  # noqa: S102
    return core_module


def main() -> None:
    core_module = _load_core()
    executor_source = _read_pinned(EXECUTOR, EXPECTED_EXECUTOR_SHA256)
    namespace = {
        "__builtins__": __builtins__, "__file__": str(EXECUTOR), "__name__": "__main__",
        "__package__": None, "PINNED_ENTRY_EXECUTOR_SHA256": EXPECTED_EXECUTOR_SHA256,
        "PINNED_TERMINAL_VALIDATOR": _terminal_validator,
    }
    for name in ("atomic_publish", "build_blind_packet", "build_execution_receipt", "canonical_json_bytes", "materialize_batches"):
        namespace[name] = getattr(core_module, name)
    exec(compile(executor_source, str(EXECUTOR), "exec"), namespace, namespace)  # noqa: S102


if __name__ == "__main__":
    main()
