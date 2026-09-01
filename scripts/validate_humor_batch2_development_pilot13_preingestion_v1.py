"""Strictly validate Pilot 13 owner inputs without deriving downstream objects."""
from __future__ import annotations
import hashlib,json,re,subprocess,unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"docs/artifacts"
SOURCE=ROOT/"owner-source-pilot13-v1.txt"; DECLARATION=ROOT/"owner-declaration-pilot13-v1.json"
REQUEST_COMMIT="8c89cbf7bdab9102ac3a5baa037489ecafabe6d7"
SOURCE_SHA="9d79b45d06fba5b950f97e7d09f38450177b7ff7d5cbf962a9e4f7af452b6a76"; DECL_SHA="5e18c30cab71ee0ab1e3599e1abc433af3bcebea881d683ed8322387d0d570e3"
def can(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def seal(n,v):return hashlib.sha256(can({"namespace":n,"value":v})).hexdigest()
def require(v,m):
    if not v:raise SystemExit(m)
def unique(pairs):
    out={}
    for k,v in pairs:require(k not in out,f"duplicate key: {k}");out[k]=v
    return out
def shape(actual,template,path="$"):
    if isinstance(template,dict):
        require(isinstance(actual,dict) and set(actual)==set(template),f"{path} field set")
        for k in template:shape(actual[k],template[k],f"{path}.{k}")
def git_bytes(path):return subprocess.check_output(["git","show",f"{REQUEST_COMMIT}:{path}"],cwd=ROOT)
def words(text):return re.findall(r"[\wăâîșț]+",unicodedata.normalize("NFKC",text).casefold())
def ngrams(text,n=5):
    w=words(text);return {tuple(w[i:i+n]) for i in range(max(0,len(w)-n+1))}
def main():
    sb,db=SOURCE.read_bytes(),DECLARATION.read_bytes();require(hashlib.sha256(sb).hexdigest()==SOURCE_SHA,"source hash");require(hashlib.sha256(db).hexdigest()==DECL_SHA,"declaration hash")
    for name,data in (("source",sb),("declaration",db)):
        require(not data.startswith(b"\xef\xbb\xbf"),f"{name} BOM");require(b"\r" not in data,f"{name} line endings");data.decode("utf-8");require(data.endswith(b"\n") and not data.endswith(b"\n\n"),f"{name} terminal LF")
    declaration=json.loads(db,object_pairs_hook=unique);template=json.loads(git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot13-owner-declaration-template-v1.json"));template.pop("template_identity");shape(declaration,template)
    require(declaration["schema_name"]=="batch2-owner-declaration-pilot13-v1" and declaration["schema_version"]=="1.0.0" and declaration["pilot_id"]=="BATCH2-DEVELOPMENT-PILOT-13","schema/pilot")
    require(declaration["trial_role"]=="LEGITIMATE_END_TO_END_MECHANISM_TRIAL","trial role");meta=declaration["source"]
    require(meta["filename"]==SOURCE.name and meta["encoding"]=="UTF-8_NO_BOM" and meta["line_endings"]=="LF_ONLY" and meta["terminal_lf_count"]==1,"declared format")
    require(meta["source_version"]=="1.0.0" and meta["intended_partition"]=="DEVELOPMENT" and meta["world_scope"]=="OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE","source metadata")
    capture,acquired=(datetime.fromisoformat(meta[k]) for k in ("capture_timestamp","acquisition_timestamp"));require(capture.tzinfo and acquired.tzinfo and capture<=acquired,"timestamps")
    ownership=declaration["ownership_declarations"];require(all(ownership[k] is True for k in ("original_authorship","owns_or_controls_required_rights","has_authority_to_make_each_selected_grant")),"ownership");require(all(ownership[k] is False for k in ownership if k not in ("original_authorship","owns_or_controls_required_rights","has_authority_to_make_each_selected_grant")),"excluded material")
    grants=declaration["independent_grants"];require(all(grants[k] is True for k in ("immutable_archival","factual_annotation_and_authority_binding","internal_discovery","construction_and_evaluation")),"required grants");require(all(grants[k] is False for k in ("model_exposure","training","runtime_integration","production_routing")),"noninheritance")
    require(all(v is True for v in declaration["source_status_declarations"].values()),"source declarations");instruction=declaration["owner_instruction"];require(instruction["request_preingestion_validation_only"] is True and instruction["operational_content_access_after_ingestion"] is False,"instruction");require(all(instruction[k] is True for k in instruction if k not in ("request_preingestion_validation_only","operational_content_access_after_ingestion")),"future permissions")
    contributor=declaration["contributor"];require(contributor["identity_disclosure_approved_for_commit"] is False and contributor["rights_holder_relationship"]=="ORIGINAL_AUTHOR_AND_RIGHTS_HOLDER","contributor");require(declaration["owner_confirmation"]["confirmed"] is True,"confirmation")
    source=sb.decode("utf-8");folded=source.casefold();paragraphs=[x for x in source.strip().split("\n\n") if x];sentences=[x for x in re.split(r"(?<=[.!?])\s+",source.strip()) if x];require(len(paragraphs)==4 and len(sentences)>=2,"bindable factual statements")
    prohibited=("?","!","glum","poant","metafor","parodi","mecanism","obliga","pilot","instruc","guvernan","absurd","witness","affordance","aliniere","template","constructor","g02","g03")
    require(not any(x in folded for x in prohibited),"neutrality/prohibited shaping")
    factual_tokens=("28 august 2026","18 senzori acustici","campanie de măsurare","sală de concerte","număr de serie","fișa campaniei","poziție numerotată","înainte de instalare","poziția efectivă","ora instalării","jurnalul campaniei","a rămas nemontat","numai la cei 18 senzori","nu a stabilit amplasarea altor echipamente","nu era cunoscut","nici dacă vreun senzor va rămâne nemontat")
    require(all(x in folded for x in factual_tokens),"scope modality time known/unknown boundaries");scope=meta["authority_scope"].casefold();require(all(x in scope for x in ("acoustic-sensor","sensor quantity","serial-number","assigned-position","unknown")),"authority scope")
    prior=[]
    for i in range(1,13):prior.append(git_bytes(f"docs/artifacts/humor-mechanics-batch2-development-pilot{i:02d}-ingestion-v1/source.utf8.txt"))
    require(sb not in prior,"prior source equality");current_lines={x for x in source.splitlines() if x};prior_lines={x for raw in prior for x in raw.decode("utf-8").splitlines() if x};require(not current_lines&prior_lines,"prior exact line reuse")
    prior_text="\n".join(x.decode("utf-8") for x in prior);require("senzori acustici" not in prior_text.casefold() and "sală de concerte" not in prior_text.casefold(),"prior entity/event reuse")
    current_grams=ngrams(source);prior_grams=set().union(*(ngrams(raw.decode("utf-8")) for raw in prior));overlap=current_grams&prior_grams;require(len(overlap)<=2,"prior source-structure/wording reuse")
    request=json.loads(git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot13-owner-input-request-v1.json"));require(request["owner_input_request_identity"]=="864763eb53512265ff0f134af16fa44f1e989c2972b3d3669ac9769af3456363","request");require(request["declaration_template_identity"]=="626574966ff8d50a17a467fad5602c3da0a9370c6854fe42d424ce1a434cd100","template")
    core={"schema_name":"batch2-development-pilot13-strict-preingestion-validation-v1","schema_version":"1.0.0","pilot_role":"LEGITIMATE_END_TO_END_MECHANISM_TRIAL","owner_input_request_commit":REQUEST_COMMIT,"owner_input_request_identity":request["owner_input_request_identity"],"declaration_template_identity":request["declaration_template_identity"],"qualification_identity":request["qualification_identity"],"executable_implementation_identity":request["executable_implementation_identity"],"provider_identity":request["provider_identity"],"emitter_identity":request["emitter_identity"],"source_sha256":SOURCE_SHA,"source_byte_length":len(sb),"declaration_sha256":DECL_SHA,"declaration_byte_length":len(db),"bindable_factual_statement_candidates":len(sentences),"checks":{"byte_exact_hashes":"PASS","utf8_no_bom_lf_only_one_terminal_lf":"PASS","completed_exact_declaration_schema":"PASS","owner_authorship_rights_authority":"PASS","strict_noninheritance":"PASS","neutral_nonhumorous_factual_authority":"PASS","scope_modality_time_known_unknown_boundaries":"PASS","pilot01_through_12_source_line_entity_event_independence":"PASS","revision_sibling_same_event_syndication":"PASS_ABSENT_OWNER_ATTESTED_AND_DETERMINISTIC_SCAN","wording_and_source_structure_reuse":"PASS_ABSENT","downstream_and_expected_outcome_shaping":"PASS_ABSENT"},"prior_fivegram_overlap_count":len(overlap),"deterministic_blockers":[],"repair_performed":False,"repair_state":"NONE_INPUTS_VALIDATED_BYTE_EXACT","proposition_binding_selection_or_sufficiency_performed":False,"downstream_suitability_evaluated":False,"authority_matrix":{k:False for k in ("prospective_identity_derivation","proposition_binding","proposition_selection","proposition_sufficiency","signing","signature_verification","ingestion","archive_write","ledger_advancement","g01a","g01b","assignment","constructor_compatibility","semantic_plan","constructor_release","constructor_invocation","realization","candidate_emission","fragment_collision","g02","g02c","g03","g03b","g03c","romanian_naturalness","voice","owner_review","g04b","model_exposure","training","runtime_integration","production_routing")},"validation_verdict":"PASS_STRICT_PREINGESTION_VALIDATION_ONLY"}
    artifact={**core,"validation_identity":seal("B2_DEVELOPMENT_PILOT13_STRICT_PREINGESTION_VALIDATION_V1",core)};write=ART/"humor-mechanics-batch2-development-pilot13-strict-preingestion-validation-v1.json";require(not write.exists(),"artifact exists");write.write_text(json.dumps(artifact,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n");print(json.dumps({"validation_verdict":artifact["validation_verdict"],"validation_identity":artifact["validation_identity"],"candidates":len(sentences),"deterministic_blockers":[],"repair_performed":False},sort_keys=True))
if __name__=="__main__":main()
