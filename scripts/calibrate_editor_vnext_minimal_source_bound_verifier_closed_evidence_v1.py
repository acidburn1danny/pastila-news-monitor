"""Calibrate the published minimal verifier using closed, immutable evidence only."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_identity(value: dict, key: str) -> None:
    core = {name: item for name, item in value.items() if name != key}
    if value.get(key) != digest(canonical(core)):
        raise ValueError(f"identity mismatch: {key}")


def load_verifier(path: Path):
    spec = importlib.util.spec_from_file_location("minimal_verifier", path)
    if spec is None or spec.loader is None:
        raise ValueError("verifier import failed")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def verify_packet(packet: dict) -> None:
    verify_identity(packet, "packet_identity")
    seen: set[str] = set()
    for span in packet["spans"]:
        if span["span_id"] in seen:
            raise ValueError("duplicate source span")
        seen.add(span["span_id"])
        raw = span["text"].encode()
        if digest(raw) != span["sha256"] or raw[span["byte_start"]:span["byte_end"]] != raw:
            raise ValueError("source packet byte binding failure")


def domain(failure_class: str) -> str:
    if "NUMERIC" in failure_class:
        return "NUMERIC"
    if failure_class in {"INVENTED_ACTOR", "ENTITY_SUBSTITUTION"}:
        return "ACTOR_ENTITY"
    if any(x in failure_class for x in ("QUALIFICATION", "MODALITY", "ALLEGATION", "ATTRIBUTED", "PROCEDURAL")):
        return "QUALIFICATION_STATUS"
    return "OTHER"


def run(closed: dict, verifier) -> dict:
    verify_identity(closed, "input_identity")
    if len(closed["rows"]) != 48:
        raise ValueError("closed evidence inventory mismatch")
    if len({item["case_id"] for item in closed["rows"]}) != 48:
        raise ValueError("duplicate closed evidence case")
    rows, by_class, by_domain = [], defaultdict(Counter), defaultdict(Counter)
    verdicts, changes = Counter(), Counter()
    false_rejections, true_failures, observed_misses = [], [], []
    fallback = abstain = 0
    for item in closed["rows"]:
        packet = item["source_packet"]
        verify_packet(packet)
        score = item["human_score_receipt"]
        if (score["case_id"] != item["case_id"] or score["pack_identity"] != closed["provenance"]["closed_pack_identity"]
                or score["receipt_identity"] not in closed["provenance"]["blind_closure_receipts"]):
            raise ValueError(f"human score closure mismatch: {item['case_id']}")
        selected_score = score["scores"][item["blind_label"]]
        source = "\n".join(span["text"] for span in packet["spans"])
        raw = json.dumps({"case_id": item["case_id"], "text": item["r2_output"]}, ensure_ascii=False, separators=(",", ":"))
        if digest(item["r2_output"].encode()) != item["r2_output_sha256"]:
            raise ValueError(f"closed output drift: {item['case_id']}")
        result = verifier.verify(source, raw, item["case_id"])
        verdict = result["verdict"]; verdicts[verdict] += 1
        by_class[item["failure_class"]][verdict] += 1; by_domain[domain(item["failure_class"])][verdict] += 1
        human_safe = selected_score["factual_safety"] == "PASS"
        if not human_safe:
            true_failures.append(item["case_id"])
            if verdict == "PASS_PROVEN": observed_misses.append(item["case_id"])
        if human_safe and verdict == "FAIL_PROVEN": false_rejections.append(item["case_id"])
        route = "ACCEPT"
        if verdict != "PASS_PROVEN":
            route = verifier.fallback(source)["route"]
            fallback += route == "SOURCE_PRESERVING_FALLBACK"; abstain += route == "ABSTAIN"
        same = item["r2_output_sha256"] == item["prior_v0"]["text_sha256"]
        if not same:
            cause = "EVIDENCE_INSUFFICIENT_DIFFERENT_OUTPUT_BYTES"
        elif item["prior_v0"]["route"] != "ACCEPTED_R2" and verdict == "PASS_PROVEN" and human_safe:
            cause = "CORRECTED_FALSE_REJECTION"
        elif verdict == "FAIL_PROVEN" and not human_safe:
            cause = "NEWLY_DETECTED_TRUE_FAILURE"
        elif verdict == "UNPROVEN":
            cause = "STILL_UNPROVEN"
        else:
            cause = "OTHER_DEMONSTRATED_FINDING"
        changes[cause] += 1
        rows.append({"case_id": item["case_id"], "failure_class": item["failure_class"], "domain": domain(item["failure_class"]),
                     "verdict": verdict, "route": route, "human_factual_safety": selected_score["factual_safety"],
                     "human_factual_sufficiency": selected_score["factual_sufficiency"], "prior_v0_route": item["prior_v0"]["route"],
                     "same_output_bytes_as_prior_v0": same, "change_cause": cause, "finding_codes": [x["code"] for x in result["findings"]],
                     "receipt_identity": result["receipt_identity"], "output_sha256": item["r2_output_sha256"]})
    prior_fallback = sum(x["prior_v0"]["route"] != "ACCEPTED_R2" for x in closed["rows"])
    miss_estimable = bool(true_failures)
    limits = list(closed["evidence_limits"])
    if not miss_estimable:
        limits.append("VERIFIER_MISS_RATE_NOT_ESTIMABLE_NO_HUMAN_NEGATIVE_OUTPUTS")
    core = {
        "schema": "editor-vnext-minimal-source-bound-verifier-closed-calibration-result", "schema_version": 1,
        "status": "PASS_WITH_EVIDENCE_LIMITATIONS", "decision": "REVISE_BEFORE_ACTIVE_INTEGRATION",
        "input_identity": closed["input_identity"], "rows": rows, "verdict_distribution": dict(verdicts),
        "true_model_failures_demonstrated": true_failures, "false_rejections": false_rejections,
        "observed_verifier_misses": observed_misses, "verifier_miss_rate_estimable": miss_estimable,
        "evidence_limitations": limits, "change_cause_distribution": dict(changes),
        "fallback_comparison": {"prior_v0_count": prior_fallback, "prior_v0_rate": prior_fallback / 48,
            "calibrated_count": fallback, "calibrated_rate": fallback / 48, "abstention_count": abstain,
            "abstention_rate": abstain / 48, "delta_count": fallback - prior_fallback, "delta_rate": (fallback - prior_fallback) / 48,
            "causal_comparison_valid": all(x["same_output_bytes_as_prior_v0"] for x in rows)},
        "by_failure_class": {key: dict(value) for key, value in sorted(by_class.items())},
        "by_domain": {key: dict(value) for key, value in sorted(by_domain.items())},
        "active_vnext_integrated": False, "legacy_dependency_count": 0, "model_loaded": False,
        "inference_performed": False, "training_performed": False, "optimizer_created": False,
    }
    core["result_identity"] = digest(canonical(core))
    return core


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--evidence", type=Path, required=True); parser.add_argument("--verifier", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError("output must be new")
    closed = json.loads(args.evidence.read_text(encoding="utf-8")); result = run(closed, load_verifier(args.verifier))
    args.output.mkdir(parents=True); (args.output / "result.json").write_bytes(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    print(json.dumps({key: result[key] for key in ("status", "decision", "verdict_distribution", "fallback_comparison", "change_cause_distribution", "result_identity")}, sort_keys=True))


if __name__ == "__main__": main()
