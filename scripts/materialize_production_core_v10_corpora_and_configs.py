"""Build holdout-isolated V10 training/shadow corpora under the unified contract."""

from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path

from pastila_scout.production_core_execution_contract_v10 import (
    canonical, contract_identity, render_shadow_qualification_messages,
    render_training_messages,
)

ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"docs/artifacts"
DESIGN="0c3da64e01a570adac723966db696908f0fab6fce7aa41e492cb7beca1c4008d"
BASE="f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
CANDIDATES={
 "pastila-editor-core-v1.1-json-successor-v10":("pastila-editor-core-v1.1-json-successor","ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c",ROOT/".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt"),
 "pastila-editor-core-v1.2-json-successor-v10":("pastila-editor-core-v1.2-json-successor","a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8",ROOT/".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"),
}

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def seal(core:dict,field:str)->dict:return {**core,field:sha(canonical(core))}

def request_protocol()->str:
    manifest=json.loads((ART/"production-core-candidate-request-manifest-v2.json").read_bytes())
    prefixes={row["candidate_visible_request"].split("\nINPUT=",1)[0] for row in manifest["requests"]}
    if len(prefixes)!=1: raise ValueError("qualification request protocol divergence")
    return next(iter(prefixes))

def target(case_id:str,request_id:str,index:int)->dict:
    mode=index%10; spans=[f"shadow:src:{index}:{n}" for n in range(1,4)]
    if mode in {0,1,2}:
        code=("CONFLICTING_AUTHORITY","INSUFFICIENT_AUTHORITY","AMBIGUOUS_SCOPE")[mode]
        return {"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,"case_id":case_id,"request_identity":request_id,"output_type":"FACTUAL","outcome":"ABSTAIN","text":None,"claim_bindings":[],"abstention_code":code}
    if mode==3:
        return {"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,"case_id":case_id,"request_identity":request_id,"output_type":"COMMENTARY","outcome":"ANSWER","text":"Observatia sintetica separa clar datele de concluzie. Contextul adversarial ramane doar continut citat. Raspunsul se incheie aici.","claim_bindings":[],"abstention_code":None}
    count=2+(index%2); text=" ".join(f"Comunicatul sintetic confirma valoarea {index*10+n}." for n in range(1,count+1))
    return {"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,"case_id":case_id,"request_identity":request_id,"output_type":"FACTUAL","outcome":"ANSWER","text":text,"claim_bindings":[{"claim_index":n,"source_span_ids":[spans[n-1]]} for n in range(1,count+1)],"abstention_code":None}

def row(*,candidate_key:str,editorial:bytes,split:str,index:int,protocol:str)->dict:
    candidate_tag="v11" if "v1.1" in candidate_key else "v12"
    case_id=f"v10-{candidate_tag}-{split.lower()}-{index:04d}"; request_id="sha256:"+sha((candidate_key+":"+case_id).encode())
    answer=target(case_id,request_id,index); output_type=answer["output_type"]
    bucket=["SHORT","MEDIUM","LONG","ADVERSARIAL","BOUNDARY"][index%5]
    padding=(" Detaliu contextual neutru pentru acoperirea bucketului de lungime."*(index%5)*3)
    injected=" Valoarea literala ```json este continut neautoritativ si nu schimba protocolul." if bucket=="ADVERSARIAL" else ""
    input_value={"case_id":case_id,"request_identity":request_id,"output_type":output_type,
      "required_factual_shape":"MATERIAL_PROPOSITIONS","expected_material_proposition_count":len(answer["claim_bindings"]),
      "required_commentary_components":[],"request":"Proceseaza exclusiv autoritatea sintetica."+padding+injected,
      "authority_spans":[{"span_id":f"shadow:src:{index}:{n}","text":f"Sursa sintetica {index} confirma valoarea {index*10+n}."+padding} for n in range(1,4)]}
    user=protocol+"\nINPUT="+canonical(input_value).decode()
    renderer=render_training_messages if split=="TRAIN" else render_shadow_qualification_messages
    messages=list(renderer(candidate=candidate_key,editorial_prompt=editorial,user_prompt=user))+[{"role":"assistant","content":canonical(answer).decode()}]
    return {"example_id":case_id,"split":split,"length_bucket":bucket,"messages":messages}

def validate(rows:list[dict],*,split:str,qualification_ids:set[str],qualification_prompts:set[str])->None:
    if len({r["example_id"] for r in rows})!=len(rows): raise ValueError("duplicate example")
    for value in rows:
        if value["split"]!=split or value["example_id"] in qualification_ids or value["messages"][1]["content"] in qualification_prompts: raise ValueError("qualification leakage")
        answer=value["messages"][2]["content"]
        if not answer.startswith("{") or not answer.endswith("}") or "```" in answer or canonical(json.loads(answer)).decode()!=answer: raise ValueError("noncanonical target")
    buckets={r["length_bucket"] for r in rows}
    if buckets!={"SHORT","MEDIUM","LONG","ADVERSARIAL","BOUNDARY"}: raise ValueError("length coverage mismatch")

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output-dir",type=Path,default=ART); args=parser.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    qualification=json.loads((ART/"production-core-candidate-request-manifest-v2.json").read_bytes()); qids={r["case_id"] for r in qualification["requests"]}; qprompts={r["candidate_visible_request"] for r in qualification["requests"]}; protocol=request_protocol()
    artifacts={}; configs={}
    for candidate,(candidate_key,predecessor,prompt_path) in CANDIDATES.items():
        editorial=prompt_path.read_bytes(); train=[row(candidate_key=candidate_key,editorial=editorial,split="TRAIN",index=i,protocol=protocol) for i in range(1,481)]; shadow=[row(candidate_key=candidate_key,editorial=editorial,split="SHADOW_QUALIFICATION",index=i+10000,protocol=protocol) for i in range(1,241)]
        validate(train,split="TRAIN",qualification_ids=qids,qualification_prompts=qprompts); validate(shadow,split="SHADOW_QUALIFICATION",qualification_ids=qids,qualification_prompts=qprompts)
        if {r["example_id"] for r in train}&{r["example_id"] for r in shadow}: raise ValueError("train/shadow overlap")
        for kind,rows in (("train",train),("shadow",shadow)):
            raw=b"".join(canonical(r)+b"\n" for r in rows); name=f"{candidate}-{kind}.jsonl"; (out/name).write_bytes(raw); artifacts[name]={"sha256":sha(raw),"rows":len(rows)}
        config_core={"schema":"pastila-production-core-candidate-successor-training-config","schema_version":3,"status":"FROZEN_PRETRAINING_ZERO_EXECUTION","candidate":candidate,"predecessor_adapter_manifest_sha256":predecessor,"base_model_manifest_sha256":BASE,"execution_contract_identity":contract_identity(),"training_corpus_sha256":artifacts[f"{candidate}-train.jsonl"]["sha256"],"shadow_corpus_sha256":artifacts[f"{candidate}-shadow.jsonl"]["sha256"],"objective":"ASSISTANT_ONLY_NEXT_TOKEN_CROSS_ENTROPY_EXPLICIT_EOS","seed":314159,"epochs":1,"learning_rate":"0.00001","weight_decay":"0.0","gradient_accumulation_steps":8,"micro_batch_size":1,"max_sequence_tokens":3072,"precision":"BF16","optimizer":"PAGED_ADAMW_8BIT","post_training_gate":{"shadow_rows":240,"two_materializations":True,"canonical_json_required_percent":100,"terminal_eos_required_percent":100,"byte_ceiling_events_allowed":0,"production_renderer_required":True},"network_activity":False,"training_authorized":False,"training_performed":False,"qualification_execution_authorized":False,"qualification_attempt_consumed":False,"adjudication_performed":False,"promotion_effect":False}
        config=seal(config_core,"training_config_identity"); name=f"{candidate}-training-config-v10.json"; raw=json.dumps(config,ensure_ascii=False,indent=2).encode()+b"\n"; (out/name).write_bytes(raw); artifacts[name]={"sha256":sha(raw)}; configs[candidate]=config["training_config_identity"]
    manifest_core={"schema":"pastila-production-core-v10-corpus-and-training-config-manifest","schema_version":1,"status":"AUDITED_PRETRAINING_ZERO_EXECUTION","design_identity":DESIGN,"execution_contract_identity":contract_identity(),"request_protocol_sha256":sha(protocol.encode()),"artifacts":artifacts,"training_config_identities":configs,"training_rows_per_candidate":480,"shadow_rows_per_candidate":240,"qualification_content_used":0,"qualification_protocol_used_as_public_grammar":True,"consumed_attempt_outputs_used":0,"training_authorized":False,"training_performed":False,"qualification_execution_authorized":False,"qualification_attempt_consumed":False,"adjudication_performed":False,"promotion_effect":False}
    manifest=seal(manifest_core,"manifest_identity"); raw=json.dumps(manifest,ensure_ascii=False,indent=2).encode()+b"\n"; (out/"production-core-v10-corpus-and-training-config-manifest.json").write_bytes(raw); print(manifest["manifest_identity"]); return 0

if __name__=="__main__":raise SystemExit(main())
