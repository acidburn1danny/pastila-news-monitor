from __future__ import annotations
import argparse, gc, hashlib, json, os, random, re, shutil, subprocess, time
from pathlib import Path
import numpy as np
import torch
import bitsandbytes as bnb
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL = Path('/root/vnext-voice-candidates-v1/sha256/be259728abcc2c864bdf4d035267a8fcf8ccc57e4e277f8bd5d0934f1963fbc')
EXPECTED_HEAD = '8305cbaf9669c6b40d4c836a96598887dca68262'
SEEDS = [1811, 3001, 4621]
SYSTEM = ('Ești VOICE în fluxul Pastila Acidă. Primești numai un setup factual autorizat. '
          'Scrie comentariu editorial în română, precis, natural și concis, cu ironie/satiră când este susținută. '
          'Nu inventa fapte, cifre, persoane, citate sau evenimente. Nu explica instrucțiunile și nu descrie stilul.')

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
def generate(model,tok,data):
    model.eval(); out=[]
    for r in data:
        p=prompt(tok,r['factual_setup']['text']); x=tok(p,return_tensors='pt',add_special_tokens=False).to('cuda')
        with torch.inference_mode(): y=model.generate(**x,max_new_tokens=220,do_sample=False,pad_token_id=tok.eos_token_id)
        text=tok.decode(y[0,x['input_ids'].shape[1]:],skip_special_tokens=True).strip()
        out.append({'record_id':r['record_id'],'episode':r.get('episode',r.get('family_identity','CONTEMPORARY_OWNER_GOLD')),'output':text,'output_sha256':hashlib.sha256(text.encode()).hexdigest()})
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
    cfg={'schema':'vnext-qwen3-second-experimental-lora-frozen-config','schema_version':1,'authority_commit':head,'base_model_identity':MODEL.name,'base_model_revision':MODEL.name,'tokenizer_identity':ident(file_manifest(MODEL,['tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt'])),'dataset_identity':'b48426314ce66a8bfb8f1e773cf171c07de0116b170dafec2a9c85228439c4e6','corpus_freeze_identity':'e2f94bb1266cbe64ea48eb244d95637c4d5f1dfdb7d250b3857834c4dc445a8c','predecessor_experiment':{'config':'7c0c2e97a1a55b2cbd6453ae179d1c0203331bda0daff2084b4c1d0f7467c1d3','training':'9eef9e86d5a4c35db2f203cf5a92f599e5aa2b1942b02b86fb0a3f33d933b231','evaluation':'4a24e59544c95fba72a17c7937650e1b5b19ca40e8a54c5582918c0fb62935f8'},'model_path':str(MODEL),'model_config_sha256':sha(MODEL/'config.json'),'dataset_sha256':expected,'seeds':SEEDS,'lora':{'r':4,'alpha':8,'dropout':0.05,'targets':['q_proj','v_proj']},'quantization':'NF4_DOUBLE_BF16','epochs':4,'learning_rate':5e-5,'batch_size':1,'gradient_accumulation':3,'max_length':1024,'optimizer':'paged_adamw_8bit','prompt_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),'decoding':{'do_sample':False,'max_new_tokens':220},'holdout_access_before_freeze':0,'promotable':False,'voice_state':'DISABLED_UNTIL_PROMOTION'}
    cfg['config_identity']=ident(cfg); (out/'frozen-config.json').write_bytes(json.dumps(cfg,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n')
    train=rows(trainp); val=rows(valp); tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True); tok.pad_token=tok.eos_token
    baseline=load_base(False); baseout=generate(baseline,tok,val); (out/'baseline-validation.json').write_text(json.dumps(baseout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); del baseline; gc.collect(); torch.cuda.empty_cache()
    summaries=[]
    for seed in SEEDS:
        setseed(seed); m=load_base(True); m=get_peft_model(m,LoraConfig(r=4,lora_alpha=8,lora_dropout=0.05,target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
        m.train(); opt=bnb.optim.PagedAdamW8bit((p for p in m.parameters() if p.requires_grad),lr=5e-5); losses=[]; steps=0; order=list(range(len(train)))
        for epoch in range(4):
            random.Random(seed+epoch).shuffle(order); opt.zero_grad(set_to_none=True)
            for j,idx in enumerate(order):
                ids,labs=encode(tok,train[idx]); ids=ids.unsqueeze(0).to('cuda'); labs=labs.unsqueeze(0).to('cuda')
                loss=m(input_ids=ids,labels=labs).loss/3; loss.backward(); losses.append(float(loss.item()*3))
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
        summary={'seed':seed,'optimizer_steps':steps,'train_loss_first':losses[0],'train_loss_last':losses[-1],'train_loss_mean':sum(losses)/len(losses),'validation_loss_mean':sum(vl)/len(vl),'package_files':files,'package_identity':ident(files),'copy_analysis':copy_metrics(vo,train)}
        summaries.append(summary); (sd/'run-summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
        del m,opt; gc.collect(); torch.cuda.empty_cache()
    result={'schema':'vnext-qwen3-second-experimental-lora-training-result','schema_version':1,'status':'TRAINING_AND_PACKAGE_PASS','config_identity':cfg['config_identity'],'runs':summaries,'holdout_access':0,'promotion':False,'voice_state':'DISABLED_UNTIL_PROMOTION'}; result['result_identity']=ident(result)
    (out/'training-result.json').write_bytes(json.dumps(result,sort_keys=True,indent=2).encode()+b'\n'); print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
