#!/usr/bin/env python3
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, tempfile
from pathlib import Path

def module(path, name):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def replace_preserving_target_mode(source,target):
    mode=target.stat().st_mode & 0o777
    shutil.copyfile(source,target)
    os.chmod(target,mode)

def run(repo,active,rollback,historical,simulate):
    b=module(repo/'scripts/build_vnext_canonical_rollback_consolidation_v1.py','builder')
    with tempfile.TemporaryDirectory(prefix='vnext-rollback-boundary-',dir='/tmp') as td:
        td=Path(td); out=td/'out'; built=b.build(repo,active,rollback,historical,out)
        expected={
          'vnext-canonical-rollback-manifest-v2.json':'rollback_manifest_identity',
          'vnext-current-active-state-authority-v2.json':'active_state_authority_identity',
          'vnext-canonical-rollback-product-lock-successor-v1.json':'product_lock_identity'}
        for name,key in expected.items():
            value=json.loads((out/name).read_text()); claim=value.pop(key)
            if claim!=b.identity(value): raise RuntimeError('identity mismatch '+name)
        manifest=json.loads((out/'vnext-canonical-rollback-manifest-v2.json').read_text())
        authority=json.loads((out/'vnext-current-active-state-authority-v2.json').read_text())
        lock=json.loads((out/'vnext-canonical-rollback-product-lock-successor-v1.json').read_text())
        if manifest['rollback_root']!=str(rollback) or manifest['authority']['product_lock_identity']!=b.ROLLBACK_LOCK_ID: raise RuntimeError('canonical rollback not immediate predecessor')
        if authority['canonical_rollback']['manifest_identity']!=manifest['rollback_manifest_identity']: raise RuntimeError('authority rollback binding')
        if lock['supersedes_product_lock_identity']!=b.ACTIVE_LOCK_ID or lock['activation_attestation']['activation_candidate_product_lock_identity']!=b.ACTIVATION_CANDIDATE_ID: raise RuntimeError('predecessor/candidate separation')
        if b.sha(active/'product-lock.json')!=b.ACTIVE_LOCK_SHA or b.sha(rollback/'product-lock.json')!=b.ROLLBACK_LOCK_SHA or b.sha(historical/'product-lock.json')!=b.HISTORICAL_LOCK_SHA: raise RuntimeError('protected root drift')
        simulation='NOT_RUN'
        if simulate:
            upper=td/'upper';work=td/'work';merged=td/'merged'
            upper.mkdir();work.mkdir();merged.mkdir()
            subprocess.run(['mount','-t','overlay','overlay','-o',f'lowerdir={active},upperdir={upper},workdir={work}',str(merged)],check=True)
            try:
                replace_preserving_target_mode(repo/'scripts/vnext_materialized_active_preflight_v10.py',merged/'app/cli/preflight.py')
                replace_preserving_target_mode(repo/'scripts/audit_vnext_materialized_active_product_v12.py',merged/'app/cli/audit.py')
                replace_preserving_target_mode(out/'vnext-current-active-state-authority-v2.json',merged/'manifest/authorities/vnext-active-product-lock-successor-v1.json')
                replace_preserving_target_mode(out/'vnext-canonical-rollback-manifest-v2.json',merged/'manifest/rollback/vnext-canonical-rollback-manifest-v1.json')
                replace_preserving_target_mode(out/'vnext-canonical-rollback-product-lock-successor-v1.json',merged/'product-lock.json')
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
                py=merged/'platform/python-ml/bin/python'
                pre=subprocess.run([str(py),'-I','-B',str(merged/'app/cli/product.py'),'--root',str(merged),'--preflight-only'],env=env,text=True,capture_output=True,check=True)
                if json.loads(pre.stdout)['status']!='PASS_PREFLIGHT':raise RuntimeError('prospective preflight')
                aud=subprocess.run([str(py),'-I','-B',str(merged/'app/cli/audit.py'),'--root',str(merged),'--rollback-root',str(rollback),'--live'],env=env,text=True,capture_output=True,check=True)
                ar=json.loads(aud.stdout)
                if ar['status']!='PASS' or ar['e2e']!='EXPORTED' or ar['rollback_integrity']!='PASS':raise RuntimeError('prospective live audit')
                simulation='PASS_INSTALL_STARTUP_E2E_ROLLBACK_AUTHORITY'
            finally:
                subprocess.run(['umount',str(merged)],check=True)
            shutil.rmtree(upper); shutil.rmtree(work); upper.mkdir(); work.mkdir()
            subprocess.run(['mount','-t','overlay','overlay','-o',f'lowerdir={active},upperdir={upper},workdir={work}',str(merged)],check=True)
            try:
                restored_lock=json.loads((merged/'product-lock.json').read_text())
                if restored_lock['product_lock_identity']!=b.ACTIVE_LOCK_ID or b.sha(merged/'product-lock.json')!=b.ACTIVE_LOCK_SHA:raise RuntimeError('prospective rollback byte restoration')
                old_aud=subprocess.run([str(merged/'platform/python-ml/bin/python'),'-I','-B',str(repo/'scripts/audit_vnext_materialized_active_product_v11.py'),'--root',str(merged),'--rollback-root',str(historical),'--live'],env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),text=True,capture_output=True,check=True)
                old_result=json.loads(old_aud.stdout)
                if old_result['status']!='PASS' or old_result['e2e']!='EXPORTED':raise RuntimeError('prospective rollback recovery')
                simulation='PASS_INSTALL_STARTUP_E2E_AND_BYTE_EXACT_ROLLBACK_RESTORE'
            finally:
                subprocess.run(['umount',str(merged)],check=True)
        result={'schema':'vnext-canonical-rollback-consolidation-result-v1','status':'PASS','blockers':0,**built,'prospective_simulation':simulation,'active_root_modified':False,'rollback_roots_modified':False,'historical_retirement_executed':False,'legacy_dependency_count':0}
        result['result_identity']=b.identity(result)
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--active',type=Path,required=True);p.add_argument('--rollback',type=Path,required=True);p.add_argument('--historical',type=Path,required=True);p.add_argument('--simulate',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.repo,a.active,a.rollback,a.historical,a.simulate),sort_keys=True))
