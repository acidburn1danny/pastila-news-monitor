"""Evaluation-only durable Stage P executor bound to runner/controller V3."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import VENV_PYTHON,ExperimentalCoreV12Executor,_PROMPT_RELATIVE,_wsl_path

from .append_only_lifecycle_v1 import AppendOnlyLifecycleV1

RUNNER_RELATIVE=Path("src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v3.py")
RUNNER_SHA256="617ee34bd05c6a32de81714b0b07bedb2f10464f0e43213258cdf8886e0c57db"
DEPENDENCY_IDENTITIES={
    Path("src/pastila_scout/semantic_admission_v2/stage_p_trie_projector_v1.py"):"8cc6f68f1ff9751ab983306e9fb39efa0ae55c52cbe8a0471a2e5e98bfc54529",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_callback_controller_v1.py"):"33f1d8fc18684e97c499b98877f3bae8682c70d7295a6e4c755d42b0ce629b37",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_incremental_tracker_v1.py"):"03a332934b1e778168c200bd5c4aad24adaf33cd7eb69a5f51c8ae535887205e",
}


class DurableConstrainedStagePCoreV12ExecutorV3(ExperimentalCoreV12Executor):
    def __init__(self,*,project_root:Path,durable_lifecycle_root:Path,max_output_tokens:int=1400)->None:
        super().__init__(project_root=project_root,max_output_tokens=max_output_tokens)
        self._durable_root=durable_lifecycle_root.resolve();self._durable_root.mkdir(parents=True,exist_ok=True)
        identities={RUNNER_RELATIVE:RUNNER_SHA256,**DEPENDENCY_IDENTITIES}
        for relative,expected in identities.items():
            target=self._project_root/relative
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
                raise RuntimeError(f"durable Stage P V3 identity drift: {relative.as_posix()}")

    def _invoke(self,authority,trace_path:Path,trace:dict[str,object])->dict[str,object]:
        unit=authority.request_envelope.request_units[0]
        request_digest=hashlib.sha256(authority.context.request_id.encode()).hexdigest()
        lifecycle_root=self._durable_root/request_digest;lifecycle_root.mkdir(parents=False,exist_ok=False)
        events=AppendOnlyLifecycleV1(lifecycle_root,actor="host")
        payload={"prompt":"\n\n".join(message.content for message in unit.messages),"max_new_tokens":self._max_output_tokens}
        with tempfile.TemporaryDirectory(prefix="pastila-stage-p-durable-v3-") as directory:
            root=Path(directory);request_path=root/"request.json";response_path=root/"response.json"
            request_path.write_text(json.dumps(payload,ensure_ascii=False),"utf-8")
            runner=self._project_root/RUNNER_RELATIVE
            command=["wsl.exe","-d","Ubuntu-24.04","--",VENV_PYTHON,_wsl_path(runner),_wsl_path(request_path),
                _wsl_path(response_path),_wsl_path(self._project_root/_PROMPT_RELATIVE),_wsl_path(lifecycle_root)]
            events.emit("HOST_LAUNCH",request_id_sha256=request_digest,request_sha256=hashlib.sha256(request_path.read_bytes()).hexdigest(),
                runner_sha256=RUNNER_SHA256,dependency_identities={path.as_posix():value for path,value in DEPENDENCY_IDENTITIES.items()},
                timeout_seconds=authority.timeout_policy.timeout_seconds)
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0));events.emit("HOST_PROCESS_STARTED",pid=process.pid)
            try:
                stdout,stderr=process.communicate(timeout=authority.timeout_policy.timeout_seconds)
            except subprocess.TimeoutExpired:
                events.emit("HOST_TIMEOUT",pid=process.pid);process.terminate();termination="TERMINATED"
                try: stdout,stderr=process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill();stdout,stderr=process.communicate();termination="KILLED"
                events.emit("HOST_TERMINATION_OBSERVED",pid=process.pid,termination=termination,returncode=process.returncode);raise
            events.emit("HOST_PROCESS_EXITED",pid=process.pid,returncode=process.returncode,
                stdout_tail=(stdout or "")[-1000:],stderr_tail=(stderr or "")[-1000:],response_exists=response_path.is_file())
            if process.returncode!=0 or not response_path.is_file(): raise RuntimeError("durable Stage P V3 runner failed")
            result=json.loads(response_path.read_text("utf-8"))
            if set(result)!={"output","terminal_eos","constraint_active"} or result["constraint_active"] is not True or not result["output"]:
                raise ValueError("durable Stage P V3 response invalid")
            events.emit("HOST_RESPONSE_VALIDATED",response_sha256=hashlib.sha256(response_path.read_bytes()).hexdigest(),terminal_eos=result["terminal_eos"])
            return {"output":result["output"],"terminal_eos":result["terminal_eos"]}


__all__=("DurableConstrainedStagePCoreV12ExecutorV3",)
