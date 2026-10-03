from __future__ import annotations
import argparse, gc, hashlib, json, os, random, re, shutil, subprocess, time
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
import bitsandbytes as bnb
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL = Path('/root/vnext-voice-candidates-v1/sha256/be259728abcc2c864bdf4d035267a8fcf8ccc57e4e277f8bd5d0934f1963fbc')
EXPECTED_HEAD = '095b2dc3c3a07905e7de2fd6c6195fa2e834f03a'
SEEDS = [2111, 3407, 4933]
SYSTEM = ('Ești VOICE în fluxul Pastila Acidă. Primești numai un setup factual autorizat. '
          'Scrie comentariu editorial în română, precis, natural și concis, cu ironie/satiră când este susținută. '
          'Nu inventa fapte, cifre, persoane, citate sau evenimente. Nu explica instrucțiunile și nu descrie stilul.')

INTERVENTION={'id':'TARGET_RELATIVE_TERMINAL_EOS_LOSS_SHARE','content_loss_share':0.95,'terminal_eos_loss_share':0.05,'per_example_total_loss_mass':1.0,'formula':'0.95*mean(content_token_ce)+0.05*terminal_eos_ce','sampling':'C0_UNIFORM'}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(x): return hashlib.sha256(canon(x)).hexdigest()
def file_manifest(root,names): return {n:sha(root/n) for n in names if (root/n).is_file()}
def rows(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def setseed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)
def prompt(tok, setup):
    msgs=[{'role':'system','content':SYSTEM},{'role':'user','content':'SETUP FACTUAL AUTORIZAT:\n'+setup.strip()+'\n\nScrie numai comentariul VOICE.'}]
    return tok.apply_chat_template(msgs,tokenize=False,add_generation_prompt=True,enable_thinking=False)
def encode(tok,row,max_len=1024):
    p=prompt(tok,row['factual_setup']['text']); a=row['gold_commentary']['text'].strip()+tok.eos_token
    pi=tok(p,add_special_tokens=False)['input_ids']; ids=tok(p+a,add_special_tokens=False,truncation=True,max_length=max_len)['input_ids']
    labels=[-100]*min(len(pi),len(ids))+ids[min(len(pi),len(ids)):]
    return torch.tensor(ids),torch.tensor(labels)
def load_base(train=False):
    q=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True)
    m=AutoModelForCausalLM.from_pretrained(MODEL,quantization_config=q,device_map={'':0},local_files_only=True)
    if train: m=prepare_model_for_kbit_training(m,use_gradient_checkpointing=True)
    return m
def a2_loss(model,ids,labels,eos_id):
    logits=model(input_ids=ids).logits[:,:-1,:].contiguous(); target=labels[:,1:].contiguous(); valid=target.ne(-100)
    target_valid=target[valid]; logits_valid=logits[valid]
    if target_valid.numel()<2 or int(target_valid[-1])!=eos_id or int(target_valid.eq(eos_id).sum())!=1: raise RuntimeError('A2 terminal EOS invariant')
    ce=F.cross_entropy(logits_valid.float(),target_valid,reduction='none')
    return 0.95*ce[:-1].mean()+0.05*ce[-1]
def generate(model,tok,data):
    model.eval(); out=[]
    for r in data:
        p=prompt(tok,r['factual_setup']['text']); x=tok(p,return_tensors='pt',add_special_tokens=False).to('cuda')
        with torch.inference_mode(): y=model.generate(**x,max_new_tokens=220,do_sample=False,pad_token_id=tok.eos_token_id,return_dict_in_generate=True)
        gen=y.sequences[0,x['input_ids'].shape[1]:].tolist(); eos_positions=[i for i,t in enumerate(gen) if t==tok.eos_token_id]; finish='EOS' if eos_positions else 'MAX_NEW_TOKENS'; cap=not eos_positions and len(gen)>=220
        text=tok.decode(gen,skip_special_tokens=True).strip(); target_text=r['gold_commentary']['text'].strip(); target_ids=tok(target_text+tok.eos_token,add_special_tokens=False)['input_ids']
        out.append({'record_id':r['record_id'],'episode':r.get('episode',r.get('family_identity','CONTEMPORARY_OWNER_GOLD')),'output':text,'output_sha256':hashlib.sha256(text.encode()).hexdigest(),'generated_token_ids':gen,'finish_reason':finish,'generation_cap_hit':cap,'generated_token_length':len(gen),'target_token_length':len(target_ids),'output_word_length':len(re.findall(r'\w+',text,re.UNICODE)),'target_word_length':len(re.findall(r'\w+',target_text,re.UNICODE))})
    return out
def ngrams(text,n):
    t=re.findall(r'\w+',text.lower(),re.UNICODE); return {tuple(t[i:i+n]) for i in range(max(0,len(t)-n+1))}
def copy_metrics(outputs,train):
    gold=[r['gold_commentary']['text'] for r in train]; exact=0; max_run=0
    gold12=set().union(*(ngrams(x,12) for x in gold))
    for o in outputs:
        norm=' '.join(o['output'].lower().split())
        exact += any(norm==' '.join(g.lower().split()) for g in gold)
        max_run=max(max_run,12 if ngrams(o['output'],12)&gold12 else 0)
    return {'exact_train_output_copies':exact,'max_detected_consecutive_train_tokens':max_run}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    repo=a.repo.resolve(); out=a.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if head!=EXPECTED_HEAD: raise SystemExit('HEAD mismatch '+head)
    trainp=repo/'docs/artifacts/vnext-voice-owner-gold-pack03-v1-train-successor.jsonl'; valp=repo/'docs/artifacts/vnext-voice-owner-gold-pack03-v1-validation-successor.jsonl'
    expected={'train':'0edc1b25c0e279bafbbb712da0f977bce9dd68f4b56f5bd775ab3ec965c81379','validation':'0e2d9ffba211af997b04f2f2238c3e6de7904c89b38e25167e63d109fe6bbdda'}
    if sha(trainp)!=expected['train'] or sha(valp)!=expected['validation']: raise SystemExit('dataset identity mismatch')
    design=json.loads((repo/'docs/artifacts/vnext-qwen3-voice-a2-design-freeze-v1.json').read_text(encoding='utf-8')); claimed=design['design_identity']
    if claimed!='0e58b1de172e151936c7d3e9060e37d601cc9286af1296fbe0453a039a70a49a' or claimed!=ident({k:v for k,v in design.items() if k!='design_identity'}): raise SystemExit('published A2 design identity mismatch')
    cfg={'schema':'vnext-qwen3-a2-explicit-stopping-frozen-config','schema_version':1,'authority_commit':head,'base_model_identity':MODEL.name,'base_model_revision':MODEL.name,'tokenizer_identity':ident(file_manifest(MODEL,['tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt'])),'dataset_identity':'b48426314ce66a8bfb8f1e773cf171c07de0116b170dafec2a9c85228439c4e6','corpus_freeze_identity':'e2f94bb1266cbe64ea48eb244d95637c4d5f1dfdb7d250b3857834c4dc445a8c','published_design_identity':'0e58b1de172e151936c7d3e9060e37d601cc9286af1296fbe0453a039a70a49a','candidate_matrix_identity':'fbafef9f5e40371f93b8b63fb855ae8330e2da057214619db41ef6a20d48761d','design_audit_identity':'57ff457e997755f056f754ab26105a80c01008b16926b971d62570c492a9ebb6','control_c0_config_identity':'4abb9cde5011b0a7e84b135f82fd98f0bcbd52661ae5cd6db215bc915bd0111d','negative_control_a1_config_identity':'383c63d7d8cbccb186d49914b3eed4b75d6adb9ad1f6bdbd675fec0f7c42c088','intervention':INTERVENTION,'intervention_identity':ident(INTERVENTION),'implementation_identity':sha(Path(__file__)),'acceptance_criteria':design['acceptance'],'premature_truncation_safeguards':design['premature_truncation_safeguards'],'model_path':str(MODEL),'model_config_sha256':sha(MODEL/'config.json'),'dataset_sha256':expected,'seeds':SEEDS,'lora':{'r':4,'alpha':8,'dropout':0.05,'targets':['q_proj','v_proj']},'quantization':'NF4_DOUBLE_BF16','epochs':4,'learning_rate':5e-5,'batch_size':1,'gradient_accumulation':3,'max_length':1024,'optimizer':'paged_adamw_8bit','prompt_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),'decoding':{'do_sample':False,'max_new_tokens':220},'holdout_access_before_freeze':0,'promotable':False,'voice_state':'DISABLED_UNTIL_PROMOTION'}
    cfg['config_identity']=ident(cfg); (out/'frozen-config.json').write_bytes(json.dumps(cfg,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n')
    train=rows(trainp); val=rows(valp); tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True); tok.pad_token=tok.eos_token
    shutil.copyfile(Path('/root/vnext-qwen3-experimental-lora-v2-run/baseline-validation.json'),out/'baseline-validation.json')
    summaries=[]
    for seed in SEEDS:
        setseed(seed); m=load_base(True); m=get_peft_model(m,LoraConfig(r=4,lora_alpha=8,lora_dropout=0.05,target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
        m.train(); opt=bnb.optim.PagedAdamW8bit((p for p in m.parameters() if p.requires_grad),lr=5e-5); losses=[]; steps=0; order=list(range(len(train)))
        for epoch in range(4):
            random.Random(seed+epoch).shuffle(order); opt.zero_grad(set_to_none=True)
            for j,idx in enumerate(order):
                ids,labs=encode(tok,train[idx]); ids=ids.unsqueeze(0).to('cuda'); labs=labs.unsqueeze(0).to('cuda')
                raw_loss=a2_loss(m,ids,labs,tok.eos_token_id); loss=raw_loss/3; loss.backward(); losses.append(float(raw_loss.item()))
                if (j+1)%3==0 or j+1==len(order): opt.step(); opt.zero_grad(set_to_none=True); steps+=1
        sd=out/f'seed-{seed}'; sd.mkdir(); m.save_pretrained(sd,safe_serialization=True); tok.save_pretrained(sd)
        vo=generate(m,tok,val); (sd/'validation-outputs.json').write_text(json.dumps(vo,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        with torch.no_grad():
            vl=[]
            for r in val:
                ids,labs=encode(tok,r); vl.append(float(m(input_ids=ids.unsqueeze(0).to('cuda'),labels=labs.unsqueeze(0).to('cuda')).loss.item()))
        files=[]
        for p in sorted(sd.iterdir()):
            if p.is_file(): files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
        summary={'seed':seed,'intervention_identity':cfg['intervention_identity'],'optimizer_steps':steps,'train_loss_first':losses[0],'train_loss_last':losses[-1],'train_loss_mean':sum(losses)/len(losses),'validation_loss_mean':sum(vl)/len(vl),'package_files':files,'package_identity':ident(files),'copy_analysis':copy_metrics(vo,train)}
        summaries.append(summary); (sd/'run-summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
        del m,opt; gc.collect(); torch.cuda.empty_cache()
    result={'schema':'vnext-qwen3-a2-explicit-stopping-training-result','schema_version':1,'status':'TRAINING_AND_PACKAGE_PASS','config_identity':cfg['config_identity'],'runs':summaries,'holdout_access':0,'promotion':False,'voice_state':'DISABLED_UNTIL_PROMOTION'}; result['result_identity']=ident(result)
    (out/'training-result.json').write_bytes(json.dumps(result,sort_keys=True,indent=2).encode()+b'\n'); print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
