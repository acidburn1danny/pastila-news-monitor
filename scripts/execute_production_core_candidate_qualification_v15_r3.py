"""Only R3 consuming route; disabled until signed publication and owner attempt consent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import audit_production_core_v15_r3_execution_authority as signed
import materialize_production_core_v15_r3_execution_authority as issuer
import preflight_production_core_candidate_qualification_v15_r3 as gate
import project_production_core_candidate_qualification_v15_r3 as mechanics


def run(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
        terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
        output: Path, *, owner_authorized: bool) -> int:
    if not owner_authorized:
        raise ValueError("separate owner authorization for one R3 attempt required")
    if (output != issuer.R3_OUTPUT or output == issuer.R2_OUTPUT
            or not output.is_absolute() or output != output.resolve(strict=True)):
        raise ValueError("R3 output path substitution")
    receipt = gate.issue(recovery, private, backup, v13_terminal, terminal,
                         rootfs, snapshot, unicode_root, output)
    report = signed.audit(recovery, private, backup, v13_terminal, terminal,
                          rootfs, snapshot, unicode_root, output)
    authority = report["authority"]
    if (report["authority_identity"] != receipt["authority_identity"]
            or report["binding_identity"] != receipt["binding_identity"]
            or report["signature_identity"] != receipt["signature_identity"]):
        raise ValueError("R3 signed authority changed after fresh gate")
    protected = (issuer.ROOT, recovery, private, backup, v13_terminal, terminal,
                 rootfs, snapshot, unicode_root, issuer.R2_OUTPUT)
    gate.verify_receipt(receipt, authority, receipt, private, output, protected)
    namespace = mechanics.build_namespace({
        "boundary_identity": authority["authority_identity"],
        "source_sha256": authority["source_sha256"],
    })
    original_atomic = mechanics.predecessor.atomic_no_replace

    def guarded_atomic(path: Path, data: bytes) -> None:
        if path == output / "attempt.json":
            # This callback executes under the mechanics' exclusive output flock.
            repeated = signed.audit(recovery, private, backup, v13_terminal,
                                    terminal, rootfs, snapshot, unicode_root, output)
            if (repeated["authority_identity"] != receipt["authority_identity"]
                    or repeated["binding_identity"] != receipt["binding_identity"]
                    or repeated["signature_identity"] != receipt["signature_identity"]):
                raise ValueError("R3 authority drift before atomic claim")
            gate.verify_receipt(receipt, repeated["authority"], receipt,
                                private, output, protected)
        original_atomic(path, data)

    namespace["atomic"] = guarded_atomic
    previous = sys.argv
    try:
        sys.argv = [
            str(Path(__file__)), "--resolution", str(recovery / "v12-executor-resolution.json"),
            "--secret", str(private / "candidate-alias-secret-v13.json"),
            "--unicode-authority-root", str(unicode_root), "--output", str(output),
        ]
        return namespace["main"]()
    finally:
        sys.argv = previous


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs",
                 "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--consume-attempt", action="store_true", required=True)
    args = parser.parse_args()
    return run(args.recovery, args.private, args.backup, args.v13_terminal,
               args.terminal, args.rootfs, args.snapshot, args.unicode_root,
               args.output, owner_authorized=args.consume_attempt)


if __name__ == "__main__":
    raise SystemExit(main())
