"""Prepare candidate-blinded development scoring packets; never reads answer keys."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Callable

from build_editor_core_editorial_mechanics_bridge import ART, PREFIX, canonical, compact, sha
from project_editor_core_bridge_causal_runs import SEEDS

SLUGS = tuple(f"{arm.lower()}-seed-{seed}" for arm in ("A1", "A2") for seed in SEEDS)


def read_responses(path: Path, expected: dict[str, str]) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("response file")
    raw = path.read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("response truncation")
    rows = [json.loads(line) for line in raw.splitlines()]
    if (len(rows) != 24 or any(compact(row).encode("utf-8") != line
                               for row, line in zip(rows, raw.splitlines(), strict=True))):
        raise ValueError("response count or canonical bytes")
    if (set(row.get("case_id") for row in rows) != set(expected)
            or len({row["case_id"] for row in rows}) != 24):
        raise ValueError("response case inventory")
    for row in rows:
        if (set(row) != {"case_id", "request_identity", "response"}
                or row["request_identity"] != expected[row["case_id"]]
                or not isinstance(row["response"], str) or not row["response"]):
            raise ValueError("response request binding")
    return {row["case_id"]: row["response"] for row in rows}


def prepare(responses_root: Path, packets_root: Path, reference_root: Path, custody_root: Path,
            *, permutation: Callable[[], list[int]] | None = None) -> dict:
    """Separate A1/A2 pairs, later R2 reference and the sealed arm map."""
    for root in (responses_root, packets_root, reference_root, custody_root):
        if root.is_symlink() or not root.is_dir():
            raise ValueError("scoring root")
    roots = [root.resolve() for root in (responses_root, packets_root, reference_root, custody_root)]
    if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(roots)
           for b in roots[i + 1:]):
        raise ValueError("scoring/custody separation")
    if os.name == "posix" and any(stat.S_IMODE(root.stat().st_mode) != 0o700
                                  for root in (reference_root, custody_root)):
        raise ValueError("reference/custody permissions")
    if any(packets_root.iterdir()) or any(reference_root.iterdir()) or any(custody_root.iterdir()):
        raise ValueError("scoring output overwrite")
    source = ART / f"{PREFIX}-development-requests.jsonl"
    requests = [json.loads(line) for line in source.read_bytes().splitlines()]
    expected = {row["example_id"]: json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])["request_identity"]
                for row in requests}
    if len(expected) != 24 or any(row["split"] != "DEVELOPMENT" or len(row["messages"]) != 2 for row in requests):
        raise ValueError("development source scope")
    if {p.name for p in responses_root.iterdir()} != {"r2.jsonl", *(f"{slug}.jsonl" for slug in SLUGS)}:
        raise ValueError("response file closure")
    outputs = {name: read_responses(responses_root / name, expected)
               for name in ("r2.jsonl", *(f"{slug}.jsonl" for slug in SLUGS))}
    mappings = []
    packet_hashes = []
    reference_hashes = []
    for row in requests:
        case_id = row["example_id"]
        request = json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])
        for seed in SEEDS:
            items = [("A1", outputs[f"a1-seed-{seed}.jsonl"][case_id]),
                     ("A2", outputs[f"a2-seed-{seed}.jsonl"][case_id])]
            order = permutation() if permutation else secrets.SystemRandom().sample(range(2), 2)
            if sorted(order) != [0, 1]:
                raise ValueError("blinding permutation")
            labels = ("X", "Y")
            options = [{"label": label, "response": items[index][1]}
                       for label, index in zip(labels, order, strict=True)]
            core = {"schema": "editor-core-bridge-blind-development-packet", "schema_version": 1,
                    "packet_id": sha(canonical([case_id, seed, options]))[:32],
                    "operator": row["operator"], "request": request, "options": options}
            packet = {**core, "packet_identity": sha(canonical(core))}
            if any(value in canonical(packet).decode("utf-8") for value in ("A1", "A2", "R2_STEP_9", "holdout-answer-key")):
                raise ValueError("candidate identity leakage")
            packet_path = packets_root / f"{packet['packet_id']}.json"
            packet_path.write_bytes(json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
            packet_hashes.append(sha(packet_path.read_bytes()))
            mappings.append({"packet_id": packet["packet_id"], "packet_identity": packet["packet_identity"],
                             "case_id": case_id, "seed": seed,
                             "arms_by_label": {label: items[index][0] for label, index in zip(labels, order, strict=True)}})
        reference_core = {"schema": "editor-core-bridge-blind-development-reference", "schema_version": 1,
                          "packet_id": sha(canonical([case_id, "reference", outputs["r2.jsonl"][case_id]]))[:32],
                          "operator": row["operator"], "request": request,
                          "response": outputs["r2.jsonl"][case_id]}
        reference = {**reference_core, "packet_identity": sha(canonical(reference_core))}
        reference_path = reference_root / f"{reference['packet_id']}.json"
        reference_path.write_bytes(json.dumps(reference, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
        reference_hashes.append(sha(reference_path.read_bytes()))
        mappings.append({"packet_id": reference["packet_id"], "packet_identity": reference["packet_identity"],
                         "case_id": case_id, "arm": "R2", "reference_after_primary_lock_only": True})
    mapping_core = {"schema": "editor-core-bridge-blind-scoring-custody", "schema_version": 1,
                    "packets": mappings, "primary_packet_file_hashes": packet_hashes,
                    "reference_packet_file_hashes": reference_hashes,
                    "development_requests_sha256": sha(source.read_bytes())}
    mapping = {**mapping_core, "custody_identity": sha(canonical(mapping_core))}
    sealed = custody_root / "sealed-arm-map.json"
    descriptor = os.open(sealed, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(json.dumps(mapping, sort_keys=True, indent=2).encode() + b"\n")
    return {"primary_pair_packets": len(packet_hashes), "later_reference_packets": len(reference_hashes),
            "custody_identity": mapping["custody_identity"], "candidate_blinded": True,
            "reference_separate_until_primary_lock": True, "answer_key_read": False, "holdout_read": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses-root", type=Path, required=True)
    parser.add_argument("--packets-root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--custody-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.responses_root, args.packets_root, args.reference_root,
                             args.custody_root), sort_keys=True))
