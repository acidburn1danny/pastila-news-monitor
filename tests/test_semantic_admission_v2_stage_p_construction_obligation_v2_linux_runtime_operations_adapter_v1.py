from __future__ import annotations

import hashlib
import json
import sys
import types
from contextlib import nullcontext
from pathlib import Path

import pytest

import pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_runtime_operations_adapter_v1 as adapter
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_supervisor_v1 import (
    supervise_injected_generation_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_adapter_v1_1 import (
    adapt_runtime_operations_v1_1,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-linux-runtime-operations-adapter-v1.json"
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_runtime_operations_adapter_v1.py"
SYSTEM_PROMPT = (ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt").read_text("utf-8")
sys.path.insert(0, str(ROOT / "tests"))
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (  # noqa: E402
    COMPATIBILITY, _authority, _policy, _terminal_fixture,
)


class FakeVector:
    def __init__(self, values): self.values = list(values)
    def tolist(self): return list(self.values)
    def __getitem__(self, item): return FakeVector(self.values[item]) if isinstance(item, slice) else self.values[item]


class FakeTensor:
    def __init__(self, rows): self.rows = [list(row) for row in rows]; self.shape = (len(rows), len(rows[0]))
    def __getitem__(self, item): return FakeVector(self.rows[item])
    def to(self, device, *, non_blocking):
        assert (device, non_blocking) == ("cuda", False)
        return self


class TokenizersBackend:
    eos_token_id = 2
    pad_token_id = None
    all_special_ids = (0, 1, 2, 11)
    def __init__(self, text, calls): self.text = text; self.calls = calls
    def __len__(self): return 131_072
    def decode(self, ids, *, skip_special_tokens, clean_up_tokenization_spaces):
        assert skip_special_tokens is True and clean_up_tokenization_spaces is False
        return self.text if 100 in ids else ""
    def apply_chat_template(self, messages, **kwargs):
        self.calls.append(("chat", messages, kwargs))
        return {"input_ids": FakeTensor([[900, 901]]),
                "attention_mask": FakeTensor([[1, 1]])}


class FakeModel:
    def __init__(self, calls): self.calls = calls; self.vision_tower = object(); self.multi_modal_projector = object()
    def eval(self): self.calls.append("eval"); return self
    def generate(self, **kwargs):
        self.calls.append(("generate", kwargs))
        assert kwargs["do_sample"] is False and kwargs["num_beams"] == 1
        assert kwargs["repetition_penalty"] == 1.0 and kwargs["use_cache"] is True
        assert kwargs["max_new_tokens"] == 731
        assert kwargs["prefix_allowed_tokens_fn"](0, FakeVector([900, 901, 100])) == [2]
        return FakeTensor([[900, 901, 100, 2]])


def _install_fake_runtime(monkeypatch, text):
    calls = []; tokenizer = TokenizersBackend(text, calls); model = FakeModel(calls)
    class AutoTokenizer:
        @staticmethod
        def from_pretrained(path, **kwargs):
            calls.append(("tokenizer", path, kwargs)); return tokenizer
    class AutoModel:
        @staticmethod
        def from_pretrained(path, **kwargs):
            calls.append(("model", path, kwargs)); return model
    class Bits:
        def __init__(self, **kwargs): calls.append(("quantization", kwargs))
    class Peft:
        @staticmethod
        def from_pretrained(value, path, **kwargs):
            calls.append(("adapter", value, path, kwargs)); return value
    torch = types.SimpleNamespace(
        bfloat16="bf16", inference_mode=lambda: nullcontext(),
        cuda=types.SimpleNamespace(empty_cache=lambda: calls.append("empty_cache")))
    transformers = types.SimpleNamespace(
        AutoTokenizer=AutoTokenizer, AutoModelForImageTextToText=AutoModel,
        BitsAndBytesConfig=Bits)
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "peft", types.SimpleNamespace(PeftModel=Peft))
    monkeypatch.setattr(adapter, "_package_version", lambda name: {
        "transformers": "5.15.0", "torch": "2.13.0+cu130", "peft": "0.20.0",
        "accelerate": "1.14.0", "bitsandbytes": "0.50.1"}[name])
    return calls, tokenizer, model


def test_fake_runtime_maps_exact_tokenize_load_generate_and_cleanup(monkeypatch) -> None:
    bound, text, _ = _terminal_fixture()
    calls, tokenizer, model = _install_fake_runtime(monkeypatch, text)
    monkeypatch.setattr(adapter, "extract_identity_bound_token_pieces_v1",
                        lambda **kwargs: bound.projector_preflight.preflight.token_piece_bundle)
    monkeypatch.setattr(adapter, "adapter_tensor_keys_from_header_v1", lambda **kwargs: ())
    monkeypatch.setattr(adapter, "parse_peft_missing_adapter_warning_v1", lambda **kwargs: ())
    monkeypatch.setattr(adapter, "validate_adapter_compatibility_gate_v1",
                        lambda **kwargs: (calls.append("compatibility_validated")
                                          or COMPATIBILITY.read_bytes()))
    prepared = adapter.prepare_linux_runtime_operations_v1(
        rendered_prompt="runtime request", system_prompt=SYSTEM_PROMPT)
    assert prepared.operations.prompt_batch.input_token_ids == (900, 901)
    assert prepared.operations.prompt_batch.attention_mask == (1, 1)
    assert json.loads(prepared.prompt_batch_receipt)["prompt_token_count"] == 2
    result = supervise_injected_generation_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        callback_preflight=bound, rendered_prompt="runtime request",
        operations=adapt_runtime_operations_v1_1(
            rendered_prompt="runtime request", operations=prepared.operations))
    assert result.status == "TERMINAL_OUTPUT" and result.raw_output == text.encode()
    assert calls.count("empty_cache") == 1
    assert prepared.operations.load_compatible is not None
    assert model.vision_tower is not None and model.multi_modal_projector is not None
    model_call = next(item for item in calls if isinstance(item, tuple) and item[0] == "model")
    assert model_call[2]["device_map"] == {"": 0}
    assert "attn_implementation" not in model_call[2]
    assert tokenizer.pad_token_id is None
    quantization = next(item for item in calls if isinstance(item, tuple) and item[0] == "quantization")
    assert quantization[1] == {
        "load_in_4bit": True, "bnb_4bit_quant_type": "nf4",
        "bnb_4bit_compute_dtype": "bf16", "bnb_4bit_use_double_quant": True,
    }
    chat = next(item for item in calls if isinstance(item, tuple) and item[0] == "chat")
    assert chat[1] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "runtime request"},
    ]
    assert calls.index("compatibility_validated") < next(
        index for index, item in enumerate(calls)
        if isinstance(item, tuple) and item[0] == "generate")


def test_package_prompt_batch_and_output_mutations_fail_before_generation(monkeypatch) -> None:
    bound, text, _ = _terminal_fixture()
    calls, _, _ = _install_fake_runtime(monkeypatch, text)
    monkeypatch.setattr(adapter, "_package_version", lambda _: "wrong")
    with pytest.raises(ValueError, match="PACKAGE_MISMATCH"):
        adapter.prepare_linux_runtime_operations_v1(
            rendered_prompt="runtime request", system_prompt=SYSTEM_PROMPT)
    assert calls == []
    monkeypatch.setattr(adapter, "_package_version", lambda name: {
        "transformers": "5.15.0", "torch": "2.13.0+cu130", "peft": "0.20.0",
        "accelerate": "1.14.0", "bitsandbytes": "0.50.1"}[name])
    with pytest.raises(ValueError, match="SYSTEM_PROMPT_IDENTITY"):
        adapter.prepare_linux_runtime_operations_v1(
            rendered_prompt="runtime request", system_prompt=SYSTEM_PROMPT + "x")


def test_compatibility_failure_releases_pre_return_model(monkeypatch) -> None:
    bound, text, _ = _terminal_fixture()
    calls, _, _ = _install_fake_runtime(monkeypatch, text)
    monkeypatch.setattr(adapter, "extract_identity_bound_token_pieces_v1",
                        lambda **kwargs: bound.projector_preflight.preflight.token_piece_bundle)
    monkeypatch.setattr(adapter, "adapter_tensor_keys_from_header_v1", lambda **kwargs: ())
    monkeypatch.setattr(adapter, "parse_peft_missing_adapter_warning_v1", lambda **kwargs: ())
    monkeypatch.setattr(
        adapter, "validate_adapter_compatibility_gate_v1",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("synthetic incompatibility")))
    prepared = adapter.prepare_linux_runtime_operations_v1(
        rendered_prompt="runtime request", system_prompt=SYSTEM_PROMPT)
    with pytest.raises(ValueError, match="synthetic incompatibility"):
        prepared.operations.load_compatible()
    assert calls.count("empty_cache") == 1
    assert not any(isinstance(item, tuple) and item[0] == "generate" for item in calls)


def test_identity_artifact_and_source_boundary() -> None:
    artifact = json.loads(ARTIFACT.read_text("utf-8"))
    ordered = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(ordered).encode()).hexdigest() == adapter.LINUX_RUNTIME_ADAPTER_IDENTITY
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "source_normalization")
    source = SOURCE.read_text("utf-8")
    assert ".generate(" in source
    assert all(term not in source for term in (
        "if __name__", "subprocess", "Popen", "wsl.exe", "build_invocation",
        ".execute(", "vision_tower =", "multi_modal_projector =", "do_sample=True",
    ))
