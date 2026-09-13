"""Tokenizer-only audit for V10 corpora; performs no model load or inference."""

from __future__ import annotations

import json, sys
from collections import Counter
from pathlib import Path


def token_ids(encoded: object) -> list[int]:
    if hasattr(encoded, "get") and encoded.get("input_ids") is not None:
        encoded=encoded.get("input_ids")
    values=getattr(encoded,"ids",encoded)
    if isinstance(values,(list,tuple)) and len(values)==1 and hasattr(values[0],"ids"):
        values=values[0].ids
    if not isinstance(values,(list,tuple)) or not all(type(item) is int for item in values):
        raise SystemExit("tokenizer output shape mismatch")
    return list(values)


def main() -> int:
    if len(sys.argv) not in {4,5}:
        raise SystemExit("usage: audit MODEL ARTIFACTS MAX_SEQUENCE_TOKENS [OUTPUT]")
    model, artifacts, ceiling = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(model,local_files_only=True,fix_mistral_regex=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
    summary={}
    paths=sorted(artifacts.glob("pastila-editor-core-v1.*-json-successor-v10-*.jsonl"))
    if len(paths)!=4: raise SystemExit("V10 corpus set mismatch")
    for path in paths:
        rows=[json.loads(line) for line in path.read_text("utf-8").splitlines()]
        lengths=[]; buckets=Counter()
        for row in rows:
            prefix=token_ids(tokenizer.apply_chat_template(row["messages"][:2],tokenize=True,add_generation_prompt=True))
            tokens=token_ids(tokenizer.apply_chat_template(row["messages"],tokenize=True,add_generation_prompt=False))
            if not tokens or tokens[-1]!=tokenizer.eos_token_id or tokenizer.eos_token_id in tokens[len(prefix):-1]:
                raise SystemExit(
                    f"supervised EOS contract mismatch: {path.name}:{row['example_id']}:"
                    f"prefix={len(prefix)}:tokens={len(tokens)}:last={tokens[-1] if tokens else None}:"
                    f"eos={tokenizer.eos_token_id}:premature={tokenizer.eos_token_id in tokens[len(prefix):-1]}"
                )
            if len(tokens)>ceiling: raise SystemExit(f"sequence ceiling exceeded: {path.name}:{row['example_id']}:{len(tokens)}")
            lengths.append(len(tokens)); buckets[row["length_bucket"]]+=1
        summary[path.name]={"rows":len(rows),"minimum_tokens":min(lengths),"maximum_tokens":max(lengths),"length_buckets":dict(sorted(buckets.items()))}
    raw=json.dumps(summary,sort_keys=True,separators=(",",":"))
    if len(sys.argv)==5: Path(sys.argv[4]).write_text(raw+"\n",encoding="utf-8")
    else: print(raw)
    return 0

if __name__=="__main__":raise SystemExit(main())
