import hashlib
import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/humor-mechanics-batch2-development-pilot11-strict-preingestion-validation-v1.json"


def test_pilot11_strict_preingestion_validation_is_sealed_and_non_authorizing() -> None:
    artifact = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(artifact)
    identity = core.pop("validation_identity")
    encoded = json.dumps({"namespace": "B2_DEVELOPMENT_PILOT11_STRICT_PREINGESTION_VALIDATION_V1", "value": core},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert identity == hashlib.sha256(encoded).hexdigest()
    assert artifact["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert artifact["source_sha256"] == "cdf1901941057914cb7b22ac1233771773e2f15bd1671bcc47e2d17d123e2bd9"
    assert artifact["declaration_sha256"] == "6fdb4ca1cac39f6b4cf4ae9614163d0641695608568bebc4e582322190a3ed21"
    assert artifact["deterministic_blockers"] == []
    assert artifact["repair_performed"] is False
    assert artifact["prospective_identities_derived"] is False
    assert artifact["proposition_sufficiency_evaluated"] is False
    assert all(value is False for value in artifact["authority_matrix"].values())
