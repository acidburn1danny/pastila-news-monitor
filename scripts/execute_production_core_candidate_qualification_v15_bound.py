"""Only successor consuming route: self-issued receipt, then atomic recheck."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import audit_production_core_v15_execution_bound_preflight as signed
import execute_production_core_candidate_qualification_v15 as mechanics
import preflight_production_core_candidate_qualification_v15_bound as gate


def run(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
        terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
        output: Path, *, owner_authorized: bool) -> int:
    if not owner_authorized:
        raise ValueError("separate owner attempt authorization required")
    if not output.is_absolute() or output != output.resolve(strict=True):
        raise ValueError("execution-bound output path must be canonical")
    receipt = gate.issue(recovery, private, backup, v13_terminal, terminal, rootfs,
                         snapshot, unicode_root, output)
    authority = signed.audit(recovery, private, backup, v13_terminal, terminal,
                             rootfs, snapshot, output)["authority"]
    protected = (gate.ROOT, recovery, private, backup, v13_terminal, terminal,
                 rootfs, snapshot, unicode_root)
    gate.verify_receipt(receipt, authority, receipt, private, output, protected)
    namespace = mechanics.build_namespace({"boundary_identity": authority["authority_identity"],
                                           "source_sha256": authority["source_sha256"]})
    original_atomic = mechanics.atomic_no_replace

    def guarded_atomic(path: Path, data: bytes) -> None:
        if path == output / "attempt.json":
            # Called by comparative mechanics under its exclusive output flock.
            repeated = signed.audit(recovery, private, backup, v13_terminal, terminal,
                                    rootfs, snapshot, output)
            if repeated["authority_identity"] != receipt["authority_identity"]:
                raise ValueError("execution-bound authority drift before attempt claim")
            gate.verify_receipt(receipt, repeated["authority"], receipt,
                                private, output, protected)
        original_atomic(path, data)

    namespace["atomic"] = guarded_atomic
    previous = sys.argv
    try:
        sys.argv = [str(Path(__file__)), "--resolution", str(recovery / "v12-executor-resolution.json"),
                    "--secret", str(private / "candidate-alias-secret-v13.json"),
                    "--unicode-authority-root", str(unicode_root), "--output", str(output)]
        return namespace["main"]()
    finally:
        sys.argv = previous


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--consume-attempt", action="store_true", required=True)
    a = parser.parse_args()
    return run(a.recovery, a.private, a.backup, a.v13_terminal, a.terminal,
               a.rootfs, a.snapshot, a.unicode_root, a.output,
               owner_authorized=a.consume_attempt)


if __name__ == "__main__":
    raise SystemExit(main())
