"""Execute V11 through a byte-pinned projection of the audited V10 executor."""
from __future__ import annotations

import hashlib
from pathlib import Path

_SOURCE = Path(__file__).with_name("execute_production_core_candidate_qualification_v10.py")
_EXPECTED = "2795c02e96ee3e65165775e0592f201de2d1508d2ce4841859601795414f5f98"
_raw = _SOURCE.read_bytes()
if hashlib.sha256(_raw).hexdigest() != _EXPECTED:
    raise SystemExit("V10 executor source mismatch")
_source = _raw.decode("utf-8")
_changes = {
    "production_core_candidate_execution_authority_v10": "production_core_candidate_execution_authority_v11",
    "scripts/execute_production_core_candidate_qualification_v10.py": "scripts/execute_production_core_candidate_qualification_v11.py",
}
for _old, _new in _changes.items():
    if _source.count(_old) != 1:
        raise SystemExit(f"V11 executor projection witness mismatch: {_old}")
    _source = _source.replace(_old, _new)
_needle = " 'production_core_candidate_execution_authority_v3':'production_core_candidate_execution_authority_v11',\n"
if _source.count(_needle) != 1:
    raise SystemExit("V11 runner projection insertion mismatch")
_source = _source.replace(
    _needle,
    _needle
    + " 'run_production_core_candidate_qualification_v3.sh':'run_production_core_candidate_qualification_v11.sh',\n",
)
exec(compile(_source, str(_SOURCE), "exec"), globals(), globals())  # noqa: S102
