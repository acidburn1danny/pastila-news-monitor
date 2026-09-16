"""Detached-signed V11 entry with fail-closed WSL capacity and snapshot bindings."""
from __future__ import annotations

import hashlib
from pathlib import Path

_SOURCE = Path(__file__).with_name("launch_production_core_candidate_qualification_v10.py")
_EXPECTED = "fe725f9f87c14bddd27c9de6a4e6a9a1018cef37df62db7d084033a4680058c7"
_raw = _SOURCE.read_bytes()
if hashlib.sha256(_raw).hexdigest() != _EXPECTED:
    raise SystemExit("V10 launcher source mismatch")
_source = _raw.decode("utf-8")
_changes = {
    "execute_production_core_candidate_qualification_v10.py": "execute_production_core_candidate_qualification_v11.py",
    "production_core_candidate_execution_authority_v10.py": "production_core_candidate_execution_authority_v11.py",
    "production-core-candidate-execution-authority-v10.binding.json": "production-core-candidate-execution-authority-v11.binding.json",
    "production-core-candidate-execution-authority-v10.binding.sig": "production-core-candidate-execution-authority-v11.binding.sig",
    "production-core-candidate-execution-authority-v10.json": "production-core-candidate-execution-authority-v11.json",
    "2795c02e96ee3e65165775e0592f201de2d1508d2ce4841859601795414f5f98": "ca3eb6a262ac2de2ffd00d320191e971b8054218ebfdb45627769224c2dbbce8",
    "bf202b19031dc914758a2c10a6c0466dfcc700c03f0d4ae2ee2b3b662e040b83": "121fb577bb075a445d12baa663a20e77e3f9f1d5a3cc9297f9a3609fa51d34f6",
    "pastila-production-core-v10-detached-authority-binding": "pastila-production-core-v11-detached-authority-binding",
    "FROZEN_SUCCESSOR_V10_UNIFIED_EXECUTION_CONTRACT_ZERO_ATTEMPTS": "FROZEN_SUCCESSOR_V11_WSL_SIGBUS_REMEDIATION_ZERO_ATTEMPTS",
    "7855e21d82402416dcee091baa7a6bcc5cb4c63783aafa33c65bd355c7d83587": "6550b88c424adda261fa723c08f3ce128d61cbdc811cb4d2b311657dc9f04983",
    '"schema_version") != 11': '"schema_version") != 12',
}
for _old, _new in _changes.items():
    if _old not in _source:
        raise SystemExit(f"V11 launcher projection witness absent: {_old}")
    _source = _source.replace(_old, _new)

# Modify the intermediate V10 projection before it executes the pinned V9 launcher.
_marker = 'exec(compile(source,str(_SOURCE),"exec"),globals(),globals())  # noqa: S102\n'
if _source.count(_marker) != 1:
    raise SystemExit("V11 launcher intermediate projection witness mismatch")
_injection = r"""
source=source.replace('"scripts/run_production_core_candidate_qualification_v3.sh",','"scripts/run_production_core_candidate_qualification_v11.sh",\n        "scripts/preflight_production_core_wsl_host_capacity_v11.py",')
source=source.replace('def main():\n    if ENTRY.is_symlink()', '''CAPACITY = ROOT / "scripts" / "preflight_production_core_wsl_host_capacity_v11.py"
CAPACITY_SHA = "2741cef65af382986abf8649a2e8a87b5d131ae1988a8d914c3b84fab58a2104"

def main():
    capacity_source = read(CAPACITY, CAPACITY_SHA)
    capacity_run = subprocess.run([sys.executable, str(CAPACITY)], cwd=ROOT, check=False, capture_output=True, text=True)
    if capacity_run.returncode != 0:
        raise SystemExit("V11 host capacity preflight failed")
    capacity = json.loads(capacity_run.stdout)
    if (capacity.get("result") != "PASS" or capacity.get("qualification_rows") != 0
            or capacity.get("candidate_execution") != 0 or capacity.get("attempt_consumption") != 0
            or hashlib.sha256(capacity_source).hexdigest() != CAPACITY_SHA):
        raise SystemExit("V11 host capacity preflight evidence mismatch")
    if ENTRY.is_symlink()''')
"""
_source = _source.replace(_marker, _injection + _marker)
exec(compile(_source, str(_SOURCE), "exec"), globals(), globals())  # noqa: S102
