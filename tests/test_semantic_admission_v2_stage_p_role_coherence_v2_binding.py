import hashlib,json
from datetime import UTC,datetime
from pathlib import Path
from pastila_scout.semantic_admission_v2.stage_p_provider_identity_v1 import MODEL_IDENTITY
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_candidate_v2 import StagePRoleCoherenceCandidateV2

ROOT=Path(__file__).resolve().parents[1]
ARTIFACT=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-role-coherence-v2-binding-candidate.json"
SOURCE=ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_candidate_v2.py"

def test_v2_candidate_uses_exact_provider_neutral_identity_and_source_hash():
 value=json.loads(ARTIFACT.read_bytes());candidate=StagePRoleCoherenceCandidateV2(project_root=ROOT)
 assert candidate.model_identity==value["model_identity"]==MODEL_IDENTITY
 assert candidate.grammar_identity==value["grammar_identity"]
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==value["candidate_source_sha256"]

def test_v2_candidate_builds_authority_without_execution():
 candidate=StagePRoleCoherenceCandidateV2(project_root=ROOT)
 request={"factual_summary":"Autoritate sintetică.","candidate":"Comentariu sintetic."}
 authority=candidate.build_authority(request,requested_at=datetime(2026,8,26,tzinfo=UTC))
 assert authority.request_envelope.request_units[0].messages[0].content==candidate.render_prompt(request)
 assert not hasattr(candidate,"execute") and not hasattr(candidate,"run") and not hasattr(candidate,"__call__")
 assert not any(json.loads(ARTIFACT.read_bytes())["authority"].values())
