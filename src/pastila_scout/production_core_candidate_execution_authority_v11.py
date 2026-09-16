"""V11 validator projection binding the no-copy WSL snapshot boundary."""
from __future__ import annotations

import hashlib
from pathlib import Path

_SOURCE = Path(__file__).with_name("production_core_candidate_execution_authority_v10.py")
_EXPECTED = "bf202b19031dc914758a2c10a6c0466dfcc700c03f0d4ae2ee2b3b662e040b83"
_raw = _SOURCE.read_bytes()
if hashlib.sha256(_raw).hexdigest() != _EXPECTED:
    raise RuntimeError("V10 execution validator source mismatch")
_source = _raw.decode("utf-8")
_changes = {
    "scripts/execute_production_core_candidate_qualification_v10.py": "scripts/execute_production_core_candidate_qualification_v11.py",
    "scripts/launch_production_core_candidate_qualification_v10.py": "scripts/launch_production_core_candidate_qualification_v11.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v10.py": "src/pastila_scout/production_core_candidate_execution_authority_v11.py",
}
for _old, _new in _changes.items():
    if _source.count(_old) != 1:
        raise RuntimeError(f"V11 validator projection witness mismatch: {_old}")
    _source = _source.replace(_old, _new)
_needle = ' "src/pastila_scout/production_core_candidate_execution_authority_v3.py":"src/pastila_scout/production_core_candidate_execution_authority_v11.py",\n'
if _source.count(_needle) != 1:
    raise RuntimeError("V11 validator runner insertion mismatch")
_source = _source.replace(
    _needle,
    _needle
    + ' "scripts/run_production_core_candidate_qualification_v3.sh":"scripts/run_production_core_candidate_qualification_v11.sh",\n',
)
exec(compile(_source, str(_SOURCE), "exec"), globals(), globals())  # noqa: S102
