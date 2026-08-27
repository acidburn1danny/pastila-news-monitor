"""Evaluation-only runner binding for Construction Role Audit V1."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
REQUEST_CANDIDATE_IDENTITY = "46633da94538451e04643adf4f291bc30033749d8768e36c8a6be5eb13621734"
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


def _construction_role_types():
    package_root = ROOT / "src/pastila_scout"; semantic_root = package_root / "semantic_admission_v2"
    for name, path in (("pastila_scout", package_root), ("pastila_scout.semantic_admission_v2", semantic_root)):
        package = types.ModuleType(name); package.__path__ = [str(path)]; sys.modules.setdefault(name, package)
    prefix = "pastila_scout.semantic_admission_v2."
    for module in ("stage_p_role_coherence_constraint_v1", "stage_p_role_coherence_constraint_v2",
                   "stage_p_scope_graph_constraint_v1", "stage_p_scope_graph_constraint_v1_1",
                   "stage_p_scope_graph_constraint_v1_2", "stage_p_creative_target_constraint_v1"):
        _load(prefix + module, semantic_root / f"{module}.py")
    dfa = _load(prefix + "stage_p_construction_role_constraint_v1",
                semantic_root / "stage_p_construction_role_constraint_v1.py")
    _load(prefix + "gate_f_trie_projector_v1", semantic_root / "gate_f_trie_projector_v1.py")
    _load(prefix + "stage_p_trie_projector_v1", semantic_root / "stage_p_trie_projector_v1.py")
    _load(prefix + "stage_p_liveness_trie_projector_v1", semantic_root / "stage_p_liveness_trie_projector_v1.py")
    projector = _load(prefix + "stage_p_diagnostic_trie_projector_v1",
                      semantic_root / "stage_p_diagnostic_trie_projector_v1.py")
    _load(prefix + "stage_p_scope_graph_incremental_tracker_v1_1",
          semantic_root / "stage_p_scope_graph_incremental_tracker_v1_1.py")
    _load(prefix + "stage_p_scope_graph_callback_controller_v1_1",
          semantic_root / "stage_p_scope_graph_callback_controller_v1_1.py")
    _load(prefix + "stage_p_construction_role_incremental_tracker_v1",
          semantic_root / "stage_p_construction_role_incremental_tracker_v1.py")
    controller = _load(prefix + "stage_p_construction_role_callback_controller_v1",
                       semantic_root / "stage_p_construction_role_callback_controller_v1.py")
    lifecycle = _load(prefix + "append_only_lifecycle_v1", semantic_root / "append_only_lifecycle_v1.py")
    return (dfa.StagePConstructionRoleConstraintStateV1, projector.StagePDiagnosticTokenTrieProjectorV1,
            controller.StagePConstructionRoleCallbackControllerV1, lifecycle.AppendOnlyLifecycleV1)


def main(arguments: list[str]) -> None:
    if len(arguments) != 4:
        raise SystemExit("usage: runner REQUEST RESPONSE PROMPT DURABLE_LIFECYCLE_ROOT")
    base = _load("pastila_stage_p_construction_role_durable_runner_base",
                 ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v3.py")
    base._types = _construction_role_types
    base.run(*map(Path, arguments))


if __name__ == "__main__":
    main(sys.argv[1:])
