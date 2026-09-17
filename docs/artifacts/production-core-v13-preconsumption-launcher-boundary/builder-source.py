"""Sign the V13 pre-consumption launcher source without granting an attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import audit_production_core_successor_execution_authority_v13 as audit_v13
import materialize_production_core_successor_execution_authority_v12 as signing
import preflight_production_core_candidate_qualification_v13 as preflight

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v13-preconsumption-launcher-boundary"
SOURCE_FILES = (
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "docs/artifacts/pastila-editor-core-v1.1-json-successor-v10-system-prompt.txt",
    "docs/artifacts/pastila-editor-core-v1.2-json-successor-v10-system-prompt.txt",
    "docs/artifacts/production-core-unicode-16-uax29-authority-v1.json",
    "scripts/execute_production_core_candidate_qualification_v3.py",
    "scripts/execute_production_core_candidate_qualification_v13.py",
    "scripts/launch_production_core_candidate_qualification_v13.py",
    "scripts/preflight_production_core_candidate_qualification_v13.py",
    "scripts/audit_production_core_v13_preconsumption_preflight.py",
    "scripts/audit_production_core_v13_launcher_boundary.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "scripts/run_production_core_candidate_qualification_v11.sh",
    "scripts/smoke_production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v13.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v12.py",
    "src/pastila_scout/production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_semantic_authority_v2.py",
)
AUTHORITY_ID = "2aaa50283451d5338b15d256becccb1ac7e557f12a677126051a036c368d2804"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build() -> dict:
    preflight.published_source_closure()
    v13 = audit_v13.audit(preflight.AUTHORITY, Path("/unused"), Path("/unused"), Path("/unused"), recompute=False)
    if v13["authority_identity"] != AUTHORITY_ID:
        raise ValueError("published V13 authority mismatch")
    sources = {}
    for name in SOURCE_FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"launcher source unavailable: {name}")
        raw = path.read_bytes()
        if subprocess.run(["git", "cat-file", "-e", f"{preflight.COMMIT}:{name}"], cwd=ROOT, capture_output=True).returncode == 0:
            committed = subprocess.check_output(["git", "show", f"{preflight.COMMIT}:{name}"], cwd=ROOT)
            if raw != committed:
                raise ValueError(f"published independent source drift: {name}")
        sources[name] = digest(raw)
    core = {
        "schema": "pastila-production-core-v13-preconsumption-launcher-boundary",
        "schema_version": 1,
        "status": "SIGNED_PREFLIGHT_ONLY_ZERO_ATTEMPTS",
        "bound_published_commit": preflight.COMMIT,
        "bound_published_tree": preflight.TREE,
        "v13_authority_identity": v13["authority_identity"],
        "v13_binding_identity": v13["binding_identity"],
        "v13_signature_identity": v13["signature_identity"],
        "source_sha256": sources,
        "builder_sha256": digest(Path(__file__).read_bytes()),
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "candidate_execution_authorized": False,
        "attempt_consumption_authorized": False,
        "adjudication": False,
        "promotion": False,
    }
    return {**core, "boundary_identity": digest(canonical(core))}


def binding_for(boundary: dict, raw: bytes) -> dict:
    return {
        "schema": "pastila-production-core-v13-preconsumption-launcher-binding",
        "schema_version": 1,
        "algorithm": "Ed25519",
        "boundary_identity": boundary["boundary_identity"],
        "boundary_sha256": digest(raw),
        "bound_published_commit": preflight.COMMIT,
        "bound_published_tree": preflight.TREE,
        "v13_authority_identity": AUTHORITY_ID,
        "builder_sha256": boundary["builder_sha256"],
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }


def materialize(private_key: Path, output: Path = OUTPUT) -> dict[str, str]:
    if output.exists() or output.is_symlink():
        raise ValueError("launcher boundary output already exists")
    signing.verify_key(private_key)
    boundary = build()
    raw = json.dumps(boundary, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    binding_raw = canonical(binding_for(boundary, raw))
    with tempfile.TemporaryDirectory(prefix=".v13-launcher-", dir=output.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        (staging / "boundary.json").write_bytes(raw)
        (staging / "binding.json").write_bytes(binding_raw)
        (staging / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private_key), "-rawin", "-in", str(staging / "binding.json"), "-out", str(staging / "binding.sig")], check=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY), "-rawin", "-in", str(staging / "binding.json"), "-sigfile", str(staging / "binding.sig")], check=True, capture_output=True)
        signature = (staging / "binding.sig").read_bytes()
        if len(signature) != 64:
            raise ValueError("Ed25519 launcher signature length mismatch")
        result = {"boundary_identity": boundary["boundary_identity"],
                  "binding_identity": digest(binding_raw), "signature_identity": digest(signature)}
        os.replace(staging, output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-key", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.private_key), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
