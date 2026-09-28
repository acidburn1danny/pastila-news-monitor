"""Reproduce the closed-evidence taxonomy for frozen VOICE factual-drift stops."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

BOUNDARY_IDENTITY = "104252702c6bb27585e3615ffec0667aa519649a54275e641aeb7be826096d0e"
ANSWER_KEY_IDENTITY = "3d02d051b73d83ec9f208beda147dd9b2c18bcb284758acba9cf31f358cec0fb"
SCORING_CLOSURE_IDENTITY = "a94d44bcf6e677d62a7715a1631544e7f6659a59d277fd674e46bc51f25ac768"
FROZEN_RESULT_IDENTITY = "5f521de2625e73db9d6958536b57799b190a0583fc26e2c03fea1fbaf8923ea3"
FROZEN_RECEIPT_SET_SHA256 = "464104f272123c76270e4d2e5d3fc469c3d14a970685f0fe0aa17479e38b6888"

R2 = "V0_R2_MINISTRAL_CONTROL"
Q3 = "V1_QWEN3_8B_NON_THINKING"
Q25 = "V2_QWEN25_7B_INSTRUCT"
CANDIDATES = (R2, Q3, Q25)

CONCRETE = "UNSUPPORTED_CONCRETE_ADDITION_OR_STATE"
NUMERIC = "NUMERIC_OR_QUANTITATIVE_MUTATION"
EPISTEMIC = "EPISTEMIC_OR_PROCEDURAL_RECAST"
CAUSAL = "UNSUPPORTED_CAUSAL_OR_EVALUATIVE_ASSERTION"
FIGURATIVE = "FIGURATIVE_IMPLICATION_WITH_FACTUAL_READING"
LIMITATION = "EVIDENCE_LIMITATION"
CLASSES = (CONCRETE, NUMERIC, EPISTEMIC, CAUSAL, FIGURATIVE, LIMITATION)

# Closed after source-bound comparison of immutable factual_setup/commentary pairs.
# This map classifies existing STOP receipts; it never changes their verdict.
TAXONOMY = {
    (R2, "VOICE-V1-01"): FIGURATIVE,
    (R2, "VOICE-V1-08"): CONCRETE,
    (R2, "VOICE-V1-09"): FIGURATIVE,
    (R2, "VOICE-V1-10"): FIGURATIVE,
    (R2, "VOICE-V1-12"): NUMERIC,
    (R2, "VOICE-V1-13"): CAUSAL,
    (R2, "VOICE-V1-15"): CONCRETE,
    (R2, "VOICE-V1-19"): NUMERIC,
    (R2, "VOICE-V1-22"): NUMERIC,
    (Q3, "VOICE-V1-03"): EPISTEMIC,
    (Q3, "VOICE-V1-05"): CONCRETE,
    (Q3, "VOICE-V1-08"): CONCRETE,
    (Q3, "VOICE-V1-09"): FIGURATIVE,
    (Q3, "VOICE-V1-10"): CAUSAL,
    (Q3, "VOICE-V1-11"): EPISTEMIC,
    (Q3, "VOICE-V1-12"): CAUSAL,
    (Q3, "VOICE-V1-13"): CAUSAL,
    (Q3, "VOICE-V1-14"): CONCRETE,
    (Q3, "VOICE-V1-16"): CONCRETE,
    (Q3, "VOICE-V1-18"): LIMITATION,
    (Q3, "VOICE-V1-19"): LIMITATION,
    (Q3, "VOICE-V1-21"): CONCRETE,
    (Q3, "VOICE-V1-23"): EPISTEMIC,
    (Q3, "VOICE-V1-24"): CONCRETE,
    (Q25, "VOICE-V1-11"): CAUSAL,
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def identity(value: dict, field: str) -> str:
    return hashlib.sha256(canonical({k: v for k, v in value.items() if k != field})).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt_set_sha256(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def derive_blind_identity(output: dict) -> str:
    return hashlib.sha256(
        canonical(
            {
                "receipt_identity": output["receipt_identity"],
                "slot_identity": output["slot_identity"],
            }
        )
    ).hexdigest()


def aggregate_bytes(paths: list[Path], base: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative = path.relative_to(base).as_posix()
        digest.update(relative.encode("utf-8") + b"\0" + file_sha256(path).encode("ascii") + b"\0")
    return digest.hexdigest()


def analyze(repo: Path, run: Path, review: Path) -> dict:
    terminal_path = repo / "docs/artifacts/editor-vnext-voice-blind-review-terminal-result-v1.json"
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    assert terminal["unsealed_result_identity"] == FROZEN_RESULT_IDENTITY
    assert identity(terminal, "unsealed_result_identity") == FROZEN_RESULT_IDENTITY
    assert terminal["overall_verdict"] == "STOP_ALL_CANDIDATES"
    assert terminal["selected_candidate"] is None
    assert terminal["boundary_identity"] == BOUNDARY_IDENTITY
    assert terminal["answer_key_identity"] == ANSWER_KEY_IDENTITY
    assert terminal["scoring_closure_identity"] == SCORING_CLOSURE_IDENTITY
    assert terminal["legacy_dependency_count"] == 0

    boundary_path = review / "editor-vnext-voice-blind-review-scoring-boundary-v1.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    assert boundary["review_boundary_identity"] == BOUNDARY_IDENTITY
    assert identity(boundary, "review_boundary_identity") == BOUNDARY_IDENTITY

    completion_path = review / "review-completion.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    assert completion["scoring_closure_identity"] == SCORING_CLOSURE_IDENTITY
    assert identity(completion, "scoring_closure_identity") == SCORING_CLOSURE_IDENTITY

    item_path = review / "editor-vnext-voice-blind-review-items-v1.jsonl"
    items = {
        row["blind_output_identity"]: row
        for row in (json.loads(line) for line in item_path.read_bytes().splitlines())
    }
    receipt_paths = sorted((review / "receipts").glob("*.json"))
    receipts = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in receipt_paths}
    assert len(items) == len(receipts) == 216
    assert receipt_set_sha256(receipt_paths) == FROZEN_RECEIPT_SET_SHA256
    for blind, receipt in receipts.items():
        assert blind == receipt["blind_output_identity"]
        assert receipt["review_boundary_identity"] == BOUNDARY_IDENTITY
        assert receipt["reviewer_receipt_identity"] == identity(receipt, "reviewer_receipt_identity")

    rows = []
    output_paths = []
    for candidate in CANDIDATES:
        candidate_outputs = sorted((run / candidate / "outputs").glob("**/*.json"))
        assert len(candidate_outputs) == 72
        for path in candidate_outputs:
            output_paths.append(path)
            output = json.loads(path.read_text(encoding="utf-8"))
            assert output["candidate_receipt"]["candidate_id"] == candidate
            blind = derive_blind_identity(output)
            item = items[blind]
            receipt = receipts[blind]
            assert receipt["case_identity"] == item["case_identity"]
            assert receipt["seed_alias"] == item["seed_alias"]
            rows.append(
                {
                    "candidate": candidate,
                    "case_id": item["case_id"],
                    "seed": path.parts[-2],
                    "blind_output_identity": blind,
                    "factual_safety": receipt["factual_safety"],
                    "factual_setup": item["factual_setup"],
                    "commentary": item["commentary"],
                }
            )
    assert len(rows) == len(output_paths) == 216

    stops = [row for row in rows if row["factual_safety"] == "STOP_FACTUAL_DRIFT"]
    assert len(stops) == 74
    per_candidate = Counter(row["candidate"] for row in stops)
    assert per_candidate == Counter({R2: 27, Q3: 44, Q25: 3})

    classified = []
    for row in stops:
        key = (row["candidate"], row["case_id"])
        assert key in TAXONOMY
        classified.append({**row, "taxonomy_class": TAXONOMY[key]})
    taxonomy_total = Counter(row["taxonomy_class"] for row in classified)
    expected_total = Counter(
        {CONCRETE: 24, NUMERIC: 9, EPISTEMIC: 9, CAUSAL: 15, FIGURATIVE: 12, LIMITATION: 5}
    )
    assert taxonomy_total == expected_total

    taxonomy_per_candidate = {}
    for candidate in CANDIDATES:
        counts = Counter(row["taxonomy_class"] for row in classified if row["candidate"] == candidate)
        taxonomy_per_candidate[candidate] = {name: counts.get(name, 0) for name in CLASSES}

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["candidate"], row["case_id"], row["commentary"])].append(row)
    mixed = []
    for (candidate, case_id, commentary), group in grouped.items():
        labels = Counter(row["factual_safety"] for row in group)
        if labels.get("STOP_FACTUAL_DRIFT") and len(labels) > 1:
            mixed.append(
                {
                    "candidate": candidate,
                    "case_id": case_id,
                    "commentary_sha256": hashlib.sha256(commentary.encode("utf-8")).hexdigest(),
                    "labels": dict(sorted(labels.items())),
                    "receipts": sorted(
                        row["blind_output_identity"]
                        for row in group
                        if row["factual_safety"] == "STOP_FACTUAL_DRIFT"
                    ),
                }
            )
    assert len(mixed) == 1
    assert mixed[0]["candidate"] == Q3 and mixed[0]["case_id"] == "VOICE-V1-18"
    assert mixed[0]["labels"] == {"PASS": 1, "STOP_FACTUAL_DRIFT": 2}

    limitation_rows = [row for row in classified if row["taxonomy_class"] == LIMITATION]
    assert len(limitation_rows) == 5
    limitation_receipts = sorted(row["blind_output_identity"] for row in limitation_rows)

    pattern_counts = Counter(TAXONOMY.values())
    assert sum(pattern_counts.values()) == 25
    immutable = {
        "review_items_sha256": file_sha256(item_path),
        "receipt_set_sha256": receipt_set_sha256(receipt_paths),
        "completion_sha256": file_sha256(completion_path),
        "boundary_sha256": file_sha256(boundary_path),
        "inference_output_set_sha256": aggregate_bytes(output_paths, run),
        "terminal_result_file_sha256": file_sha256(terminal_path),
    }
    core = {
        "schema": "editor-vnext-voice-stop-factual-drift-closed-evidence-taxonomy",
        "schema_version": 1,
        "status": "PASS_WITH_EVIDENCE_LIMITATION",
        "bindings": {
            "review_boundary_identity": BOUNDARY_IDENTITY,
            "answer_key_identity": ANSWER_KEY_IDENTITY,
            "scoring_closure_identity": SCORING_CLOSURE_IDENTITY,
            "frozen_terminal_result_identity": FROZEN_RESULT_IDENTITY,
        },
        "closed_evidence": {
            "review_items": 216,
            "score_receipts": 216,
            "inference_outputs": 216,
            "stop_factual_drift": 74,
            "per_candidate": {candidate: per_candidate[candidate] for candidate in CANDIDATES},
            "distinct_candidate_case_patterns": len(TAXONOMY),
            "immutable_identities": immutable,
        },
        "taxonomy": {
            "classes": list(CLASSES),
            "receipt_weighted_total": {name: taxonomy_total.get(name, 0) for name in CLASSES},
            "receipt_weighted_per_candidate": taxonomy_per_candidate,
            "distinct_pattern_total": {name: pattern_counts.get(name, 0) for name in CLASSES},
            "evidence_limitation_receipts": limitation_receipts,
            "mixed_label_byte_identical_groups": mixed,
        },
        "claims": {
            "demonstrated": [
                "69_OF_74_STOPS_HAVE_SOURCE_BOUND_OBSERVABLE_TRIGGER",
                "72_OF_74_STOPS_BELONG_TO_UNANIMOUS_THREE_SEED_STOP_GROUPS",
                "NUMERIC_MUTATION_IS_R2_SPECIFIC_IN_THIS_COHORT",
                "EPISTEMIC_PROCEDURAL_RECAST_IS_QWEN3_SPECIFIC_IN_THIS_COHORT",
            ],
            "suggested": [
                "ONE_PASS_COMMENTARY_BLURS_FACTUAL_ANCHORS_AND_RHETORICAL_REALIZATION",
                "R2_CREATIVE_EXTRAPOLATION_AND_QWEN3_GENERALIZATION_ARE_DISTINCT_FAILURE_MODES",
            ],
            "undetermined": [
                "REVIEWER_RATIONALE_FOR_EACH_STOP",
                "FALSE_REJECTION_RATE_FOR_FIGURATIVE_COMMENTARY",
                "INTERNAL_MODEL_CAUSE",
            ],
        },
        "frozen_state": {
            "overall_verdict": "STOP_ALL_CANDIDATES",
            "selected_candidate": None,
            "receipts_modified": False,
            "scores_modified": False,
            "verdicts_modified": False,
            "inference_outputs_modified": False,
            "rescoring": False,
            "new_inference": False,
            "legacy_dependency_count": 0,
        },
    }
    return {**core, "taxonomy_result_identity": hashlib.sha256(canonical(core)).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.repo, args.run, args.review)
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    if args.output:
        args.output.write_bytes(payload)
    print(
        json.dumps(
            {
                "status": result["status"],
                "stops": result["closed_evidence"]["stop_factual_drift"],
                "identity": result["taxonomy_result_identity"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
