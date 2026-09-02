from copy import deepcopy
import json
from pathlib import Path
import pytest
from pastila_scout.semantic_authority_objective_selection_v2_1 import canonical_identity,validate_policy

PATH=Path(__file__).resolve().parents[1]/"docs/artifacts/semantic-contract-v2-objective-owner-executable-authority-selection-governance-v2.json"
def policy():return json.loads(PATH.read_text(encoding="utf-8"))
def reseal(v):v["governance_identity"]=canonical_identity(v,"governance_identity")

def test_frozen_policy_is_canonical_and_valid():validate_policy(policy())

@pytest.mark.parametrize("mutate",[
 lambda v:v["snapshots"].update(selector="LATEST"),lambda v:v["snapshots"].update(official_manifest_and_complete_archive_digest_required=False),
 lambda v:v["frame"].update(key="REGISTRY_LOCAL_ID"),lambda v:v["frame"].update(cross_registry_merge="KEEP_BOTH"),lambda v:v["frame"].update(semantic_fields_projected=True),
 lambda v:v["external_commitment"].update(canonical_commitment="OWNER_CHOICE"),lambda v:v["external_commitment"].update(git_or_local_time_authoritative=True),
 lambda v:v["entropy"].update(round_rule="OWNER_CHOICE"),lambda v:v["entropy"].update(signature_verification=False),
 lambda v:v["selection"].update(integer_encoding="NATIVE_ENDIAN"),lambda v:v["selection"].update(acceptance="X_MOD_N"),lambda v:v["selection"].update(redraw=True),
 lambda v:v["source_version"].update(selected_entry_requires_preexisting_content_digest=False),lambda v:v["scope"].update(rule="LATEST_BYTES"),
 lambda v:v["extraction"].update(visit_all_segments=False),lambda v:v["extraction"].update(coverage_visible=True),lambda v:v["extraction"].update(complete_negative_space=False),
 lambda v:v["execution_lifecycle"].update(abort_after_external_commitment="RESTART"),lambda v:v["execution_lifecycle"].update(new_run_same_governance=True),
])
def test_resealed_attack_variants_fail(mutate):
 v=deepcopy(policy());mutate(v);reseal(v)
 with pytest.raises(ValueError):validate_policy(v)

def test_design_performs_no_frame_or_source_action():
 v=policy();assert v["frame_executed"] is False;assert v["source_selected_or_acquired"] is False;assert v["authority_basis_created_or_admitted"] is False;assert v["curriculum_population_started"] is False;assert v["pilot15_prepared"] is False;assert v["blind_or_future_family_access"] is False
