"""Build and audit the fixture-only VNext VOICE bake-off boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

PLAN_ID = "2ddc49ed46d0e891aef7b69b4874de5305c32346b8ec0962f296c50859faaa61"
CANDIDATE_LOCK = "3aca84d7470bc56c976bd5fd7101daf978a138ecb025ae1d17661a07c21b14ee"
R2_LOCK = "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"
SEEDS = [161803, 271828, 314159]
INVARIANTS = ["EDITOR_SETUP_BYTES_IMMUTABLE", "COMMENTARY_SEPARATE", "NO_NEW_FACTUAL_CLAIMS", "ABSTENTION_ALLOWED", "NO_SOURCEPACKET_AUTHORITY_FOR_VOICE"]
CANDIDATES = [
    {"candidate_id":"V0_R2_MINISTRAL_CONTROL","revision":f"BOUND_BY_VNEXT_R2_LOCK_{R2_LOCK}","tokenizer_sha256":"d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135","root":"components/r2-reference-v1"},
    {"candidate_id":"V1_QWEN3_8B_NON_THINKING","revision":"b968826d9c46dd6066d109eabc6255188de91218","tokenizer_sha256":"aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4","root":"components/voice-candidates-v1/qwen3-8b"},
    {"candidate_id":"V2_QWEN25_7B_INSTRUCT","revision":"a09a35458c702b33eeacc393d103063234e8bc28","tokenizer_sha256":"c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539","root":"components/voice-candidates-v1/qwen2.5-7b-instruct"},
]

SETUPS = [
"Primăria Brașov a anunțat luni că lucrările la pod încep pe 14 octombrie și vor dura aproximativ șase luni.",
"Compania Arin estimează că furnizarea apei va fi reluată la ora 18:00, dacă reparația decurge conform planului.",
"Procurorii susțin că trei firme ar fi falsificat documente; dosarul se află în faza de urmărire penală.",
"Inflația anuală a coborât la 5,1% în august, de la 5,4% în iulie, potrivit Institutului Național de Statistică.",
"Consiliul local a aprobat proiectul cu 17 voturi pentru, 5 împotrivă și 2 abțineri.",
"Ministerul a propus plafonarea tarifului la 0,80 lei pe kilometru; măsura nu a fost încă adoptată.",
"Spitalul Județean a primit 12 ventilatoare, în valoare totală de 2,4 milioane de lei, printr-un program european.",
"Poliția cercetează un accident produs marți în Cluj; două persoane au fost transportate la spital.",
"Operatorul feroviar a anulat patru trenuri după o avarie și estimează reluarea circulației miercuri dimineață.",
"Curtea de Apel a menținut măsura controlului judiciar; hotărârea poate fi contestată.",
"Asociația producătorilor estimează o scădere de 8% a recoltei, pe baza datelor preliminare.",
"Universitatea a deschis 320 de locuri la master, dintre care 140 sunt finanțate de la buget.",
"Autoritatea de reglementare a amendat compania cu 50.000 de lei pentru încălcarea obligațiilor de informare.",
"Guvernul a adoptat ordonanța vineri, iar prevederile intră în vigoare după publicarea în Monitorul Oficial.",
"Sindicatul afirmă că 600 de angajați ar putea fi afectați de restructurare; compania nu a anunțat concedieri.",
"Meteorologii au emis un cod portocaliu pentru șase județe, valabil de la ora 12:00 până la ora 22:00.",
"Banca a raportat un profit net de 1,2 miliarde de lei în primul semestru, cu 9% peste perioada similară.",
"Parlamentul a retrimis proiectul comisiei de specialitate, fără un vot final în plen.",
"Inspectorii au retras de la vânzare 3.911 produse după ce au constatat etichetarea incorectă.",
"Compania aeriană a mutat zborul de la ora 09:30 la 13:10 din cauza condițiilor meteo.",
"Primarul a declarat că noua parcare ar putea fi terminată în 2027, dacă finanțarea este aprobată.",
"Raportul preliminar indică 42 de clădiri avariate, însă evaluarea autorităților continuă.",
"Federația a suspendat clubul pentru două etape; decizia nu este definitivă.",
"Furnizorul a redus prețul de la 1,35 lei la 1,21 lei pe kilowatt-oră pentru contractele noi.",
]

def canonical(v: object) -> bytes:
    return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()

def identified(v: dict, field: str) -> dict:
    body = {k:x for k,x in v.items() if k != field}
    return {**body, field: hashlib.sha256(canonical(body)).hexdigest()}

def build(repo: Path) -> dict:
    art = repo / "docs/artifacts"; art.mkdir(parents=True, exist_ok=True)
    cases=[]
    for i,text in enumerate(SETUPS,1):
        body={"schema":"editor-vnext-voice-bakeoff-case","schema_version":1,"case_id":f"VOICE-V1-{i:02d}","editor_setup_packet_identity":hashlib.sha256(f"packet:{i}:{text}".encode()).hexdigest(),"factual_setup":text,"factual_setup_sha256":hashlib.sha256(text.encode()).hexdigest(),"bounded_voice_instruction":"Scrie separat un comentariu Pastila Acidă, fără a adăuga afirmații factuale.","optional_repetition_hints":[]}
        cases.append(identified(body,"case_identity"))
    case_bytes=b"".join(canonical(x)+b"\n" for x in cases)
    (art/"editor-vnext-voice-bakeoff-boundary-v1-cases.jsonl").write_bytes(case_bytes)
    runtime_slots=[]; answer=[]
    for case in cases:
      for seed in SEEDS:
        aliases=[]
        for rank,c in enumerate(CANDIDATES):
          alias=hashlib.sha256(f"{case['case_id']}:{seed}:{rank}".encode()).hexdigest()[:12]
          aliases.append((alias,c))
        aliases.sort(key=lambda x:x[0])
        for blind_index,(_,c) in enumerate(aliases):
          slot=identified({"schema":"editor-vnext-voice-bakeoff-slot","schema_version":1,"case_id":case["case_id"],"case_identity":case["case_identity"],"seed":seed,"blind_label":f"BLIND_{blind_index+1}","output_relative_path":f"outputs/{case['case_id']}/{seed}/BLIND_{blind_index+1}.json","decoding_identity":"VOICE_BAKEOFF_DETERMINISTIC_DECODING_V1","answer_key_excluded":True},"slot_identity")
          runtime_slots.append(slot); answer.append({"slot_identity":slot["slot_identity"],"candidate_id":c["candidate_id"]})
    (art/"editor-vnext-voice-bakeoff-boundary-v1-slots.jsonl").write_bytes(b"".join(canonical(x)+b"\n" for x in runtime_slots))
    (art/"editor-vnext-voice-bakeoff-boundary-v1-answer-key.json").write_bytes(json.dumps(identified({"schema":"editor-vnext-voice-bakeoff-answer-key","schema_version":1,"runtime_access":"FORBIDDEN","mappings":answer},"answer_key_identity"),ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
    protocol=identified({"schema":"editor-vnext-voice-bakeoff-execution-boundary","schema_version":1,"status":"PASS_FIXTURE_ONLY_STOP_BEFORE_MODEL_LOAD","bindings":{"plan_identity":PLAN_ID,"candidate_lock_identity":CANDIDATE_LOCK,"r2_lock_identity":R2_LOCK,"candidates":CANDIDATES},"matrix":{"cases":24,"candidates":3,"seeds":SEEDS,"slots":216},"decoding":{"identity":"VOICE_BAKEOFF_DETERMINISTIC_DECODING_V1","do_sample":False,"temperature":None,"top_p":None,"max_new_tokens":256,"structured_json":True,"qwen3_enable_thinking":False},"factual_invariants":INVARIANTS,"runtime":{"platform":{"torch":"2.13.0+cu130","transformers":"5.15.0","accelerate":"1.14.0","bitsandbytes":"0.50.1"},"quantization":{"backend":"bitsandbytes","bits":4,"quant_type":"nf4","compute_dtype":"bfloat16","double_quant":True,"execute":False},"answer_key_path_forbidden":True,"model_load_authorized":False},"terminal_rules":{"STOP":["IDENTITY_DRIFT","SETUP_MUTATION","UNSUPPORTED_FACTUAL_CLAIM","OOM","VRAM_ABOVE_14_5_GIB","LEGACY_DEPENDENCY"],"REVISE":["STRUCTURAL_FAILURE_ABOVE_2_PERCENT","ABSTENTION_ABOVE_20_PERCENT","LATENCY_ABOVE_30_SECONDS","NON_REPLICATED_QUALITY_ADVANTAGE"],"CONTINUE":["ZERO_FACTUAL_DRIFT","ZERO_SETUP_MUTATION","DEPENDENCY_GATES_PASS","SIGN_TEST_P_LT_0_05","AT_LEAST_15_WINS_AT_MOST_5_LOSSES","REPLICATED_TWO_SEEDS","NO_REPETITION_REGRESSION"]},"output_schema":{"required":["slot_identity","commentary","abstained","candidate_receipt"],"forbidden":["factual_setup","source_packet","answer_key"]},"case_inventory_sha256":hashlib.sha256(case_bytes).hexdigest()},"boundary_identity")
    (art/"editor-vnext-voice-bakeoff-boundary-v1.json").write_bytes(json.dumps(protocol,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
    return audit(repo)

def audit(repo: Path) -> dict:
    art=repo/"docs/artifacts"; protocol=json.loads((art/"editor-vnext-voice-bakeoff-boundary-v1.json").read_text(encoding="utf-8")); cases=[json.loads(x) for x in (art/"editor-vnext-voice-bakeoff-boundary-v1-cases.jsonl").read_text(encoding="utf-8").splitlines()]; slots=[json.loads(x) for x in (art/"editor-vnext-voice-bakeoff-boundary-v1-slots.jsonl").read_text(encoding="utf-8").splitlines()]
    assert identified(protocol,"boundary_identity")["boundary_identity"]==protocol["boundary_identity"]
    assert protocol["bindings"]["plan_identity"]==PLAN_ID and protocol["bindings"]["candidate_lock_identity"]==CANDIDATE_LOCK and protocol["bindings"]["r2_lock_identity"]==R2_LOCK
    assert len(cases)==24 and len(slots)==216 and len({x["slot_identity"] for x in slots})==216
    assert {x["seed"] for x in slots}==set(SEEDS) and {x["case_id"] for x in slots}=={x["case_id"] for x in cases}
    assert all(x["answer_key_excluded"] and "candidate_id" not in x for x in slots)
    assert protocol["factual_invariants"]==INVARIANTS and protocol["runtime"]["model_load_authorized"] is False
    forbidden=("VoiceFactAtomBundle","EventAuthorityBundle","EvidencePacket","factual ledger","semantic authority","/root/pf9","F:\\pt")
    payload=b"".join(p.read_bytes() for p in art.glob("editor-vnext-voice-bakeoff-boundary-v1*"))
    assert not any(x.encode() in payload for x in forbidden)
    return {"status":"PASS","boundary_identity":protocol["boundary_identity"],"cases":24,"seeds":3,"candidates":3,"slots":216,"legacy_dependency_count":0,"model_loaded":False,"inference_performed":False}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--repo",type=Path,default=Path(".")); p.add_argument("--audit-only",action="store_true"); a=p.parse_args()
    print(json.dumps(audit(a.repo) if a.audit_only else build(a.repo),sort_keys=True))
