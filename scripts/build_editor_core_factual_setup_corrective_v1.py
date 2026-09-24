"""Build the deterministic R2-centered EDITOR factual-setup corrective pack v1."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; PREFIX='editor-core-factual-setup-corrective-v1'
SYSTEM="""Aplică EDITOR FACTUAL SETUP CONTRACT v1. Scrie exact 2-3 propoziții factuale, suficiente și concise. Păstrează actorii, entitățile, atribuirea, cifrele, calificările, incertitudinea și statutul procedural. Nu inventa actori sau fapte și nu transforma acuzații, propuneri ori estimări în fapte stabilite. Fără VOICE, comedy, sarcasm, comentariu sau finisare de emisiune. Returnează exclusiv obiectul JSON structural cerut."""
CLASSES=('INVENTED_ACTOR','ENTITY_SUBSTITUTION','CATEGORICAL_ALLEGATION','LOST_QUALIFICATION','INCOMPLETE_NUMERIC_RECONCILIATION','INCOMPLETE_PROCEDURAL_STATUS')
def canon(x): return json.dumps(x,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def sha(x): return hashlib.sha256(x).hexdigest()
def response(cid,rid,text,spans):
    return {'schema':'pastila-core-v2-structured-qualification-response','schema_version':2,'case_id':cid,'request_identity':rid,'output_type':'FACTUAL','outcome':'ANSWER','text':text,'claim_bindings':[{'claim_index':i,'source_span_ids':spans} for i in (1,2)],'abstention_code':None}
def content(kind,n):
    entity=f"Entitatea {kind.title()} {n}"; city=('Sibiu','Iași','Craiova','Ploiești','Arad','Suceava')[n%6]; a=140+n*7; b=11+n
    if kind=='INVENTED_ACTOR':
        return 'Explicați decizia și implementarea fără a introduce actori.',[("consiliu",f"Consiliul local din {city} a aprobat programul {entity}."),("directie",f"Direcția tehnică a anunțat că implementarea începe joi."),("stadiu","Contractul nu a fost încă semnat.")],f"Consiliul local din {city} a aprobat programul {entity}, iar Direcția tehnică anunță că implementarea ar urma să înceapă joi. Contractul nu a fost încă semnat."
    if kind=='ENTITY_SUBSTITUTION':
        return 'Păstrați exact entitatea și locul menționate.',[("operator",f"Operatorul {entity} administrează rețeaua din {city}."),("incident",f"O avarie a afectat {a} de utilizatori ai rețelei {entity}."),("remediere",f"Operatorul {entity} estimează remedierea vineri.")],f"Operatorul {entity}, care administrează rețeaua din {city}, anunță că o avarie a afectat {a} de utilizatori. Același operator estimează remedierea vineri."
    if kind=='CATEGORICAL_ALLEGATION':
        return 'Redați acuzația și stadiul verificării fără a o confirma.',[("raport",f"Un raport preliminar susține că {entity} ar fi omis {b} declarații."),("raspuns",f"{entity} contestă acuzația."),("control","Autoritatea spune că verificarea continuă și faptele nu sunt stabilite.")],f"Un raport preliminar susține că {entity} ar fi omis {b} declarații, acuzație contestată de entitate. Autoritatea precizează că verificarea continuă și că faptele nu sunt stabilite."
    if kind=='LOST_QUALIFICATION':
        return 'Păstrați toate condițiile și incertitudinile relevante.',[("estimare",f"Institutul estimează o probabilitate de {b}% pentru depășirea pragului."),("conditie","Estimarea este valabilă numai dacă precipitațiile continuă până joi."),("revizie","Prognoza poate fi revizuită după noile măsurători.")],f"Institutul estimează la {b}% probabilitatea depășirii pragului, numai dacă precipitațiile continuă până joi. Prognoza poate fi revizuită după noile măsurători."
    if kind=='INCOMPLETE_NUMERIC_RECONCILIATION':
        return 'Reconciliați complet valorile inițiale și corectate.',[("initial",f"Inventarul provizoriu cuprindea {a} de dosare."),("duplicate",f"Verificarea a identificat {b} înregistrări duplicate."),("final",f"Totalul corectat este de {a-b} dosare distincte.")],f"Inventarul provizoriu cuprindea {a} de dosare, dintre care {b} erau înregistrări duplicate. După eliminarea lor, totalul corectat este de {a-b} dosare distincte."
    return 'Păstrați complet statutul procedural și efectul juridic actual.',[("propunere",f"Comisia a propus suspendarea autorizației {entity} pentru {b} zile."),("vot","Propunerea urmează să fie votată luni de plen."),("efect","Până la vot nu există o decizie finală, iar autorizația rămâne în vigoare.")],f"Comisia a propus suspendarea pentru {b} zile a autorizației {entity}, iar plenul urmează să voteze luni. Până la vot nu există o decizie finală, iar autorizația rămâne în vigoare."
def row(cid,kind,n,split,with_target):
    request,raw_spans,target=content(kind,n); spans=[{'span_id':f'{cid}:s{i}','source_id':s,'text':t} for i,(s,t) in enumerate(raw_spans,1)]
    core={'schema':'editor-factual-setup-request','schema_version':1,'case_id':cid,'output_type':'FACTUAL','sentence_budget':{'minimum':2,'maximum':3},'request':request,'authority_spans':spans}; core['request_identity']='sha256:'+sha(canon(core))
    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':'Aplică EDITOR FACTUAL SETUP CONTRACT v1.\nINPUT='+canon(core).decode()}]
    ans=response(cid,core['request_identity'],target,[s['span_id'] for s in spans]); base={'example_id':cid,'split':split,'failure_class':kind,'messages':messages}
    if with_target: base['messages']=messages+[{'role':'assistant','content':canon(ans).decode()}]
    return base,{'example_id':cid,'failure_class':kind,'request_identity':core['request_identity'],'assistant_target':canon(ans).decode()}
def build():
    train=[]; hold=[]; keys=[]
    for ci,kind in enumerate(CLASSES):
        for j in range(8): train.append(row(f'ec-fsc-v1-t-{ci+1}-{j+1:02d}',kind,100+ci*20+j,'CORRECTIVE_TARGETED',True)[0])
        for j in range(4): train.append(row(f'ec-fsc-v1-r-{ci+1}-{j+1:02d}',kind,300+ci*20+j,'REPLAY_PROTECTION',True)[0])
        for j in range(4):
            req,key=row(f'ec-fsc-v1-h-{ci+1}-{j+1:02d}',kind,700+ci*20+j,'INDEPENDENT_HOLDOUT',False); hold.append(req); keys.append(key)
    payloads={'training':train,'holdout-requests':hold,'holdout-answer-key':keys}; artifacts={}
    for name,rows in payloads.items():
        raw=b''.join(canon(x)+b'\n' for x in rows); (ART/f'{PREFIX}-{name}.jsonl').write_bytes(raw); artifacts[name]={'rows':len(rows),'sha256':sha(raw)}
    config={'schema':'editor-factual-setup-corrective-config','schema_version':1,'parent_adapter_sha256':'c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02','contract_identity':'67a5cd5813d422c513795dd88b561db3f74a55ee2a932d8bcb2d0d1035eb0b37','targeted_rows':48,'replay_rows':24,'holdout_rows':24,'training_authorized':False,'voice_or_chief_objective':False}
    config['config_identity']=sha(canon(config)); (ART/f'{PREFIX}-config.json').write_bytes(json.dumps(config,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n')
    core={'schema':'editor-factual-setup-corrective-manifest','schema_version':1,'artifacts':artifacts,'config_sha256':sha((ART/f'{PREFIX}-config.json').read_bytes()),'failure_classes':list(CLASSES),'development_holdout_disjoint':True,'historical_holdouts_read':False,'training_authorized':False}
    manifest={**core,'manifest_identity':sha(canon(core))}; (ART/f'{PREFIX}-manifest.json').write_bytes(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n'); return manifest
if __name__=='__main__': print(json.dumps(build(),ensure_ascii=False,sort_keys=True))
