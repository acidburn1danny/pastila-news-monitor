import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"

def test_materialization_and_output_closure():
    x=json.loads((ART/"vnext-voice-candidate-materialization-v1.json").read_text())
    assert x["status"] == "PASS" and x["inference_outputs"] == 216
    assert set(x["candidates"]) == {"V0_R2_MINISTRAL_CONTROL","V1_QWEN3_8B_NON_THINKING","V2_QWEN25_7B_INSTRUCT"}

def test_terminal_candidate_decisions():
    x=json.loads((ART/"vnext-voice-candidate-commentary-bakeoff-result-v1.json").read_text())
    assert x["status"] == "PASS_BAKEOFF_CLOSED_NO_PROMOTABLE_CANDIDATE"
    assert x["per_candidate"]["V0_R2_MINISTRAL_CONTROL"]["unsupported_number_cases"] == ["VOICE-V1-06","VOICE-V1-22"]
    assert x["per_candidate"]["V1_QWEN3_8B_NON_THINKING"]["unsupported_number_cases"] == ["VOICE-V1-04"]
    assert x["per_candidate"]["V2_QWEN25_7B_INSTRUCT"]["abstentions"] == 66
    assert x["selected_candidate"] is None

def test_blind_packet_and_protected_state():
    x=json.loads((ART/"vnext-voice-candidate-commentary-bakeoff-result-v1.json").read_text())
    raw=(ART/"vnext-voice-candidate-bakeoff-v1-blind-review.jsonl").read_bytes()
    assert len(raw.splitlines()) == 216 and hashlib.sha256(raw).hexdigest() == x["blind_review_sha256"]
    assert x["voice_state"] == "DISABLED_UNTIL_PROMOTION" and x["legacy_dependency_count"] == 0
