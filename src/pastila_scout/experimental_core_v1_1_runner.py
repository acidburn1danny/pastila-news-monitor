"""WSL-side single-request runner for the frozen experimental Core V1.1."""

import json
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
ADAPTER = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.3/runs/pastila-editor-core-v1-1-targeted-20260820-001/checkpoint-final/adapter")


def main() -> None:
    request_path, response_path, prompt_path = map(Path, sys.argv[1:4])
    request = json.loads(request_path.read_text("utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL,
        local_files_only=True,
        quantization_config=quantization,
        device_map={"": 0},
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    )
    model.model.vision_tower = None
    model.model.multi_modal_projector = None
    model = PeftModel.from_pretrained(model, ADAPTER, is_trainable=False)
    model.eval()
    batch = tokenizer.apply_chat_template(
        [
            {"role": "system", "content": prompt_path.read_text("utf-8")},
            {"role": "user", "content": request["prompt"]},
        ],
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )
    batch = {name: value.to("cuda") for name, value in batch.items()}
    with torch.inference_mode():
        generated = model.generate(
            **batch,
            do_sample=False,
            num_beams=1,
            repetition_penalty=1.0,
            max_new_tokens=int(request["max_new_tokens"]),
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
            use_cache=True,
        )
    tokens = generated[0, batch["input_ids"].shape[1] :].cpu()
    response_path.write_text(
        json.dumps(
            {
                "output": tokenizer.decode(tokens, skip_special_tokens=True),
                "terminal_eos": bool(
                    len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id
                ),
            },
            ensure_ascii=False,
        ),
        "utf-8",
    )


if __name__ == "__main__":
    main()
