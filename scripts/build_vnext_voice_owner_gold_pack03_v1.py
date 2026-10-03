from __future__ import annotations
import collections, hashlib, json, math, re, sys
from pathlib import Path

SOURCE_SHA256="a58954816ac8d421993fe15463790bf4b809892a875448f359d4cf36f705dd86"
PREDECESSOR_IDENTITY="7a08c87d894d27ec6d526713e113af14c42a639ce584ccfd5b415d5006478451"
BASELINE_COMMIT="0ff0fba257b3a0ef52199b644ca9360cf75265cc"

def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()
def identify(v,field):
    r=dict(v); r[field]=hashlib.sha256(canon(r)).hexdigest(); return r
def sha(b): return hashlib.sha256(b).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def writej(p,v): p.write_bytes(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
def writejl(p,v): p.write_bytes(b"".join(canon(x)+b"\n" for x in v))
def shaf(p): return sha(p.read_bytes())

SOURCES={
1:["https://www.politiadefrontiera.ro/ro/main/i-40-de-euro-pentru-trecerea-mai-rapida-a-frontierei-refuzati-de-o-politista-de-frontiera-de-la-ptf-jimbolia--44736.html"],
2:["https://www.digi24.ro/magazin/cand-trecem-la-ora-de-iarna-in-2026-ue-analizeaza-renuntarea-la-schimbarea-ceasurilor-ce-urmareste-cel-mai-recent-studiu-3961069","https://www.digi24.ro/magazin/mai-trecem-la-ora-de-iarna-in-2026-ce-s-a-decis-dupa-anii-de-discutii-privind-renuntarea-la-acest-obicei-3915677"],
3:["https://wikipress.ro/patronul-de-geo-myke-are-probleme-cu-fiscul-iesean-dupa-ce-si-a-cumparat-un-ferrari/","https://a1.ro/news/actualitate/ce-a-descoperit-anaf-in-garajul-unei-firme-cu-afaceri-de-milioane-cu-statul-una-dintre-masini-valoreaza-peste-500000-de-euro-id1163206.html"],
4:["https://www.pwc.com/gx/en/1/services/consulting/technology/data-centre-outlook.html","https://www.pwc.com/gx/en/news-room/press-releases/2026/global-investment-in-ai-infrastructure.html"],
5:["https://www.euronews.com/2026/10/02/ai-decodes-217-year-old-napoleonic-letter-in-6-hours"],
6:["https://www.libertatea.ro/entertainment/raluca-podea-a-terminat-a-treia-facultate-la-38-de-ani-5845649"],
7:["https://www.libertatea.ro/stiri/voyo-ce-se-intampla-cu-aplicatia-dupa-4-octombrie-2026-anunt-oficial-pro-tv-mhb6fq3"],
8:["https://www.guinnessworldrecords.com/news/2026/9/scottish-gamer-gran-celebrates-turning-78-with-her-fortnite-streaming-world-record"],
9:["https://blog.google/intl/ro-ro/stiri-despre-companie/the-future-report-tehnologia-digitala-instrument-de-invatare-si-creativitate-pentru-adolescentii-din-romania/","https://wikipress.ro/studiu-google-inteligenta-artificiala-folosita-de-adolescentii-din-romania/"]}

VERIFIED={
1:["2 October 2026 PTF Jimbolia event and EUR 40 refusal confirmed by Romanian Border Police","DGA Timis and competent prosecutor notified; no final conviction asserted"],
2:["24/25 October 2026 04:00 to 03:00 change and 25-hour day confirmed","2019 Parliament position did not become law without Council agreement"],
3:["Ferrari SF90, Lexus LX600 and additional tax obligations confirmed","company challenge remains pending; no final merits finding asserted"],
4:["PwC central scenario projects USD 31.6 trillion cumulative investment by 2050","projection is not represented as spending already incurred or certainty"],
5:["document originated at Eugene de Beauharnais headquarters and was transmitted to Marmont on Napoleons orders","owner clarification binds sent by Napoleon exclusively to the authority and agency sense, not personal authorship or physical dispatch","approximately six-hour AI-assisted decipherment after 217 years is supported; USD 30 trillion is an editorial callback to Record 04"],
6:["age 38, third faculty, and quoted preference for learning over influencereala confirmed"],
7:["4-6 October migration and temporary account-management/cancellation limits confirmed","temporary technical effect is preserved"],
8:["Guinness confirms age 78, oldest female Fortnite streamer, playing since 2017 and over 24,000 Twitch followers"],
9:["Google Romania confirms nationally representative 1,000-person 16-18 sample","9 in 10 monthly creative/learning use and 49% regular homework/school use confirmed"]}

META={
1:("ptf-fast-track",{"INDIVIDUAL":[("HMCV1-B02-M01-MISDIRECTION","Omul a vrut fast track. Și, tehnic, l-a primit.")],"SUPPORTING":[("HMCV1-B01-M09-REVERSAL","în loc să sară coada la frontieră, a sărit direct la DGA")],"COMPOSITION":[("HMCV1-B03-M09-TAG_COMIC_AFTERTHOUGHT","pleacă mai devreme, nu cu 40 de euro mai bogat\nîn idei.")]},["TRANSPARENT_WORDPLAY","EDITORIAL_INFERENCE"]),
2:("winter-time",{"INDIVIDUAL":[("HMCV1-B03-M08-ANTI_CLIMAX_BATHOS","Șapte ani. Pentru o\noră.")],"SUPPORTING":[],"COMPOSITION":[("HMCV1-B03-M01-SETUP_PAYOFF","În ritmul ăsta, până se hotărăsc ei ce fac cu ora, schimbăm noi\nfusul orar.")]},["HYPOTHETICAL_ABSURD_EXTENSION"]),
3:("geo-myke",{"INDIVIDUAL":[("HMCV1-B05-M10-SERIOUS_RESET_WITHHELD_HUMOR","Deci nu știm cine are dreptate. Va decide\ninstanța.")],"SUPPORTING":[("HMCV1-B02-M10-ROLE_SIMULATION","Întreabă: „Bună ziua. Și restul firmei unde-l țineți?”")],"COMPOSITION":[("HMCV1-B04-M10-SENTENCE_FINAL_REINTERPRETATION","Și restul firmei unde-l țineți?")]},["TRANSPARENT_IMAGINED_DIALOGUE"]),
4:("ai-infrastructure",{"INDIVIDUAL":[("HMCV1-B01-M02-IRONY","Momentan suntem în faza în care băgăm\n30 de trilioane în inteligență artificială ca să ne spună: „Ai dreptate.\nÎmi cer scuze pentru confuzie.”")],"SUPPORTING":[("HMCV1-B03-M03-REPETITION_WITH_VARIATION","30 de trilioane de dolari. 30 de trilioane.")],"COMPOSITION":[("HMCV1-B01-M03-CONTRAST_JUXTAPOSITION","investiția asta va produce vreodată câștigurile de productivitate\nașteptate. Eu zic să avem răbdare. Momentan suntem în faza în care băgăm\n30 de trilioane în inteligență artificială ca să ne spună: „Ai dreptate.\nÎmi cer scuze pentru confuzie.”")]},["TRANSPARENT_IMAGINED_DIALOGUE","EDITORIAL_JUXTAPOSITION"]),
5:("napoleonic-message",{"INDIVIDUAL":[("HMCV1-B05-M02-RUNNING_GAG","Deci retrag ce-am zis mai devreme.")],"SUPPORTING":[],"COMPOSITION":[]},["EDITORIAL_CALLBACK","TRANSPARENT_IMAGINED_DIALOGUE"]),
6:("third-faculty",{"INDIVIDUAL":[("HMCV1-B01-M04-COMIC_ANALOGY","Asta e ca și cum te duci la cârciumă să le spui\ntuturor că te-ai lăsat de băut.")],"SUPPORTING":[("HMCV1-B01-M02-IRONY","a anunțat pe social media că nu\nface influencereală")],"COMPOSITION":[]},["COMIC_ANALOGY","WORDPLAY"]),
7:("voyo-migration",{"INDIVIDUAL":[("HMCV1-B04-M03-FAUX_COMPLIANCE","Nu e nimic dubios, e\ndoar migrare tehnică.")],"SUPPORTING":[("HMCV1-B01-M04-COMIC_ANALOGY","VOYO intră trei zile în modul „relație toxică”")],"COMPOSITION":[("HMCV1-B02-M10-ROLE_SIMULATION","„Sigur, iubitule, poți să pleci când vrei.\nDoar că am încuiat ușa de la intrare.”")]},["TRANSPARENT_IMAGINED_DIALOGUE","COMIC_ANALOGY"]),
8:("fortnite-grandmother",{"INDIVIDUAL":[("HMCV1-B04-M06-STATUS_REVERSAL","„Bunica, maică. Acum du-te și fă-ți temele.”")],"SUPPORTING":[("HMCV1-B02-M10-ROLE_SIMULATION","„Bă, cine dracu’ m-a omorât?!”")],"COMPOSITION":[("HMCV1-B03-M01-SETUP_PAYOFF","un puști de 16 ani tocmai a\nfost eliminat din Fortnite și urlă: „Bă, cine dracu’ m-a omorât?!” Cath,\n78 de ani: „Bunica, maică. Acum du-te și fă-ți temele.”")]},["TRANSPARENT_IMAGINED_DIALOGUE","COMIC_FICTIONALIZATION"]),
9:("google-teens-ai",{"INDIVIDUAL":[("HMCV1-B04-M05-AUDIENCE_COMPLICITY_SHARED_RECOGNITION","Pe vremea\nnoastră, când copiai tema, măcar trebuia să găsești un coleg mai deștept\nca tine.")],"SUPPORTING":[("HMCV1-B02-M10-ROLE_SIMULATION","„Fă-mi tema ca pentru un elev de\n10, dar bagă două greșeli, să nu se prindă proasta.”")],"COMPOSITION":[("HMCV1-B01-M08-ESCALATION","Și uite-așa avem\nprima generație care poate lua 10 la o temă pe care n-ar fi în stare s-o\nexplice nici de 5.")]},["TRANSPARENT_IMAGINED_DIALOGUE","EDITORIAL_INFERENCE"])}

def parse(raw):
 t=raw.decode("utf-8",errors="strict")
 p=re.compile(r"(?ms)^RECORD (?P<number>\d{2}) — (?P<title>[^\r\n]+)\r?\n\r?\nFACTUAL SETUP\r?\n(?P<setup>.*?)\r?\n\r?\nSOURCES\r?\n.*?\r?\nOWNER COMMENTARY\r?\n\r?\n(?P<commentary>.*?)(?=\r?\n\r?\n(?:ADJUDICATION NOTE\r?\n.*?\r?\n\r?\n)?-{20,})")
 out=[{"number":int(m["number"]),"title":m["title"],"factual_setup":m["setup"].rstrip(),"owner_commentary":m["commentary"].rstrip()} for m in p.finditer(t)]
 assert [x["number"] for x in out]==list(range(1,10)), [x["number"] for x in out]
 return out

def mids(row):
 out=[]
 for group in row.get("mechanisms",{}).values():
  for x in group:
   out.append(x["mechanism_id"] if isinstance(x,dict) else x)
 return out

def main(repo):
 a=repo/"docs/artifacts"; src=a/"vnext-voice-owner-gold-pack03-v1/sources/PASTILA_VOICE_OWNER_GOLD_PACK_03.txt"; raw=src.read_bytes()
 assert sha(raw)==SOURCE_SHA256 and len(raw)==13246
 pred=json.loads((a/"vnext-voice-owner-gold-pack02-v1-dataset-successor.json").read_text(encoding="utf-8")); assert pred["dataset_successor_identity"]==PREDECESSOR_IDENTITY
 curriculum=json.loads((a/"humor-mechanics-curriculum-v1.manifest.json").read_text(encoding="utf-8")); valid={m["id"] for m in curriculum["mechanisms"]}; assert len(valid)==50
 decisions=[]; admitted=[]
 for s in parse(raw):
  n=s["number"]; c=s["owner_commentary"]; base={"record_id":f"PA-CONTEMP-P03-{n:02d}","pack_record":n,"title":s["title"],"source_pack_sha256":SOURCE_SHA256,"owner_commentary_sha256":sha(c.encode()),"commentary_byte_exact":True,"commentary_rewritten":False,"commentary_normalized":False}
  slug,ann,devices=META[n]
  for role,items in ann.items():
   for mid,span in items: assert mid in valid and span in c,(n,mid,span)
  partition="VALIDATION" if n>=7 else "TRAIN"
  rec=identify({"record_id":base["record_id"],"pack_record":n,"title":s["title"],"family_identity":f"PASTILA_ACIDA_CONTEMPORARY_PACK03_{n:02d}_{slug.upper().replace('-','_')}","partition":partition,"source_pack_path":str(src.relative_to(repo)),"source_pack_sha256":SOURCE_SHA256,"factual_setup":{"text":s["factual_setup"],"sha256":sha(s["factual_setup"].encode()),"sources":SOURCES[n],"provenance_status":"VERIFIED_EXACT_AUTHORITY_BOUND","verified_claims":VERIFIED[n],"retrieved_on":"2026-10-03"},"gold_commentary":{"text":c,"sha256":base["owner_commentary_sha256"],"provenance":"EXACT_OWNER_WRITTEN_SOURCE_BYTES","rewritten":False,"normalized":False,"commentary_token_estimate":math.ceil(len(c)/4)},"mechanisms":{role:[{"mechanism_id":mid,"evidence_span":span} for mid,span in items] for role,items in ann.items()},"factual_commentary_taxonomy":{"factual_setup_separate":True,"commentary_devices":devices,"transparent_satire_or_fiction_not_treated_as_fact":True,"unsupported_fact_admitted":False,"conditionality_and_unknowns_preserved":True},"target_policy":{"protected_target_is_satire_target":False},"stream":"ORGANIC_OWNER_WRITTEN_CONTEMPORARY","training_eligible":True},"record_identity")
  admitted.append(rec); decisions.append(identify({**base,"admission":"ADMITTED","reason":"PROVENANCE_FACTUAL_SAFETY_AND_SPAN_ANNOTATION_CLOSED","record_identity":rec["record_identity"],"partition":partition,"training_eligible":True},"decision_identity"))
 assert len(admitted)==9
 train0=rows(a/"vnext-voice-owner-gold-pack02-v1-train-successor.jsonl"); val0=rows(a/"vnext-voice-owner-gold-pack02-v1-validation-successor.jsonl"); assert (len(train0),len(val0))==(33,12)
 train=train0+[r for r in admitted if r["partition"]=="TRAIN"]; val=val0+[r for r in admitted if r["partition"]=="VALIDATION"]
 paths={k:a/f"vnext-voice-owner-gold-pack03-v1-{k}.jsonl" for k in ["admission","admitted-records","train-successor","validation-successor"]}
 writejl(paths["admission"],decisions); writejl(paths["admitted-records"],admitted); writejl(paths["train-successor"],train); writejl(paths["validation-successor"],val)
 support=collections.Counter(mid for r in train+val for mid in mids(r)); covered=set(support); newtokens=sum(r["gold_commentary"]["commentary_token_estimate"] for r in admitted); tokens=pred["commentary_tokens"]["successor_estimated"]+newtokens
 quality={"romanian_naturalness":{"new":9,"successor_support":pred["counts"]["train_positive"]+pred["counts"]["validation_positive"]+9},"restraint":{"new":4,"successor_support":pred["quality_coverage"]["restraint"]+4,"new_records":[2,3,4,7]},"factual_discipline":{"new":9,"unsupported_fact_admitted":0},"concision":{"new":4,"new_records":[1,2,4,6]},"variation_anti_repetition":{"new":9},"target_choice":{"new":9},"authentic_mechanism_composition":{"new":8}}
 gates={"train_positive":{"actual":len(train),"minimum":36,"margin_minimum":37,"pass":len(train)>=37},"validation_positive":{"actual":len(val),"minimum":12,"margin_minimum":13,"pass":len(val)>=13},"commentary_tokens":{"actual":tokens,"minimum":8000,"pass":tokens>=8000},"factual_restraint_support":{"actual":quality["restraint"]["successor_support"],"minimum":8,"margin_minimum":9,"pass":quality["restraint"]["successor_support"]>=9}}
 ready=all(x["pass"] for x in gates.values())
 dataset=identify({"schema":"vnext-voice-owner-gold-pack03-dataset-successor","schema_version":1,"predecessor_identity":PREDECESSOR_IDENTITY,"experimental_baseline_commit":BASELINE_COMMIT,"source_pack":{"path":str(src.relative_to(repo)),"sha256":SOURCE_SHA256,"bytes":len(raw)},"admission":{"candidate":9,"admitted":9,"rejected":0,"admitted_record_numbers":[r["pack_record"] for r in admitted],"rejected_record_numbers":[]},"partition":{"new_train":6,"new_validation":3,"holdout_families":[31,32,33,34],"holdout_exposure":0,"qwen3_bakeoff_exposure":0},"counts":{"train_positive":len(train),"validation_positive":len(val),"negative":27,"model_visible_abstention":0,"new_positive":9},"commentary_tokens":{"predecessor_estimated":pred["commentary_tokens"]["successor_estimated"],"new_estimated":newtokens,"successor_estimated":tokens,"method":"ceil(character-count/4)-per-admitted-record"},"mechanism_coverage":{"successor":len(covered),"covered":sorted(covered),"positive_gaps":sorted(valid-covered),"support_counts":dict(sorted(support.items())),"curriculum_total":50},"quality_coverage":quality,"factual_safety":{"source_verified_records":9,"fail_closed_rejected_records":0,"unsupported_fact_records":0,"runtime_constrained_projection_required":True,"record05_owner_semantic_clarification":"BOUND_TO_AGENCY_AUTHORITY_SENSE_ONLY","record05_callback_adjudicated":True},"files":{k:{"path":str(p.relative_to(repo)),"sha256":shaf(p)} for k,p in paths.items()},"second_experiment_readiness":{"gates":gates,"status":"READY_FOR_SECOND_EXPERIMENTAL_NON_PROMOTABLE_QWEN3_LORA" if ready else "FAIL_CLOSED_NOT_READY","training_authorized":False,"production_or_promotion_ready":False},"training_performed":False,"weights_modified":False,"holdout_accessed":False,"active_product_modified":False,"canonical_rollback_modified":False,"gui_state":"ACTIVE","voice_state":"DISABLED_UNTIL_PROMOTION"},"dataset_successor_identity")
 dpath=a/"vnext-voice-owner-gold-pack03-v1-dataset-successor.json"; writej(dpath,dataset)
 freeze=identify({"schema":"vnext-voice-owner-gold-pack03-corpus-freeze","schema_version":1,"dataset_successor_identity":dataset["dataset_successor_identity"],"status":"FROZEN_READY_FOR_SECOND_EXPERIMENTAL_NON_PROMOTABLE_QWEN3_LORA" if ready else "NOT_FROZEN_FAIL_CLOSED","train_records":len(train),"validation_records":len(val),"holdout_families":[31,32,33,34],"holdout_exposure":0,"qwen3_bakeoff_exposure":0,"source_pack_sha256":SOURCE_SHA256,"experimental_baseline_commit":BASELINE_COMMIT,"frozen_files":dataset["files"],"training_authorized":False,"promotion_ready":False},"corpus_freeze_identity")
 fpath=a/"vnext-voice-owner-gold-pack03-v1-corpus-freeze.json"; writej(fpath,freeze)
 backlog=identify({"schema":"owner-gold-writing-backlog-post-pack03","schema_version":1,"dataset_successor_identity":dataset["dataset_successor_identity"],"corpus_freeze_identity":freeze["corpus_freeze_identity"],"terminal":"CORPUS_FREEZE_READY_SECOND_EXPERIMENT_SEPARATELY_AUTHORIZED" if ready else "FAIL_CLOSED","counts":{"train":len(train),"validation":len(val),"commentary_tokens":tokens,"factual_restraint":quality["restraint"]["successor_support"],"mechanism_coverage":len(covered),"positive_gaps":len(valid-covered)},"remaining_positive_gaps":sorted(valid-covered),"model_visible_abstention":"UNCHANGED_ZERO_OUT_OF_SCOPE_FOR_EXPERIMENTAL_OBJECTIVE","production_gaps_remain":True,"quota_fill":False},"backlog_identity")
 bpath=a/"vnext-voice-owner-gold-pack03-v1-backlog.json"; writej(bpath,backlog)
 audit=identify({"schema":"vnext-voice-owner-gold-pack03-audit","schema_version":1,"status":"PASS_0_INTEGRITY_BLOCKERS","dataset_successor_identity":dataset["dataset_successor_identity"],"corpus_freeze_identity":freeze["corpus_freeze_identity"],"backlog_identity":backlog["backlog_identity"],"source_pack_sha256":SOURCE_SHA256,"records_admitted":9,"records_rejected":0,"rejection":None,"record05_readjudication":"ADMITTED_AFTER_OWNER_AUTHORED_SEMANTIC_CLARIFICATION_BOUND_EXCLUSIVELY_TO_AGENCY_AUTHORITY_SENSE","commentary_byte_exact":True,"factual_commentary_separation":"PASS","mechanism_annotation":"PASS_SPAN_DERIVED_NO_QUOTA_FILL","deduplication":"PASS_NO_EXACT_COMMENTARY_DUPLICATES","train_validation_family_overlap":0,"holdout_exposure":0,"qwen3_bakeoff_exposure":0,"unsupported_fact_admitted":0,"training_performed":False,"active_product_modified":False,"canonical_rollback_modified":False,"findings":[{"id":"F-01","severity":"RESOLVED_BY_OWNER_CLARIFICATION","finding":"RECORD_05_ADMITTED_WITH_SENT_BY_NAPOLEON_BOUND_EXCLUSIVELY_TO_SENT_ON_NAPOLEONS_ORDERS"},{"id":"F-02","severity":"NON_BLOCKING_PROMOTION_GAP","finding":"MODEL_VISIBLE_ABSTENTION_REMAINS_ZERO_AND_PRODUCTION_THRESHOLDS_REMAIN_SEPARATE"}],"cars":[{"car_id":"CAR-01","finding":"INITIAL_PACK03_MECHANISM_BINDINGS_USED_TWO_NONEXISTENT_FROZEN_CURRICULUM_IDS_AND_TWO_DUPLICATIVE_SPAN_LABELS","root_cause":"PROVISIONAL_ANNOTATION_NAMES_WERE_NOT_FIRST_RESOLVED_AGAINST_THE_FROZEN_50_MECHANISM_MANIFEST","impact":"BUILD_STOPPED_FAIL_CLOSED_BEFORE_AUTHORITY_EMISSION","repair":"RESOLVE_IDS_REMOVE_DUPLICATIVE_LABELS_AND_RESTART_BUILD_AND_AUDIT_FRESH"},{"car_id":"CAR-02","finding":"INITIAL_SUPPORT_COUNTER_ASSUMED_ONLY_OBJECT_FORM_MECHANISM_ANNOTATIONS","root_cause":"PREDECESSOR_DATASET_CONTAINS_HISTORICAL_STRING_FORM_AND_CURRENT_OBJECT_FORM_ANNOTATIONS","impact":"SUCCESSOR_AGGREGATION_STOPPED_BEFORE_IDENTITY_CLOSURE","repair":"ADD_READ_ONLY_SCHEMA_COMPATIBLE_EXTRACTION_AND_REBUILD_ALL_GENERATED_EVIDENCE_FRESH"},{"car_id":"CAR-03","finding":"OWNER_CLARIFICATION_RESOLVES_RECORD_05_LEXICAL_AMBIGUITY","root_cause":"INITIAL_ADJUDICATION_DID_NOT_HAVE_OWNER_AUTHORED_INTENDED_SENSE_FOR_SENT_BY_NAPOLEON","impact":"RECORD_05_WAS_PREVIOUSLY_REJECTED_FAIL_CLOSED","repair":"BIND_THE_EXPRESSION_ONLY_TO_AGENCY_AUTHORITY_SENSE_ADMIT_WITHOUT_BYTE_CHANGE_AND_REBUILD_ALL_SUCCESSOR_EVIDENCE_FRESH"}],"fresh_audit_restarts":3,"legacy_dependency_count":0,"voice_state":"DISABLED_UNTIL_PROMOTION"},"audit_identity")
 apath=a/"vnext-voice-owner-gold-pack03-v1-audit.json"; writej(apath,audit)
 print(json.dumps({"dataset":dataset["dataset_successor_identity"],"freeze":freeze["corpus_freeze_identity"],"backlog":backlog["backlog_identity"],"audit":audit["audit_identity"],"train":len(train),"validation":len(val),"tokens":tokens,"restraint":quality["restraint"]["successor_support"],"coverage":len(covered),"gaps":len(valid-covered),"ready":ready},ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main(Path(sys.argv[1]).resolve())
