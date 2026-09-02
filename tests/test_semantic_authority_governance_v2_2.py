import json
from copy import deepcopy
from pathlib import Path
import pytest
from pastila_scout.semantic_authority_governance_v2_2 import identity, validate

PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/semantic-contract-v2-objective-authority-selection-governance-v2-2.json"
def policy(): return json.loads(PATH.read_text(encoding="utf-8"))
def reseal(value): value["governance_identity"] = identity(value, "governance_identity")
def test_frozen_policy(): validate(policy())
@pytest.mark.parametrize("attack", [
 lambda p:p["external_freeze"].update(verified=False),
 lambda p:p["release_selection"].update(rule="OWNER_CHOICE"),
 lambda p:p["release_selection"].update(unavailable="USE_LATEST"),
 lambda p:p["archive_commitment"].update(etag_accepted=True),
 lambda p:p["archive_commitment"].update(missing_digest="ALLOW"),
 lambda p:p["archive_commitment"].update(all_manifest_objects_required=False),
 lambda p:p["lifecycle"].update(rekor_frame_commitment="PRECOMPUTE"),
 lambda p:p["lifecycle"].update(drand_round="OWNER_CHOICE"),
 lambda p:p.update(frame_executed=True),
])
def test_resealed_attack_fails(attack):
    value=deepcopy(policy()); attack(value); reseal(value)
    with pytest.raises(ValueError): validate(value)
