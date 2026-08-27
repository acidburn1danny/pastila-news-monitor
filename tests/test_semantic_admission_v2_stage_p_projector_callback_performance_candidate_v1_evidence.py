from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-projector-callback-performance-remediation-design-v1.json"
C=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-projector-callback-performance-candidate-v1.json"
def ident(v):return hashlib.sha256("\n".join(v["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest()
def test_identities_exactness_speed_and_no_execution():
 d=json.loads(D.read_bytes());c=json.loads(C.read_bytes());assert ident(d)==d["canonical_identity"] and ident(c)==c["canonical_identity"]
 assert c["real_tokenizer_evidence"]["all_allowed_sets_equal_v1"] is True
 assert c["real_tokenizer_evidence"]["string_empty"]["v2_seconds"]<.1
 assert c["real_tokenizer_evidence"]["string_empty"]["v1_seconds"]>4
 assert c["real_tokenizer_evidence"]["model_loads"]==0 and c["real_tokenizer_evidence"]["probe_executions"]==0
 assert all(value is False for value in c["authority"].values())
