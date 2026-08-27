"""Contract-remediated, evaluation-only SAV2 Core adapters."""
from __future__ import annotations
import hashlib
from pathlib import Path
from .core_adapter import CoreV12SemanticEvaluatorAdapter
from .models import GateIdV2

GATE_F_SOURCE_SHA256="baabb0f4830bad3d9d1c06adc1c074131d517ebb7715257dd6aa157fd5bc61b3"
GATE_S_SOURCE_SHA256="43dbbd21e77a49bfbfca42d585a986d7f012aeb754ad5a96a23eaaca97f001e8"
GATE_F_EXECUTION_SHA256="71f3d337c310d142b641efefcdec0ea8722db5fa5aebfa458acb45cea355ef57"
GATE_S_EXECUTION_SHA256="db09a481768e6d1c021b8eacac23be8449288993bec7eaa5ea4ad96866e8b2dc"
GATE_F_EVALUATOR_IDENTITY_V22="dee9034a840dfd08c9cd8ae9a1952161f1283914a35109fa375695afbd290c2e"
GATE_S_EVALUATOR_IDENTITY_V22="313c6817c7c2ddf75c736dd2c823e25f8ceaf7ac295e09625415f23f32a66b51"

class CoreV12SemanticEvaluatorAdapterV22(CoreV12SemanticEvaluatorAdapter):
    def __init__(self,*,project_root:Path,executor,gate_id:GateIdV2)->None:
        super().__init__(project_root=project_root,executor=executor,gate_id=gate_id)
        name,source_hash,execution_hash,evaluator_identity=(("semantic-admission-v2-gate-f-contract-v2-2-prompt.txt",GATE_F_SOURCE_SHA256,GATE_F_EXECUTION_SHA256,GATE_F_EVALUATOR_IDENTITY_V22) if gate_id is GateIdV2.FACTUAL_SEMANTIC else ("semantic-admission-v2-gate-s-contract-v2-2-prompt.txt",GATE_S_SOURCE_SHA256,GATE_S_EXECUTION_SHA256,GATE_S_EVALUATOR_IDENTITY_V22))
        data=(project_root/"docs"/"artifacts"/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=source_hash or not data.endswith(b"\n") or data.endswith(b"\n\n"):
            raise RuntimeError("SAV2.2 source prompt identity drift")
        execution=data[:-1]
        if hashlib.sha256(execution).hexdigest()!=execution_hash:
            raise RuntimeError("SAV2.2 executable prompt identity drift")
        self._template=execution.decode("utf-8",errors="strict")
        self.prompt_identity="sha256:"+execution_hash
        self.evaluator_identity=evaluator_identity

__all__=("CoreV12SemanticEvaluatorAdapterV22","GATE_F_EVALUATOR_IDENTITY_V22","GATE_S_EVALUATOR_IDENTITY_V22")
