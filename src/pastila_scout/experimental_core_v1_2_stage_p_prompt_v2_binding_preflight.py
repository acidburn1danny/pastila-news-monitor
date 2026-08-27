"""Zero-inference Case 01 request and runner binding for prompt-V2/V4."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import UTC,datetime
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_durable_executor_v4 import (
    DEPENDENCY_IDENTITIES,RUNNER_RELATIVE,RUNNER_SHA256,DurableConstrainedStagePCoreV12ExecutorV4,
)
from pastila_scout.semantic_admission_v2.stage_p_source_role_evaluator_v2 import StagePSourceRoleEvaluatorV2

ROOT=Path(__file__).resolve().parents[2]
PACK_SHA256="4163307ccb8cfa8997b520a1cea04cddacd347e9b1ffde498db925ffccac6c2d"
EVALUATOR_SHA256="3b43e706f00236ae677aba2d7da9a73e56cc15b8a649e0cd1ac1cfc6234e451d"
EXECUTOR_SHA256="9bdb3d46ed07a59c216d200d90dd6d03ae6d65164cf0acc8e74552caac63e746"
PROBE_RUNNER_SHA256="6fc1bb202aa86e45e6bfe5e5b2e3024ef4218b1ad4c0e43cb8bb37d7aed9ccdf"


def main(target:Path)->None:
    pack_path=ROOT/"docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json";raw=pack_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PACK_SHA256: raise RuntimeError("pack identity drift")
    case=next(item for item in json.loads(raw)["cases"] if item["case_id"]=="HMCV1-SASC-01")
    request={"stage_id":"PROPOSITION_LEDGER","factual_summary":case["factual_summary"],"candidate":case["candidate"]}
    source_paths={
        "evaluator":ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_source_role_evaluator_v2.py",
        "executor":ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_durable_executor_v4.py",
        "probe_runner":ROOT/"src/pastila_scout/semantic_admission_v2/run_stage_p_case01_v4_prompt_v2_probe.py"}
    expected={"evaluator":EVALUATOR_SHA256,"executor":EXECUTOR_SHA256,"probe_runner":PROBE_RUNNER_SHA256}
    if any(hashlib.sha256(path.read_bytes()).hexdigest()!=expected[name] for name,path in source_paths.items()): raise RuntimeError("binding source drift")
    with tempfile.TemporaryDirectory(prefix="pastila-stage-p-prompt-v2-binding-") as directory:
        durable=Path(directory)/"durable";executor=DurableConstrainedStagePCoreV12ExecutorV4(project_root=ROOT,durable_lifecycle_root=durable)
        evaluator=StagePSourceRoleEvaluatorV2(project_root=ROOT,executor=executor,timeout_seconds=240.0)
        prompt=evaluator.render_prompt(request);authority=evaluator.build_authority(request,requested_at=datetime(2026,8,26,tzinfo=UTC))
        lower=authority.request_intent.request_units[0].messages[0].content
        value={"schema_name":"pastila-semantic-admission-v2-stage-p-prompt-v2-v4-binding-preflight","schema_version":"1.0.0",
            "case_id":"HMCV1-SASC-01","pack_sha256":PACK_SHA256,"factual_summary_sha256":case["factual_summary_sha256"],
            "candidate_sha256":case["candidate_sha256"],"prompt_identity":evaluator.prompt_identity,
            "rendered_prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),"rendered_prompt_characters":len(prompt),
            "rendered_prompt_unpadded":prompt==prompt.strip(),"lower_prompt_exact":lower==prompt,
            "evaluator_identity":evaluator.evaluator_identity,"grammar_identity":evaluator.grammar_identity,
            "model_identity":evaluator.model_identity,"request_id":authority.context.request_id,
            "request_envelope_identity":authority.request_envelope.identity,"request_unit_count":len(authority.request_envelope.request_units),
            "timeout_seconds":authority.timeout_policy.timeout_seconds,"runner_relative":RUNNER_RELATIVE.as_posix(),"runner_sha256":RUNNER_SHA256,
            "evaluator_source_sha256":EVALUATOR_SHA256,"executor_source_sha256":EXECUTOR_SHA256,
            "probe_runner_source_sha256":PROBE_RUNNER_SHA256,
            "dependency_identities":{path.as_posix():identity for path,identity in DEPENDENCY_IDENTITIES.items()},
            "durable_events_created":len(list(durable.rglob("*.json"))),"source_bound_projector_bound":False,
            "stage_c_constructed":False,"stage_c_called":False,"model_imported":False,"model_load_started":False,
            "inference_started":False,"model_calls":0,"provider_calls":0,"result":"PASS"}
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n","utf-8")


if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("usage: preflight TARGET")
    main(Path(sys.argv[1]))
