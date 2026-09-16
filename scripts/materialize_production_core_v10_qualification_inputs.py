"""Reseal the unchanged qualification matrix for V10 candidates and prompts."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from pastila_scout.production_core_execution_contract_v10 import compose_system_prompt
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"docs/artifacts";MANIFEST="6c3bf1d21e85a454069ccd4e80f542fa5005ea6b89b41bb0d90b4acad2533314"
PROMPTS={"pastila-editor-core-v1.1-json-successor-v10":ROOT/".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt","pastila-editor-core-v1.2-json-successor-v10":ROOT/".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"}
def canonical(v):return json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
def reseal(value,field):
 core=dict(value);core.pop(field,None);return {**core,field:hashlib.sha256(canonical(core)).hexdigest()}
def build():
 generation=json.loads((ART/"production-core-successor-comparative-qualification-generation-v9.json").read_bytes());generation["status"]="FROZEN_SUCCESSOR_V10_UNIFIED_CONTRACT_PREINFERENCE_CANDIDATE_NEUTRAL";generation["candidate_object_manifest_identity"]=MANIFEST;generation=reseal(generation,"qualification_generation_identity")
 qualification=json.loads((ART/"production-core-successor-candidate-generation-qualification-v9.json").read_bytes());qualification["status"]="PASS_SUCCESSOR_V10_UNIFIED_CONTRACT_OFFLINE_PREINFERENCE_ZERO_CANDIDATE_EXECUTION";qualification["qualification_generation_identity"]=generation["qualification_generation_identity"];qualification["candidate_object_manifest_identity"]=MANIFEST;qualification=reseal(qualification,"qualification_identity")
 prompts={name:compose_system_prompt(name.removesuffix("-v10"),path.read_bytes()).encode() for name,path in PROMPTS.items()}
 return generation,qualification,prompts
def put(path,raw):
 if path.exists() and path.read_bytes()!=raw:raise SystemExit(f"published artifact differs: {path.name}")
 path.write_bytes(raw)
def main():
 generation,qualification,prompts=build();put(ART/"production-core-successor-comparative-qualification-generation-v10.json",json.dumps(generation,ensure_ascii=False,indent=2).encode()+b"\n");put(ART/"production-core-successor-candidate-generation-qualification-v10.json",json.dumps(qualification,ensure_ascii=False,indent=2).encode()+b"\n")
 for candidate,raw in prompts.items():put(ART/f"{candidate}-system-prompt.txt",raw)
 print(generation["qualification_generation_identity"]);print(qualification["qualification_identity"]);return 0
if __name__=="__main__":raise SystemExit(main())
