"""M6C.6A.1 ownership and dependency-direction checks."""

from pathlib import Path

GENERIC = Path("src/pastila_scout/editor/qa/corrective_action/execution_plan")


def test_generic_planning_has_no_revision_provider_or_dispatch_ownership():
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in GENERIC.glob("*.py")
    )
    for forbidden in (
        "DraftRevisionPolicy",
        "DraftRevisionScope",
        "DraftRevisionInstructions",
        "execution_dispatch",
        "openai",
        "anthropic",
        "httpx",
        "sqlite3",
        "plugin",
    ):
        assert forbidden not in source


def test_capability_extension_uses_typed_fields_not_payload_mappings():
    path = Path(
        "src/pastila_scout/editor/qa/corrective_action/executors/"
        "draft_revision/planning.py"
    )
    source = path.read_text(encoding="utf-8")
    assert "class DraftRevisionPlanningInput" in source
    assert "dict[str, Any]" not in source
    assert "Mapping[str" not in source
    assert "ControlledGeneration" not in source
