"""python test_ia.py  — confere limpeza das fichas e o cache, sem chamar a IA."""
import json
import os
import tempfile
from pathlib import Path

import ia

assert ia.ficha({"p": " Café ", "v": "Solúvel", "q": 0.2, "u": "kg", "m": "Nescafé"}) == \
    {"p": "café", "v": "solúvel", "q": 0.2, "u": "kg", "m": "Nescafé"}
assert ia.ficha({"p": "", "v": "", "q": 1, "u": "L", "m": ""}) is None
assert ia.ficha({"p": "fralda", "v": "", "q": None, "u": "un", "m": "Huggies"})["u"] == "un"
assert ia.ficha({"p": "leite", "v": "", "q": "x", "u": "L", "m": ""})["u"] == ""  # q inválido some com a unidade

os.environ["GEMINI_API_KEY"] = "teste"
chamadas = []
def falsa(nomes, chave):
    chamadas.append(list(nomes))
    return {i: {"i": i, "p": "leite", "v": "", "q": 1, "u": "L", "m": ""} for i in range(len(nomes))}

with tempfile.TemporaryDirectory() as d:
    cache = Path(d) / "ia.json"
    cache.write_text(json.dumps({"Leite A 1L": {"p": "leite", "v": "", "q": 1, "u": "L", "m": "A"}}), encoding="utf-8")
    ofertas = [{"nome": "Leite A 1L"}, {"nome": "Leite B 1L"}]
    assert ia.enriquecer(ofertas, cache, chamar=falsa) == 1
    assert chamadas == [["Leite B 1L"]]  # só o nome novo vai para a IA
    assert ofertas[0]["ia"]["m"] == "A" and ofertas[1]["ia"]["p"] == "leite"
    assert "Leite B 1L" in json.loads(cache.read_text(encoding="utf-8"))
print("ok")
