"""Strict Pilot 14 pre-ingestion validation; emits receipt JSON to stdout only."""
from __future__ import annotations
import hashlib, json, re, subprocess, unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "owner-source-pilot14-v1.txt"
DECL = ROOT / "owner-declaration-pilot14-v1.json"
ART = ROOT / "docs" / "artifacts"
SOURCE_SHA = "aec2bccf7ec0cc9f059785d00be1fe891a5b4c64b834da0cb9743518ff9e512d"
DECL_SHA = "6f00f326d4f40d82bb856bb1d737f4b859af8f9b0285168d36b91913f01b5580"
REQUEST_SHA = "45fcec1a037f065b312414b7c39820ae8a70ad6580cfd27754b4a8f75bb76025"
TEMPLATE_SHA = "87d5f0f579b4773e660f58a85fa3dafdf48b89f6e2b539af3e02ae48576be835"

def require(value: bool, message: str) -> None:
    if not value: raise SystemExit(message)

def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}"); result[key] = value
    return result

def shape(actual, template, path="$".strip()):
    if isinstance(template, dict):
        require(isinstance(actual, dict) and set(actual) == set(template), f"{path} field set")
        for key in template: shape(actual[key], template[key], f"{path}.{key}")

def words(text: str):
    return re.findall(r"[^\W\d_]+|\d+", unicodedata.normalize("NFKC", text).casefold(), re.UNICODE)

def ngrams(text: str, n: int = 5):
    tokens = words(text); return {tuple(tokens[i:i+n]) for i in range(max(0, len(tokens)-n+1))}

def git_source(pilot: int) -> bytes:
    path = f"docs/artifacts/humor-mechanics-batch2-development-pilot{pilot:02d}-ingestion-v1/source.utf8.txt"
    return subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT)

def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def main() -> None:
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECL.read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest() == SOURCE_SHA, "source hash")
    require(hashlib.sha256(declaration_bytes).hexdigest() == DECL_SHA, "declaration hash")
    for name, data in (("source", source_bytes), ("declaration", declaration_bytes)):
        require(not data.startswith(b"\xef\xbb\xbf"), f"{name} BOM")
        require(b"\r" not in data, f"{name} CR line ending")
        data.decode("utf-8")
        require(data.endswith(b"\n") and not data.endswith(b"\n\n"), f"{name} terminal LF")
    template_path = ART / "humor-mechanics-batch2-development-pilot14-owner-declaration-template-v1.json"
    request_path = ART / "humor-mechanics-batch2-development-pilot14-owner-input-request-v1.json"
    require(hashlib.sha256(template_path.read_bytes()).hexdigest() == TEMPLATE_SHA, "template binding")
    require(hashlib.sha256(request_path.read_bytes()).hexdigest() == REQUEST_SHA, "request binding")
    template = json.loads(template_path.read_bytes(), object_pairs_hook=unique)
    declaration = json.loads(declaration_bytes, object_pairs_hook=unique)
    shape(declaration, template)
    require(declaration["schema_name"] == "batch2-owner-declaration-pilot14-v1", "schema")
    require(declaration["pilot_id"] == "BATCH2-DEVELOPMENT-PILOT-14", "pilot")
    require(declaration["trial_role"] == "GENUINE_END_TO_END_MECHANISM_TRIAL", "role")
    metadata = declaration["source"]
    require(metadata["filename"] == SOURCE.name and metadata["world_scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE", "source metadata")
    captured = datetime.fromisoformat(metadata["capture_timestamp"]); acquired = datetime.fromisoformat(metadata["acquisition_timestamp"])
    require(captured.tzinfo is not None and acquired.tzinfo is not None and captured <= acquired, "timestamps")
    ownership = declaration["ownership_declarations"]
    require(all(ownership[k] is True for k in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "rights")
    require(all(ownership[k] is False for k in ownership if k not in {"original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant"}), "excluded material")
    grants = declaration["independent_grants"]
    require(all(grants[k] is True for k in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "required grants")
    require(all(grants[k] is False for k in ("model_exposure", "training", "runtime_integration", "production_routing")), "strict noninheritance")
    require(all(value is True for value in declaration["source_status_declarations"].values()), "source declarations")
    require(declaration["owner_confirmation"]["confirmed"] is True, "owner confirmation")
    instruction = declaration["owner_instruction"]
    require(instruction["request_preingestion_validation_only"] is True and instruction["operational_content_access_after_ingestion"] is False, "owner instruction")
    source = source_bytes.decode("utf-8"); folded = source.casefold()
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", source.strip()) if x]
    require(len(sentences) >= 2, "minimum bindable propositions")
    prohibited = ("glum", "poant", "parodi", "mecanism", "constructor", "affordance", "witness", "g02", "g03", "pilot 13")
    require(not any(token in folded for token in prohibited), "neutrality or prohibited shaping")
    required = ("30 august 2026", "22 de rame", "expoziție temporară", "număr de inventar", "lățime", "înălțime", "nu au fost mutate", "nu era cunoscut")
    require(all(token in folded for token in required), "time scope modality or unknown boundary")
    prior = [git_source(i) for i in range(1, 14)]
    require(source_bytes not in prior, "prior source equality")
    prior_texts = [raw.decode("utf-8") for raw in prior]
    current_lines = {line for line in source.splitlines() if line}
    prior_lines = {line for text in prior_texts for line in text.splitlines() if line}
    require(not current_lines & prior_lines, "exact prior line reuse")
    overlap = ngrams(source) & set().union(*(ngrams(text) for text in prior_texts))
    require(len(overlap) <= 2, "prior wording/source-structure reuse")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    require(request["acquisition_boundaries"]["source_acquisition_independent_of_v5_4_ontology_and_rule_inventory"] is True, "V5.4 acquisition independence")
    core = {
        "schema_name":"batch2-development-pilot14-strict-preingestion-validation-v1",
        "pilot_role":"GENUINE_END_TO_END_MECHANISM_TRIAL",
        "source_sha256":SOURCE_SHA,"source_byte_length":len(source_bytes),
        "declaration_sha256":DECL_SHA,"declaration_byte_length":len(declaration_bytes),
        "owner_input_request_identity":REQUEST_SHA,"declaration_template_identity":TEMPLATE_SHA,
        "bindable_factual_statement_candidates":len(sentences),
        "candidate_status":"PASS_NOT_YET_BOUND_OR_SELECTED",
        "independence":"PASS_PILOTS_01_THROUGH_13_NO_EXACT_SOURCE_OR_LINE_REUSE",
        "prior_fivegram_overlap_count":len(overlap),
        "revision_same_event_syndication_source_family":"PASS_ABSENT_OWNER_ATTESTED_AND_DETERMINISTIC_SCAN",
        "prohibited_shaping":"PASS_ABSENT",
        "v5_4_ontology_rule_inventory_independence":"PASS",
        "deterministic_blockers":[],"repair_state":"NONE_INPUTS_VALIDATED_BYTE_EXACT",
        "downstream_suitability_evaluated":False,"proposition_selected":False,
        "validation_verdict":"PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    }
    identity = hashlib.sha256(canonical({"namespace":"B2_DEVELOPMENT_PILOT14_STRICT_PREINGESTION_VALIDATION_V1","value":core})).hexdigest()
    print(json.dumps({**core, "validation_identity":identity}, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__": main()
