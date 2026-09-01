import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_humor_batch2_development_pilot13_construction_once_v5_3_3.py"


def test_runner_is_one_shot_clause_only_and_stops_before_downstream_gates():
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)
    assert 'ConstructorPacketCapabilityV1(prepared).read_constructor_packet()' in source
    assert 'invoke_clause_only_provider({"clause": clause})' in source
    assert "observe_and_conform_surface" in source and "conditional_emit" in source
    assert '"retry_authority": False' in source
    assert '"fragment_collision_evaluation": "NOT_PERFORMED"' in source
    assert "fragment_collision" not in "\n".join(
        line for line in source.splitlines() if line.lstrip().startswith(("from ", "import "))
    )


def test_runner_has_no_preexisting_attempt_outputs():
    assert not (ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-v1.txt").exists()
    assert not (ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot13-construction-attempt01-v1.json").exists()
