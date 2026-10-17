"""python test_andreazza.py  — confere o parser de um item da API do app (amostra real de 2026-10-17)."""
from andreazza import oferta_app

cats = {"43": "AÇOUGUE/FRIOS/CONGELADOS"}
o = oferta_app({
    "id": "282928", "id_category": "43", "code": "409832", "title": "Entrecot Bovino Chef Pedaço Resfriado Kg ",
    "subtitle": "<s>R$ 54,90</s>", "observation": None, "price": "R$ 49,99", "max": 10, "max_unit": "kg",
    "must_activate": "1", "image": "https://images.meuandreazza.com.br/x.png",
    "date_start_formatted": "16/10/2026", "date_end_formatted": "18/10/2026",
}, cats)
assert (o["de"], o["por"], o["pct"]) == (54.9, 49.99, 8.9), o
assert (o["ini"], o["fim"], o["k"], o["m"]) == ("2026-10-16", "2026-10-18", "a409832", "andreazza"), o
assert o["nome"] == "Entrecot Bovino Chef Pedaço Resfriado Kg" and o["cats"] == ["Açougue/Frios/Congelados"], o
assert o["obs"] == "limite 10 kg · ative no app", o

p = oferta_app({
    "id": "1", "id_category": "9", "code": "", "title": "Pizza Sadia 440g", "subtitle": "LEVE 2 PAGUE CADA",
    "observation": "<p>Exceto:&nbsp;Zero Lactose</p>\n", "price": "R$ 12,99", "max": 6, "max_unit": "unidades",
    "must_activate": "1", "image": "", "date_start_formatted": "11/10/2026", "date_end_formatted": "18/10/2026",
}, cats)
assert (p["de"], p["por"], p["pct"], p["cats"], p["k"]) == (None, 12.99, 0, [], "a1"), p
assert p["obs"] == "Leve 2 pague cada R$ 12,99 · Exceto: Zero Lactose · limite 6 un. · ative no app", p
print("ok")
