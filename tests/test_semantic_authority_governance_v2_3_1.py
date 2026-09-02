import hashlib, itertools, json
from pathlib import Path
import pytest
import pastila_scout.semantic_authority_governance_v2_3_1 as g

REG="CROSSREF_ANNUAL_PUBLIC_DATA_FILE"; VER="1"*64
def row(i,day,available=True):
 return {"registry":REG,"release_id":i,"publication_date":day,"official_release_record_identity":hashlib.sha256((i+'r').encode()).hexdigest(),"completeness_evidence_identity":hashlib.sha256((i+'c').encode()).hexdigest(),"archive_commitment_identity":hashlib.sha256((i+'a').encode()).hexdigest(),"immutable_locator_set_identity":hashlib.sha256((i+'l').encode()).hexdigest(),"archive_available":available}
def evidence(rows,**changes):
 value={"schema":g.HISTORY_SCHEMA,"governance_identity":g.GOVERNANCE_IDENTITY,"registry":REG,"cutoff_utc":g.CUTOFF_UTC,"cutoff_date_exclusive":"2026-09-02","coverage_claim":g.COVERAGE,"authority_sources":["PUBLISHER_RELEASE_INDEX","PUBLISHER_ARCHIVE_LISTING"],"release_count":len(rows),"release_set_sha256":g.release_set_sha256(rows),"capture_identity":"2"*64,"attestation_identity":"3"*64,"verifier_identity":VER};value.update(changes);return value
def select(rows,e=None,verify=lambda *_:True):return g.select_verified_predecessor_release(rows,registry=REG,history_evidence=e or evidence(rows),verifier_identity=VER,verify_external_attestation=verify)
def test_frozen_record():g.validate_governance(json.loads(Path('docs/artifacts/semantic-contract-v2-objective-authority-selection-governance-v2-3-1.json').read_text(encoding='utf-8')))
def test_permutation_older_and_postcutoff_invariance():
 rows=[row('old','2025-01-01'),row('winner','2026-03-17'),row('future','2027-01-01')]
 assert {select(list(p))['release_id'] for p in itertools.permutations(rows)}=={'winner'}
 assert select(rows+[row('older','2024-01-01'),row('future2','2028-01-01')])['release_id']=='winner'
def test_cutoff_is_not_caller_controlled_and_official_date_precision_is_exact():
 assert 'cutoff' not in g.select_verified_predecessor_release.__annotations__
 with pytest.raises(ValueError):select([row('x','2026-03-17T00:00:00Z')])
 for key,value in [('cutoff_utc','2026-03-18T00:00:00Z'),('cutoff_date_exclusive','2026-03-18'),('governance_identity','0'*64),('schema','OLD')]:
  rows=[row('x','2026-03-17')]
  with pytest.raises(ValueError):select(rows,evidence(rows,**{key:value}))
def test_asserted_external_verification_is_not_a_field_and_attestation_must_verify():
 rows=[row('x','2026-03-17')]
 bad=evidence(rows);bad['external_verification']=True
 with pytest.raises(ValueError):select(rows,bad)
 with pytest.raises(ValueError,match='attestation'):select(rows,verify=lambda *_:False)
def test_omission_insertion_count_root_and_replay_fail_closed():
 rows=[row('old','2025-01-01'),row('winner','2026-03-17')];proof=evidence(rows)
 with pytest.raises(ValueError,match='root'):select(rows[:-1],proof)
 for key,value in [('release_count',1),('release_set_sha256','0'*64),('registry','OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT'),('verifier_identity','4'*64)]:
  with pytest.raises(ValueError):select(rows,evidence(rows,**{key:value}))
def test_alias_duplicate_tie_and_unavailable_winner_fail_without_fallback():
 a=row('a','2026-03-17');b=row('b','2026-03-17')
 with pytest.raises(ValueError,match='ambiguous'):select([a,b])
 b=row('b','2026-02-01');b['archive_commitment_identity']=a['archive_commitment_identity']
 with pytest.raises(ValueError,match='alias'):select([a,b])
 with pytest.raises(ValueError,match='fallback'):select([row('old','2025-01-01'),row('winner','2026-03-17',False)])
def test_unknown_missing_mixed_registry_and_malformed_identities_fail():
 x=row('x','2026-03-17');x['semantic_hint']='convenient'
 with pytest.raises(ValueError):select([x])
 x=row('x','2026-03-17');x['registry']='OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT'
 with pytest.raises(ValueError):select([x])
 x=row('x','2026-03-17');x['official_release_record_identity']='bad'
 with pytest.raises(ValueError):select([x])
