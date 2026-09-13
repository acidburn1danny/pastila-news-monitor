"""Audit V9's gate mismatch and materialize the zero-execution V10 design."""

from __future__ import annotations

import argparse, hashlib, json
from collections import Counter
from pathlib import Path

from pastila_scout.production_core_execution_contract_v10 import canonical, contract_core, contract_identity

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/"docs/artifacts"
EXECUTION=ROOT/".pastila-runtime/production-core-successor-execution-v9-attempt1"
OUTPUT=ART/"production-core-v10-unified-execution-contract-design.json"
V9_DISPOSITION="7855e21d82402416dcee091baa7a6bcc5cb4c63783aafa33c65bd355c7d83587"

def load(path: Path) -> dict:
    if path.is_symlink() or not path.is_file(): raise ValueError(f"regular file required: {path}")
    return json.loads(path.read_bytes())

def build(execution: Path=EXECUTION) -> dict[str,object]:
    disposition=load(ART/"production-core-v9-terminal-disposition.json")
    if disposition.get("disposition_identity")!=V9_DISPOSITION: raise ValueError("V9 disposition mismatch")
    observations=[load(path) for path in execution.rglob("*.observation.json")]
    receipts=[load(path) for path in execution.rglob("*.receipt.json")]
    if len(observations)!=2400 or len(receipts)!=2400: raise ValueError("V9 evidence cardinality mismatch")
    termination=Counter(row["termination_reason"] for row in observations)
    output_status=Counter(row["candidate_output_status"] for row in observations)
    overflow_cases=Counter((row["candidate"],row["case_id"]) for row in observations if row["termination_reason"]!="TERMINAL_EOS")
    expected_overflow={("pastila-editor-core-v1.1-json-successor-v2",case):6 for case in ("pcq-eos-007","pcq-eos-009","pcq-eos-013","pcq-eos-014")}
    if termination!={"TERMINAL_EOS":2376,"OUTPUT_BYTE_CEILING_EXCEEDED":24} or output_status!={"EXECUTION_ENVELOPE_PASS":2376,"EXECUTION_ENVELOPE_FAIL_CLOSED":24} or dict(overflow_cases)!=expected_overflow:
        raise ValueError("V9 root-cause evidence mismatch")
    core={"schema":"pastila-production-core-v10-unified-execution-design","schema_version":1,
      "status":"AUDITED_DESIGN_FROZEN_ZERO_TRAINING_ZERO_QUALIFICATION_EXECUTION",
      "predecessor_disposition_identity":V9_DISPOSITION,"root_cause":"NON_REPRESENTATIVE_DEVELOPMENT_GATE_PROMPT_AND_DISTRIBUTION_MISMATCH",
      "v9_evidence":{"runtime_envelope_pass":2376,"structural_failures":2400,"byte_ceiling_failures":24,
        "deterministic_v1_1_overflow_cases":dict(sorted((case,count) for (_,case),count in overflow_cases.items()))},
      "execution_contract":contract_core(),"execution_contract_identity":contract_identity(),
      "required_invariants":["ONE_RENDERER_SOURCE_FOR_ALL_PHASES","BYTE_IDENTICAL_SYSTEM_COMPOSITION","BYTE_IDENTICAL_CHAT_TEMPLATE_OPTIONS","BYTE_IDENTICAL_GENERATION_POLICY","DISJOINT_SHADOW_CONTENT_SAME_GRAMMAR_AND_LENGTH_BUCKETS","ZERO_MARKDOWN_FENCES","TERMINAL_EOS_AFTER_CLOSING_BRACE","BYTE_CEILING_HEADROOM","TWO_REPRODUCIBLE_MATERIALIZATIONS","FAIL_CLOSED_ON_ANY_DIVERGENCE"],
      "gates_before_training_authority":["renderer consumer import scan","phase projection executable smoke","wrong editorial hash negative","phase mutation negative","qualification leakage negative"],
      "gates_after_training_before_candidate_manifest":["qualification-shaped shadow matrix","100 percent canonical JSON","100 percent terminal EOS","zero byte ceiling events","long-context and adversarial coverage"],
      "training_authorized":False,"training_performed":False,"qualification_execution_authorized":False,
      "qualification_attempt_consumed":False,"adjudication_performed":False,"promotion_effect":False}
    return {**core,"design_identity":hashlib.sha256(canonical(core)).hexdigest()}

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,default=OUTPUT); args=parser.parse_args()
    value=build(); raw=json.dumps(value,ensure_ascii=False,indent=2).encode()+b"\n"
    if args.output.exists() and (args.output.is_symlink() or args.output.read_bytes()!=raw): raise SystemExit("published V10 design differs")
    if not args.output.exists(): args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(raw)
    print(value["design_identity"]); return 0

if __name__=="__main__": raise SystemExit(main())
