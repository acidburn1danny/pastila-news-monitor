from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/".semantic-admission-v2-stage-p-construction-obligation-v2-one-shot-model-load-v1-evidence"


def test_manifest_identity_and_every_raw_lifecycle_file():
    manifest=json.loads((EVIDENCE/"manifest.json").read_text("utf-8"))
    identity=hashlib.sha256("\n".join(manifest["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest()
    assert identity==manifest["canonical_identity"]=="49b74b00edb7fde2afea3c46cdc2ad53ad7910e1cec418e0ae686b9c87ae8134"
    for entry in manifest["files"]:
        raw=(EVIDENCE/entry["path"]).read_bytes()
        assert len(raw)==entry["size"]
        assert hashlib.sha256(raw).hexdigest()==entry["sha256"]


def test_result_is_one_attempt_load_only_and_warning_bounded():
    result=json.loads((EVIDENCE/"result.json").read_text("utf-8"))
    assert result["attempts_authorized"]==result["attempts_consumed"]==1
    assert result["model_load_completed"] is result["adapter_attach_completed"] is True
    assert result["cleanup_completed"] is True
    assert result["compatibility_observations"]==[
      "TRANSFORMERS_TIED_WEIGHT_CONFIGURATION_WARNING",
      "PEFT_MISSING_VISION_TOWER_ADAPTER_KEYS_WARNING"]
    assert result["raw_stderr_persisted"] is False
    assert (result["generation_calls"],result["retry_calls"],result["fallback_calls"],
            result["stage_c_entries"])==(0,0,0,0)
    assert result["generation_readiness"]=="NOT_GRANTED"


def test_wsl_receipt_binds_consumed_authority_and_stderr_hash():
    receipt=json.loads((EVIDENCE/"wsl-execution-receipt.json").read_text("utf-8"))
    result=json.loads((EVIDENCE/"result.json").read_text("utf-8"))
    assert receipt["authority_reference"]=="4fa3865ffc6fd10bdaa7ec969d5f630651d877bf631cc44f2bde9bfebddfb674"
    assert receipt["return_code"]==0 and receipt["timed_out"] is False
    assert receipt["stderr_sha256"]==result["raw_stderr_sha256"]
