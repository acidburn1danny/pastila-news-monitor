"""WSL worker: compare two local tokenizer configurations; never load a model."""
import hashlib
import json
import sys
from pathlib import Path

from transformers import AutoTokenizer

source, target, model = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
samples = json.loads(source.read_text("utf-8"))
legacy = AutoTokenizer.from_pretrained(model, local_files_only=True)
fixed = AutoTokenizer.from_pretrained(model, local_files_only=True, fix_mistral_regex=True)
records = []
for sample in samples:
    old = legacy.encode(sample["text"], add_special_tokens=False)
    new = fixed.encode(sample["text"], add_special_tokens=False)
    records.append({
        "id": sample["id"],
        "legacy_count": len(old),
        "fixed_count": len(new),
        "identical_token_ids": old == new,
        "legacy_sha256": hashlib.sha256(json.dumps(old, separators=(",", ":")).encode()).hexdigest(),
        "fixed_sha256": hashlib.sha256(json.dumps(new, separators=(",", ":")).encode()).hexdigest(),
        "first_difference": next((index for index, pair in enumerate(zip(old, new)) if pair[0] != pair[1]), None if len(old) == len(new) else min(len(old), len(new))),
    })
different = [record["id"] for record in records if not record["identical_token_ids"]]
target.write_text(json.dumps({"legacy_class": type(legacy).__name__, "fixed_class": type(fixed).__name__, "different_count": len(different), "different_ids": different, "records": records}, indent=2) + "\n", "utf-8")
