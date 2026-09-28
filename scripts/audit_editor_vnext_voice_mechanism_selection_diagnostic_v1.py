"""Fresh read-only audit of the VNext VOICE mechanism selection evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.build_editor_vnext_voice_mechanism_selection_diagnostic_v1 import build, RESULT
except ModuleNotFoundError:  # Direct script execution places scripts/ on sys.path.
    from build_editor_vnext_voice_mechanism_selection_diagnostic_v1 import build, RESULT


def audit() -> dict:
    stored = json.loads(RESULT.read_text(encoding="utf-8"))
    if stored != build():
        raise ValueError("diagnostic result is not reproducible")
    evidence = {
        "executor": ROOT / "src/pastila_scout/voice_executor_v2/executor.py",
        "models": ROOT / "src/pastila_scout/voice_executor_v2/models.py",
        "activation": ROOT / "src/pastila_scout/voice_executor_v2/production_activation.py",
        "composition": ROOT / "src/pastila_scout/desktop_v1/voice_v2_composition.py",
    }
    text = {name: path.read_text(encoding="utf-8") for name, path in evidence.items()}
    obligations = {
        "model_free_executor": "model-free deterministic executor" in text["executor"],
        "fact_atom_dependency": "VoiceFactAtomBundle" in text["models"],
        "event_authority_dependency": "event_authority_identity" in text["executor"],
        "owner_selection_dependency": "program_selection" in text["executor"],
        "repetition_dependency": "repetition_snapshot" in text["executor"],
        "bounded_activation": "BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1" in text["activation"],
        "governed_context_dependency": "PersistedStoryGovernedContextLoaderV2" in text["composition"],
        "no_product_root_mutation": stored["product_root_modified"] is False,
        "no_product_lock_mutation": stored["product_lock_modified"] is False,
    }
    if not all(obligations.values()):
        raise ValueError({key: value for key, value in obligations.items() if not value})
    return {"status": "PASS", "obligations": obligations, "result_identity": stored["result_identity"]}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
