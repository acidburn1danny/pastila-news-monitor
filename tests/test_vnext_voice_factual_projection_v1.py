from pastila_scout.vnext_voice_factual_projection_v1 import FactualSafetyClass, classify_numeric_claims, projection_decision

def test_entailed_difference_is_not_drift():
    claims=classify_numeric_claims("Inflația a coborât la 5,1% de la 5,4%.","Scăderea de 0,3% a primit aplauze.")
    assert claims[-1].classification is FactualSafetyClass.ENTAILED_DERIVATION

def test_currency_equivalence_is_not_drift():
    claims=classify_numeric_claims("Tariful este 0,80 lei pe kilometru.","Cine spune că 80 de bani sunt puțini?")
    assert claims[-1].classification is FactualSafetyClass.SEMANTIC_EQUIVALENCE
    articulated=classify_numeric_claims("Tariful este 0,80 lei pe kilometru.","Cine spune că 80 de banii nu sunt un bănuț?")
    assert articulated[-1].classification is FactualSafetyClass.SEMANTIC_EQUIVALENCE

def test_unsupported_number_rejected():
    result=projection_decision("Raportul indică 42 de clădiri.","Poate sunt 43.")
    assert result["decision"]=="REJECT_UNSUPPORTED_FACT" and result["unsupported"]==["43"]

def test_supported_copy_allowed():
    assert projection_decision("Sunt 42 de clădiri.","Numărul 42 a primit ștampilă.")["decision"]=="ALLOW_NUMERIC_PROJECTION"
