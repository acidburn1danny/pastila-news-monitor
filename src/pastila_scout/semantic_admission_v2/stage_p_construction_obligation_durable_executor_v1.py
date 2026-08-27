"""Durable evaluation-only executor for Construction Obligation Projection V1."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import ExperimentalCoreV12Executor, _PROMPT_RELATIVE, _wsl_path

from .append_only_lifecycle_v1 import AppendOnlyLifecycleV1
from .durable_lifecycle_reconciliation_v1 import reconcile_durable_lifecycle_v1
from .stage_p_construction_role_durable_executor_v1 import DEPENDENCY_IDENTITIES as BASE_DEPENDENCIES
from .stage_p_scope_graph_durable_executor_v1_2 import (
    StagePConstraintLivenessExecutionErrorV1, read_constraint_liveness_failure_v1,
)


RUNNER_RELATIVE = Path("src/pastila_scout/experimental_core_v1_2_stage_p_construction_obligation_runner_v1.py")
RUNNER_SHA256 = "1669926e3e69ba6bbf1c7c7368edfbb7a8485fa14458d0bcae50a3272c6ffe17"
WSL_DISTRIBUTION = "Ubuntu-24.04"
VENV_PYTHON = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/.venv/bin/python3"
DEPENDENCY_IDENTITIES = {
    **BASE_DEPENDENCIES,
    Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_constraint_v1.py"): "a5db3847530e1208fbc96f5a4af6e577b248ec2507c9045280b648420d0ad935",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_incremental_tracker_v1.py"): "259f1c06d8aa81bf027484bab64fcb532f109a8ee6821637ec5519c3b5b77e9a",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_callback_controller_v1.py"): "2d62132520164cdacf277e2b68975688a02bb294e301811a71e16afa74f21178",
}


class DurableConstructionObligationStagePExecutorV1(ExperimentalCoreV12Executor):
    def __init__(self, *, project_root: Path, durable_lifecycle_root: Path,
                 max_output_tokens: int = 3200) -> None:
        super().__init__(project_root=project_root, max_output_tokens=max_output_tokens)
        self._durable_root = durable_lifecycle_root.resolve()
        self._durable_root.mkdir(parents=True, exist_ok=True)
        for relative, expected in {RUNNER_RELATIVE: RUNNER_SHA256, **DEPENDENCY_IDENTITIES}.items():
            target = self._project_root / relative
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"construction-obligation dependency identity drift: {relative.as_posix()}")

    def _invoke(self, authority, trace_path: Path, trace: dict[str, object]) -> dict[str, object]:
        unit = authority.request_envelope.request_units[0]
        digest = hashlib.sha256(authority.context.request_id.encode()).hexdigest()
        lifecycle_root = self._durable_root / digest; lifecycle_root.mkdir(parents=False, exist_ok=False)
        events = AppendOnlyLifecycleV1(lifecycle_root, actor="host")
        dependencies = {path.as_posix(): identity for path, identity in DEPENDENCY_IDENTITIES.items()
                        if path.name != "durable_lifecycle_reconciliation_v1.py"}
        payload = {"prompt": "\n\n".join(message.content for message in unit.messages),
                   "max_new_tokens": self._max_output_tokens}
        with tempfile.TemporaryDirectory(prefix="pastila-stage-p-construction-obligation-") as directory:
            root = Path(directory); request_path = root / "request.json"; response_path = root / "response.json"
            request_path.write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
            command = ["wsl.exe", "-d", WSL_DISTRIBUTION, "--", VENV_PYTHON,
                _wsl_path(self._project_root / RUNNER_RELATIVE), _wsl_path(request_path),
                _wsl_path(response_path), _wsl_path(self._project_root / _PROMPT_RELATIVE),
                _wsl_path(lifecycle_root)]
            trace.update(runner_launch_attempted=True,
                         runner_path=_wsl_path(self._project_root / RUNNER_RELATIVE),
                         durable_lifecycle_relative_path=digest); self._write_trace(trace_path, trace)
            events.emit("HOST_LAUNCH", request_id_sha256=digest,
                request_sha256=hashlib.sha256(request_path.read_bytes()).hexdigest(),
                runner_sha256=RUNNER_SHA256, dependency_identities=dependencies,
                timeout_seconds=authority.timeout_policy.timeout_seconds)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            events.emit("HOST_PROCESS_STARTED", pid=process.pid)
            try:
                stdout, stderr = process.communicate(timeout=authority.timeout_policy.timeout_seconds)
            except subprocess.TimeoutExpired:
                events.emit("HOST_TIMEOUT", pid=process.pid); process.terminate()
                try: stdout, stderr = process.communicate(timeout=5); termination = "TERMINATED"
                except subprocess.TimeoutExpired:
                    process.kill(); stdout, stderr = process.communicate(); termination = "KILLED"
                events.emit("HOST_TERMINATION_OBSERVED", pid=process.pid, termination=termination,
                            returncode=process.returncode)
                self._reconcile(trace_path, trace, lifecycle_root, digest, dependencies); raise
            events.emit("HOST_PROCESS_EXITED", pid=process.pid, returncode=process.returncode,
                stdout_tail=(stdout or "")[-1000:], stderr_tail=(stderr or "")[-1000:],
                response_exists=response_path.is_file())
            trace.update(stderr_tail=(stderr or "")[-4000:], stdout_tail=(stdout or "")[-4000:],
                         response_received=response_path.is_file())
            if process.returncode != 0 or not response_path.is_file():
                liveness = read_constraint_liveness_failure_v1(lifecycle_root)
                if liveness is not None:
                    value = liveness.as_json_value(); events.emit("HOST_CONSTRAINT_LIVENESS_FAILURE_CLASSIFIED", **value)
                    trace["failure_classification"] = value
                    self._reconcile(trace_path, trace, lifecycle_root, digest, dependencies)
                    raise StagePConstraintLivenessExecutionErrorV1(liveness)
                trace["failure_classification"] = {"code": "PROVIDER_OR_TRANSPORT_FAILURE"}
                self._reconcile(trace_path, trace, lifecycle_root, digest, dependencies)
                raise RuntimeError("durable construction-obligation runner failed")
            self._reconcile(trace_path, trace, lifecycle_root, digest, dependencies)
            result = json.loads(response_path.read_text("utf-8"))
            if (set(result) != {"output", "terminal_eos", "constraint_active"}
                    or result["constraint_active"] is not True or not result["output"]):
                raise ValueError("durable construction-obligation response invalid")
            events.emit("HOST_RESPONSE_VALIDATED",
                        response_sha256=hashlib.sha256(response_path.read_bytes()).hexdigest(),
                        terminal_eos=result["terminal_eos"])
            trace["response_validation_passed"] = True
            self._reconcile(trace_path, trace, lifecycle_root, digest, dependencies)
            return {"output": result["output"], "terminal_eos": result["terminal_eos"]}

    def _reconcile(self, trace_path, trace, lifecycle_root, relative_path, dependencies) -> None:
        receipt = reconcile_durable_lifecycle_v1(root=lifecycle_root, relative_path=relative_path,
            expected_runner_sha256=RUNNER_SHA256, expected_dependency_identities=dependencies)
        value = receipt.as_json_value(); trace["durable_lifecycle_reconciliation"] = value
        trace["model_load_started"] = trace["model_load_succeeded"] = value["model_load"] == "OBSERVED"
        trace["inference_started"] = value["generation"] == "OBSERVED"
        trace["inference_succeeded"] = value["terminal_eos"] == "OBSERVED"
        self._write_trace(trace_path, trace)


__all__ = ("DEPENDENCY_IDENTITIES", "RUNNER_RELATIVE", "RUNNER_SHA256", "VENV_PYTHON",
           "WSL_DISTRIBUTION", "DurableConstructionObligationStagePExecutorV1")
