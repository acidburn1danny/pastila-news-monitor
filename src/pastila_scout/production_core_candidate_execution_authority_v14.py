"""V14 identities over byte-pinned candidate execution validation mechanics."""
from __future__ import annotations

import hashlib
from pathlib import Path

_SOURCE = Path(__file__).with_name("production_core_candidate_execution_authority_v3.py")
_EXPECTED = "5616841ee9dfc3c174d100aed07c79419df8850c0f63fbd7add9b1fd527ef33b"
_raw = _SOURCE.read_bytes()
if hashlib.sha256(_raw).hexdigest() != _EXPECTED:
    raise RuntimeError("V3 validator mechanics changed")
_source = _raw.decode("utf-8")
_changes = {
    "b7af3517a14e987efa344e9cd9c7bcbbdd9ddb3656cc9060e72fdca71ca7c8d2": "65d5b2502c0ff3a30367cceccda2a2e5c772844cb70500445a186deebf1d4567",
    "fc9033f03c2d11f933183a5a8fac2df8d01bf44a1e28e1db3d252eabb7332605": "309facaf268c79cdf3e6c635bec47c46c68121b7b5eb543f07c801048386da13",
    "d868b2cd1dd40f62d98dc61afdb9ace81dec78588a78fc82efdc347ab7cc335d": "6c3bf1d21e85a454069ccd4e80f542fa5005ea6b89b41bb0d90b4acad2533314",
    "ee86684da529d0b1a75c172d5ed2c3ec65f21da5f350d53cb7dda500f4449dca": "345b9faeaaef2820efb630b9a30e10e9b037b4fbbb4cbebe81d9abd196fe6920",
    "ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c": "813131dc9cae57a66f216957475479e716594c46a67f77783122ff955aa7ee32",
    "a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8": "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f",
    "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc": "91c84e9ab10cbecdfdd7e255b133c56263feb546d55d7e1ea01362f9be5567bb",
    "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17": "70e125c8fa6e58f3864419bec34f6685a95bcb7bbfb9455838aaf593d01fac36",
    "scripts/execute_production_core_candidate_qualification_v3.py": "scripts/execute_production_core_candidate_qualification_v14.py",
    "scripts/launch_production_core_candidate_qualification_v9.py": "scripts/launch_production_core_candidate_qualification_v14.py",
    "scripts/run_production_core_candidate_qualification_v3.sh": "scripts/run_production_core_candidate_qualification_v14.sh",
    "src/pastila_scout/production_core_candidate_execution_authority_v3.py": "src/pastila_scout/production_core_candidate_execution_authority_v14.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v3.py": "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
}
for _old, _new in _changes.items():
    _count = 2 if _old in (
        "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
        "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
        "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
    ) else 1
    if _source.count(_old) != _count:
        raise RuntimeError(f"V14 validator projection witness mismatch: {_old}")
    _source = _source.replace(_old, _new)
_syntax_witness = "except TypeError, ValueError:"
if _source.count(_syntax_witness) != 1:
    raise RuntimeError("V14 validator syntax repair witness mismatch")
_source = _source.replace(_syntax_witness, "except (TypeError, ValueError):")
_rootfs_witness = '            physical_identities.append(item["physical_identity"])'
if _source.count(_rootfs_witness) != 1:
    raise RuntimeError("V14 shared-rootfs validator witness mismatch")
_source = _source.replace(_rootfs_witness, '            if role != "rootfs":\n                physical_identities.append(item["physical_identity"])')
exec(compile(_source, str(_SOURCE), "exec"), globals(), globals())  # noqa: S102 - pinned mechanics
