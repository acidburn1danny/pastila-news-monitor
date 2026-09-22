"""Fail-closed published successor authority check; safe before model load."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from build_editor_core_editorial_mechanics_bridge import canonical, sha

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = "docs/artifacts/editor-core-editorial-bridge-causal-execution-authority-v2.json"
OLD = "37846897e4ef69b9ab10aeaadf33a78de16c2098"
IDENTITY = "9d1ece6eddc0c24e3d91a2e1c4f05f25f0dc36405e48fb78c872cdf9c8ffd019"
PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
SEEDS = (271828, 314159, 161803)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL)


def verify(arm: str, seed: int, *, require_published: bool = True) -> dict:
    if arm not in ("A1", "A2") or type(seed) is not int or seed not in SEEDS:
        raise ValueError("unauthorized slot")
    raw = (ROOT / AUTHORITY).read_bytes()
    authority = json.loads(raw)
    if raw != json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n":
        raise ValueError("noncanonical authority")
    core = {k: v for k, v in authority.items() if k != "authority_identity"}
    slots = [{"arm": a, "seed": s, "output_slug": f"{a.lower()}-seed-{s}",
              "max_optimizer_steps": 12, "run_limit": 1}
             for a in ("A1", "A2") for s in SEEDS]
    expected = {"schema": "editor-core-bridge-causal-execution-authority", "schema_version": 2,
                "supersedes_execution_gate_from_commit": OLD,
                "scope": "SYNTHETIC_DEVELOPMENT_CAUSAL_A1_A2_ONLY",
                "parent_adapter_identity": PARENT,
                "parent_checkpoint_identity": "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be",
                "slots": slots, "holdout_access_authorized": False,
                "adjudication_authorized": False, "parent_selection_authorized": False,
                "promotion_authorized": False, "publication_required": True,
                "per_run_owner_invocation_required": True,
                "real_training_authorized_after_publication": True,
                "claimed_result": "CONTROLLED_SYNTHETIC_DEVELOPMENT_EDITORIAL_SIGNAL_ONLY"}
    if core != expected or authority.get("authority_identity") != IDENTITY or sha(canonical(core)) != IDENTITY:
        raise ValueError("successor authority contract")
    head = git("rev-parse", "HEAD").decode().strip()
    if head == OLD:
        raise ValueError("successor not committed")
    subprocess.run(["git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
                    "merge-base", "--is-ancestor", OLD, head], check=True)
    if git("show", f"{head}:{AUTHORITY}") != raw:
        raise ValueError("authority blob not in HEAD")
    if require_published:
        upstream = git("rev-parse", "@{upstream}").decode().strip()
        if upstream != head:
            raise ValueError("upstream mismatch")
        branch = git("symbolic-ref", "--quiet", "--short", "HEAD").decode().strip()
        if branch != "successor/core-v2-v12-runner-binding-remediation":
            raise ValueError("branch mismatch")
        remote = git("ls-remote", "--heads", "origin", branch).decode().split()[0]
        if remote != head:
            raise ValueError("remote mismatch")
    return {"status": "PASS_PUBLISHED_SUCCESSOR_AUTHORITY" if require_published else "PASS_LOCAL_COMMIT_ONLY",
            "commit": head, "authority_identity": IDENTITY,
            "slot": f"{arm.lower()}-seed-{seed}", "max_optimizer_steps": 12}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("A1", "A2"), required=True)
    parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.arm, args.seed), sort_keys=True))
