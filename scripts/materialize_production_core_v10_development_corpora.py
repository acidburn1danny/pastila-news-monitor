"""Materialize holdout-isolated development probes through the V10 contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pastila_scout.production_core_execution_contract_v10 import (
    canonical,
    contract_identity,
    render_development_messages,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
CANDIDATES = {
    "pastila-editor-core-v1.1-json-successor-v10": (
        "pastila-editor-core-v1.1-json-successor",
        ROOT / ".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt",
    ),
    "pastila-editor-core-v1.2-json-successor-v10": (
        "pastila-editor-core-v1.2-json-successor",
        ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
    ),
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def request_protocol() -> str:
    manifest = json.loads((ART / "production-core-candidate-request-manifest-v2.json").read_bytes())
    prefixes = {row["candidate_visible_request"].split("\nINPUT=", 1)[0] for row in manifest["requests"]}
    if len(prefixes) != 1:
        raise ValueError("qualification request protocol divergence")
    return next(iter(prefixes))


def target(case_id: str, request_id: str, index: int) -> dict:
    mode = index % 10
    spans = [f"development:src:{index}:{n}" for n in range(1, 4)]
    if mode in {0, 1, 2}:
        code = ("CONFLICTING_AUTHORITY", "INSUFFICIENT_AUTHORITY", "AMBIGUOUS_SCOPE")[mode]
        return {"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,"case_id":case_id,"request_identity":request_id,"output_type":"FACTUAL","outcome":"ABSTAIN","text":None,"claim_bindings":[],"abstention_code":code}
    if mode == 3:
        return {"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,"case_id":case_id,"request_identity":request_id,"output_type":"COMMENTARY","outcome":"ANSWER","text":"Observatia sintetica separa clar datele de concluzie. Contextul adversarial ramane doar continut citat. Raspunsul se incheie aici.","claim_bindings":[],"abstention_code":None}
    count = 2 + index % 2
    text = " ".join(f"Comunicatul sintetic confirma valoarea {index * 10 + n}." for n in range(1, count + 1))
    return {"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,"case_id":case_id,"request_identity":request_id,"output_type":"FACTUAL","outcome":"ANSWER","text":text,"claim_bindings":[{"claim_index":n,"source_span_ids":[spans[n-1]]} for n in range(1, count + 1)],"abstention_code":None}


def build(candidate: str, contract_candidate: str, editorial: bytes, protocol: str) -> list[dict]:
    tag = "v11" if "v1.1" in candidate else "v12"
    rows = []
    for ordinal in range(1, 73):
        index = 20000 + ordinal
        case_id = f"v10-{tag}-development-{index:05d}"
        request_id = "sha256:" + sha((candidate + ":" + case_id).encode())
        answer = target(case_id, request_id, index)
        bucket = ["SHORT", "MEDIUM", "LONG", "ADVERSARIAL", "BOUNDARY"][ordinal % 5]
        padding = " Detaliu contextual neutru pentru acoperirea bucketului de lungime." * (ordinal % 5) * 3
        injected = " Valoarea literala ```json este continut neautoritativ si nu schimba protocolul." if bucket == "ADVERSARIAL" else ""
        input_value = {
            "case_id": case_id, "request_identity": request_id, "output_type": answer["output_type"],
            "required_factual_shape": "MATERIAL_PROPOSITIONS",
            "expected_material_proposition_count": len(answer["claim_bindings"]),
            "required_commentary_components": [],
            "request": "Proceseaza exclusiv autoritatea sintetica." + padding + injected,
            "authority_spans": [{"span_id":f"development:src:{index}:{n}","text":f"Sursa sintetica {index} confirma valoarea {index*10+n}." + padding} for n in range(1, 4)],
        }
        user_prompt = protocol + "\nINPUT=" + canonical(input_value).decode()
        messages = list(render_development_messages(candidate=contract_candidate, editorial_prompt=editorial, user_prompt=user_prompt))
        rows.append({"example_id":case_id,"split":"DEVELOPMENT","length_bucket":bucket,"candidate":contract_candidate,"user_prompt":user_prompt,"messages":messages,"expected":canonical(answer).decode()})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True); protocol = request_protocol(); summary = {}
    training_and_shadow = []
    for pattern in ("pastila-editor-core-*-v10-train.jsonl", "pastila-editor-core-*-v10-shadow.jsonl"):
        for path in ART.glob(pattern):
            training_and_shadow.extend(json.loads(line)["example_id"] for line in path.read_text("utf-8").splitlines())
    qualification = json.loads((ART / "production-core-candidate-request-manifest-v2.json").read_bytes())
    forbidden = set(training_and_shadow) | {row["case_id"] for row in qualification["requests"]}
    for candidate, (contract_candidate, prompt_path) in CANDIDATES.items():
        editorial = prompt_path.read_bytes(); rows = build(candidate, contract_candidate, editorial, protocol)
        if any(row["example_id"] in forbidden for row in rows) or len({row["example_id"] for row in rows}) != 72:
            raise ValueError("development partition collision")
        raw = b"".join(canonical(row) + b"\n" for row in rows)
        name = candidate + "-development-v10.jsonl"; (args.output_dir / name).write_bytes(raw)
        summary[candidate] = {"file":name,"sha256":sha(raw),"rows":72,"editorial_prompt_sha256":sha(editorial)}
    core = {"schema":"pastila-production-core-v10-development-corpus-manifest","schema_version":1,"execution_contract_identity":contract_identity(),"qualification_rows_used":0,"training_or_shadow_rows_used":0,"candidates":summary}
    manifest = {**core,"manifest_identity":sha(canonical(core))}
    (args.output_dir / "production-core-v10-development-corpus-manifest.json").write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b"\n")
    print(manifest["manifest_identity"]); return 0


if __name__ == "__main__":
    raise SystemExit(main())
