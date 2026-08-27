"""Durable evaluation-only executor bound to the Role Coherence V1 runner."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import VENV_PYTHON, ExperimentalCoreV12Executor, _PROMPT_RELATIVE, _wsl_path

from .append_only_lifecycle_v1 import AppendOnlyLifecycleV1
from .durable_lifecycle_reconciliation_v1 import reconcile_durable_lifecycle_v1


RUNNER_RELATIVE = Path("src/pastila_scout/experimental_core_v1_2_stage_p_role_coherence_runner_v1.py")
RUNNER_SHA256 = "61e5daafa07262ecf913441cd0121dfc6976891ef80f7f9fc3f55e4a0b2cfbd2"
DEPENDENCY_IDENTITIES = {
    Path("src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v3.py"): "617ee34bd05c6a32de81714b0b07bedb2f10464f0e43213258cdf8886e0c57db",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_constraint_v1.py"): "0cf522bf94dac4ad480b3e28c5b17ae78e372ddce91ffa75ba70e657a79b57b2",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_trie_projector_v1.py"): "8cc6f68f1ff9751ab983306e9fb39efa0ae55c52cbe8a0471a2e5e98bfc54529",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_incremental_tracker_v1.py"): "ee8ffe3420edff80026795d8e33fa014fe0a35ba57befdd0c24b49679839f53b",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_callback_controller_v1.py"): "240b87e079b0dec825d96e300a6de1c31be9e7d3ff9e7067f7acd80dceb3dd4f",
    Path("src/pastila_scout/semantic_admission_v2/append_only_lifecycle_v1.py"): "74ad3892060f3e98ae1a5fc2b243c5100891259518b67bdb3e37f586bc4635a3",
    Path("src/pastila_scout/semantic_admission_v2/durable_lifecycle_reconciliation_v1.py"): "aae76d0a4a53e0b9987038f3f9ae105f23585b77fa089dc0fc6d5d31b2901df5",
}


class DurableRoleCoherenceStagePExecutorV1(ExperimentalCoreV12Executor):
    def __init__(self, *, project_root: Path, durable_lifecycle_root: Path, max_output_tokens: int = 1400) -> None:
        super().__init__(project_root=project_root, max_output_tokens=max_output_tokens)
        self._durable_root = durable_lifecycle_root.resolve()
        self._durable_root.mkdir(parents=True, exist_ok=True)
        for relative, expected in {RUNNER_RELATIVE: RUNNER_SHA256, **DEPENDENCY_IDENTITIES}.items():
            target = self._project_root / relative
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"role-coherence Stage P identity drift: {relative.as_posix()}")

    def _invoke(self, authority, trace_path: Path, trace: dict[str, object]) -> dict[str, object]:
        unit = authority.request_envelope.request_units[0]
        request_digest = hashlib.sha256(authority.context.request_id.encode()).hexdigest()
        lifecycle_root = self._durable_root / request_digest
        lifecycle_root.mkdir(parents=False, exist_ok=False)
        events = AppendOnlyLifecycleV1(lifecycle_root, actor="host")
        dependencies = {
            path.as_posix(): value for path, value in DEPENDENCY_IDENTITIES.items()
            if path.name != "durable_lifecycle_reconciliation_v1.py"
        }
        payload = {"prompt": "\n\n".join(message.content for message in unit.messages), "max_new_tokens": self._max_output_tokens}
        with tempfile.TemporaryDirectory(prefix="pastila-stage-p-role-coherence-v1-") as directory:
            root = Path(directory)
            request_path, response_path = root / "request.json", root / "response.json"
            request_path.write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
            runner = self._project_root / RUNNER_RELATIVE
            command = [
                "wsl.exe", "-d", "Ubuntu-24.04", "--", VENV_PYTHON, _wsl_path(runner),
                _wsl_path(request_path), _wsl_path(response_path), _wsl_path(self._project_root / _PROMPT_RELATIVE),
                _wsl_path(lifecycle_root),
            ]
            trace.update(runner_launch_attempted=True, runner_path=_wsl_path(runner), durable_lifecycle_relative_path=request_digest)
            self._write_trace(trace_path, trace)
            events.emit(
                "HOST_LAUNCH", request_id_sha256=request_digest,
                request_sha256=hashlib.sha256(request_path.read_bytes()).hexdigest(), runner_sha256=RUNNER_SHA256,
                dependency_identities=dependencies, timeout_seconds=authority.timeout_policy.timeout_seconds,
            )
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            events.emit("HOST_PROCESS_STARTED", pid=process.pid)
            try:
                stdout, stderr = process.communicate(timeout=authority.timeout_policy.timeout_seconds)
            except subprocess.TimeoutExpired:
                events.emit("HOST_TIMEOUT", pid=process.pid)
                process.terminate()
                termination = "TERMINATED"
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    termination = "KILLED"
                events.emit("HOST_TERMINATION_OBSERVED", pid=process.pid, termination=termination, returncode=process.returncode)
                self._reconcile(trace_path, trace, lifecycle_root, request_digest, dependencies)
                raise
            events.emit(
                "HOST_PROCESS_EXITED", pid=process.pid, returncode=process.returncode,
                stdout_tail=(stdout or "")[-1000:], stderr_tail=(stderr or "")[-1000:], response_exists=response_path.is_file(),
            )
            trace.update(stderr_tail=(stderr or "")[-4000:], stdout_tail=(stdout or "")[-4000:], response_received=response_path.is_file())
            self._reconcile(trace_path, trace, lifecycle_root, request_digest, dependencies)
            if process.returncode != 0 or not response_path.is_file():
                raise RuntimeError("durable role-coherence Stage P runner failed")
            result = json.loads(response_path.read_text("utf-8"))
            if set(result) != {"output", "terminal_eos", "constraint_active"} or result["constraint_active"] is not True or not result["output"]:
                raise ValueError("durable role-coherence Stage P response invalid")
            events.emit(
                "HOST_RESPONSE_VALIDATED", response_sha256=hashlib.sha256(response_path.read_bytes()).hexdigest(),
                terminal_eos=result["terminal_eos"],
            )
            trace["response_validation_passed"] = True
            self._reconcile(trace_path, trace, lifecycle_root, request_digest, dependencies)
            return {"output": result["output"], "terminal_eos": result["terminal_eos"]}

    def _reconcile(self, trace_path, trace, lifecycle_root, relative_path, dependencies) -> None:
        receipt = reconcile_durable_lifecycle_v1(
            root=lifecycle_root, relative_path=relative_path, expected_runner_sha256=RUNNER_SHA256,
            expected_dependency_identities=dependencies,
        )
        value = receipt.as_json_value()
        trace["durable_lifecycle_reconciliation"] = value
        trace["model_load_started"] = value["model_load"] == "OBSERVED"
        trace["model_load_succeeded"] = value["model_load"] == "OBSERVED"
        trace["inference_started"] = value["generation"] == "OBSERVED"
        trace["inference_succeeded"] = value["terminal_eos"] == "OBSERVED"
        self._write_trace(trace_path, trace)


__all__ = ("DEPENDENCY_IDENTITIES", "RUNNER_RELATIVE", "RUNNER_SHA256", "DurableRoleCoherenceStagePExecutorV1")
