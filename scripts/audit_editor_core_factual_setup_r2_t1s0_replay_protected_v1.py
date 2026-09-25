from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
P = "editor-core-factual-setup-r2-t1s0-replay-protected-v1"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text("utf-8").splitlines() if x]


def ident(value: dict, field: str) -> str:
    core = dict(value); core.pop(field, None)
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_span(assistant: str, span: dict) -> None:
    assert span["field"] == "text"
    assert assistant[span["start"]:span["end"]] == span["text"]
    assert span["text"] == json.loads(assistant)["text"]


def validate_protocol(protocol: dict, recipes: dict, evaluation: dict) -> None:
    assert protocol["parent"] == "R2_STEP_9" and protocol["seeds"] == [161803, 271828, 314159]
    assert protocol["fixed"]["recipe_level"] == "S0_CONTROL"
    assert protocol["fixed"]["learning_rate"] == recipes["levels"]["S0_CONTROL"]["learning_rate"] == "0.0000005"
    assert protocol["fixed"]["evaluator_identity"] == evaluation["evaluation_identity"]
    assert protocol["single_causal_difference"] == "CRITICAL_SPAN_WEIGHTING_ADDED_TO_24_REPLAY_TEXT_VALUES"
    assert protocol["common_repetition_gate"]["applies_identically_to_both_arms"] is True
    assert protocol["real_runs_authorized"] is False and protocol["training_authorized"] is False
    assert protocol["parent_selection_authority"] is False and protocol["historical_holdouts_allowed"] is False


def audit(art: Path) -> dict:
    source = load_jsonl(art / "editor-core-factual-setup-corrective-v1-training.jsonl")
    control = load_jsonl(art / "editor-core-factual-setup-r2-causal-diagnostic-v1-challenger-signal.jsonl")
    protected_path = art / f"{P}-protected-signal.jsonl"
    protected = load_jsonl(protected_path)
    protocol = load_json(art / f"{P}-protocol.json")
    manifest = load_json(art / f"{P}-manifest.json")
    recipes = load_json(art / "editor-core-factual-setup-r2-causal-diagnostic-v1-recipes.json")
    evaluation = load_json(art / "editor-core-factual-setup-r2-causal-diagnostic-v1-evaluation.json")
    assert len(source) == len(control) == len(protected) == 72
    source_by_id = {x["example_id"]: x for x in source}
    changed = 0; targeted_same = 0; replay_protected = 0; span_count = 0
    coverage: dict[str, int] = {}
    for old, new in zip(control, protected, strict=True):
        assert old["example_id"] == new["example_id"]
        assert old["assistant_target_sha256"] == new["assistant_target_sha256"]
        assistant = source_by_id[old["example_id"]]["messages"][-1]["content"]
        assert hashlib.sha256(assistant.encode()).hexdigest() == old["assistant_target_sha256"]
        if old["split"] == "CORRECTIVE_TARGETED":
            assert old == new; targeted_same += 1
        else:
            changed += old != new
            replay_protected += 1
            assert old["critical_spans"] == [] and new["critical_weight"] == "3.0"
            assert new["signal"] == "CONTRACT_CRITICAL_SPAN_WEIGHTED_REPLAY_PROTECTION"
            assert len(new["critical_spans"]) == 1
            span = new["critical_spans"][0]
            validate_span(assistant, span)
            payload = json.loads(assistant)
            assert 2 <= len([x for x in payload["text"].split(".") if x.strip()]) <= 3
            assert span["text"] not in (old["example_id"], old["failure_class"])
            coverage[new["replay_protection"]] = coverage.get(new["replay_protection"], 0) + 1
            span_count += 1
    assert (targeted_same, changed, replay_protected, span_count) == (48, 24, 24, 24)
    assert coverage == {"ACTOR_FIDELITY": 8, "EPISTEMIC_QUALIFICATION": 8, "NUMERIC_RECONCILIATION": 4, "PROCEDURAL_STATUS": 4}
    assert protocol["protocol_identity"] == ident(protocol, "protocol_identity")
    assert manifest["pack_identity"] == ident(manifest, "pack_identity")
    validate_protocol(protocol, recipes, evaluation)
    assert manifest["protected_signal_sha256"] == hashlib.sha256(protected_path.read_bytes()).hexdigest()
    return {"status":"PASS","blockers":0,"protocol_identity":protocol["protocol_identity"],"pack_identity":manifest["pack_identity"],"rows":72,"targeted_rows_byte_identical":48,"replay_rows_protected":24,"critical_spans":24,"coverage":coverage,"training_performed":False,"historical_holdouts_read":False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--art-dir", type=Path, default=ART)
    args = parser.parse_args()
    print(json.dumps(audit(args.art_dir), sort_keys=True))


if __name__ == "__main__":
    main()
