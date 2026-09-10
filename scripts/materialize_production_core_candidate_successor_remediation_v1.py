"""Build holdout-isolated raw-JSON remediation data and successor training configs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREDECESSOR_DISPOSITION = "acd5b874de1a3b9c638194836d94f6f7b569781c2b63f778b04c8cb44871084f"
BASE_MODEL = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
PREDECESSORS = {
    "pastila-editor-core-v1.1-json-successor": "0bc4bb1b83b5c1375c1e676844dea079831e7ad0b90db955fa89a2f7d65c3e47",
    "pastila-editor-core-v1.2-json-successor": "22b5a7bde7194c66d895b9acab5791a8d8573df67f93704eab933666df7978a2",
}
SYSTEM = (
    "Răspunde exclusiv cu obiectul JSON compact cerut de utilizator. Primul byte trebuie "
    "să fie { și ultimul byte trebuie să fie }. Nu folosi Markdown, code fences, explicații "
    "sau whitespace exterior. Păstrează exact ordinea și tipurile câmpurilor cerute."
)


def compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sealed(core: dict, field: str) -> dict:
    return {**core, field: sha(compact(core).encode())}


def examples() -> list[dict]:
    rows = []
    for index in range(1, 241):
        case_id = f"rem3-{index:03d}"
        request_identity = f"sha256:{sha(case_id.encode())}"
        kind = index % 4
        if kind == 0:
            output_type, outcome = "FACTUAL", "ABSTAIN"
            text, bindings, code = None, [], "INSUFFICIENT_AUTHORITY"
            task = "Nu există autoritate suficientă; abține-te conform contractului."
        elif kind == 1:
            output_type, outcome = "FACTUAL", "ANSWER"
            text = f"Atelierul Meridian {index} a deschis laboratorul și a instalat {index + 30} de stații."
            bindings = [
                {"claim_index": 1, "source_span_ids": [f"rem:src:{index}:a"]},
                {"claim_index": 2, "source_span_ids": [f"rem:src:{index}:b"]},
            ]
            code = None
            task = f"Redă cele două fapte despre Atelierul Meridian {index}, cu binding-uri în ordine."
        elif kind == 2:
            output_type, outcome = "COMMENTARY", "ANSWER"
            text = f"Orașul Solaris {index} inaugurează încă un panou. Birocrația a primit, în sfârșit, propria umbră."
            bindings, code = [], None
            task = "Scrie două propoziții de comentariu fără afirmații factuale suplimentare."
        else:
            output_type, outcome = "FACTUAL", "ABSTAIN"
            text, bindings, code = None, [], "CONFLICTING_AUTHORITY"
            task = "Sursele sintetice se contrazic; abține-te conform contractului."
        answer = {
            "schema": "pastila-core-v2-structured-qualification-response",
            "schema_version": 2,
            "case_id": case_id,
            "request_identity": request_identity,
            "output_type": output_type,
            "outcome": outcome,
            "text": text,
            "claim_bindings": bindings,
            "abstention_code": code,
        }
        user = (
            "Returnează exact un obiect JSON compact UTF-8 NFC urmat imediat de EOF; "
            "fără Markdown sau fences. Câmpuri exact în ordinea schema,schema_version,"
            "case_id,request_identity,output_type,outcome,text,claim_bindings,abstention_code. "
            f"case_id={case_id}; request_identity={request_identity}; output_type={output_type}. {task}"
        )
        rows.append(
            {
                "example_id": case_id,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": compact(answer)},
                ],
            }
        )
    return rows


def assert_isolated(rows: list[dict]) -> None:
    qualification = json.loads(
        (ART / "production-core-candidate-request-manifest-v2.json").read_bytes()
    )
    frozen_ids = {row["case_id"] for row in qualification["requests"]}
    frozen_requests = {row["candidate_visible_request"] for row in qualification["requests"]}
    for row in rows:
        if row["example_id"] in frozen_ids:
            raise SystemExit("qualification case leaked into remediation")
        user = row["messages"][1]["content"]
        if user in frozen_requests or any(case_id in user for case_id in frozen_ids):
            raise SystemExit("qualification request leaked into remediation")
        assistant = row["messages"][2]["content"]
        if not assistant.startswith("{") or not assistant.endswith("}") or "```" in assistant:
            raise SystemExit("non-raw remediation target")
        if compact(json.loads(assistant)) != assistant:
            raise SystemExit("noncanonical remediation target")


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    rows = examples()
    assert_isolated(rows)
    corpus = b"".join(compact(row).encode() + b"\n" for row in rows)
    corpus_name = "production-core-candidate-successor-remediation-corpus-v1.jsonl"
    write(args.output_dir / corpus_name, corpus)
    corpus_core = {
        "schema": "pastila-production-core-candidate-successor-remediation-corpus",
        "schema_version": 1,
        "status": "FROZEN_HOLDOUT_ISOLATED_RAW_JSON_TARGETS",
        "predecessor_terminal_disposition_identity": PREDECESSOR_DISPOSITION,
        "example_count": len(rows),
        "corpus_sha256": sha(corpus),
        "qualification_or_holdout_examples_used": 0,
        "consumed_attempt_outputs_used": 0,
        "target_markdown_fence_count": 0,
        "candidate_execution_performed": False,
        "promotion_effect": False,
    }
    manifest = sealed(corpus_core, "corpus_identity")
    write(
        args.output_dir / "production-core-candidate-successor-remediation-corpus-v1.json",
        json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b"\n",
    )
    for candidate, predecessor in PREDECESSORS.items():
        config_core = {
            "schema": "pastila-production-core-candidate-successor-training-config",
            "schema_version": 1,
            "status": "FROZEN_PRETRAINING_ZERO_EXECUTION",
            "candidate": candidate,
            "predecessor_adapter_manifest_sha256": predecessor,
            "base_model_manifest_sha256": BASE_MODEL,
            "remediation_corpus_identity": manifest["corpus_identity"],
            "objective": "ASSISTANT_ONLY_NEXT_TOKEN_CROSS_ENTROPY_RAW_JSON_EOF",
            "seed": 314159,
            "epochs": 3,
            "learning_rate": "0.00005",
            "warmup_ratio": "0.05",
            "weight_decay": "0.0",
            "gradient_accumulation_steps": 8,
            "micro_batch_size": 1,
            "max_sequence_tokens": 1924,
            "precision": "BF16",
            "optimizer": "PAGED_ADAMW_8BIT",
            "lora": {"r": 16, "alpha": 32, "dropout": "0.05", "continue_from_predecessor": True},
            "network_activity": False,
            "candidate_execution_performed": False,
            "qualification_attempt_consumed": False,
            "promotion_effect": False,
        }
        config = sealed(config_core, "training_config_identity")
        name = candidate.replace("pastila-editor-core-", "production-core-")
        write(args.output_dir / f"{name}-training-config-v1.json", json.dumps(config, indent=2).encode() + b"\n")
    print(manifest["corpus_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
