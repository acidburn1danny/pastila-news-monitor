"""Deferred Linux runtime operations for Construction-Obligation V2.

Importing this module performs no runtime import or operation.  The public
preparation function is intentionally not an entry point and owns no process,
filesystem, WSL, provider, or authority-receipt behavior.
"""
from __future__ import annotations

import gc
import hashlib
import warnings
from dataclasses import dataclass
from importlib.metadata import version as _package_version
from pathlib import Path
from typing import Callable, Sequence

from .stage_p_construction_obligation_v2_adapter_compatibility_gate_v1 import (
    canonical_adapter_compatibility_observation_v1,
    validate_adapter_compatibility_gate_v1,
)
from .stage_p_construction_obligation_v2_injected_generation_worker_v1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOutputV1,
)
from .stage_p_construction_obligation_v2_model_load_linux_worker_v1 import (
    ADAPTER_PATH, BASE_MODEL_PATH,
)
from .stage_p_construction_obligation_v2_model_load_linux_worker_v1_1 import (
    adapter_tensor_keys_from_header_v1,
    parse_peft_missing_adapter_warning_v1,
)
from .stage_p_construction_obligation_v2_runtime_operations_adapter_v1_1 import (
    ExplicitRuntimeGenerationOperationsV1_1,
)
from .stage_p_construction_obligation_v2_runtime_operations_contract_v1 import (
    DECODER_IDENTITY, DEVICE_TRANSFER_POLICY, TOKENIZER_IDENTITY,
    RuntimePromptBatchV1, validate_runtime_prompt_batch_v1,
)
from .stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    PROJECTOR_FREEZE_IDENTITY, SPECIAL_TOKEN_IDS, TRANSFORMERS_VERSION,
    TokenPieceBundleV1, TokenizerRuntimeIdentityV1,
    extract_identity_bound_token_pieces_v1,
)


LINUX_RUNTIME_ADAPTER_IDENTITY = "757ebf033bc762a6fd95b5ee22f16bc19b8d21ab62c60c280ea3f55e1bba387c"
SYSTEM_PROMPT_SHA256 = "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17"
PACKAGE_IDENTITIES = (
    "transformers==5.15.0", "torch==2.13.0+cu130", "peft==0.20.0",
    "accelerate==1.14.0", "bitsandbytes==0.50.1",
)


@dataclass(slots=True)
class LinuxGenerationResourceV1:
    model: object | None
    torch_runtime: object


@dataclass(frozen=True, slots=True)
class PreparedLinuxRuntimeOperationsV1:
    operations: ExplicitRuntimeGenerationOperationsV1_1
    token_piece_bundle: TokenPieceBundleV1
    tokenizer: object
    prompt_batch_receipt: bytes


def prepare_linux_runtime_operations_v1(
    *, rendered_prompt: str, system_prompt: str,
) -> PreparedLinuxRuntimeOperationsV1:
    """Load the exact tokenizer and prepare deferred model operations."""
    _validate_packages()
    if (type(system_prompt) is not str
            or hashlib.sha256(system_prompt.encode("utf-8")).hexdigest() != SYSTEM_PROMPT_SHA256):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH")
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH, local_files_only=True)
    identity = TokenizerRuntimeIdentityV1(
        TOKENIZER_IDENTITY, DECODER_IDENTITY, TRANSFORMERS_VERSION,
        type(tokenizer).__name__, len(tokenizer), tokenizer.eos_token_id,
        tuple(sorted(tokenizer.all_special_ids)), PROJECTOR_FREEZE_IDENTITY,
    )
    pieces = extract_identity_bound_token_pieces_v1(
        tokenizer=tokenizer, identity=identity)
    encoded = tokenizer.apply_chat_template(
        [{"role": "system", "content": system_prompt},
         {"role": "user", "content": rendered_prompt}],
        tokenize=True, add_generation_prompt=True,
        return_tensors="pt", return_dict=True,
    )
    if type(encoded) is not dict or set(encoded) != {"input_ids", "attention_mask"}:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_PROMPT_TENSOR_SHAPE_INVALID")
    input_ids = _row(encoded["input_ids"], "INPUT_IDS")
    attention_mask = _row(encoded["attention_mask"], "ATTENTION_MASK")
    batch = RuntimePromptBatchV1(
        input_ids, attention_mask, len(input_ids),
        hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest(),
        TOKENIZER_IDENTITY, DECODER_IDENTITY, 1, DEVICE_TRANSFER_POLICY,
    )
    receipt = validate_runtime_prompt_batch_v1(
        rendered_prompt=rendered_prompt, batch=batch)

    def load_compatible() -> InjectedCompatibleGenerationResourceV1:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForImageTextToText, BitsAndBytesConfig

        model = None
        try:
            quantization = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
            model = AutoModelForImageTextToText.from_pretrained(
                BASE_MODEL_PATH, local_files_only=True,
                quantization_config=quantization, device_map={"": 0},
                dtype=torch.bfloat16, low_cpu_mem_usage=True,
            )
            adapter_keys = adapter_tensor_keys_from_header_v1(
                adapter_path=Path(ADAPTER_PATH))
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                model = PeftModel.from_pretrained(
                    model, ADAPTER_PATH, is_trainable=False)
            missing = parse_peft_missing_adapter_warning_v1(
                messages=tuple(str(item.message) for item in caught))
            observed = canonical_adapter_compatibility_observation_v1()
            observed = type(observed)(
                observed.adapter_config_sha256, observed.adapter_weights_sha256,
                observed.peft_model_source_sha256, observed.peft_lora_layer_source_sha256,
                observed.target_modules, observed.init_lora_weights,
                observed.inference_mode, observed.rank, observed.lora_alpha,
                observed.lora_dropout, adapter_keys, missing, (),
            )
            compatibility = validate_adapter_compatibility_gate_v1(observed=observed)
            model.eval()
            return InjectedCompatibleGenerationResourceV1(
                LinuxGenerationResourceV1(model, torch), compatibility)
        except Exception:
            model = None
            gc.collect()
            torch.cuda.empty_cache()
            raise

    def generate_once(
        resource: object, observed_batch: RuntimePromptBatchV1,
        maximum_output_tokens: int,
        allowed: Callable[[Sequence[int]], tuple[int, ...]],
    ) -> InjectedGenerationOutputV1:
        if type(resource) is not LinuxGenerationResourceV1 or resource.model is None:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_LINUX_RESOURCE_EXACT_TYPE_REQUIRED")
        if observed_batch != batch:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_LINUX_PROMPT_BATCH_DRIFT")
        if (type(maximum_output_tokens) is not int
                or not 0 < maximum_output_tokens <= 3200):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_LINUX_OUTPUT_CEILING_INVALID")
        runtime_batch = {
            key: value.to("cuda", non_blocking=False)
            for key, value in encoded.items()
        }

        def prefix_allowed_tokens(batch_id, input_token_ids):
            if type(batch_id) is not int or batch_id != 0:
                raise ValueError("CONSTRUCTION_OBLIGATION_V2_LINUX_BATCH_ID_INVALID")
            return list(allowed(tuple(input_token_ids.tolist())))

        torch_runtime = resource.torch_runtime
        with torch_runtime.inference_mode():
            generated = resource.model.generate(
                **runtime_batch, do_sample=False, num_beams=1,
                repetition_penalty=1.0, max_new_tokens=maximum_output_tokens,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=(tokenizer.pad_token_id
                              if tokenizer.pad_token_id is not None
                              else tokenizer.eos_token_id),
                use_cache=True,
                prefix_allowed_tokens_fn=prefix_allowed_tokens,
            )
        generated_ids = tuple(generated[0][batch.prompt_token_count:].tolist())
        output = tokenizer.decode(
            generated_ids, skip_special_tokens=True,
            clean_up_tokenization_spaces=False).encode("utf-8")
        terminal = bool(
            generated_ids and generated_ids[-1] == tokenizer.eos_token_id)
        return InjectedGenerationOutputV1(output, generated_ids, terminal)

    def cleanup(resource: object) -> None:
        if type(resource) is not LinuxGenerationResourceV1:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_LINUX_RESOURCE_EXACT_TYPE_REQUIRED")
        resource.model = None
        gc.collect()
        resource.torch_runtime.cuda.empty_cache()

    operations = ExplicitRuntimeGenerationOperationsV1_1(
        batch, load_compatible, generate_once, cleanup)
    return PreparedLinuxRuntimeOperationsV1(
        operations, pieces, tokenizer, receipt)


def _validate_packages() -> None:
    observed = tuple(
        f"{name}=={_package_version(name)}"
        for name in ("transformers", "torch", "peft", "accelerate", "bitsandbytes")
    )
    if observed != PACKAGE_IDENTITIES:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_LINUX_RUNTIME_PACKAGE_MISMATCH")


def _row(tensor: object, label: str) -> tuple[int, ...]:
    if not hasattr(tensor, "shape") or tuple(tensor.shape)[0:1] != (1,):
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_RUNTIME_{label}_BATCH_INVALID")
    try:
        value = tuple(tensor[0].tolist())
    except Exception as exc:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_RUNTIME_{label}_TENSOR_INVALID") from exc
    if any(type(item) is not int for item in value):
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_RUNTIME_{label}_TENSOR_INVALID")
    return value


__all__ = (
    "LINUX_RUNTIME_ADAPTER_IDENTITY", "LinuxGenerationResourceV1",
    "PreparedLinuxRuntimeOperationsV1", "prepare_linux_runtime_operations_v1",
)
