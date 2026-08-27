"""Identity-bind durable Stage P evaluation runner to Scope Graph V1; not executed by this candidate."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
REQUEST_CANDIDATE_IDENTITY = "229595d7220e0121257f40d15dcdcd8d6fb40e4943b660b48e17450554354ada"
GRAMMAR_IDENTITY = "sha256:95d16d95cef7163dbad0e149c7607400e531f8a086c92d6aa41209783d4edc59"
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _scope_graph_types():
    package_root = ROOT / "src/pastila_scout"
    semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    _load(prefix + "stage_p_role_coherence_constraint_v1", semantic_root / "stage_p_role_coherence_constraint_v1.py")
    _load(prefix + "stage_p_role_coherence_constraint_v2", semantic_root / "stage_p_role_coherence_constraint_v2.py")
    dfa = _load(prefix + "stage_p_scope_graph_constraint_v1", semantic_root / "stage_p_scope_graph_constraint_v1.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    projector = _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    _load(prefix + "stage_p_scope_graph_incremental_tracker_v1", semantic_root / "stage_p_scope_graph_incremental_tracker_v1.py")
    controller = _load(prefix + "stage_p_scope_graph_callback_controller_v1", semantic_root / "stage_p_scope_graph_callback_controller_v1.py")
    lifecycle = _load(prefix + "append_only_lifecycle_v1", semantic_root / "append_only_lifecycle_v1.py")
    return (dfa.StagePScopeGraphConstraintStateV1, projector.StagePTokenTrieProjectorV1,
            controller.StagePScopeGraphCallbackControllerV1, lifecycle.AppendOnlyLifecycleV1)


def main(arguments: list[str]) -> None:
    if len(arguments) != 4:
        raise SystemExit("usage: runner REQUEST RESPONSE PROMPT DURABLE_LIFECYCLE_ROOT")
    base = _load("pastila_stage_p_scope_graph_durable_runner_v3_base",
                 ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v3.py")
    base._types = _scope_graph_types
    base.run(*map(Path, arguments))


if __name__ == "__main__":
    main(sys.argv[1:])
