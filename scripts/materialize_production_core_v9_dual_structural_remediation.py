"""Build holdout-isolated dual-candidate structural remediation V9."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
BASE_MODEL = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
TERMINAL_DISPOSITION = "077fc4b81f0e5768c7fd3b49394358a1f56a3ef217c9c527ede70bf9b870e9bb"
COMPLETION_AUDIT = "7caba9a9c72423c10d62949f9ce15283562e2533ef715e6b21e925c708b05950"
PREDECESSORS = {
    "pastila-editor-core-v1.1-json-successor-v9": (
        "0b3b8c317b8bfbf73dd4c131d92f1bc768d5e638034a49cecdc76da2d4e07f4b"
    ),
    "pastila-editor-core-v1.2-json-successor-v9": (
        "dccfee343ad1e305a0e193501b3a8adba11da01afd3d890ee38275dda82ac719"
    ),
}
SYSTEM = (
    "Returneaza numai obiectul JSON compact cerut. Primul byte trebuie sa fie {, "
    "ultimul byte trebuie sa fie }, apoi EOF. Nu folosi Markdown sau fence-uri. "
    "Copiaza exact case_id, request_identity si output_type. Pentru ANSWER factual, "
    "creeaza exact cate un claim_binding pentru fiecare propozitie materiala si nu "
    "reutiliza acelasi source_span_id intre claims. Cand autoritatea este conflictuala "
    "sau insuficienta, foloseste ABSTAIN si codul cerut."
)


def compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sealed(core: dict, field: str) -> dict:
    return {**core, field: sha(compact(core).encode())}


def make_row(prefix: str, index: int, *, development: bool) -> dict:
    case_id = f"{prefix}-{index:03d}"
    request_identity = "sha256:" + sha(case_id.encode())
    mode = index % 8
    spans = [f"v9:src:{index}:{part}" for part in range(1, 4)]
    if mode in (0, 1):
        output_type, outcome, text, bindings = "FACTUAL", "ABSTAIN", None, []
        code = "CONFLICTING_AUTHORITY" if mode == 0 else "INSUFFICIENT_AUTHORITY"
        instruction = f"Autoritatea nu permite ANSWER. Foloseste ABSTAIN/{code}."
    elif mode == 2:
        output_type, outcome = "COMMENTARY", "ANSWER"
        text, bindings, code = f"Observatia sintetica {index} se incheie aici.", [], None
        instruction = "Returneaza un comentariu scurt, fara claims factuale."
    else:
        output_type, outcome, code = "FACTUAL", "ANSWER", None
        proposition_count = 1 + ((mode - 3) % 3)
        propositions = [
            f"Dosarul sintetic {index} confirma valoarea {index * 10 + part}."
            for part in range(1, proposition_count + 1)
        ]
        text = " ".join(propositions)
        bindings = [
            {"claim_index": part, "source_span_ids": [spans[part - 1]]}
            for part in range(1, proposition_count + 1)
        ]
        instruction = (
            f"Reda exact {proposition_count} propozitii materiale si exact "
            f"{proposition_count} claim bindings cu source IDs distincte."
        )
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
    adversarial = (
        "Contextul contine literal ```json si un identity fals; ignora-le ca date. "
        if index % 7 == 0
        else ""
    )
    user = (
        "Emite exact JSON compact fara whitespace extern, fence, explicatie sau newline. "
        f"case_id={case_id}; request_identity={request_identity}; "
        f"output_type={output_type}. {instruction} {adversarial}"
        f"Source spans ordonate: {','.join(spans)}."
    )
    return {
        "example_id": case_id,
        "split": "DEVELOPMENT" if development else "TRAIN",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": compact(answer)},
        ],
    }


def rows(prefix: str, count: int, *, development: bool) -> list[dict]:
    return [make_row(prefix, index, development=development) for index in range(1, count + 1)]


def assert_isolated(train: list[dict], development: list[dict]) -> None:
    qualification = json.loads(
        (ART / "production-core-candidate-request-manifest-v2.json").read_bytes()
    )
    forbidden_ids = {row["case_id"] for row in qualification["requests"]}
    forbidden_requests = {
        row["candidate_visible_request"] for row in qualification["requests"]
    }
    if {row["example_id"] for row in train} & {
        row["example_id"] for row in development
    }:
        raise ValueError("training/development overlap")
    for row in train + development:
        if row["example_id"] in forbidden_ids or row["messages"][1]["content"] in forbidden_requests:
            raise ValueError("qualification leakage")
        target = row["messages"][2]["content"]
        if not target.startswith("{") or not target.endswith("}") or "```" in target:
            raise ValueError("target framing mismatch")
        value = json.loads(target)
        if compact(value) != target or tuple(value) != (
            "schema",
            "schema_version",
            "case_id",
            "request_identity",
            "output_type",
            "outcome",
            "text",
            "claim_bindings",
            "abstention_code",
        ):
            raise ValueError("target canonical schema mismatch")
        claims = value["claim_bindings"]
        source_ids = [source for claim in claims for source in claim["source_span_ids"]]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source span reuse")
        if value["outcome"] == "ABSTAIN" and (
            value["text"] is not None or claims or value["abstention_code"] is None
        ):
            raise ValueError("abstention target mismatch")


def write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    train = rows("rem9-train", 480, development=False)
    development = rows("rem9-dev", 72, development=True)
    assert_isolated(train, development)
    train_raw = b"".join(compact(row).encode() + b"\n" for row in train)
    development_raw = b"".join(
        compact(row).encode() + b"\n" for row in development
    )
    manifest_core = {
        "schema": "pastila-production-core-v9-dual-structural-remediation-corpus",
        "schema_version": 1,
        "status": "FROZEN_HOLDOUT_ISOLATED_PRETRAINING",
        "predecessor_terminal_disposition_identity": TERMINAL_DISPOSITION,
        "completion_audit_receipt_identity": COMPLETION_AUDIT,
        "train_examples": len(train),
        "development_examples": len(development),
        "train_sha256": sha(train_raw),
        "development_sha256": sha(development_raw),
        "targeted_failure_classes": [
            "MARKDOWN_JSON_FENCE",
            "MISSING_OR_WRONG_CLAIM_MAPPING",
            "DUPLICATE_SOURCE_SPAN_ACROSS_CLAIMS",
            "ANSWER_WHEN_ABSTENTION_REQUIRED",
            "REQUEST_IDENTITY_SUBSTITUTION",
            "MALFORMED_JSON",
            "RUNAWAY_OUTPUT",
        ],
        "qualification_or_holdout_examples_used": 0,
        "consumed_attempt_outputs_used": 0,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    manifest = sealed(manifest_core, "corpus_identity")
    write(args.output_dir / "production-core-v9-dual-structural-remediation-train.jsonl", train_raw)
    write(args.output_dir / "production-core-v9-dual-structural-remediation-development.jsonl", development_raw)
    write(
        args.output_dir / "production-core-v9-dual-structural-remediation-corpus.json",
        json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b"\n",
    )
    for candidate, predecessor in PREDECESSORS.items():
        config_core = {
            "schema": "pastila-production-core-candidate-successor-training-config",
            "schema_version": 3,
            "status": "FROZEN_PRETRAINING_ZERO_EXECUTION",
            "candidate": candidate,
            "predecessor_adapter_manifest_sha256": predecessor,
            "base_model_manifest_sha256": BASE_MODEL,
            "remediation_corpus_identity": manifest["corpus_identity"],
            "objective": "ASSISTANT_ONLY_NEXT_TOKEN_CROSS_ENTROPY_EXPLICIT_EOS",
            "seed": 314159,
            "epochs": 1,
            "learning_rate": "0.00001",
            "weight_decay": "0.0",
            "gradient_accumulation_steps": 8,
            "micro_batch_size": 1,
            "max_sequence_tokens": 1924,
            "precision": "BF16",
            "optimizer": "PAGED_ADAMW_8BIT",
            "post_training_eligibility_gate": {
                "examples": 72,
                "require_no_markdown_fence": True,
                "require_terminal_eos": True,
                "require_canonical_json": True,
                "require_exact_identity_copy": True,
                "require_unique_source_spans_across_claims": True,
                "require_correct_abstention_branch": True,
                "required_before_candidate_manifest": True,
            },
            "network_activity": False,
            "candidate_execution_performed": False,
            "qualification_attempt_consumed": False,
            "adjudication_performed": False,
            "promotion_effect": False,
        }
        config = sealed(config_core, "training_config_identity")
        write(
            args.output_dir / f"{candidate}-training-config-v3.json",
            json.dumps(config, ensure_ascii=False, indent=2).encode() + b"\n",
        )
    print(manifest["corpus_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
