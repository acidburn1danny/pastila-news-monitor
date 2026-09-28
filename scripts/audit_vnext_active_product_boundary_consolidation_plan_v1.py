from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "docs/vnext-active-product-boundary-consolidation-plan-v1.md",
    "docs/artifacts/vnext-active-product-dependency-graph-v1.json",
    "docs/artifacts/vnext-active-product-component-migration-matrix-v1.json",
    "docs/artifacts/vnext-active-product-workflow-state-contract-v1.json",
    "docs/artifacts/vnext-active-product-consolidation-acceptance-gates-v1.json",
    "scripts/audit_vnext_active_product_boundary_consolidation_plan_v1.py",
]
PRODUCT_ROOT = "/root/pastila-vnext/v1"
FORBIDDEN_ACTIVE = {
    "QWEN3_CANDIDATE_CLOSURE", "QWEN25_CANDIDATE_CLOSURE",
    "REJECTED_VOICE_CANDIDATE_DEPENDENCIES", "BAKEOFF_RUNS",
    "REVIEW_UI_SERVER", "HUMAN_REVIEW_RECEIPTS_AS_RUNTIME_DEPENDENCY",
    "SCORING_UNSEAL_TAXONOMY_TOOLING", "HISTORICAL_EXECUTION_AUTHORITIES",
    "EXPERIMENTAL_ADAPTERS", "FAILED_RUNS", "DEVELOPMENT_FIXTURE_AUTHORITIES",
    "FROZEN_EVIDENCE_REPORTS", "CLEAN_ROOM_WORKSPACES",
    "LEGACY_REPOSITORY_RUNTIME",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_identity(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def git_scope(commit: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def audit(commit: str | None) -> dict:
    assert len(FILES) == 6 and len(set(FILES)) == 6
    for name in FILES:
        assert (ROOT / name).is_file(), name

    plan = (ROOT / FILES[0]).read_text(encoding="utf-8")
    graph = load(FILES[1])
    matrix = load(FILES[2])
    workflow = load(FILES[3])
    gates = load(FILES[4])

    assert graph["verdict"] == "C_REFACTOR_CONSOLIDATE_BEFORE_CONTINUING"
    assert graph["architecture"] == "MODULAR_MONOLITH"
    assert graph["product_root"] == PRODUCT_ROOT
    assert graph["legacy_dependency_count"] == 0
    assert graph["stop_all_candidates"] is True
    assert set(graph["explicitly_excluded"]) == FORBIDDEN_ACTIVE
    assert all(node["active"] is True for node in graph["nodes"])
    active_ids = {node["id"] for node in graph["nodes"]}
    assert not active_ids.intersection({"voice", "gui", "shadow_verifier"})
    assert all(item["active_dependency"] is False for item in graph["disabled_boundaries"])

    for node in graph["nodes"]:
        target = PurePosixPath(PRODUCT_ROOT) / node["target_path"]
        assert str(target).startswith(PRODUCT_ROOT + "/")
        assert "/v2" not in str(target).lower()
    for item in graph["disabled_boundaries"]:
        target = PurePosixPath(PRODUCT_ROOT) / item["target_path"]
        assert str(target).startswith(PRODUCT_ROOT + "/")

    classes = {row["classification"] for row in matrix["rows"]}
    assert classes == {"KEEP", "MERGE", "REBUILD", "ARCHIVE", "DROP"}
    assert all(row["target"] and row["acceptance"] for row in matrix["rows"])
    excluded_rows = [row for row in matrix["rows"] if not row["active_dependency"]]
    assert any("voice-candidates" in row["current"] for row in excluded_rows)
    assert matrix["cleanup_gate"] == "GLOBAL_VNEXT_MIGRATION_PASS_AND_SEPARATE_OWNER_AUTHORIZATION"

    assert workflow["artifact_types"]["EDITOR_DRAFT"]["eligible_as_accepted_setup"] is False
    assert workflow["artifact_types"]["ACCEPTED_SETUP"]["eligible_for_voice"] is True
    assert workflow["voice"]["state"] == "DISABLED_UNTIL_PROMOTION"
    assert workflow["voice"]["r2_may_serve_as_voice"] is False
    assert workflow["chief_editor"]["separate_model"] is False
    assert workflow["final"]["mode"] == "DETERMINISTIC_ASSEMBLY_EXPORT"
    assert ["FACTUAL_REVIEW_PENDING", "ACCEPTED_SETUP"] in workflow["transitions"]
    assert ["FACTUAL_REVIEW_PENDING", "SOURCE_FALLBACK"] in workflow["transitions"]
    assert ["FACTUAL_REVIEW_PENDING", "ABSTAINED"] in workflow["transitions"]

    policy = gates["development_evaluation_policy"]
    assert policy["pilot_required"] is True
    assert policy["maximum_observations_before_checkpoint"] == 100
    assert policy["checkpoint_verdicts"] == ["STOP", "REVISE", "CONTINUE"]
    assert policy["intermediates_default"] == "EPHEMERAL"
    assert gates["cleanup"]["executed_by_this_checkpoint"] is False
    gate_ids = {gate["id"] for gate in gates["gates"]}
    assert gate_ids == {"FOUNDATION", "SCOUT", "SOURCE_PACKET", "EDITOR", "FACTUAL_ACCEPTANCE", "VOICE", "FINAL", "GUI", "DEPLOYMENT", "GLOBAL_VNEXT_MIGRATION"}

    required_plan = [
        "DESIGN AUTHORITY ONLY", "MODULAR MONOLITH", PRODUCT_ROOT,
        "EditorDraft", "AcceptedSetup", "STOP_ALL_CANDIDATES",
        "LEGACY_DEPENDENCY_COUNT = 0", "maximum 100 observations",
    ]
    for phrase in required_plan:
        assert phrase in plan, phrase
    assert "/v2" not in plan.lower()

    scope = git_scope(commit) if commit else FILES
    if commit:
        assert scope == sorted(FILES), {"expected": sorted(FILES), "actual": scope}

    blobs = {name: sha256(ROOT / name) for name in FILES}
    return {
        "verdict": "PASS",
        "blockers": 0,
        "scope": sorted(scope),
        "blob_sha256": blobs,
        "identities": {
            "plan": blobs[FILES[0]],
            "active_dependency_graph": canonical_identity(graph),
            "component_migration_matrix": canonical_identity(matrix),
            "workflow_state_contract": canonical_identity(workflow),
            "consolidation_acceptance_gates": canonical_identity(gates),
        },
        "cross_artifact_consistency": "PASS",
        "product_root_target": PRODUCT_ROOT,
        "product_lock_modified_by_checkpoint": False,
        "product_root_modified_by_checkpoint": False,
        "v2_absent": True,
        "stop_all_candidates": True,
        "legacy_dependency_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit")
    args = parser.parse_args()
    print(json.dumps(audit(args.commit), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
