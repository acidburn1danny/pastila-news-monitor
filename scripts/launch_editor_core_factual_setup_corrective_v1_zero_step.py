"""Fail-closed zero-step launcher for EDITOR factual-setup corrective v1."""
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'
COMMIT='1c7ca27d38199dbf547d157bf2d09ddcaf33632c'; TREE='ccc6414075ea96341406c1ed89d2926bd8cc2ab6'
MANIFEST='50b387a0025025f5daac68cd65ab5570a731f9bb0db2a82c023921829e806a88'; CONFIG='2b813d0485a3d3e186e4b5a4c88139af83d8d54fb25e759cee0921ee94da230b'
PARENT_ADAPTER='c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02';PARENT_CHECKPOINT='96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be'
BOUNDARY='0e8f70e013668c56e76053c38dfbd62331813553de31735492db183be7b3169f'
FILES=('docs/artifacts/editor-core-factual-setup-corrective-v1-config.json','docs/artifacts/editor-core-factual-setup-corrective-v1-holdout-answer-key.jsonl','docs/artifacts/editor-core-factual-setup-corrective-v1-holdout-requests.jsonl','docs/artifacts/editor-core-factual-setup-corrective-v1-manifest.json','docs/artifacts/editor-core-factual-setup-corrective-v1-token-audit.json','docs/artifacts/editor-core-factual-setup-corrective-v1-training.jsonl','docs/editor-core-factual-setup-corrective-v1.md','scripts/audit_editor_core_factual_setup_corrective_v1.py','scripts/audit_editor_core_factual_setup_corrective_v1_tokens.py','scripts/build_editor_core_factual_setup_corrective_v1.py','scripts/run_editor_core_factual_setup_corrective_v1_token_audit.sh','tests/test_editor_core_factual_setup_corrective_v1.py')
ZERO_STEP_FILES=('docs/artifacts/editor-core-factual-setup-corrective-v1-zero-step-boundary.json','scripts/launch_editor_core_factual_setup_corrective_v1_zero_step.py','tests/test_editor_core_factual_setup_corrective_v1_zero_step.py')
def canonical(x):return json.dumps(x,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(p.read_bytes())
def flat_manifest(root):
    if root.is_symlink() or not root.is_dir():raise ValueError('parent adapter root')
    rows=[]
    for p in sorted(root.iterdir(),key=lambda x:x.name.encode()):
        if p.is_symlink() or not p.is_file():raise ValueError('parent adapter closure')
        rows.append(p.name.encode()+b'\0'+p.stat().st_size.to_bytes(8,'big')+bytes.fromhex(file_sha(p)))
    return sha(b''.join(rows))
def validate_public():
    git=['git','-c',f'safe.directory={ROOT}']; tree=subprocess.check_output([*git,'rev-parse',f'{COMMIT}^{{tree}}'],cwd=ROOT,text=True).strip()
    if tree!=TREE:raise ValueError('published tree')
    upstream_name=subprocess.check_output([*git,'rev-parse','--abbrev-ref','--symbolic-full-name','@{upstream}'],cwd=ROOT,text=True).strip()
    if upstream_name!='origin/successor/core-v2-v12-runner-binding-remediation':raise ValueError('published upstream')
    upstream=subprocess.check_output([*git,'rev-parse','@{upstream}'],cwd=ROOT,text=True).strip()
    if subprocess.run([*git,'merge-base','--is-ancestor',COMMIT,upstream],cwd=ROOT).returncode:raise ValueError('published dataset ancestry')
    names=tuple(subprocess.check_output([*git,'diff-tree','--no-commit-id','--name-only','-r',COMMIT],cwd=ROOT,text=True).splitlines())
    if names!=FILES:raise ValueError('published scope')
    for name in FILES:
        if subprocess.check_output([*git,'show',f'{COMMIT}:{name}'],cwd=ROOT)!=(ROOT/name).read_bytes():raise ValueError('published blob drift')
    for name in ZERO_STEP_FILES:
        if subprocess.check_output([*git,'show',f'{upstream}:{name}'],cwd=ROOT)!=(ROOT/name).read_bytes():raise ValueError('published zero-step blob drift')
    m=json.loads((ART/'editor-core-factual-setup-corrective-v1-manifest.json').read_text(encoding='utf-8'));c=json.loads((ART/'editor-core-factual-setup-corrective-v1-config.json').read_text(encoding='utf-8'))
    if m['manifest_identity']!=MANIFEST or c['config_identity']!=CONFIG or c['parent_adapter_sha256']!=PARENT_ADAPTER or c['training_authorized'] is not False:raise ValueError('dataset binding')
    b=json.loads((ART/'editor-core-factual-setup-corrective-v1-zero-step-boundary.json').read_text(encoding='utf-8'));ident=b.pop('boundary_identity')
    if ident!=BOUNDARY or ident!=sha(canonical(b)):raise ValueError('boundary identity')
    return m,c
def validate_parent(checkpoint):
    if checkpoint.is_symlink() or not checkpoint.is_dir():raise ValueError('parent checkpoint root')
    if flat_manifest(checkpoint/'adapter')!=PARENT_ADAPTER:raise ValueError('parent adapter identity')
    r=json.loads((checkpoint/'checkpoint.json').read_text(encoding='utf-8'));ident=r.pop('checkpoint_identity',None)
    if ident!=PARENT_CHECKPOINT or ident!=sha(canonical(r)) or r.get('optimizer_steps')!=9:raise ValueError('parent checkpoint identity')
def output_snapshot(output):
    if not output.is_absolute() or str(output).startswith('/mnt/') or output.is_symlink() or not output.is_dir():raise ValueError('output root')
    if subprocess.check_output(['findmnt','-n','-o','FSTYPE','--target',str(output)],text=True).strip()!='ext4':raise ValueError('output ext4')
    if list(output.iterdir()):raise ValueError('output not empty')
    return output.stat().st_dev,output.stat().st_ino
def zero_step(checkpoint,output):
    before=output_snapshot(output);validate_public();validate_parent(checkpoint);after=output_snapshot(output)
    if before!=after:raise ValueError('output identity changed')
    core={'schema':'editor-factual-setup-corrective-zero-step-receipt','schema_version':1,'status':'PASS_ZERO_STEP_ZERO_TRAINING','published_commit':COMMIT,'published_tree':TREE,'manifest_identity':MANIFEST,'config_identity':CONFIG,'boundary_identity':BOUNDARY,'parent':'R2_STEP_9','parent_adapter_identity':PARENT_ADAPTER,'parent_checkpoint_identity':PARENT_CHECKPOINT,'output_entries_before':0,'output_entries_after':0,'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'promotion':False,'release':False}
    return {**core,'receipt_identity':sha(canonical(core)),'output_runtime_observation':{'device':before[0],'inode':before[1]}}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parent-checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(zero_step(a.parent_checkpoint,a.output),sort_keys=True))
