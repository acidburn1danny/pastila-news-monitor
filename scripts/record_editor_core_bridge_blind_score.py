"""Fixture-testable, append-only blind scoring handoff. No model or answer key access."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from build_editor_core_editorial_mechanics_bridge import canonical, sha

PHASES = {"primary": ("editor-core-bridge-blind-development-packet", 72),
          "reference": ("editor-core-bridge-blind-development-reference", 24)}
RATINGS = {"PASS", "FAIL", "INDETERMINATE"}
WINNERS = {"X", "Y", "TIE", "INDETERMINATE"}


def _load(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or linked file")
    raw = path.read_bytes()
    obj = json.loads(raw)
    if raw != json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n":
        raise ValueError("noncanonical file")
    return obj


def _packet(path: Path, phase: str) -> dict:
    obj = _load(path)
    if (obj.get("schema") != PHASES[phase][0] or obj.get("schema_version") != 1
            or path.name != f"{obj.get('packet_id')}.json"):
        raise ValueError("packet schema or path")
    core = {k: v for k, v in obj.items() if k != "packet_identity"}
    if obj.get("packet_identity") != sha(canonical(core)):
        raise ValueError("packet identity")
    if phase == "primary" and [x.get("label") for x in obj.get("options", [])] != ["X", "Y"]:
        raise ValueError("options")
    return obj


def _score(score: dict, phase: str) -> None:
    expected = {"factual", "editorial", "romanian", "winner", "note"} if phase == "primary" else {"factual", "editorial", "romanian", "note"}
    if set(score) != expected:
        raise ValueError("score fields")
    labels = ("X", "Y") if phase == "primary" else ("R2",)
    for field in ("factual", "editorial", "romanian"):
        if set(score[field]) != set(labels) or any(v not in RATINGS for v in score[field].values()):
            raise ValueError("rating")
    if phase == "primary" and score["winner"] not in WINNERS:
        raise ValueError("winner")
    if not isinstance(score["note"], str) or len(score["note"]) > 2000:
        raise ValueError("note")
    if (any(v != "PASS" for v in score["factual"].values())
            or (phase == "primary" and score["winner"] == "INDETERMINATE")) and not score["note"].strip():
        raise ValueError("reason required")


def _validate_record(path: Path, packet_path: Path, phase: str, reviewer: str) -> dict:
    packet = _packet(packet_path, phase)
    obj = _load(path)
    core = {k: v for k, v in obj.items() if k != "record_identity"}
    if (set(obj) != {"schema", "schema_version", "phase", "reviewer_id", "packet_id",
                     "packet_identity", "packet_file_sha256", "score", "record_identity"}
            or obj["schema"] != "editor-core-bridge-blind-human-score" or obj["schema_version"] != 1
            or obj["phase"] != phase or obj["reviewer_id"] != reviewer
            or obj["packet_id"] != packet["packet_id"]
            or obj["packet_identity"] != packet["packet_identity"]
            or obj["packet_file_sha256"] != sha(packet_path.read_bytes())
            or obj["record_identity"] != sha(canonical(core))
            or path.name != f"{packet['packet_id']}.score.json"):
        raise ValueError("score binding or identity")
    _score(obj["score"], phase)
    return obj


def record(packet_path: Path, scores_root: Path, phase: str, reviewer: str, score: dict,
           *, primary_packets: Path | None = None, primary_scores: Path | None = None) -> dict:
    if phase not in PHASES or not reviewer or reviewer.strip() != reviewer or len(reviewer) > 100:
        raise ValueError("phase/reviewer")
    if scores_root.is_symlink() or not scores_root.is_dir():
        raise ValueError("scores root")
    if (scores_root / "closure.json").exists():
        raise ValueError("phase locked")
    if phase == "reference":
        if primary_packets is None or primary_scores is None:
            raise ValueError("primary closure required")
        reference_handoff(primary_packets, primary_scores, packet_path.parent, reviewer)
    packet = _packet(packet_path, phase)
    _score(score, phase)
    core = {"schema": "editor-core-bridge-blind-human-score", "schema_version": 1,
            "phase": phase, "reviewer_id": reviewer, "packet_id": packet["packet_id"],
            "packet_identity": packet["packet_identity"],
            "packet_file_sha256": sha(packet_path.read_bytes()), "score": score}
    obj = {**core, "record_identity": sha(canonical(core))}
    target = scores_root / f"{packet['packet_id']}.score.json"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    _validate_record(target, packet_path, phase, reviewer)
    return obj


def verify(packets_root: Path, scores_root: Path, phase: str, reviewer: str, *, lock: bool = False) -> dict:
    if phase not in PHASES or packets_root.is_symlink() or scores_root.is_symlink():
        raise ValueError("phase/root")
    if (not packets_root.is_dir() or not scores_root.is_dir()
            or packets_root.resolve() == scores_root.resolve()
            or packets_root.resolve() in scores_root.resolve().parents
            or scores_root.resolve() in packets_root.resolve().parents):
        raise ValueError("separation")
    packets = sorted(packets_root.iterdir())
    if len(packets) != PHASES[phase][1] or any(p.suffix != ".json" for p in packets):
        raise ValueError("packet inventory")
    ids = [_packet(p, phase)["packet_id"] for p in packets]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate packet")
    expected = {f"{packet_id}.score.json" for packet_id in ids}
    actual = {p.name for p in scores_root.iterdir()}
    if actual not in (expected, expected | {"closure.json"}):
        raise ValueError("incomplete/extra/duplicate scores")
    records = [_validate_record(scores_root / f"{packet_id}.score.json", packet, phase, reviewer)
               for packet, packet_id in zip(packets, ids, strict=True)]
    core = {"schema": "editor-core-bridge-blind-score-closure", "schema_version": 1,
            "phase": phase, "reviewer_id": reviewer, "count": len(records),
            "record_identities": sorted(r["record_identity"] for r in records),
            "packet_file_sha256": sorted(sha(p.read_bytes()) for p in packets)}
    closure = {**core, "closure_identity": sha(canonical(core))}
    closure_path = scores_root / "closure.json"
    if closure_path.exists():
        if _load(closure_path) != closure:
            raise ValueError("closure mutation")
    elif lock:
        fd = os.open(closure_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps(closure, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        for path in scores_root.iterdir():
            path.chmod(0o400)
        if os.name == "posix":
            scores_root.chmod(0o500)
    return closure


def reference_handoff(primary_packets: Path, primary_scores: Path, reference_packets: Path,
                      reviewer: str) -> dict:
    closure = verify(primary_packets, primary_scores, "primary", reviewer)
    if not (primary_scores / "closure.json").exists():
        raise ValueError("primary not irreversibly locked")
    if reference_packets.resolve() in (primary_packets.resolve(), primary_scores.resolve()):
        raise ValueError("reference separation")
    packets = list(reference_packets.iterdir())
    if len(packets) != 24:
        raise ValueError("reference inventory")
    for path in packets:
        _packet(path, "reference")
    return {"primary_closure_identity": closure["closure_identity"], "reference_count": 24,
            "reference_packet_file_sha256": sorted(sha(p.read_bytes()) for p in packets)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("verify", "lock", "reference-handoff"))
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--phase", choices=tuple(PHASES), default="primary")
    parser.add_argument("--reference-packets", type=Path)
    args = parser.parse_args()
    if args.action == "reference-handoff":
        if args.reference_packets is None:
            parser.error("--reference-packets required")
        result = reference_handoff(args.packets, args.scores, args.reference_packets, args.reviewer)
    else:
        result = verify(args.packets, args.scores, args.phase, args.reviewer, lock=args.action == "lock")
    print(json.dumps(result, sort_keys=True))
