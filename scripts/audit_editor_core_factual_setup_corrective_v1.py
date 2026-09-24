"""Fail-closed closure and anti-contamination audit for factual-setup corrective v1."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; PREFIX='editor-core-factual-setup-corrective-v1'
def sha(x): return hashlib.sha256(x).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def load(p): return [json.loads(x) for x in p.read_bytes().splitlines()]
def audit():
    m=json.loads((ART/f'{PREFIX}-manifest.json').read_text(encoding='utf-8')); c=json.loads((ART/f'{PREFIX}-config.json').read_text(encoding='utf-8'))
    sets={n:load(ART/f'{PREFIX}-{n}.jsonl') for n in ('training','holdout-requests','holdout-answer-key')}
    for n,rows in sets.items():
        raw=(ART/f'{PREFIX}-{n}.jsonl').read_bytes(); assert len(rows)==m['artifacts'][n]['rows'] and sha(raw)==m['artifacts'][n]['sha256']
    assert (len(sets['training']),len(sets['holdout-requests']),len(sets['holdout-answer-key']))==(72,24,24)
    ids={n:{x['example_id'] for x in rows} for n,rows in sets.items()}; assert not(ids['training']&ids['holdout-requests']); assert ids['holdout-requests']==ids['holdout-answer-key']
    assert all(len(x['messages'])==3 for x in sets['training']); assert all(len(x['messages'])==2 for x in sets['holdout-requests'])
    assert not any('assistant_target' in canon(x).decode() for x in sets['holdout-requests'])
    new_targets={x['messages'][2]['content'] for x in sets['training']}|{x['assistant_target'] for x in sets['holdout-answer-key']}
    old_targets=set(); scanned=[]
    for p in sorted(ART.glob('*.jsonl')):
        if p.name.startswith(PREFIX) or 'holdout' in p.name.lower(): continue
        if not ('training' in p.name.lower() or 'new-train' in p.name.lower() or 'benchmark-v1-answer-key' in p.name.lower()): continue
        scanned.append(p.name)
        for x in load(p):
            if isinstance(x.get('assistant_target'),str): old_targets.add(x['assistant_target'])
            for msg in x.get('messages',[]):
                if msg.get('role')=='assistant': old_targets.add(msg.get('content',''))
    assert not(new_targets&old_targets)
    counts={k:sum(x['failure_class']==k for x in sets['training']) for k in m['failure_classes']}; holdcounts={k:sum(x['failure_class']==k for x in sets['holdout-requests']) for k in m['failure_classes']}
    assert set(counts.values())=={12} and set(holdcounts.values())=={4}
    core={'schema':'editor-factual-setup-corrective-audit','schema_version':1,'status':'PASS','manifest_identity':m['manifest_identity'],'config_identity':c['config_identity'],'training_rows':72,'targeted_rows':48,'replay_rows':24,'holdout_rows':24,'training_class_counts':counts,'holdout_class_counts':holdcounts,'exact_target_contamination':0,'historical_holdouts_read':False,'historical_non_holdout_files_scanned':scanned,'voice_chief_objective':False}
    return {**core,'audit_identity':sha(canon(core))}
if __name__=='__main__': print(json.dumps(audit(),ensure_ascii=False,sort_keys=True))
