"""Freeze the uninvoked V4 constructor implementation and nonblind denyset."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "e2433eaa71d1d13a0252a030647d35cd85b6017e"
MODULE_PATH = "src/pastila_scout/humor_batch2_development_constructor_v4.py"
ASSIGNMENT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-sealed-rebalancing-assignment-v4.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-constructor-facing-rebalancing-assignment-proposal-v4.json"
AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-rebalancing-assignment-design-audit-v4.json"
GOVERNANCE_PATH = "docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-governance-v4.json"
SCHEMA_PATH = "docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-conformance-schema-v4.json"
CANDIDATE_PATHS = [
    f"docs/artifacts/humor-mechanics-batch2-development-pilot{i:02d}-candidate01-v1.txt"
    for i in range(1, 8)
]


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(blob(path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def normalize_words(raw: bytes) -> list[str]:
    text = unicodedata.normalize("NFKC", raw.decode("utf-8")).casefold()
    return re.findall(r"[^\W_]+", text, flags=re.UNICODE)


def ngram_hashes(words: list[str], minimum: int = 3, maximum: int = 8) -> set[str]:
    values: set[str] = set()
    for size in range(minimum, maximum + 1):
        values.update(
            hashlib.sha256(" ".join(words[index:index + size]).encode()).hexdigest()
            for index in range(len(words) - size + 1)
        )
    return values


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), "artifact already exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    assignment, packet, assignment_audit = load(ASSIGNMENT_PATH), load(PACKET_PATH), load(AUDIT_PATH)
    governance, schema = load(GOVERNANCE_PATH), load(SCHEMA_PATH)
    require(assignment["sealed_assignment_identity"] == "87c2c2d9f5607e1bdcfcf4b2e01bda2039635e2f9c41c633338d4b42d627259a", "assignment")
    require(packet["constructor_facing_packet_identity"] == "2ecb50bcca118b4c62f67d6ee05c685ce1073030d6ef8f26d5930185c87ce48c", "packet")
    require(assignment_audit["audit_identity"] == "d5dc3abb29535200ae98488fd61ce9de7877e0b301d550407d92b5492171bdeb", "assignment audit")
    require(governance["governance_identity"] == "cc86204c6f199c80ef7c7bf87a58cf3c62d17acb1fe14bd2666bbf5ba86692f6", "governance")
    require(schema["schema_identity"] == "12c96a72555a26181abd5d0e7fa033a425fdacafb3a7fb197a21b39358da1dbe", "schema")

    historical_v1 = blob("src/pastila_scout/humor_batch2_development_constructor_v1.py")
    current_v1 = (ROOT / "src/pastila_scout/humor_batch2_development_constructor_v1.py").read_bytes()
    require(current_v1 == historical_v1, "historical constructor V1 changed")
    module = (ROOT / MODULE_PATH).read_bytes()
    tree = ast.parse(module.decode("utf-8"), filename=MODULE_PATH)
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    prohibited_imports = {"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "transformers", "torch", "importlib"}
    require(not imports.intersection(prohibited_imports), "prohibited constructor import")
    source_text = module.decode("utf-8")
    require(not re.search(r"\b[0-9a-f]{64}\b", source_text, re.I), "identity literal in constructor")
    require("candidate01" not in source_text and "pilot08" not in source_text.casefold(), "candidate/pilot routing")
    require("constructor_facing_packet_identity" not in source_text and "source_sha256" not in source_text, "identity routed branch")
    documentation_nodes = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    romanian_words = {"în", "din", "spre", "când", "iar", "până", "chiar", "această", "este"}
    multiword_surface_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in documentation_nodes
        and len(node.value.split()) >= 3
        and (
            any(ord(character) > 127 for character in node.value)
            or romanian_words.intersection(node.value.casefold().split())
        )
    ]
    require(not multiword_surface_literals, "multiword surface/marker literal")

    sources = []
    all_hashes: set[str] = set()
    for path in CANDIDATE_PATHS:
        raw = blob(path)
        words = normalize_words(raw)
        hashes = ngram_hashes(words)
        all_hashes.update(hashes)
        sources.append({
            "path": path,
            "git_blob_oid_sha1": subprocess.check_output(["git", "rev-parse", f"{COMMIT}:{path}"], cwd=ROOT, text=True).strip(),
            "surface_sha256": hashlib.sha256(raw).hexdigest(),
            "normalized_word_count": len(words),
            "normalized_ngram_hash_count": len(hashes),
            "partition": "DEVELOPMENT_NONBLIND",
        })
    denyset_core = {
        "schema_name": "batch2-nonblind-development-fragment-denyset-v4",
        "schema_version": "4.0.0",
        "governance_identity": governance["governance_identity"],
        "source_commit": COMMIT,
        "eligible_corpus": "NONBLIND_DEVELOPMENT_ONLY",
        "blind_reserve_accessed": False,
        "candidate_sources": sources,
        "normalization": "UNICODE_NFKC_CASEFOLD_ALPHANUMERIC_WORDS",
        "ngram_word_lengths": [3, 4, 5, 6, 7, 8],
        "normalized_ngram_sha256": sorted(all_hashes),
        "complete_surface_text_included": False,
        "model_or_semantic_similarity_used": False,
    }
    denyset = {**denyset_core, "fragment_denyset_identity": seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V4", denyset_core)}
    implementation_core = {
        "schema_name": "batch2-development-constructor-implementation-v4",
        "schema_version": "4.0.0",
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "module_path": MODULE_PATH,
        "module_sha256": hashlib.sha256(module).hexdigest(),
        "public_entrypoint": "construct_development_candidate_v4",
        "construction_revision_family_id": assignment["construction_revision_family_id"],
        "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "identity_routed_surface_branches": False,
        "complete_candidate_surface_literals": False,
        "reusable_multiword_creative_marker_literals": False,
        "filesystem_environment_process_network_model_access": False,
        "constructor_v1_sha256": hashlib.sha256(historical_v1).hexdigest(),
        "constructor_v1_status": "BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE",
        "invocations": 0,
        "candidate_surface": None,
        "release_authority": False,
    }
    implementation = {**implementation_core, "constructor_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V4", implementation_core)}
    audit_core = {
        "schema_name": "batch2-development-constructor-v4-static-audit-v1",
        "schema_version": "1.0.0",
        "assignment_identity": assignment["sealed_assignment_identity"],
        "constructor_facing_proposal_identity": packet["constructor_facing_packet_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "constructor_v1_byte_exact": "PASS",
        "pathless_import_allowlist": "PASS",
        "identity_routed_surface_branch_scan": "PASS_ZERO_HITS",
        "complete_candidate_surface_literal_scan": "PASS_ZERO_HITS",
        "reusable_creative_marker_literal_scan": "PASS_ZERO_HITS",
        "blind_reserve_access": "PASS_NONE",
        "nonblind_development_denyset": f"PASS_{len(sources)}_FAMILIES_{len(all_hashes)}_UNIQUE_NGRAM_HASHES",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "g02b_release": "NOT_PERFORMED",
        "fragment_collision_evaluation": "NOT_PERFORMED_POSTCONSTRUCTION_ONLY",
        "downstream_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_IMPLEMENTATION_AND_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V4_STATIC_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-nonblind-development-fragment-denyset-v4.json", denyset)
    write("humor-mechanics-batch2-development-constructor-implementation-v4.json", implementation)
    write("humor-mechanics-batch2-development-constructor-v4-static-audit-v1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "constructor_implementation_identity": implementation["constructor_implementation_identity"],
                      "fragment_denyset_identity": denyset["fragment_denyset_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
