"""Bounded zero-inference impact assessment for the Mistral tokenizer regex warning."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.core_adapter_v2_3 import CoreV12SemanticEvaluatorAdapterV23
try:
    from scripts.run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload
except ModuleNotFoundError:
    from run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload

OUT = ROOT / ".semantic-admission-v2-tokenizer-regex-impact-v1-evidence"
DISTRO = "Ubuntu-24.04"
VENV_PYTHON = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/.venv/bin/python"
MODEL = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142"


class ForbiddenExecutor:
    def execute(self, request):
        raise AssertionError("tokenizer assessment invoked an executor")


def _wsl(path: Path, *, must_exist: bool = True) -> str:
    value = PureWindowsPath(path.resolve(strict=must_exist))
    return f"/mnt/{value.drive[0].lower()}/" + "/".join(value.parts[1:])


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    target = OUT / "impact-assessment.json"
    if target.exists():
        raise RuntimeError("tokenizer regex impact assessment already sealed")
    data = preflight_payload()
    adapter = CoreV12SemanticEvaluatorAdapterV23(project_root=ROOT, executor=ForbiddenExecutor(), gate_id=GateIdV2.FACTUAL_SEMANTIC)
    samples: list[dict[str, str]] = []
    case_ids = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-run3-constrained-plan.json").read_text("utf-8"))["case_ids"]
    for case_id in case_ids:
        case, attempt = data["cases"][case_id], data["attempts"][case_id]
        candidate = json.loads(attempt["raw_output"])["commentary"]
        request = {
            "gate_id": "FACTUAL_SEMANTIC",
            "factual_summary": case["factual_summary"],
            "candidate": candidate,
        }
        samples.append({"id": f"prompt:{case_id}", "text": adapter.render_prompt(request)})
    samples.extend(
        [
            {"id": "canonical:pass", "text": '{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]}'},
            {"id": "canonical:indeterminate", "text": '{"gate_id":"FACTUAL_SEMANTIC","decision":"INDETERMINATE","reason_records":[{"code":"ADMISSION_INDETERMINATE","status":"DECISIVE","candidate_span":null,"authority_support":null,"unsupported_proposition":"x","confidence":0.5}]}'},
            {"id": "prefix:fail-span", "text": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"'},
            {"id": "prefix:fail-support", "text": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":null,"authority_support":"'},
            {"id": "romanian:diacritics-punctuation", "text": "Când instituția spune «poate», comentariul nu are voie să audă «sigur». Și nici să inventeze intenții."},
        ]
    )
    worker = ROOT / "scripts/tokenizer_regex_impact_worker_v1.py"
    with tempfile.TemporaryDirectory(prefix="sav2-tokenizer-impact-") as directory:
        root = Path(directory); source = root / "samples.json"; result_path = root / "result.json"
        source.write_text(json.dumps(samples, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run(
            ["wsl.exe", "-d", DISTRO, "--", VENV_PYTHON, _wsl(worker), _wsl(source), _wsl(result_path, must_exist=False), MODEL],
            check=False, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        result = json.loads(result_path.read_text("utf-8")) if result_path.is_file() else None
    receipt = {
        "schema_name": "pastila-semantic-admission-v2-tokenizer-regex-impact",
        "schema_version": "1.0.0",
        "checked_at": datetime.now(UTC).isoformat(),
        "source_preflight_identity": "8a251fd00eca9bc5474bbdc87c444308c211b3321d587c873a277e728b48d983",
        "sample_count": len(samples),
        "exact_gate_f_prompt_count": 10,
        "worker_sha256": _sha(worker.read_bytes()),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "comparison": result,
        "model_load_started": False,
        "inference_started": False,
        "model_calls": 0,
        "provider_calls": 0,
        "runner_modified": False,
        "run4_execution_authorized": False,
        "runtime_authority": False,
        "training_authority": False,
    }
    receipt["result"] = "PASS" if completed.returncode == 0 and result is not None else "FAIL"
    OUT.mkdir(exist_ok=False)
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(receipt["result"])


if __name__ == "__main__":
    main()
