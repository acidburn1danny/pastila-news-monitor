"""Adversarial audit for the signed R4 human-adjudicator client."""
import json,subprocess
import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_r4_adjudicator_client_boundary as issuer
def audit():
 root=issuer.OUTPUT
 if root.is_symlink() or {p.name for p in root.iterdir()}!=set(issuer.ARTIFACTS):raise ValueError('artifact set mismatch')
 p={name:root/name for name in issuer.ARTIFACTS};raw=p['boundary.json'].read_bytes();binding=p['binding.json'].read_bytes();signature=p['binding.sig'].read_bytes();value=json.loads(raw);core=dict(value);claimed=core.pop('boundary_identity')
 if claimed!=issuer.identity(core) or value!=issuer.build() or binding!=issuer.canonical(issuer.binding_for(value,raw)) or p['builder-source.py'].read_bytes()!=(issuer.ROOT/'scripts/materialize_production_core_v15_r4_adjudicator_client_boundary.py').read_bytes():raise ValueError('client boundary reproduction mismatch')
 subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(signing.PUBLIC_KEY),'-rawin','-in',str(p['binding.json']),'-sigfile',str(p['binding.sig'])],check=True,capture_output=True)
 if value['packet_count']!=1986 or value['excluded_structural_failures']!=414 or value['role_closure']!=1986 or value['real_keys_accessed'] or value['real_receipts_created'] or value['semantic_verdict'] is not None or value['promotion']:raise ValueError('client state mismatch')
 return {'verdict':'PASS + 0 BLOCKERS','boundary_identity':claimed,'binding_identity':issuer.digest(binding),'signature_identity':issuer.digest(signature),'ed25519':'PASS','source_closure':'PASS','keys_accessed':0,'receipts_created':0,'semantic_verdict':None,'promotion':False}
if __name__=='__main__':print(json.dumps(audit(),sort_keys=True))
