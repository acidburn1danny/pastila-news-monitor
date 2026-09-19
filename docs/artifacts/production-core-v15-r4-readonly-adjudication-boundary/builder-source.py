"""Materialize a signed, non-verdict R4 read-only adjudication boundary."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import materialize_production_core_successor_execution_authority_v12 as signing
from pastila_scout.production_core_r4_readonly_adjudication import canonical, close_r4_evidence

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v15-r4-readonly-adjudication-boundary"
R4_OUTPUT = Path("/root/pf9-v15-r4-preconsumption-output")
R4_COMMIT = "13d9decbfdff22151a0bfaf64b3dd828463dbae1"
R4_TREE = "810d23709e585da8caafac7cb7fd0dadd196fae6"
BRANCH = "successor/core-v2-v12-runner-binding-remediation"
ARTIFACTS = ("boundary.json", "binding.json", "binding.sig", "builder-source.py")
SOURCES = (
    "src/pastila_scout/production_core_r4_readonly_adjudication.py",
    "scripts/materialize_production_core_v15_r4_readonly_adjudication_boundary.py",
    "scripts/audit_production_core_v15_r4_readonly_adjudication_boundary.py",
    "tests/test_production_core_v15_r4_readonly_adjudication_boundary.py",
    "docs/production-core-v15-r4-readonly-adjudication-boundary.md",
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build(output: Path = R4_OUTPUT) -> dict[str, object]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", R4_COMMIT, head], cwd=ROOT).returncode:
        raise ValueError("R4 published source checkpoint is not an ancestor")
    descendants = subprocess.check_output(
        ["git", "rev-list", "--reverse", "--parents", f"{R4_COMMIT}..{head}"],
        cwd=ROOT, text=True,
    ).splitlines()
    if (head != R4_COMMIT
            and (not descendants or any(len(row.split()) != 2 for row in descendants)
                 or descendants[0].split()[1] != R4_COMMIT
                 or descendants[-1].split()[0] != head)):
        raise ValueError("adjudication checkpoint must be a linear R4 successor")
    if subprocess.check_output(["git", "rev-parse", f"{R4_COMMIT}^{{tree}}"], cwd=ROOT, text=True).strip() != R4_TREE:
        raise ValueError("R4 published source tree drift")
    remote = subprocess.check_output(["git", "rev-parse", f"refs/remotes/origin/{BRANCH}"], cwd=ROOT, text=True).strip()
    if remote != R4_COMMIT:
        raise ValueError("R4 remote publication drift")
    authority_raw = (ROOT / "docs/artifacts/production-core-v15-r4-execution-authority/authority.json").read_bytes()
    authority = json.loads(authority_raw)
    if authority.get("authority_identity") != "a1bbd95e21b73c903a99d661c43a53448c7d50dab38c95c09e143b5d40740aa9":
        raise ValueError("R4 execution authority drift")
    generation = json.loads((ROOT / "docs/artifacts/production-core-successor-comparative-qualification-generation-v13.json").read_bytes())
    evidence = close_r4_evidence(output, generation["schedule"])
    source_sha256 = {name: digest((ROOT / name).read_bytes()) for name in SOURCES}
    registry = (ROOT / "docs/artifacts/production-core-semantic-adjudicator-public-key-registry-v1.json").read_bytes()
    core = {
        "schema": "pastila-production-core-v15-r4-readonly-adjudication-boundary",
        "schema_version": 1,
        "status": "SIGNED_READY_FOR_TWO_INDEPENDENT_HUMAN_RECEIPTS_NO_VERDICT",
        "published_r4_commit": R4_COMMIT,
        "published_r4_tree": R4_TREE,
        "r4_execution_authority_identity": authority["authority_identity"],
        "r4_binding_identity": digest((ROOT / "docs/artifacts/production-core-v15-r4-execution-authority/binding.json").read_bytes()),
        "r4_signature_identity": digest((ROOT / "docs/artifacts/production-core-v15-r4-execution-authority/binding.sig").read_bytes()),
        "qualification_generation_identity": authority["qualification_generation_identity"],
        "qualification_identity": authority["qualification_identity"],
        "request_manifest_identity": generation["request_manifest_identity"],
        "corpus_identity": json.loads((ROOT / "docs/artifacts/production-core-candidate-request-manifest-v2.json").read_bytes())["corpus_identity"],
        "assertion_manifest_identity": json.loads((ROOT / "docs/artifacts/production-core-qualification-assertions-v2.json").read_bytes())["assertion_manifest_identity"],
        "rubric_identity": json.loads((ROOT / "docs/artifacts/production-core-qualification-rubric-v2.json").read_bytes())["rubric_identity"],
        "adjudicator_registry_identity": json.loads(registry)["registry_identity"],
        "adjudicator_registry_sha256": digest(registry),
        "r4_evidence": evidence,
        "adjudication_rule": "TWO_DISTINCT_OWNER_REGISTERED_ED25519_RECEIPTS_OVER_EXACT_BLINDED_ROW; BOTH_PASS_REQUIRED; OTHERWISE_FAIL_CLOSED",
        "candidate_identity_disclosure": False,
        "attempt_mutation_authorized": False,
        "candidate_execution_authorized": False,
        "retry_or_redraw_authorized": False,
        "adjudication_performed": False,
        "adjudication_verdict": None,
        "promotion": False,
        "source_sha256": source_sha256,
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
    }
    return {**core, "boundary_identity": digest(canonical(core))}


def binding_for(boundary: dict[str, object], raw: bytes) -> dict[str, object]:
    return {
        "schema": "pastila-production-core-v15-r4-readonly-adjudication-binding",
        "schema_version": 1,
        "algorithm": "Ed25519",
        "boundary_identity": boundary["boundary_identity"],
        "boundary_sha256": digest(raw),
        "published_r4_commit": R4_COMMIT,
        "r4_evidence": boundary["r4_evidence"],
        "source_sha256": boundary["source_sha256"],
        "adjudication_performed": False,
        "promotion": False,
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
    }


def materialize(key: Path) -> dict[str, str]:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError("adjudication boundary already exists")
    signing.verify_key(key)
    boundary = build()
    raw = json.dumps(boundary, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    binding = canonical(binding_for(boundary, raw))
    with tempfile.TemporaryDirectory(prefix=".r4-adjudication-", dir=OUTPUT.parent) as temporary:
        stage = Path(temporary) / "payload"; stage.mkdir()
        (stage / "boundary.json").write_bytes(raw)
        (stage / "binding.json").write_bytes(binding)
        (stage / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(key), "-rawin", "-in", str(stage / "binding.json"), "-out", str(stage / "binding.sig")], check=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY), "-rawin", "-in", str(stage / "binding.json"), "-sigfile", str(stage / "binding.sig")], check=True, capture_output=True)
        stage.rename(OUTPUT)
    return {"boundary_identity": str(boundary["boundary_identity"]), "binding_identity": digest(binding), "signature_identity": digest((OUTPUT / "binding.sig").read_bytes())}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--private-key", type=Path, required=True)
    print(json.dumps(materialize(parser.parse_args().private_key), sort_keys=True))
