"""Adversarial audit of the signed R4 adjudication-execution boundary."""
import json, subprocess
import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_r4_adjudication_execution_boundary as issuer
def audit():
 root=issuer.OUTPUT
 if root.is_symlink() or {p.name for p in root.iterdir()}!=set(issuer.ARTIFACTS): raise ValueError('artifact set mismatch')
 p={n:root/n for n in issuer.ARTIFACTS}; raw=p['boundary.json'].read_bytes(); bound=p['binding.json'].read_bytes(); sig=p['binding.sig'].read_bytes(); a=json.loads(raw); core=dict(a); claimed=core.pop('boundary_identity')
 if claimed!=issuer.identity(core) or a!=issuer.build() or bound!=issuer.canonical(issuer.binding_for(a,raw)) or p['builder-source.py'].read_bytes()!=(issuer.ROOT/'scripts/materialize_production_core_v15_r4_adjudication_execution_boundary.py').read_bytes(): raise ValueError('boundary reproduction mismatch')
 subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(signing.PUBLIC_KEY),'-rawin','-in',str(p['binding.json']),'-sigfile',str(p['binding.sig'])],check=True,capture_output=True)
 if a['projection']!={'packet_count':1986,'excluded_structural_failures':414,'packet_inventory_root':a['projection']['packet_inventory_root'],'packet_projection_root':a['projection']['packet_projection_root']} or a['real_packets_materialized'] or a['real_receipts_created'] or a['adjudication_performed'] or a['semantic_verdict'] is not None or a['promotion']: raise ValueError('execution state mismatch')
 return {'verdict':'PASS + 0 BLOCKERS','boundary_identity':claimed,'binding_identity':issuer.digest(bound),'signature_identity':issuer.digest(sig),'ed25519':'PASS','source_closure':'PASS','projection_closure':'PASS','packets_created':0,'receipts_created':0,'semantic_verdict':None,'promotion':False}
if __name__=='__main__': print(json.dumps(audit(),sort_keys=True))
