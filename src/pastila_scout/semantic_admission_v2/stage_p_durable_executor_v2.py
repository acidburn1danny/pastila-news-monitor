"""Evaluation-only Stage P executor with timeout-surviving append-only lifecycle."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import VENV_PYTHON,ExperimentalCoreV12Executor,_PROMPT_RELATIVE,_wsl_path

from .append_only_lifecycle_v1 import AppendOnlyLifecycleV1

RUNNER_RELATIVE=Path("src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v2.py")
RUNNER_SHA256="dfd4e97f59d92611307e8c5fd8413bb4177f67afcedc45f86f460d4aeb4467ad"


class DurableConstrainedStagePCoreV12ExecutorV2(ExperimentalCoreV12Executor):
    def __init__(self,*,project_root:Path,durable_lifecycle_root:Path,max_output_tokens:int=1400)->None:
        super().__init__(project_root=project_root,max_output_tokens=max_output_tokens)
        self._durable_root=durable_lifecycle_root.resolve();self._durable_root.mkdir(parents=True,exist_ok=True)
        runner=self._project_root/RUNNER_RELATIVE
        if not runner.is_file() or hashlib.sha256(runner.read_bytes()).hexdigest()!=RUNNER_SHA256:
            raise RuntimeError("durable Stage P runner identity drift")

    def _invoke(self,authority,trace_path:Path,trace:dict[str,object])->dict[str,object]:
        unit=authority.request_envelope.request_units[0]
        request_digest=hashlib.sha256(authority.context.request_id.encode()).hexdigest()
        lifecycle_root=self._durable_root/request_digest;lifecycle_root.mkdir(parents=False,exist_ok=False)
        events=AppendOnlyLifecycleV1(lifecycle_root,actor="host")
        payload={"prompt":"\n\n".join(message.content for message in unit.messages),"max_new_tokens":self._max_output_tokens}
        with tempfile.TemporaryDirectory(prefix="pastila-stage-p-durable-") as directory:
            root=Path(directory);request_path=root/"request.json";response_path=root/"response.json"
            request_path.write_text(json.dumps(payload,ensure_ascii=False),"utf-8")
            runner=self._project_root/RUNNER_RELATIVE
            command=["wsl.exe","-d","Ubuntu-24.04","--",VENV_PYTHON,_wsl_path(runner),_wsl_path(request_path),
                _wsl_path(response_path),_wsl_path(self._project_root/_PROMPT_RELATIVE),_wsl_path(lifecycle_root)]
            events.emit("HOST_LAUNCH",request_id_sha256=request_digest,request_sha256=hashlib.sha256(request_path.read_bytes()).hexdigest(),
                runner_sha256=RUNNER_SHA256,timeout_seconds=authority.timeout_policy.timeout_seconds)
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0));events.emit("HOST_PROCESS_STARTED",pid=process.pid)
            try:
                stdout,stderr=process.communicate(timeout=authority.timeout_policy.timeout_seconds)
            except subprocess.TimeoutExpired:
                events.emit("HOST_TIMEOUT",pid=process.pid)
                process.terminate();termination="TERMINATED"
                try: stdout,stderr=process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill();stdout,stderr=process.communicate();termination="KILLED"
                events.emit("HOST_TERMINATION_OBSERVED",pid=process.pid,termination=termination,returncode=process.returncode)
                raise
            events.emit("HOST_PROCESS_EXITED",pid=process.pid,returncode=process.returncode,
                stdout_tail=(stdout or "")[-1000:],stderr_tail=(stderr or "")[-1000:],response_exists=response_path.is_file())
            if process.returncode!=0 or not response_path.is_file(): raise RuntimeError("durable Stage P runner failed")
            result=json.loads(response_path.read_text("utf-8"))
            if set(result)!={"output","terminal_eos","constraint_active"} or result["constraint_active"] is not True or not result["output"]:
                raise ValueError("durable Stage P response invalid")
            events.emit("HOST_RESPONSE_VALIDATED",response_sha256=hashlib.sha256(response_path.read_bytes()).hexdigest(),terminal_eos=result["terminal_eos"])
            return {"output":result["output"],"terminal_eos":result["terminal_eos"]}


__all__=("DurableConstrainedStagePCoreV12ExecutorV2",)
