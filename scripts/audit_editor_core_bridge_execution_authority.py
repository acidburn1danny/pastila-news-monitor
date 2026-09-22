"""Read-only authority audit for the published A1/A2 causal pilot commit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

PUBLISHED = "37846897e4ef69b9ab10aeaadf33a78de16c2098"
PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
PROTOCOL = "docs/artifacts/editor-core-editorial-bridge-development-causal-pilot-v1.json"
ROUTE = "scripts/run_editor_core_bridge_causal_pilot.sh"


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL)


def audit(root: Path) -> dict:
    head = git(root, "rev-parse", "HEAD").decode().strip()
    subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", PUBLISHED, head],
                   check=True, stderr=subprocess.DEVNULL)
    protocol_bytes = git(root, "show", f"{PUBLISHED}:{PROTOCOL}")
    if (root / PROTOCOL).read_bytes() != protocol_bytes:
        raise ValueError("protocol worktree mutation")
    protocol = json.loads(protocol_bytes)
    if (protocol.get("parent_adapter_identity") != PARENT
            or protocol.get("candidate_arms") != ["A1", "A2"]
            or protocol.get("seeds") != [271828, 314159, 161803]
            or protocol.get("evaluation_splits_allowed") != ["SYNTHETIC_DEVELOPMENT_ONLY"]
            or "SYNTHETIC_HOLDOUT" not in protocol.get("evaluation_splits_forbidden", [])
            or protocol.get("real_runs_authorized") is not False
            or protocol.get("optimizer_steps_authorized") != 0
            or protocol.get("parent_change_authorized") is not False):
        raise ValueError("published authority/protocol drift")
    route_bytes = git(root, "show", f"{PUBLISHED}:{ROUTE}")
    local_route_is_published = (root / ROUTE).read_bytes() == route_bytes
    if b"BRIDGE_A1A2_OWNER_AUTHORIZED" not in route_bytes:
        raise ValueError("execution route identity drift")
    return {"published_commit": PUBLISHED,
            "tree": git(root, "rev-parse", f"{PUBLISHED}^{{tree}}").decode().strip(),
            "development_parent": PARENT, "matched_run_slots": 6,
            "holdout_access_authorized": False, "real_runs_authorized": False,
            "optimizer_steps_authorized": 0, "execution_authority": "BLOCKED",
            "local_route_is_published": local_route_is_published,
            "finding": "environment owner flag is not a successor authority to the published protocol"}


if __name__ == "__main__":
    print(json.dumps(audit(Path(__file__).resolve().parents[1]), sort_keys=True))
