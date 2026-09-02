"""Static validation for objective authority-selection governance V2.1."""
from __future__ import annotations
import hashlib,json
from typing import Any,Mapping

def canonical_identity(value:Mapping[str,Any],field:str)->str:
 body={k:v for k,v in value.items() if k!=field}
 return hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def validate_policy(v:Mapping[str,Any])->None:
 required={"governance_identity","snapshots","frame","external_commitment","entropy","selection","source_version","scope","extraction","execution_lifecycle"}
 if required-set(v):raise ValueError("incomplete V2.1 policy")
 if v["governance_identity"]!=canonical_identity(v,"governance_identity"):raise ValueError("identity mismatch")
 s=v["snapshots"]
 if s.get("roots")!=["CROSSREF_ANNUAL_PUBLIC_DATA_FILE","OPENALEX_PUBLIC_SNAPSHOT"]:raise ValueError("root skew")
 if s.get("selector")!="EARLIEST_OFFICIAL_RELEASE_WITH_PUBLICATION_TIMESTAMP_AFTER_V1_FREEZE":raise ValueError("snapshot choice")
 if s.get("official_manifest_and_complete_archive_digest_required") is not True:raise ValueError("snapshot proof")
 if s.get("unavailable_or_unverifiable")!="TERMINAL_NO_FRAME":raise ValueError("snapshot fallback")
 f=v["frame"]
 if f.get("key")!="NORMALIZED_DOI_ELSE_REGISTRY_NAMESPACE_PLUS_STABLE_ID":raise ValueError("frame key")
 if f.get("cross_registry_merge")!="ONE_KEY_ONE_ENTRY_ALL_PROVENANCE_RETAINED":raise ValueError("duplicate weighting")
 if f.get("allowed_filters")!=["STABLE_KEY_PRESENT","IMMUTABLE_CONTENT_DIGEST_PRESENT","EXPLICIT_ACQUISITION_RIGHT_PRESENT"]:raise ValueError("filter discretion")
 if f.get("semantic_fields_projected") is not False or f.get("complete_decision_log") is not True:raise ValueError("frame shaping")
 c=v["external_commitment"]
 if c.get("service")!="SIGSTORE_REKOR_PUBLIC_TRANSPARENCY_LOG" or c.get("inclusion_and_signed_tree_head_required") is not True:raise ValueError("commit anchor")
 if c.get("canonical_commitment")!="EARLIEST_VALID_LOG_INDEX_FOR_GOVERNANCE_AND_SNAPSHOT_TUPLE":raise ValueError("multi-commit grinding")
 if c.get("git_or_local_time_authoritative") is not False:raise ValueError("local time authority")
 e=v["entropy"]
 if e.get("chain_hash")!="52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971":raise ValueError("entropy chain")
 if e.get("round_rule")!="FIRST_ROUND_AT_OR_AFTER_REKOR_INTEGRATED_TIME_PLUS_86400_SECONDS":raise ValueError("round choice")
 if e.get("signature_verification") is not True:raise ValueError("entropy proof")
 q=v["selection"]
 if q.get("algorithm")!="SHA256_REJECTION_SAMPLING_V2_1" or q.get("integer_encoding")!="UNSIGNED_BIG_ENDIAN_256":raise ValueError("sampling ambiguity")
 if q.get("acceptance")!="X_LESS_THAN_FLOOR_2_POW_256_DIV_N_TIMES_N":raise ValueError("modulo bias")
 if q.get("retry_input")!="DOMAIN_PLUS_SEED_PLUS_UINT64_BE_COUNTER_STARTING_ZERO":raise ValueError("retry ambiguity")
 if q.get("draws")!=1 or q.get("redraw") is not False:raise ValueError("redraw")
 x=v["source_version"]
 if x.get("selected_entry_requires_preexisting_content_digest") is not True or x.get("digest_mismatch")!="TERMINAL_NO_SOURCE_NO_REDRAW":raise ValueError("mutable content")
 if v["scope"].get("rule")!="EXACT_BYTES_MATCHING_PREEXISTING_CONTENT_DIGEST":raise ValueError("scope")
 a=v["extraction"]
 if a.get("segmenter_identity_frozen_before_frame") is not True or a.get("visit_all_segments") is not True or a.get("drop_segments") is not False:raise ValueError("extraction selection")
 if a.get("coverage_visible") is not False or a.get("complete_negative_space") is not True:raise ValueError("extraction shaping")
 l=v["execution_lifecycle"]
 if l.get("abort_after_external_commitment")!="TERMINAL_RECORDED_NO_RESTART" or l.get("new_run_same_governance") is not False:raise ValueError("selective abort")
 if l.get("all_attempts_discoverable_from_transparency_log") is not True:raise ValueError("suppressed attempts")
