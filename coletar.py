"""Rotina diária: busca ofertas do VIA Clube e do Andreazza, compara com ontem e gera site/index.html.

Credenciais via variáveis de ambiente (segredos do GitHub):
  VIA_LOGIN (CPF), VIA_SENHA, VIA_XAPIKEY, VIA_LOJA (padrão 8 = VIA CAXIAS)
  ANDREAZZA_LOGIN (CPF), ANDREAZZA_SENHA (sem eles, Andreazza usa só a revista PDF)
  GEMINI_API_KEY (opcional: fichas de produto pela IA, ver ia.py)
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import andreazza
import ia

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SITE = ROOT / "site"
API = "https://apiapp.zoombox.com.br/v16"
OFERTAS = "https://9zli2drdqe.execute-api.us-east-1.amazonaws.com/v1/ofertas"
VAREJISTA = "dw-zbd-viaatacadista-cacador-sc"
BRT = timezone(timedelta(hours=-3))  # Brasil sem horário de verão desde 2019


def req(url, body=None, token=None):
    headers = {"idvarejista": VAREJISTA, "x-api-key": os.environ["VIA_XAPIKEY"],
               "Accept": "application/json", "User-Agent": "okhttp/4.12.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def buscar():
    cpf, loja = os.environ["VIA_LOGIN"], os.environ.get("VIA_LOJA", "8")
    token = req(f"{API}/login", {"login": cpf, "senha": os.environ["VIA_SENHA"], "revisaoApple": False})["access_token"]
    d = req(f"{OFERTAS}?{urllib.parse.urlencode({'lojas': loja, 'cpfcnpj': cpf})}", token=token)
    return d.get("ofertas", []) if isinstance(d, dict) else d


def enxugar(o):
    eans = o.get("eans") or []
    return {
        "id": o["idoferta"],
        "k": eans[0] if eans else o.get("nomeoferta", ""),  # chave estável entre dias
        "nome": (o.get("nomeoferta") or "").strip(),
        "de": o.get("valorde"),
        "por": o.get("valorpor"),
        "pct": round(float(o.get("percentualdesconto") or 0), 1),
        "ini": o.get("validadede"),
        "fim": o.get("validadeate"),
        "lim": o.get("limitecompra"),
        "cats": [c.title() for c in (o.get("categorias") or [])],
        "img": (o.get("imagem") or "").split("?")[0],
        "dest": bool(o.get("destaquecomercial")),
        "esg": bool(o.get("esgotado")),
    }


def marcar(hoje, ontem):
    antes = {o["k"]: o for o in ontem}
    mercados = {o.get("m", "via") for o in ontem}  # mercado novo no site não vira "tudo novo"
    for o in hoje:
        a = antes.get(o["k"])
        if a is None:
            o["st"] = "nova" if o["m"] in mercados else "continua"
        else:
            o["st"] = "renovada" if a["fim"] != o["fim"] else "continua"
    return hoje


def fonte(nome, f):
    """Uma fonte com erro não derruba a outra; o aviso aparece no resumo do GitHub Actions."""
    try:
        return f()
    except Exception as e:
        print(f"::warning::{nome} falhou: {e!r}")
        return None


def main():
    agora = datetime.now(BRT)
    dia = agora.strftime("%Y-%m-%d")
    DATA.mkdir(exist_ok=True)
    SITE.mkdir(exist_ok=True)

    via = fonte("VIA", lambda: [dict(enxugar(o), m="via") for o in buscar()])
    andr = fonte("Andreazza", lambda: andreazza.coletar(dia))
    if via is None and andr is None:
        raise SystemExit("nenhuma fonte de ofertas funcionou")
    ofertas = [o for o in (via or []) + (andr or []) if o["por"] is not None]
    anteriores = sorted(p for p in DATA.glob("*.json") if p.stem < dia)
    ontem = json.loads(anteriores[-1].read_text(encoding="utf-8")) if anteriores else []
    marcar(ofertas, ontem)
    n_ia = fonte("IA", lambda: ia.enriquecer(ofertas, DATA / "ia.json"))
    (DATA / f"{dia}.json").write_text(json.dumps(ofertas, ensure_ascii=False), encoding="utf-8")

    payload = {"dia": dia, "hora": agora.strftime("%H:%M"), "temOntem": bool(ontem), "ofertas": ofertas}
    (DATA / "latest.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # site só quando existir template com o marcador /*__DATA__*/null
    tpl = ROOT / "template.html"
    if tpl.exists() and "/*__DATA__*/null" in (t := tpl.read_text(encoding="utf-8")):
        blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
        (SITE / "index.html").write_text(t.replace("/*__DATA__*/null", blob), encoding="utf-8")
    print(f"{dia}: {len(via or [])} VIA + {len(andr or [])} Andreazza, {sum(o['st'] == 'nova' for o in ofertas)} novas, "
          f"IA: {n_ia or 0} fichas novas, {sum('ia' in o for o in ofertas)} ofertas com ficha")


if __name__ == "__main__":
    main()
