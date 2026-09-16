import hashlib,importlib,json
from pathlib import Path
import pytest
from pastila_scout import production_core_candidate_execution_authority_v10 as v10

ROOT=Path(__file__).resolve().parents[1]
def test_v10_overrides_only_frozen_identities_and_objects():
 assert hashlib.sha256((ROOT/"src/pastila_scout/production_core_candidate_execution_authority_v3.py").read_bytes()).hexdigest()==v10._EXPECTED_SOURCE_SHA256
 assert v10.GENERATION_IDENTITY=="a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7"
 assert v10.QUALIFICATION_IDENTITY=="607ef6193b312c6d2e5d581c10caf9cb8a3a14a5b46166888e9bd8bddade5a45"
 assert v10.CANDIDATE_MANIFEST_IDENTITY=="6c3bf1d21e85a454069ccd4e80f542fa5005ea6b89b41bb0d90b4acad2533314"
 assert [row[2] for row in v10.EXPECTED_OBJECTS[2:]]==["813131dc9cae57a66f216957475479e716594c46a67f77783122ff955aa7ee32","8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f"]
 assert v10.MATRIX_ROWS==2400
def test_v10_preflight_accepts_only_resealed_inputs():
 generation=json.loads((ROOT/"docs/artifacts/production-core-successor-comparative-qualification-generation-v10.json").read_bytes());requests=json.loads((ROOT/"docs/artifacts/production-core-candidate-request-manifest-v2.json").read_bytes());manifest=json.loads((ROOT/"docs/artifacts/production-core-successor-candidate-object-manifest-v10.json").read_bytes());qualification=json.loads((ROOT/"docs/artifacts/production-core-successor-candidate-generation-qualification-v10.json").read_bytes())
 assert len(v10.validate_preflight(generation,requests,manifest,qualification))==2400
 changed=dict(generation);changed["candidate_object_manifest_identity"]="0"*64
 with pytest.raises(v10.ExecutionAuthorityError):v10.validate_preflight(changed,requests,manifest,qualification)
def test_attempt_remains_unconsumed_until_separate_execution_authorization():
 source=(ROOT/"src/pastila_scout/production_core_candidate_execution_authority_v10.py").read_text("utf-8")
 assert "build_attempt(" not in source and "candidate_execution_authorized" not in source
