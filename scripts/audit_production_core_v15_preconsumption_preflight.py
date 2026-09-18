"""Fresh read-only audit of the published V15 authority and V15 output gate."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import preflight_production_core_candidate_qualification_v15 as gate


def audit(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path, output: Path) -> dict[str, object]:
    remote = subprocess.check_output(
        ["git", "ls-remote", "--heads", "origin", f"refs/heads/{gate.BRANCH}"],
        cwd=gate.ROOT, text=True).strip().split()
    if (len(remote) != 2 or remote[1] != f"refs/heads/{gate.BRANCH}"
            or subprocess.run(["git", "merge-base", "--is-ancestor", gate.COMMIT, remote[0]],
                              cwd=gate.ROOT, capture_output=True).returncode):
        raise ValueError("published V15 remote checkpoint mismatch")
    receipt = gate.preflight(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot, unicode_root, output)
    if (receipt["verdict"] != "PASS + 0 BLOCKERS" or receipt["authority_identity"] != gate.AUTHORITY
            or receipt["binding_identity"] != gate.BINDING or receipt["signature_identity"] != gate.SIGNATURE
            or receipt["candidate_execution"] != 0 or receipt["attempt_consumption"] != 0
            or receipt["output"]["entries"] != 0 or receipt["qualification_matrix"] != "PASS"
            or receipt["unicode_authority"] != "PASS" or receipt["executable_capabilities"] != "PASS"
            or receipt["adjudication"] is not False
            or receipt["promotion"] is not False):
        raise ValueError("V15 preflight receipt rejected")
    return {"verdict": "PASS + 0 BLOCKERS", "published_checkpoint": gate.COMMIT,
            "preflight_identity": receipt["preflight_identity"], "authority_identity": gate.AUTHORITY,
            "binding_identity": gate.BINDING, "signature_identity": gate.SIGNATURE,
            "ed25519_verification": "PASS", "source_closure": "PASS",
            "runtime_object_closure": "PASS", "snapshot_closure": "PASS",
            "isolated_cuda": "PASS", "v14_terminal_evidence": "UNCHANGED",
            "v15_output": "EMPTY_NATIVE_EXT4", "candidate_execution": 0,
            "attempt_consumption": 0, "adjudication": False, "promotion": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.recovery, args.private, args.backup, args.v13_terminal,
                           args.terminal, args.rootfs, args.snapshot, args.unicode_root, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
