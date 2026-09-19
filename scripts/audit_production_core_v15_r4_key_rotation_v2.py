"""Fresh adversarial audit for the signed R4 key-rotation successor."""
import json,subprocess
import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_r4_key_rotation_v2 as issuer
def audit():
 root=issuer.OUTPUT
 if root.is_symlink() or {p.name for p in root.iterdir()}!=set(issuer.ARTIFACTS):raise ValueError('artifact set mismatch')
 sig_a=(root/'pop-a.sig').read_bytes();sig_b=(root/'pop-b.sig').read_bytes();registry,responses,authority,boundary=issuer.build(sig_a,sig_b);raws={n:issuer.canonical(v) for n,v in [('registry',registry),('authority',authority),('boundary',boundary)]};binding=issuer.canonical(issuer.binding_for(registry,authority,boundary,raws))
 expected={'registry.json':raws['registry'],'authority.json':raws['authority'],'boundary.json':raws['boundary'],'binding.json':binding,'pop-a.json':issuer.canonical(responses['ADJUDICATOR_A']),'pop-b.json':issuer.canonical(responses['ADJUDICATOR_B']),'builder-source.py':(issuer.ROOT/'scripts/materialize_production_core_v15_r4_key_rotation_v2.py').read_bytes()}
 for name,raw in expected.items():
  if (root/name).read_bytes()!=raw:raise ValueError(f'artifact reproduction mismatch: {name}')
 subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(signing.PUBLIC_KEY),'-rawin','-in',str(root/'binding.json'),'-sigfile',str(root/'binding.sig')],check=True,capture_output=True)
 if registry['supersedes_registry_identity']!=issuer.OLD_REGISTRY or authority['successor_registry_identity']!=registry['registry_identity'] or boundary['rotation_authority_identity']!=authority['rotation_authority_identity'] or boundary['real_receipts_created'] or boundary['adjudication_performed'] or boundary['semantic_verdict'] is not None or boundary['promotion']:raise ValueError('successor closure mismatch')
 return {'verdict':'PASS + 0 BLOCKERS','registry_identity':registry['registry_identity'],'rotation_authority_identity':authority['rotation_authority_identity'],'boundary_identity':boundary['boundary_identity'],'binding_identity':issuer.digest(binding),'signature_identity':issuer.digest((root/'binding.sig').read_bytes()),'pop_a':'PASS','pop_b':'PASS','ed25519':'PASS','source_closure':'PASS','supersession_closure':'PASS','bridge_closure':'PASS','receipts_created':0,'adjudication':False,'semantic_verdict':None,'promotion':False}
if __name__=='__main__':print(json.dumps(audit(),sort_keys=True))
