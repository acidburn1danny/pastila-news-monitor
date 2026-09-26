"""CAR successor runtime for the anchored contrastive safety diagnostic."""
from __future__ import annotations

# The published v1 runtime remains immutable failure evidence.  Reuse its
# stable primitives, then override only the preparation and failure boundary.
import hashlib
import json
import os
from pathlib import Path

import editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1 as legacy
from editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1 import *  # noqa: F403


def validate_training_mapping(tokenizer, corpus_path: Path, annotations_path: Path,
                              pairs_path: Path, retention_path: Path) -> dict:
    corpus = [json.loads(x) for x in corpus_path.read_text(encoding="utf-8").splitlines() if x]
    annotations = {x["example_id"]: x for x in (json.loads(y) for y in annotations_path.read_text(encoding="utf-8").splitlines() if y)}
    pairs = {x["example_id"] for x in (json.loads(y) for y in pairs_path.read_text(encoding="utf-8").splitlines() if y)}
    replay = {x["example_id"] for x in (json.loads(y) for y in retention_path.read_text(encoding="utf-8").splitlines() if y)}
    rows = {x["example_id"]: x for x in corpus}
    if len(rows) != 72 or len(annotations) != 72 or len(pairs) != 48 or len(replay) != 24 or set(rows) != pairs | replay:
        raise ValueError("training partition inventory")
    mapped = 0
    for eid, row in rows.items():
        spans = annotations[eid]["critical_spans"]
        if eid in replay:
            if spans:
                raise ValueError(f"replay critical spans forbidden:{eid}")
            continue
        if not spans:
            raise ValueError(f"corrective critical spans required:{eid}")
        try:
            selected = legacy._chat_span_tokens(tokenizer, row["messages"], spans)
        except Exception as exc:
            raise ValueError(f"critical mapping failure:{eid}:{exc}") from exc
        if not selected:
            raise ValueError(f"corrective critical token coverage empty:{eid}")
        mapped += 1
    return {"training_rows": 72, "corrective_rows": 48, "replay_rows": 24,
            "corrective_nonempty_token_mappings": mapped, "replay_empty_span_rows": 24}


class SlotFailure(RuntimeError):
    def __init__(self, phase: str, example_id: str | None, message: str):
        super().__init__(message); self.phase = phase; self.example_id = example_id


def _atomic_failure(output: Path, slot: str, exc: BaseException) -> None:
    phase = getattr(exc, "phase", "RUNTIME")
    example_id = getattr(exc, "example_id", None)
    core = {"schema":"editor-r2-anchored-contrastive-slot-failure","schema_version":2,
            "status":"FAIL_CLOSED","slot_id":slot,"example_id":example_id,
            "phase":phase,"error_type":type(exc).__name__,"eligible_evidence":False}
    receipt = {**core, "failure_identity": identity(core)}  # noqa: F405
    staging = output / ".failure-staging"; staging.mkdir(exist_ok=False)
    path = staging / "failure.json"
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    os.replace(path, output / "failure.json"); staging.rmdir()


def run_slot_v2(model_path: Path, parent_path: Path, corpus_path: Path, annotations_path: Path,
                pairs_path: Path, retention_path: Path, development_path: Path,
                output: Path, arm: str, seed: int) -> dict:
    # Validate the complete mapping before delegating to the unchanged training
    # recipe. Replay rows intentionally carry no critical weighting.
    try:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, fix_mistral_regex=True)
        validate_training_mapping(tokenizer, corpus_path, annotations_path, pairs_path, retention_path)
    except Exception as exc:
        text = str(exc); eid = text.split(":", 2)[1] if ":" in text else None
        raise SlotFailure("PRE_MODEL_TRAINING_MAPPING", eid, text) from exc

    # v1 rejected replay empty spans during its own preparation. Supply a
    # temporary in-memory-compatible annotations file whose replay spans cover
    # the full editorial text with neutral weight 1 achieved below is unsafe;
    # therefore execute the corrected implementation embedded locally.
    return _run_corrected_slot(model_path, parent_path, corpus_path, annotations_path,
                               pairs_path, retention_path, development_path,
                               output, arm, seed)


def _run_corrected_slot(model_path: Path, parent_path: Path, corpus_path: Path, annotations_path: Path,
                        pairs_path: Path, retention_path: Path, development_path: Path,
                        output: Path, arm: str, seed: int) -> dict:
    """Delegate to v1 with its span helper narrowed to the validated replay case."""
    original = legacy._chat_span_tokens
    def replay_aware(tokenizer, messages, spans):
        return set() if not spans else original(tokenizer, messages, spans)
    legacy._chat_span_tokens = replay_aware
    try:
        return legacy._run_authorized_slot(model_path, parent_path, corpus_path, annotations_path,
                                           pairs_path, retention_path, development_path,
                                           output, arm, seed)
    finally:
        legacy._chat_span_tokens = original


def main() -> int:
    import argparse
    p=argparse.ArgumentParser()
    for name in ("model","parent","corpus","annotations","pairs","retention","development","output"):
        p.add_argument(f"--{name}",type=Path,required=True)
    p.add_argument("--arm",choices=sorted(ARMS),required=True); p.add_argument("--seed",type=int,choices=SEEDS,required=True)  # noqa: F405
    p.add_argument("--execute-authorized",action="store_true"); a=p.parse_args(); sid=slot_id(a.arm,a.seed)  # noqa: F405
    if not a.execute_authorized or os.environ.get("ANCHORED_CONTRASTIVE_REAL_RUN_AUTHORIZED")!="1":
        raise SystemExit("separate real-run authorization required")
    try:
        result=run_slot_v2(a.model,a.parent,a.corpus,a.annotations,a.pairs,a.retention,a.development,a.output,a.arm,a.seed)
    except BaseException as exc:
        _atomic_failure(a.output,sid,exc); raise
    print(json.dumps(result,sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
