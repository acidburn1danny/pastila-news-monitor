"""Build the frozen synthetic multi-source EDITOR contract benchmark v1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-factual-setup-benchmark-v1"
SYSTEM = """Respectă contractul EDITOR. Primești numai sursele factuale pentru un singur subiect. Scrie un setup factual de exact două sau trei propoziții, suficient ca autoritate pentru o etapă VOICE separată. Selectează și reconciliază faptele relevante din toate sursele, elimină redundanța și păstrează exact actorii, atribuirea, cronologia, numele, cifrele, modalitatea, incertitudinea și statutul procedural. Nu transforma afirmațiile sau estimările în fapte stabilite și nu inventa informații. Româna trebuie să fie gramaticală, inteligibilă și lipsită de ambiguități. Nu scrie sarcasm, ironie, roast, glume, comentariu, punchline, personalitate stilistică sau proză finală de emisiune.

Returnează exact un obiect JSON compact NFC UTF-8, fără Markdown sau text extern, cu schema și ordinea câmpurilor cerute. Primul byte este {, ultimul este }, urmat imediat de EOS/EOF."""


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def compact(value: object) -> str:
    return canonical(value).decode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


VARIANTS = [
    ("Arin", "Brașov", 127, 19, "luni"),
    ("Vela", "Oradea", 184, 27, "marți"),
    ("Meridian", "Buzău", 231, 34, "miercuri"),
]


def definitions() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for index, (name, city, total, secondary, day) in enumerate(VARIANTS, 1):
        cases.extend([
            {
                "operator": "MULTISOURCE_FACT_SELECTION",
                "request": "Rezumați aprobările pentru centrul medical și stadiul implementării; excludeți proiectul sportiv fără legătură.",
                "spans": [
                    ("consiliu", f"Consiliul local din {city} a aprobat {total} de milioane de lei pentru noul centru medical {name}."),
                    ("minister", f"Ministerul a precizat că finanțarea centrului {name} este aprobată, dar contractul de execuție nu a fost încă semnat."),
                    ("sport", f"În aceeași ședință au fost alocate {secondary} milioane de lei pentru modernizarea stadionului municipal."),
                ],
                "target": f"Consiliul local din {city} a aprobat {total} de milioane de lei pentru centrul medical {name}. Ministerul precizează că finanțarea este aprobată, însă contractul de execuție nu a fost încă semnat.",
                "required": [f"{total} de milioane", f"centrul medical {name}", "contractul de execuție nu a fost încă semnat"],
                "forbidden": ["stadion", f"{secondary} milioane", "lucrările au început"],
            },
            {
                "operator": "ATTRIBUTED_CONTEST",
                "request": "Prezentați acuzația, răspunsul entității și stadiul verificării fără a decide cine are dreptate.",
                "spans": [
                    ("inspectori", f"Inspectorii afirmă într-o notă preliminară că Depozitul {name} ar fi omis {total} de înregistrări."),
                    ("depozit", f"Depozitul {name} contestă afirmația și spune că registrul transmis conține toate operațiunile."),
                    ("autoritate", "Autoritatea de control declară că verificarea este în curs și că nu a stabilit încă situația de fapt."),
                ],
                "target": f"Inspectorii afirmă într-o notă preliminară că Depozitul {name} ar fi omis {total} de înregistrări, acuzație contestată de depozit. Autoritatea de control spune că verificarea este în curs și că situația de fapt nu a fost încă stabilită.",
                "required": ["Inspectorii afirmă", "ar fi omis", "contestată", "verificarea este în curs", "nu a fost încă stabilită"],
                "forbidden": ["a omis", "încălcare confirmată", "vinovat"],
            },
            {
                "operator": "CHRONOLOGY_UPDATE",
                "request": "Redați succint evoluția și situația actuală, în ordine cronologică.",
                "spans": [
                    ("initial", f"Locuitorii din cartierul {name} au fost evacuați {day} dimineață după o alertă privind o conductă."),
                    ("return", f"Primăria din {city} a permis revenirea locuitorilor în aceeași seară, după măsurători."),
                    ("latest", "Operatorul rețelei a anunțat ulterior că strada principală rămâne închisă până la finalizarea reparației."),
                ],
                "target": f"Locuitorii cartierului {name} au fost evacuați {day} dimineață după o alertă privind o conductă și au putut reveni în aceeași seară. Operatorul rețelei anunță că strada principală rămâne închisă până la finalizarea reparației.",
                "required": ["evacuați", "au putut reveni", "strada principală rămâne închisă", "finalizarea reparației"],
                "forbidden": ["strada a fost redeschisă", "conducta a explodat"],
            },
            {
                "operator": "NUMERIC_RECONCILIATION",
                "request": "Folosiți totalul corectat și explicați relația cu inventarul anterior, fără a amesteca valorile.",
                "spans": [
                    ("initial", f"Un inventar provizoriu a raportat {total} de dosare depuse la agenția din {city}."),
                    ("breakdown", f"Agenția a precizat că {total-secondary} de dosare erau distincte, iar {secondary} erau înregistrări duplicate."),
                    ("correction", f"Buletinul corectat stabilește totalul la {total-secondary} de dosare, după eliminarea duplicatelor."),
                ],
                "target": f"Inventarul provizoriu indica {total} de dosare la agenția din {city}. Buletinul corectat stabilește însă {total-secondary} de dosare distincte, după eliminarea a {secondary} de înregistrări duplicate.",
                "required": [f"{total}", f"{total-secondary}", f"{secondary}", "provizoriu", "corectat", "duplicate"],
                "forbidden": [f"{total} de dosare distincte", "dosare respinse"],
            },
            {
                "operator": "PROCEDURAL_STATUS",
                "request": "Explicați măsura propusă și pașii procedurali rămași, fără a o prezenta ca aplicată.",
                "spans": [
                    ("proposal", f"Comisia tehnică a propus suspendarea autorizației companiei {name} pentru {secondary} zile."),
                    ("vote", f"Propunerea urmează să fie votată de plenul autorității {day}."),
                    ("status", "Până la vot nu există o decizie finală, iar autorizația rămâne în vigoare."),
                ],
                "target": f"Comisia tehnică a propus suspendarea pentru {secondary} zile a autorizației companiei {name}, iar plenul urmează să voteze {day}. Până la vot nu există o decizie finală, iar autorizația rămâne în vigoare.",
                "required": ["a propus", f"{secondary} zile", "urmează să voteze", "nu există o decizie finală", "rămâne în vigoare"],
                "forbidden": ["a suspendat", "autorizația este suspendată", "decizie definitivă"],
            },
            {
                "operator": "MODALITY_UNCERTAINTY",
                "request": "Rezumați riscul estimat și măsura pregătită, păstrând incertitudinea și statutul neactivat.",
                "spans": [
                    ("forecast", f"Institutul estimează o probabilitate de {secondary}% ca nivelul râului {name} să depășească pragul de atenție."),
                    ("local", f"Primăria din {city} pregătește evacuarea preventivă a unei străzi, dar măsura nu a fost activată."),
                    ("uncertainty", "Institutul avertizează că prognoza se poate modifica odată cu noile măsurători."),
                ],
                "target": f"Institutul estimează la {secondary}% probabilitatea ca râul {name} să depășească pragul de atenție și avertizează că prognoza se poate modifica. Primăria din {city} pregătește o posibilă evacuare preventivă, dar măsura nu a fost activată.",
                "required": [f"{secondary}%", "estimează", "se poate modifica", "pregătește", "nu a fost activată"],
                "forbidden": ["va depăși", "a dispus evacuarea", "evacuarea a început"],
            },
            {
                "operator": "COMPRESSION_WITH_DISTRACTOR",
                "request": "Rezumați numai întreruperea curentă, cauza atribuită și termenul estimat de remediere.",
                "spans": [
                    ("incident", f"Operatorul {name} anunță că {total} de consumatori din {city} au rămas fără apă după avarierea unei conducte."),
                    ("repair", f"Operatorul estimează reluarea furnizării {day} la ora 18:00, dacă reparația decurge conform planului."),
                    ("history", f"Rețeaua din {city} a fost construită în urmă cu 42 de ani și a trecut printr-o extindere în 2011."),
                ],
                "target": f"Operatorul {name} anunță că {total} de consumatori din {city} au rămas fără apă după avarierea unei conducte. Furnizarea ar urma să fie reluată {day} la ora 18:00, dacă reparația decurge conform planului.",
                "required": [f"{total} de consumatori", "fără apă", "avarierea unei conducte", f"{day} la ora 18:00", "dacă"],
                "forbidden": ["42 de ani", "2011", "va fi reluată cu certitudine"],
            },
            {
                "operator": "CROSS_SOURCE_SUFFICIENCY",
                "request": "Construiți setup-ul complet al deciziei, aplicării și efectului imediat folosind toate sursele relevante.",
                "spans": [
                    ("decision", f"Consiliul universității {name} a decis reducerea taxei de înscriere cu {secondary}% pentru candidații eligibili."),
                    ("application", f"Universitatea precizează că reducerea se aplică sesiunii din {city} care începe {day}."),
                    ("scope", f"Măsura privește numai taxa de înscriere; celelalte taxe, în valoare cumulată de {total} de lei, nu se modifică."),
                ],
                "target": f"Universitatea {name} reduce cu {secondary}% taxa de înscriere pentru candidații eligibili în sesiunea din {city} care începe {day}. Măsura nu modifică celelalte taxe, în valoare cumulată de {total} de lei.",
                "required": [f"{secondary}%", "taxa de înscriere", "candidații eligibili", city, day, "nu modifică celelalte taxe", f"{total} de lei"],
                "forbidden": ["toate taxele", "taxele au fost eliminate"],
            },
        ])
    return cases


def build() -> dict[str, object]:
    request_rows = []
    key_rows = []
    for number, case in enumerate(definitions(), 1):
        case_id = f"ec-editor-setup-v1-{number:02d}"
        spans = [{"span_id": f"{case_id}:s{i}", "source_id": source, "text": text}
                 for i, (source, text) in enumerate(case["spans"], 1)]
        core = {
            "schema": "editor-factual-setup-request", "schema_version": 1,
            "case_id": case_id, "output_type": "FACTUAL",
            "sentence_budget": {"minimum": 2, "maximum": 3},
            "request": case["request"], "authority_spans": spans,
        }
        core["request_identity"] = "sha256:" + sha(canonical(core))
        user = "Aplică EDITOR FACTUAL SETUP CONTRACT v1.\nINPUT=" + compact(core)
        request_rows.append({"example_id": case_id, "split": "INDEPENDENT_SELECTION_BENCHMARK",
                             "operator": case["operator"], "messages": [
                                 {"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]})
        sources = [span["span_id"] for span in spans]
        answer = {
            "schema": "pastila-core-v2-structured-qualification-response", "schema_version": 2,
            "case_id": case_id, "request_identity": core["request_identity"], "output_type": "FACTUAL",
            "outcome": "ANSWER", "text": case["target"],
            "claim_bindings": [{"claim_index": i, "source_span_ids": sources}
                               for i in range(1, 3)], "abstention_code": None,
        }
        key_rows.append({"example_id": case_id, "operator": case["operator"],
                         "request_identity": core["request_identity"], "required_evidence": case["required"],
                         "forbidden_inferences": case["forbidden"], "assistant_target": compact(answer)})
    requests = b"".join(canonical(row) + b"\n" for row in request_rows)
    key = b"".join(canonical(row) + b"\n" for row in key_rows)
    request_path = ART / f"{PREFIX}-requests.jsonl"
    key_path = ART / f"{PREFIX}-answer-key.jsonl"
    request_path.write_bytes(requests)
    key_path.write_bytes(key)
    contract_path = ART / "editor-core-factual-setup-contract-v1.json"
    core = {
        "schema": "editor-core-factual-setup-benchmark-manifest", "schema_version": 1,
        "status": "FROZEN_PRE_INFERENCE", "cases": 24, "operators": 8,
        "cases_per_operator": 3, "sources_per_case": 3,
        "sentence_minimum": 2, "sentence_maximum": 3,
        "requests_sha256": sha(requests), "answer_key_sha256": sha(key),
        "contract_sha256": sha(contract_path.read_bytes()),
        "historical_holdouts_read": False, "training_data_used": False,
        "voice_comedy_or_final_polish_objective": False,
        "allowed_claim": "R1_CHECKPOINT_8_VS_R2_STEP_9_ON_THIS_SYNTHETIC_MULTISOURCE_EDITOR_CONTRACT_BENCHMARK",
        "forbidden_claims": ["NATURALISTIC_TRANSFER", "PROMOTION", "RELEASE"],
    }
    manifest = {**core, "manifest_identity": sha(canonical(core))}
    (ART / f"{PREFIX}-manifest.json").write_bytes(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), sort_keys=True))
