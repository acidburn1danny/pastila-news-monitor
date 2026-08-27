"""Evaluation-only provider adapters for the authorized two-case staged proof."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1,ApplicationRequestAuthorityV1
from pastila_scout.experimental_core_v1_2 import VENV_PYTHON,ExperimentalCoreV12Executor,_PROMPT_RELATIVE,_wsl_path
from pastila_scout.provider_execution_v2 import CancellationTokenV2,ExecutionOutcomeV2,TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import ProviderFinishReasonV2,ProviderResultStatusV2

from .staged_gate_f_contract_v1 import PropositionLedgerV1,StagedGateFPromptContractV1

STAGE_P_RUNNER_RELATIVE=Path("src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner.py")
STAGE_P_RUNNER_SHA256="089a73a83c18eb080b08a55d8b9a224a8beb3835a996c610e16b5506cc2ba644"
STAGE_P_GRAMMAR_IDENTITY="sha256:019040dc2e424a57671221e1800d5b9dab100b31f6a23c85fca59cfebb541007"
STAGE_C_GRAMMAR_IDENTITY="sha256:"+hashlib.sha256((Path(__file__).parent/"gate_f_constraint_v1.py").read_bytes()).hexdigest()
MODEL_IDENTITY="pastila-editor-core-v1.2-experimental"


class ConstrainedStagePCoreV12ExecutorV1(ExperimentalCoreV12Executor):
    def __init__(self,*,project_root:Path,max_output_tokens:int=1400)->None:
        super().__init__(project_root=project_root,max_output_tokens=max_output_tokens)
        runner=self._project_root/STAGE_P_RUNNER_RELATIVE
        if not runner.is_file() or hashlib.sha256(runner.read_bytes()).hexdigest()!=STAGE_P_RUNNER_SHA256:
            raise RuntimeError("Stage P constrained runner identity drift")

    def _invoke(self,authority,trace_path:Path,trace:dict[str,object])->dict[str,object]:
        if len(authority.request_envelope.request_units)!=1: raise ValueError("Stage P requires exactly one request unit")
        unit=authority.request_envelope.request_units[0]
        payload={"prompt":"\n\n".join(message.content for message in unit.messages),"max_new_tokens":self._max_output_tokens}
        runner=self._project_root/STAGE_P_RUNNER_RELATIVE
        with tempfile.TemporaryDirectory(prefix="pastila-stage-p-constrained-") as directory:
            root=Path(directory);request_path=root/"request.json";response_path=root/"response.json";runner_trace=root/"runner-lifecycle.json"
            request_path.write_text(json.dumps(payload,ensure_ascii=False),"utf-8")
            trace.update(runner_path=_wsl_path(runner),runner_launch_attempted=True,constraint_active=True,stage="PROPOSITION_LEDGER")
            self._write_trace(trace_path,trace)
            completed=subprocess.run(["wsl.exe","-d","Ubuntu-24.04","--",VENV_PYTHON,_wsl_path(runner),_wsl_path(request_path),
                _wsl_path(response_path),_wsl_path(self._project_root/_PROMPT_RELATIVE),_wsl_path(runner_trace)],check=False,capture_output=True,
                text=True,encoding="utf-8",errors="replace",timeout=authority.timeout_policy.timeout_seconds,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if runner_trace.is_file(): trace.update(json.loads(runner_trace.read_text("utf-8")))
            trace.update(stderr_tail=(completed.stderr or "")[-4000:],stdout_tail=(completed.stdout or "")[-4000:],response_received=response_path.is_file())
            self._write_trace(trace_path,trace)
            if completed.returncode!=0 or not response_path.is_file(): raise RuntimeError("Stage P constrained local runner failed")
            result=json.loads(response_path.read_text("utf-8"))
            if set(result)!={"output","terminal_eos","constraint_active"} or result["constraint_active"] is not True or not result["output"]:
                raise ValueError("Stage P constrained runner returned invalid response")
            return {"output":result["output"],"terminal_eos":result["terminal_eos"]}


class StagedCoreV12EvaluatorV1:
    def __init__(self,*,project_root:Path,executor,stage:str,timeout_seconds:float=240.0)->None:
        if stage not in {"P","C"}: raise ValueError("unknown staged evaluator")
        self.stage=stage;self._executor=executor;self._timeout=timeout_seconds
        self._contract=StagedGateFPromptContractV1(project_root)
        self.prompt_identity=self._contract.stage_p_prompt_identity if stage=="P" else self._contract.stage_c_prompt_identity
        self.grammar_identity=STAGE_P_GRAMMAR_IDENTITY if stage=="P" else STAGE_C_GRAMMAR_IDENTITY
        self.model_identity=MODEL_IDENTITY
        self.evaluator_identity=hashlib.sha256(f"{stage}\n{self.prompt_identity}\n{self.grammar_identity}\n{MODEL_IDENTITY}".encode()).hexdigest()

    def render_prompt(self,request:dict[str,object])->str:
        summary,candidate=request.get("factual_summary"),request.get("candidate")
        if type(summary) is not str or type(candidate) is not str: raise ValueError("staged source text invalid")
        if self.stage=="P": return self._contract.render_stage_p(factual_summary=summary,candidate=candidate)
        ledger=PropositionLedgerV1.model_validate_json(json.dumps(request.get("stage_p_ledger"),ensure_ascii=False,separators=(",",":")))
        return self._contract.render_stage_c(factual_summary=summary,candidate=candidate,ledger=ledger)

    def __call__(self,request:dict[str,object])->str:
        prompt=self.render_prompt(request)
        authority=ApplicationRequestAuthorityV1().build(ApplicationProviderRequestV1(ProviderChoiceV1.OLLAMA,prompt,
            f"semantic-admission-v2:staged-{self.stage.lower()}:{hashlib.sha256(prompt.encode()).hexdigest()[:32]}",datetime.now(UTC),
            TimeoutPolicyV2(timeout_seconds=self._timeout),CancellationTokenV2(cancellation_requested=False)))
        result=self._executor.execute(authority)
        if(result.outcome is not ExecutionOutcomeV2.COMPLETED or result.provider_result is None
            or result.provider_result.status is not ProviderResultStatusV2.SUCCESS or len(result.provider_result.outputs)!=1
            or result.provider_result.outputs[0].finish_reason is not ProviderFinishReasonV2.COMPLETED):
            raise RuntimeError(f"staged {self.stage} evaluator failed")
        return result.provider_result.outputs[0].generated_text


__all__=("ConstrainedStagePCoreV12ExecutorV1","StagedCoreV12EvaluatorV1","MODEL_IDENTITY",
    "STAGE_P_GRAMMAR_IDENTITY","STAGE_C_GRAMMAR_IDENTITY")
