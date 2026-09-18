"""V15 attempt validator over the byte-pinned V14 qualification mechanics.

Only executable source names change. Qualification rows, object identities,
response rules, and checkpoint semantics remain those of the V14 validator.
"""
from __future__ import annotations

from pastila_scout import production_core_candidate_execution_authority_v14 as predecessor

_source = predecessor._source
_paths = {
    "scripts/execute_production_core_candidate_qualification_v14.py":
        "scripts/execute_production_core_candidate_qualification_v15.py",
    "scripts/launch_production_core_candidate_qualification_v14.py":
        "scripts/launch_production_core_candidate_qualification_v15.py",
    "scripts/run_production_core_candidate_qualification_v14.sh":
        "scripts/run_production_core_candidate_qualification_v15.sh",
    "src/pastila_scout/production_core_candidate_execution_authority_v14.py":
        "src/pastila_scout/production_core_candidate_execution_authority_v15.py",
}
for _old, _new in _paths.items():
    if _source.count(_old) != 1:
        raise RuntimeError(f"V15 validator source-key witness mismatch: {_old}")
    _source = _source.replace(_old, _new)

_witness = '            "scripts/launch_production_core_candidate_qualification_v15.py",'
if _source.count(_witness) != 1:
    raise RuntimeError("V15 published preflight source witness mismatch")
_source = _source.replace(
    _witness,
    _witness + '\n            "scripts/preflight_production_core_candidate_qualification_v15.py",',
)
exec(compile(_source, __file__, "exec"), globals(), globals())  # noqa: S102 - pinned projection
