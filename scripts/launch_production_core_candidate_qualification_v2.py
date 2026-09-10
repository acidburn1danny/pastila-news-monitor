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
EXECUTOR = ROOT / "scripts" / "execute_production_core_candidate_qualification_v2.py"
CORE = (
    ROOT
    / "src"
    / "pastila_scout"
    / "production_core_candidate_execution_authority_v2.py"
)
SEMANTIC = ROOT / "src" / "pastila_scout" / "production_core_semantic_authority_v2.py"
ART = ROOT / "docs" / "artifacts"
EXECUTOR_SHA = "692fb99600e50997253692488034c86d416913d2cc9637aa914345fad891e87e"
CORE_SHA = "8e012d04785135f3c924bab4c8a72ce0fc8559abc3702d7eb4c4d1225c302461"
SEMANTIC_SHA = "af079fb50f281e09433dba299feaf9c2354bb4946df8e476658f71cc228d4c41"
ARTIFACTS = {
    "production-core-comparative-qualification-generation-v2.json": "4ff3998dff0b2fd64f0dddc29e7e351ab20e9b0bad214b70b039c728ce5a03cb",
    "production-core-candidate-request-manifest-v2.json": "b07d11975e558056a9350c75522c7d2fce2b9e6e924ea2a691cf76d70eb652d6",
    "production-core-candidate-object-manifest-v2.json": "4cdee10999056dac6ef3e2bcb7680aa69fa7c0973d296781267517b11af597ae",
    "production-core-candidate-generation-qualification-v2.json": "9498433a4ff1dc7c3640b8ca509caab0ac3cd82a81266d4d158e6e55aaba9c43",
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
    mechanism_raw = read(ART / "production-core-candidate-execution-authority-v2.json")
    mechanism = json.loads(mechanism_raw)
    core = dict(mechanism)
    recorded = core.pop("execution_authority_identity", None)
    sources = mechanism.get("source_sha256", {})
    authority = mechanism.get("authority_identities")
    expected_sources = {
        "docs/schemas/production-core-candidate-execution-authority-v2.schema.json",
        "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
        "scripts/execute_production_core_candidate_qualification_v2.py",
        "scripts/launch_production_core_candidate_qualification_v2.py",
        "scripts/resolve_production_core_object_authority_v2.sh",
        "scripts/run_production_core_candidate_qualification_v2.sh",
        "src/pastila_scout/production_core_candidate_execution_authority_v2.py",
        "src/pastila_scout/production_core_candidate_qualification_runner_v2.py",
        "src/pastila_scout/production_core_semantic_authority_v2.py",
        "tests/test_production_core_candidate_execution_authority_v2.py",
    }
    expected_authority = {
        "qualification_generation_identity": module.GENERATION_IDENTITY,
        "qualification_identity": module.QUALIFICATION_IDENTITY,
        "request_manifest_identity": module.REQUEST_MANIFEST_IDENTITY,
        "candidate_object_manifest_identity": module.CANDIDATE_MANIFEST_IDENTITY,
    }
    if (
        tuple(mechanism)
        != (
            "schema",
            "schema_version",
            "status",
            "authority_identities",
            "source_sha256",
            "matrix_rows",
            "attempt_ordinal",
            "retry_or_redraw_authorized",
            "adjudication_performed",
            "candidate_execution_performed",
            "promotion_effect",
            "execution_authority_identity",
        )
        or mechanism.get("schema")
        != "pastila-production-core-candidate-execution-authority"
        or mechanism.get("schema_version") != 2
        or mechanism.get("status") != "PASS_OFFLINE_EXECUTION_AUTHORITY_ZERO_ATTEMPTS"
        or authority != expected_authority
        or not isinstance(sources, dict)
        or set(sources) != expected_sources
        or mechanism.get("matrix_rows") != 2400
        or mechanism.get("attempt_ordinal") != 1
        or mechanism.get("retry_or_redraw_authorized") is not False
        or recorded != module.identity(core)
        or hashlib.sha256(read(ENTRY)).hexdigest()
        != sources.get("scripts/launch_production_core_candidate_qualification_v2.py")
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
