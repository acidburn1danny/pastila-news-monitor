"""Fail-closed one-shot supervisor for the seven successor inference slots."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

CANDIDATES = ("r2", "a1-seed-271828", "a1-seed-314159", "a1-seed-161803",
              "a2-seed-271828", "a2-seed-314159", "a2-seed-161803")


class Journal:
    def __init__(self, root: Path):
        self.root = root
        self.terminal = False

    def write(self, event: str, **fields: object) -> None:
        if self.terminal:
            raise RuntimeError("terminal event already written")
        row = {"event": event, "time_unix": int(time.time()), **fields}
        with (self.root / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        if event == "PROGRAM_END":
            self.terminal = True


def execute(args: argparse.Namespace) -> dict:
    os.umask(0o077)
    for root in (args.output_root, args.scoring_root, args.log_root):
        if root.exists():
            raise RuntimeError(f"refuse existing root: {root}")
    args.output_root.mkdir(mode=0o700)
    args.log_root.mkdir(mode=0o700)
    journal = Journal(args.log_root)
    try:
        authority = json.loads(args.authority.read_bytes())
        if authority.get("authority_identity") != args.authority_identity:
            raise RuntimeError("authority identity")
        journal.write("PROGRAM_START", authority_identity=args.authority_identity)
        environment = dict(os.environ, BRIDGE_CAUSAL_INFERENCE_OWNER_AUTHORIZED="1")
        for candidate in CANDIDATES:
            target = args.output_root / candidate
            target.mkdir(mode=0o700)
            journal.write("SLOT_START", candidate=candidate)
            adapter = args.parent_adapter if candidate == "r2" else args.training_root / candidate / "adapter"
            with (args.log_root / f"{candidate}.log").open("xb") as log:
                result = subprocess.run(["bash", str(args.route), str(args.rootfs), str(args.model),
                                         str(adapter), str(args.requests), str(target), candidate,
                                         str(args.worker), "--inference-authorized"],
                                        env=environment, stdout=log, stderr=subprocess.STDOUT)
            journal.write("SLOT_END", candidate=candidate, returncode=result.returncode)
            if result.returncode:
                raise RuntimeError(f"slot failed: {candidate}")

        sys.path.insert(0, str(args.repository / "scripts"))
        from audit_editor_core_bridge_causal_responses_v3 import audit
        from prepare_editor_core_bridge_blind_scoring import audit_prepared, prepare
        identities = {row["candidate"]: row["adapter_sha256"] for row in authority["candidates"]}
        inference = audit(args.output_root, args.requests, identities)
        args.scoring_root.mkdir(mode=0o700)
        responses, primary, reference, custody = (args.scoring_root / name for name in
                                                   ("responses", "primary", "reference", "custody"))
        for root in (responses, primary, reference, custody):
            root.mkdir(mode=0o700)
        for candidate in CANDIDATES:
            shutil.copyfile(args.output_root/candidate/"responses.jsonl", responses/f"{candidate}.jsonl")
        prepared = prepare(responses, primary, reference, custody)
        audited = audit_prepared(primary, reference, custody)
        terminal = {"status": "PASS", "inference": inference, "prepared": prepared, "audited": audited}
        (args.log_root / "terminal.json").write_text(json.dumps(terminal, sort_keys=True, indent=2)+"\n")
        journal.write("PROGRAM_END", status="PASS")
        return terminal
    except Exception as exc:
        if not journal.terminal:
            journal.write("PROGRAM_END", status="BLOCKED", error=repr(exc))
        raise


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    for name in ("repository", "authority", "route", "worker", "rootfs", "model", "parent-adapter",
                 "training-root", "requests", "output-root", "scoring-root", "log-root"):
        value.add_argument(f"--{name}", type=Path, required=True)
    value.add_argument("--authority-identity", required=True)
    return value


if __name__ == "__main__":
    result = execute(parser().parse_args())
    print(json.dumps(result, sort_keys=True))
