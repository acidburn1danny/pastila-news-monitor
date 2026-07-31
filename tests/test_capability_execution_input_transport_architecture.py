"""M6C.6B.2 capability-neutral transport architecture checks."""

from pathlib import Path


def test_transport_does_not_import_revision_provider_or_runtime_semantics():
    path = Path(
        "src/pastila_scout/editor/qa/corrective_action/"
        "execution_dispatch/input_transport.py"
    )
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "DraftRevision",
        "openai",
        "anthropic",
        "httpx",
        "sqlite3",
        "provider",
        "registry",
        "discovery",
    ):
        assert forbidden not in source
    assert "class CorrectiveActionExecutorRequestV2" in source
    assert "revision_scope" not in source
    assert "revision_policy" not in source
    assert "revision_instructions" not in source
