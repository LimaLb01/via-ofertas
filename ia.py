"""Fichas de produto pela IA do Gemini (free tier): produto da lista, variante, tamanho e marca.

Só nomes nunca vistos vão para a IA (cache em data/ia.json), então são poucas chamadas por dia.
Sem GEMINI_API_KEY, ou com erro/cota estourada, as ofertas seguem sem ficha e o site usa as regras.
"""
import json
import os
import time
import urllib.request

MODELO = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
LOTE = 60  # nomes por chamada

PROMPT = """Você organiza ofertas de supermercado brasileiro para uma lista de compras.
Para cada nome numerado, devolva um objeto com:
- i: o número do nome
- p: o item como a pessoa escreve na lista de compras, em português, minúsculo, com acentos e sem marca.
  Produtos diferentes têm p diferentes: "leite", "leite condensado", "creme de leite", "doce de leite", "leite em pó".
  Itens que substituem um ao outro têm o mesmo p: café em pó e café solúvel são p "café".
  Exemplos: "arroz", "feijão", "café", "refrigerante", "cerveja", "papel higiênico", "carne bovina", "frango", "sabão em pó".
- v: variação dentro do mesmo item, minúsculo, "" se não houver
  (ex.: café "em pó"/"solúvel"/"cápsula"; leite "integral"/"desnatado"/"zero lactose"; feijão "preto"/"carioca"; refrigerante "cola"/"guaraná").
- q: quantidade total da embalagem em kg ou L como número (500g = 0.5; 6x350ml = 2.1; vendido por kg = 1). null se não der para saber.
- u: "kg" ou "L" quando q existe; "un" quando é vendido por unidade sem peso (rolos, fraldas, unidade); "" se não der.
- m: marca, "" se não houver.
Não invente marca nem tamanho que não estejam no nome."""

SCHEMA = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
    "i": {"type": "INTEGER"}, "p": {"type": "STRING"}, "v": {"type": "STRING"},
    "q": {"type": "NUMBER", "nullable": True}, "u": {"type": "STRING"}, "m": {"type": "STRING"},
}, "required": ["i", "p", "v", "q", "u", "m"]}}


def ficha(f):
    """Limpa a resposta da IA; None se não serve."""
    p = str(f.get("p") or "").strip().lower()
    if not p:
        return None
    u = f.get("u") if f.get("u") in ("kg", "L", "un") else ""
    try:
        q = float(f["q"]) if f.get("q") is not None and u in ("kg", "L") else None
    except (TypeError, ValueError):
        q = None
    if q is not None and not 0 < q < 1000:
        q = None
    return {"p": p, "v": str(f.get("v") or "").strip().lower(), "q": q, "u": u if q or u == "un" else "",
            "m": str(f.get("m") or "").strip()}


def chamar(nomes, chave):
    texto = PROMPT + "\n\n" + "\n".join(f"{i}: {n}" for i, n in enumerate(nomes))
    body = {"contents": [{"parts": [{"text": texto}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0}}
    r = urllib.request.Request(URL.format(MODELO), data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json", "x-goog-api-key": chave})
    with urllib.request.urlopen(r, timeout=120) as resp:
        d = json.loads(resp.read().decode("utf-8"))
    return {x.get("i"): x for x in json.loads(d["candidates"][0]["content"]["parts"][0]["text"])}


def enriquecer(ofertas, cache_path, chamar=chamar):
    """Põe o["ia"] nas ofertas; devolve quantos nomes novos a IA classificou."""
    chave = os.environ.get("GEMINI_API_KEY", "")
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    novos = sorted({o["nome"] for o in ofertas} - cache.keys()) if chave else []
    feitos = 0
    for k in range(0, len(novos), LOTE):
        lote = novos[k:k + LOTE]
        if k:
            time.sleep(5)  # free tier tem limite por minuto
        try:
            res = chamar(lote, chave)
        except Exception as e:  # cota ou erro: guarda o que já veio, o resto tenta amanhã
            print(f"::warning::IA parou em {k}/{len(novos)} nomes: {e!r}")
            break
        for i, n in enumerate(lote):
            if f := ficha(res.get(i) or {}):
                cache[n] = f
                feitos += 1
    if novos:
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, sort_keys=True, indent=0), encoding="utf-8")
    for o in ofertas:
        if f := cache.get(o["nome"]):
            o["ia"] = f
    return feitos
