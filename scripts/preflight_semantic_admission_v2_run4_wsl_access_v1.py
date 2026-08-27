"""Zero-inference WSL access and exact-runner readiness preflight after Run 3."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".semantic-admission-v2-run4-wsl-access-preflight-v1-evidence"
VENV_PYTHON = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/.venv/bin/python"
DISTRO = "Ubuntu-24.04"
CONSTRAINED = ROOT / "src/pastila_scout/experimental_core_v1_2_gate_f_constrained_runner.py"
ORDINARY = ROOT / "src/pastila_scout/experimental_core_v1_2_runner.py"


def _wsl(path: Path, *, must_exist: bool = True) -> str:
    value = PureWindowsPath(path.resolve(strict=must_exist))
    return f"/mnt/{value.drive[0].lower()}/" + "/".join(value.parts[1:])


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _call(arguments: list[str], timeout: int = 180) -> dict[str, object]:
    completed = subprocess.run(
        ["wsl.exe", "-d", DISTRO, "--", *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {
        "arguments": arguments,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> None:
    target = OUT / "zero-inference-wsl-access-preflight.json"
    if target.exists():
        raise RuntimeError("Run 4 WSL access preflight already sealed")
    with tempfile.TemporaryDirectory(prefix="sav2-run4-wsl-preflight-") as directory:
        lifecycle = Path(directory) / "constrained-lifecycle.json"
        service = _call(["/bin/true"])
        paths = _call(["/usr/bin/test", "-r", _wsl(CONSTRAINED), "-a", "-r", _wsl(ORDINARY)])
        ordinary_compile = _call(
            [VENV_PYTHON, "-c", "import pathlib; compile(pathlib.Path(__import__('sys').argv[1]).read_text('utf-8'), __import__('sys').argv[1], 'exec')", _wsl(ORDINARY)]
        )
        constrained = _call([VENV_PYTHON, _wsl(CONSTRAINED), "--preflight-only", _wsl(lifecycle, must_exist=False)], timeout=300)
        constrained_lifecycle = json.loads(lifecycle.read_text("utf-8")) if lifecycle.is_file() else None
    calls = (service, paths, ordinary_compile, constrained)
    lifecycle_safe = bool(
        constrained_lifecycle
        and constrained_lifecycle.get("result") == "PASS"
        and constrained_lifecycle.get("model_imported") is False
        and constrained_lifecycle.get("model_load_started") is False
        and constrained_lifecycle.get("generation_started") is False
        and constrained_lifecycle.get("model_calls") == 0
        and constrained_lifecycle.get("provider_calls") == 0
    )
    result = {
        "schema_name": "pastila-semantic-admission-v2-run4-wsl-access-preflight",
        "schema_version": "1.0.0",
        "checked_at": datetime.now(UTC).isoformat(),
        "source_run3_identity": "d567adaddd889063ae48d65d647c8676b6a4ea87f9f9cc047ed80888af12ee07",
        "distro": DISTRO,
        "constrained_runner": {"path": str(CONSTRAINED.relative_to(ROOT)), "sha256": _sha(CONSTRAINED)},
        "ordinary_runner": {"path": str(ORDINARY.relative_to(ROOT)), "sha256": _sha(ORDINARY)},
        "checks": calls,
        "constrained_lifecycle": constrained_lifecycle,
        "wsl_service_accessible": service["returncode"] == 0,
        "runner_paths_readable": paths["returncode"] == 0,
        "ordinary_runner_compiles": ordinary_compile["returncode"] == 0,
        "constrained_lifecycle_safe": lifecycle_safe,
        "model_load_started": False,
        "inference_started": False,
        "model_calls": 0,
        "provider_calls": 0,
        "run4_execution_authorized": False,
        "runtime_authority": False,
        "training_authority": False,
    }
    result["result"] = "PASS" if all(call["returncode"] == 0 for call in calls) and lifecycle_safe else "FAIL"
    OUT.mkdir(exist_ok=False)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(result["result"])


if __name__ == "__main__":
    main()
