"""Content-addressed terminal entry for Core V2 comparative execution."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import types
from pathlib import Path

ENTRY = Path(__file__).absolute()
ROOT = ENTRY.parent.parent
EXECUTOR = ROOT / "scripts" / "execute_production_core_candidate_qualification_v3.py"
CORE = (
    ROOT
    / "src"
    / "pastila_scout"
    / "production_core_candidate_execution_authority_v3.py"
)
SEMANTIC = ROOT / "src" / "pastila_scout" / "production_core_semantic_authority_v2.py"
CHECKPOINT = ROOT / "src" / "pastila_scout" / "production_core_checkpoint_resume_v6.py"
ART = ROOT / "docs" / "artifacts"
OPENSSL = Path(r"C:\Program Files\FireDaemon OpenSSL 3.5\bin\openssl.exe")
SIGNING_PUBLIC_KEY = ART / "production-core-v8-1-signing-public.pem"
SIGNING_PUBLIC_KEY_SHA256 = "29616718e9d17a3c88f630af52fee0ef7a9dc7adc519412c4870f06b63ca1cca"
SIGNED_BINDING = ART / "production-core-candidate-execution-authority-v8-1.binding.json"
DETACHED_SIGNATURE = ART / "production-core-candidate-execution-authority-v8-1.binding.sig"
EXECUTOR_SHA = "5e873f291da0c861bf55355ad522b87dd06e276d17d9b290092aa3c8556ab9f7"
CORE_SHA = "404a180db4500b6e6cb633d9e17e3b5a3ec8ae615f9babdcf0ad50f8f0d1989c"
CHECKPOINT_SHA = "d33e08722a0f4759644cd6b1e902570ec430202bfe6a7c1f2c269fbc722b8d58"
SEMANTIC_SHA = "af079fb50f281e09433dba299feaf9c2354bb4946df8e476658f71cc228d4c41"
ARTIFACTS = {
    "production-core-successor-comparative-qualification-generation-v5.json": "6bd336c2e1ff733f02fd4d05065a8dbb5364eeebaf5dd10a7e6f8cdc32a4995d",
    "production-core-candidate-request-manifest-v2.json": "b07d11975e558056a9350c75522c7d2fce2b9e6e924ea2a691cf76d70eb652d6",
    "production-core-successor-candidate-object-manifest-v5.json": "01003a0e9f005f717c7525c0d7fa9462208633c1bff44c8003d0c6f10d17b2f3",
    "production-core-successor-candidate-generation-qualification-v5.json": "cdb139b0a2e330a7b64529add4b4c9cfb7b9e1c3abe078537c09505fdc5089d0",
}


def read(path, expected=None):
    if path.is_symlink():
        raise SystemExit("entry symlink rejected")
    fd = os.open(
        path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise SystemExit("entry regular file required")
        with os.fdopen(fd, "rb", closefd=False) as h:
            data = h.read()
    finally:
        os.close(fd)
    if expected is not None and hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit("entry byte authority mismatch")
    return data


def main():
    if ENTRY.is_symlink() or not ENTRY.is_file():
        raise SystemExit("entry path rejected")
    core_source = read(CORE, CORE_SHA)
    module = types.ModuleType("pinned_execution_authority_v2")
    module.__file__ = str(CORE)
    exec(  # noqa: S102 - execute only the byte-exact, hash-verified frozen source.
        compile(core_source, str(CORE), "exec"), module.__dict__, module.__dict__
    )
    semantic_source = read(SEMANTIC, SEMANTIC_SHA)
    semantic = types.ModuleType("pinned_semantic_authority_v2")
    semantic.__file__ = str(SEMANTIC)
    sys.modules[semantic.__name__] = semantic
    exec(  # noqa: S102 - execute only the byte-exact, hash-verified frozen source.
        compile(semantic_source, str(SEMANTIC), "exec"),
        semantic.__dict__,
        semantic.__dict__,
    )
    raw = {name: read(ART / name, digest) for name, digest in ARTIFACTS.items()}
    checkpoint_source = read(CHECKPOINT, CHECKPOINT_SHA)
    checkpoint = types.ModuleType("pinned_checkpoint_resume_v6")
    checkpoint.__file__ = str(CHECKPOINT)
    exec(  # noqa: S102 - execute only the byte-exact, hash-verified source.
        compile(checkpoint_source, str(CHECKPOINT), "exec"),
        checkpoint.__dict__,
        checkpoint.__dict__,
    )
    public_key = read(SIGNING_PUBLIC_KEY, SIGNING_PUBLIC_KEY_SHA256)
    if b"-----BEGIN PUBLIC KEY-----" not in public_key:
        raise SystemExit("signing public key encoding mismatch")
    binding_raw = read(SIGNED_BINDING)
    signature = read(DETACHED_SIGNATURE)
    if len(signature) != 64 or not OPENSSL.is_file():
        raise SystemExit("detached signing boundary unavailable")
    verified = subprocess.run(
        [
            str(OPENSSL),
            "pkeyutl",
            "-verify",
            "-pubin",
            "-inkey",
            str(SIGNING_PUBLIC_KEY),
            "-rawin",
            "-in",
            str(SIGNED_BINDING),
            "-sigfile",
            str(DETACHED_SIGNATURE),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if verified.returncode != 0:
        raise SystemExit("detached authority signature invalid")
    binding = json.loads(binding_raw)
    mechanism_raw = read(
        ART / "production-core-candidate-execution-authority-v8-1.json"
    )
    mechanism = json.loads(mechanism_raw)
    core = dict(mechanism)
    recorded = core.pop("execution_authority_identity", None)
    sources = mechanism.get("source_sha256", {})
    authority = mechanism.get("authority_identities")
    expected_sources = {
        "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
        "scripts/execute_production_core_candidate_qualification_v3.py",
        "scripts/launch_production_core_candidate_qualification_v4.py",
        "scripts/resolve_production_core_object_authority_v2.sh",
        "scripts/run_production_core_candidate_qualification_v3.sh",
        "scripts/smoke_production_core_checkpoint_resume_v6.py",
        "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
        "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
        "src/pastila_scout/production_core_checkpoint_resume_v6.py",
        "src/pastila_scout/production_core_semantic_authority_v2.py",
    }
    expected_authority = {
        "qualification_generation_identity": module.GENERATION_IDENTITY,
        "qualification_identity": module.QUALIFICATION_IDENTITY,
        "request_manifest_identity": module.REQUEST_MANIFEST_IDENTITY,
        "candidate_object_manifest_identity": module.CANDIDATE_MANIFEST_IDENTITY,
        "candidate_audit_receipt_identity": "7519871ebd5cc566a06a8c24f04976244cda9e0653e35464adc1ef8bd80b77a2",
    }
    if (
        tuple(binding)
        != (
            "schema",
            "schema_version",
            "algorithm",
            "public_key_sha256",
            "authority_identity",
            "authority_sha256",
            "bound_source_commit",
            "source_sha256",
            "candidate_execution_authorized",
            "attempt_consumption_authorized",
        )
        or binding.get("schema")
        != "pastila-production-core-v8-1-detached-authority-binding"
        or binding.get("schema_version") != 1
        or binding.get("algorithm") != "Ed25519"
        or binding.get("public_key_sha256") != SIGNING_PUBLIC_KEY_SHA256
        or binding.get("authority_identity") != recorded
        or binding.get("authority_sha256")
        != hashlib.sha256(mechanism_raw).hexdigest()
        or binding.get("bound_source_commit")
        != mechanism.get("bound_source_commit")
        or binding.get("source_sha256") != sources
        or binding.get("candidate_execution_authorized") is not False
        or binding.get("attempt_consumption_authorized") is not False
    ):
        raise SystemExit("signed authority binding mismatch")
    if (
        tuple(mechanism)
        != (
            "schema",
            "schema_version",
            "status",
            "bound_source_commit",
            "predecessor_terminal_failure_identity",
            "predecessor_root_cause_addendum_identity",
            "authority_identities",
            "source_sha256",
            "matrix_rows",
            "checkpoint_policy",
            "lifecycle_completed_contract",
            "attempt_ordinal",
            "attempt_consumption_authorized",
            "candidate_execution_authorized",
            "retry_or_redraw_authorized",
            "adjudication_performed",
            "candidate_execution_performed",
            "promotion_effect",
            "execution_authority_identity",
        )
        or mechanism.get("schema")
        != "pastila-production-core-candidate-execution-authority"
        or mechanism.get("schema_version") != 9
        or mechanism.get("status")
        != "FROZEN_SUCCESSOR_V8_1_LAUNCH_BINDING_REPAIR_ZERO_ATTEMPTS"
        or authority != expected_authority
        or not isinstance(sources, dict)
        or set(sources) != expected_sources
        or mechanism.get("matrix_rows") != 2400
        or mechanism.get("checkpoint_policy") != {
            "checkpoint_count": 12,
            "rows_per_checkpoint": 200,
            "ordinal_source": "VALIDATED_AUTHORITY_SCHEDULE",
            "atomic_publish": True,
            "content_addressed_receipt": True,
            "same_attempt_resume_only": True,
            "recalculate_finalized_rows": False,
        }
        or mechanism.get("attempt_ordinal") != 1
        or mechanism.get("predecessor_terminal_failure_identity")
        != "a4eb2c19c9b47a74236793adc01cd807d4ed5048415407095737553a12185fc6"
        or mechanism.get("predecessor_root_cause_addendum_identity")
        != "06661c7dc7c73d80bfef026da13e50732de27eb2f19cc3d4ad674e3ede44f84d"
        or mechanism.get("lifecycle_completed_contract")
        != {
            "termination_reason_required": True,
            "termination_reason_observation_binding_required": True,
            "missing_wrong_or_extra_fields_rejected": True,
        }
        or mechanism.get("attempt_consumption_authorized") is not False
        or mechanism.get("candidate_execution_authorized") is not False
        or mechanism.get("retry_or_redraw_authorized") is not False
        or recorded != module.identity(core)
        or hashlib.sha256(read(ENTRY)).hexdigest()
        != sources.get("scripts/launch_production_core_candidate_qualification_v4.py")
        or hashlib.sha256(semantic_source).hexdigest()
        != sources.get("src/pastila_scout/production_core_semantic_authority_v2.py")
        or mechanism.get("candidate_execution_performed") is not False
        or mechanism.get("adjudication_performed") is not False
        or mechanism.get("promotion_effect") is not False
    ):
        raise SystemExit("mechanism identity mismatch")

    def terminal(candidate):
        if candidate != raw:
            raise SystemExit("terminal snapshot substitution")
        values = [json.loads(candidate[name]) for name in ARTIFACTS]
        module.validate_preflight(*values)

    executor = read(EXECUTOR, EXECUTOR_SHA)
    namespace = {
        "__builtins__": __builtins__,
        "__file__": str(EXECUTOR),
        "__name__": "__main__",
        "__package__": None,
        "PINNED_ENTRY_EXECUTOR_SHA256": EXECUTOR_SHA,
        "PINNED_TERMINAL_VALIDATOR": terminal,
        "PINNED_EXECUTION_MECHANISM": mechanism,
        "PINNED_ROOTFS_SHA256": module.EXPECTED_OBJECTS[0][2],
        "build_checkpoint_receipt": checkpoint.build_receipt,
        "validate_checkpoint_chain": checkpoint.validate_chain,
        "write_checkpoint_receipt": checkpoint.write_receipt,
    }
    for name in (
        "GENERATION_IDENTITY",
        "MATRIX_ROWS",
        "build_attempt",
        "build_terminal_failure",
        "canonical",
        "identity",
        "materialize_batches",
        "result_status",
        "validate_attempt",
        "validate_boundary_logs",
        "validate_case_receipt",
        "validate_completion",
        "validate_observation",
        "validate_preflight",
        "validate_terminal_failure",
    ):
        namespace[name] = getattr(module, name)
    namespace["Unicode16SentenceAuthority"] = semantic.Unicode16SentenceAuthority
    namespace["PINNED_UNICODE_AUTHORITY_SHA256"] = (
        semantic.SENTENCE_PROPERTY_SHA256,
        semantic.SENTENCE_TEST_SHA256,
        semantic.UAX29_SHA256,
    )
    namespace["validate_response_v2"] = semantic.validate_response_v2
    exec(  # noqa: S102 - execute only the byte-exact, hash-verified frozen source.
        compile(executor, str(EXECUTOR), "exec"), namespace, namespace
    )


if __name__ == "__main__":
    main()
