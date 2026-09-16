"""V10 identities over the byte-pinned, previously audited execution validator."""
from __future__ import annotations
import hashlib
from pathlib import Path

_SOURCE=Path(__file__).with_name("production_core_candidate_execution_authority_v3.py")
_EXPECTED_SOURCE_SHA256="5616841ee9dfc3c174d100aed07c79419df8850c0f63fbd7add9b1fd527ef33b"
_raw=_SOURCE.read_bytes()
if hashlib.sha256(_raw).hexdigest()!=_EXPECTED_SOURCE_SHA256:
 raise RuntimeError("V3 execution validator source mismatch")
exec(compile(_raw,str(_SOURCE),"exec"),globals(),globals())  # noqa: S102 - byte-pinned local authority

GENERATION_IDENTITY="a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7"
QUALIFICATION_IDENTITY="607ef6193b312c6d2e5d581c10caf9cb8a3a14a5b46166888e9bd8bddade5a45"
CANDIDATE_MANIFEST_IDENTITY="6c3bf1d21e85a454069ccd4e80f542fa5005ea6b89b41bb0d90b4acad2533314"
EXPECTED_OBJECTS=(
 ("rootfs","file","274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"),
 ("base_model","flat-dir","f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"),
 ("adapter_v1_1","flat-dir","813131dc9cae57a66f216957475479e716594c46a67f77783122ff955aa7ee32"),
 ("adapter_v1_2","flat-dir","8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f"),
)
