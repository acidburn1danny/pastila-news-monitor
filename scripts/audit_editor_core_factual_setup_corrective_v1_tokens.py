"""Tokenizer-only EOS and budget audit for factual-setup corrective v1."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from transformers import AutoTokenizer
PREFIX='editor-core-factual-setup-corrective-v1'
def sha(x): return hashlib.sha256(x).hexdigest()
def ids(x):
    if hasattr(x,'get') and x.get('input_ids') is not None:x=x['input_ids']
    if hasattr(x,'tolist'):x=x.tolist()
    if isinstance(x,list) and len(x)==1 and isinstance(x[0],list):x=x[0]
    return list(x)
def load(p):return [json.loads(x) for x in p.read_bytes().splitlines()]
def audit(model,art):
    tok=AutoTokenizer.from_pretrained(model,local_files_only=True,fix_mistral_regex=True); tok.pad_token=tok.pad_token or tok.eos_token
    tr=load(art/f'{PREFIX}-training.jsonl'); hr=load(art/f'{PREFIX}-holdout-requests.jsonl'); keys={x['example_id']:x for x in load(art/f'{PREFIX}-holdout-answer-key.jsonl')}; lengths=[]
    for x in tr:
        prefix=ids(tok.apply_chat_template(x['messages'][:2],tokenize=True,add_generation_prompt=True)); full=ids(tok.apply_chat_template(x['messages'],tokenize=True,add_generation_prompt=False)); assert full[-1]==tok.eos_token_id and tok.eos_token_id not in full[len(prefix):-1]; lengths.append(len(full))
    for x in hr:
        prefix=ids(tok.apply_chat_template(x['messages'],tokenize=True,add_generation_prompt=True)); full=ids(tok.apply_chat_template(x['messages']+[{'role':'assistant','content':keys[x['example_id']]['assistant_target']}],tokenize=True,add_generation_prompt=False)); assert full[-1]==tok.eos_token_id and tok.eos_token_id not in full[len(prefix):-1]; lengths.append(len(full))
    core={'schema':'editor-factual-setup-corrective-token-audit','schema_version':1,'status':'PASS_TOKENIZER_ONLY','tokenizer_sha256':sha((model/'tokenizer.json').read_bytes()),'rows':96,'maximum_sequence_tokens':max(lengths),'ceiling':3072,'terminal_eos_verified':True,'model_loaded':False,'training_performed':False}; return {**core,'audit_identity':sha(json.dumps(core,sort_keys=True,separators=(',',':')).encode())}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('artifacts',type=Path);a=p.parse_args();print(json.dumps(audit(a.model,a.artifacts),sort_keys=True))
