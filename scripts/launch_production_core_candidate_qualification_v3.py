"""Content-addressed terminal entry for Core V2 comparative execution."""

from __future__ import annotations

import hashlib
import json
import os
import stat
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
ART = ROOT / "docs" / "artifacts"
EXECUTOR_SHA = "a95fb47d559fd8609d1ea79e4f7318cd0b9f49075186a858c579cddd375705a7"
CORE_SHA = "37f9bf16df723b2695bc254d6eef2bb5d7566ad18dcad49ff235625d607e55b8"
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
    mechanism_raw = read(ART / "production-core-candidate-execution-authority-v4.json")
    mechanism = json.loads(mechanism_raw)
    core = dict(mechanism)
    recorded = core.pop("execution_authority_identity", None)
    sources = mechanism.get("source_sha256", {})
    authority = mechanism.get("authority_identities")
    expected_sources = {
        "docs/schemas/production-core-candidate-execution-authority-v4.schema.json",
        "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
        "scripts/execute_production_core_candidate_qualification_v3.py",
        "scripts/launch_production_core_candidate_qualification_v3.py",
        "scripts/resolve_production_core_object_authority_v2.sh",
        "scripts/run_production_core_candidate_qualification_v3.sh",
        "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
        "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
        "src/pastila_scout/production_core_semantic_authority_v2.py",
        "tests/test_production_core_successor_execution_authority_v3.py",
    }
    expected_authority = {
        "qualification_generation_identity": module.GENERATION_IDENTITY,
        "qualification_identity": module.QUALIFICATION_IDENTITY,
        "request_manifest_identity": module.REQUEST_MANIFEST_IDENTITY,
        "candidate_object_manifest_identity": module.CANDIDATE_MANIFEST_IDENTITY,
        "root_cause_addendum_identity": "5290e19dae6d775d03200629b98980823a43495da607cf952286d2a052ed7672",
    }
    if (
        tuple(mechanism)
        != (
            "schema",
            "schema_version",
            "status",
            "bound_source_commit",
            "predecessor_attempt_identity",
            "predecessor_attempt_consumed_permanently",
            "authority_identities",
            "source_sha256",
            "matrix_rows",
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
        or mechanism.get("schema_version") != 4
        or mechanism.get("status")
        != "FROZEN_SUCCESSOR_EXECUTION_AUTHORITY_ZERO_ATTEMPTS_OWNER_EXECUTION_NOT_AUTHORIZED"
        or authority != expected_authority
        or not isinstance(sources, dict)
        or set(sources) != expected_sources
        or mechanism.get("matrix_rows") != 2400
        or mechanism.get("attempt_ordinal") != 1
        or mechanism.get("bound_source_commit")
        != "6c72a3c45c4a251a8fe61db82aea5bd462238120"
        or mechanism.get("predecessor_attempt_identity")
        != "337bb8acc130cc02f77f83c7a026b9212c781ba06d11989e64ef11b334f6a5ca"
        or mechanism.get("predecessor_attempt_consumed_permanently") is not True
        or mechanism.get("attempt_consumption_authorized") is not False
        or mechanism.get("candidate_execution_authorized") is not False
        or mechanism.get("retry_or_redraw_authorized") is not False
        or recorded != module.identity(core)
        or hashlib.sha256(read(ENTRY)).hexdigest()
        != sources.get("scripts/launch_production_core_candidate_qualification_v3.py")
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
