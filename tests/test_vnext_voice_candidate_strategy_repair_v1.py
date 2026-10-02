from pastila_scout.vnext_voice_factual_projection_v1 import enforce_candidate_projection


def test_abstention_commentary_is_normalized_fail_closed():
    result = enforce_candidate_projection("Fapt acceptat.", {"status": "ABSTAIN", "commentary": "text rezidual"})
    assert result == {"status": "ABSTAIN", "commentary": "", "decision": "NORMALIZE_ABSTENTION", "findings": ["ABSTAIN_WITH_COMMENTARY"]}


def test_unsupported_numeric_claim_abstains():
    result = enforce_candidate_projection("Raportul indică 42 de clădiri.", {"status": "COMMENTARY", "commentary": "Poate sunt 43."})
    assert result["status"] == "ABSTAIN" and result["decision"] == "REJECT_UNSUPPORTED_FACT"


def test_supported_commentary_passes_unchanged():
    result = enforce_candidate_projection("Raportul indică 42 de clădiri.", {"status": "COMMENTARY", "commentary": " Numărul 42 a primit ștampilă. "})
    assert result["status"] == "COMMENTARY" and result["commentary"] == "Numărul 42 a primit ștampilă."


def test_malformed_response_abstains():
    result = enforce_candidate_projection("Fapt.", {"status": "COMMENTARY", "commentary": ""})
    assert result["status"] == "ABSTAIN" and result["decision"] == "REJECT_MALFORMED_RESPONSE"
