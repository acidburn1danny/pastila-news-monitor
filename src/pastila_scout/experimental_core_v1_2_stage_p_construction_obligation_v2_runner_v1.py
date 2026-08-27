"""Source-only Construction-Obligation V2 runner candidate; no entry point."""
from __future__ import annotations
import importlib
from pathlib import Path
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import RunnerRequestV1,parse_runner_request_v1

RUNNER_IDENTITY="4f2c2b790b1e6f843e81fba418935f629867cf179fda3f548caac9f1306d03c2"

def validate_request_only_v1(*,request_path:Path)->RunnerRequestV1:
 if not isinstance(request_path,Path) or not request_path.is_file():raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_FILE_REQUIRED")
 raw=request_path.read_bytes()
 if len(raw)>600_000:raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_TOO_LARGE")
 return parse_runner_request_v1(raw_request=raw)

def _deferred_runtime_imports_after_validation(*,validated_request:RunnerRequestV1):
 if type(validated_request)is not RunnerRequestV1:raise TypeError("CONSTRUCTION_OBLIGATION_V2_VALIDATED_RUNNER_REQUEST_REQUIRED")
 return tuple(importlib.import_module(name) for name in ("torch","transformers","peft"))

__all__=("RUNNER_IDENTITY","validate_request_only_v1")
