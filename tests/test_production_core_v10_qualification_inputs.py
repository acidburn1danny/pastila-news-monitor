import hashlib,importlib.util,json
from pathlib import Path
from pastila_scout.production_core_execution_contract_v10 import OUTPUT_PROTOCOL,compose_system_prompt
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"docs/artifacts";SCRIPT=ROOT/"scripts/materialize_production_core_v10_qualification_inputs.py"
def module():
 spec=importlib.util.spec_from_file_location("inputs_v10",SCRIPT);value=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(value);return value
def unseal(value,field,canonical):
 core=dict(value);claimed=core.pop(field);assert hashlib.sha256(canonical(core)).hexdigest()==claimed
def test_v10_reseal_preserves_matrix_without_redraw():
 value=module();generation,qualification,prompts=value.build();old=json.loads((ART/"production-core-successor-comparative-qualification-generation-v9.json").read_bytes())
 assert generation["schedule"]==old["schedule"] and generation["matrix"]==old["matrix"] and len(generation["schedule"])==2400
 assert generation["retry_or_redraw_authorized"] is False and generation["qualification_attempt_consumed"] is False and generation["candidate_execution_performed"] is False
 assert generation["candidate_object_manifest_identity"]==value.MANIFEST==qualification["candidate_object_manifest_identity"]
 assert qualification["qualification_generation_identity"]==generation["qualification_generation_identity"] and qualification["qualification_attempt_consumed"] is False
 unseal(generation,"qualification_generation_identity",value.canonical);unseal(qualification,"qualification_identity",value.canonical)
def test_prompts_are_exact_contract_projection():
 value=module();_,_,prompts=value.build()
 for candidate,path in value.PROMPTS.items():
  expected=compose_system_prompt(candidate.removesuffix("-v10"),path.read_bytes()).encode();assert prompts[candidate]==expected;assert prompts[candidate].endswith(OUTPUT_PROTOCOL.encode())
def test_materialized_files_match_builder():
 value=module();generation,qualification,prompts=value.build();assert json.loads((ART/"production-core-successor-comparative-qualification-generation-v10.json").read_bytes())==generation;assert json.loads((ART/"production-core-successor-candidate-generation-qualification-v10.json").read_bytes())==qualification
 for candidate,raw in prompts.items():assert (ART/f"{candidate}-system-prompt.txt").read_bytes()==raw
