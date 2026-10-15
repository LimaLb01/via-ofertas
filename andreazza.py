"""Ofertas do Supermercados Andreazza a partir da revista em PDF publicada em superandreazza.com.br/ofertas/.

Layout da revista (Montserrat): nome em Medium ~9pt, detalhe em Regular ~7pt, preço em ExtraBold 22pt
logo abaixo. Em "LEVE N PAGUE" vem o preço normal em 14pt acima do preço promocional.
"""
import hashlib
import re
import sys
import urllib.request
from datetime import date

import pymupdf

PAGINA = "https://superandreazza.com.br/ofertas/"
PRECO = re.compile(r"^(\d{1,4}),(\d{2})")
DARK = 0x231F20


def baixar(url):
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=120) as f:
        return f.read()


def revista():
    """URL do PDF do mês e validade (ini, fim) em ISO, lidos da página de ofertas."""
    h = baixar(PAGINA).decode("utf-8", "replace")
    pdf = re.search(r'href="(https://superandreazza\.com\.br/wp-content/uploads/[^"]+\.pdf)"', h)
    val = re.search(r"válidas de (\d{2})/(\d{2})(?:/(\d{4}))? a (\d{2})/(\d{2})/(\d{4})", h)
    if not pdf or not val:
        raise RuntimeError("Andreazza: não achei PDF ou validade na página de ofertas")
    d1, m1, a1, d2, m2, a2 = val.groups()
    return pdf.group(1), f"{a1 or a2}-{m1}-{d1}", f"{a2}-{m2}-{d2}"


def _spans(page):
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].strip()
                if t:
                    x0, y0, x1, y1 = s["bbox"]
                    yield {"t": t, "x": x0, "y": y0, "y1": y1, "sz": s["size"], "f": s["font"], "c": s["color"]}


def _valor(t):
    m = PRECO.match(t)
    return float(f"{m.group(1)}.{m.group(2)}") if m else None


def _perto(s, precos, max_dy=110):
    """Preço mais próximo logo abaixo do span (texto fica alinhado à esquerda ou centralizado sobre o preço)."""
    best, nota = None, 1e9
    for p in precos:
        dy, dx = p["y"] - s["y"], abs(p["x"] - s["x"])
        if -2 <= dy <= max_dy and dx < 45:
            n = dy + 2 * dx
            if n < nota:
                best, nota = p, n
    return best


def extrair(pdf_bytes):
    """Lista de dicts {nome, det, dep, de, por, leve} da revista."""
    out = []
    for page in pymupdf.open(stream=pdf_bytes, filetype="pdf"):
        sp = list(_spans(page))
        heads = [s["t"].title().replace(" E ", " e ") for s in sp if "Light" in s["f"] and s["sz"] > 25]
        dep = heads[0] if len(heads) == 1 else ""  # capa/receitas não têm departamento
        precos = [s for s in sp if "ExtraBold" in s["f"] and s["sz"] >= 17 and _valor(s["t"]) is not None]
        for p in precos:
            p.update(nome=[], det=[], de=None, leve="")
        for s in sp:
            if "ExtraBold" in s["f"] and 12 <= s["sz"] < 17 and _valor(s["t"]) is not None:
                if (p := _perto(s, precos, 60)) and abs(p["x"] - s["x"]) < 12:
                    p["de"] = _valor(s["t"])
            elif s["c"] == 0xFFFFFF and s["t"].upper().startswith("LEVE"):
                if p := _perto(s, precos, 40):
                    p["leve"] = s["t"]
            elif s["c"] == DARK and s["t"] != "cada" and 5.5 <= s["sz"] <= 10 and re.search(r"Medium|Regular|Italic", s["f"]):
                if (p := _perto(s, precos)) and s["y1"] <= p["y"] + 6:
                    (p["nome"] if s["sz"] >= 7.5 and "Medium" in s["f"] else p["det"]).append(s)
        for p in precos:
            if not p["nome"]:
                continue
            junta = lambda xs: " ".join(x["t"] for x in sorted(xs, key=lambda x: (x["y"], x["x"])))
            por = _valor(p["t"])
            de = p["de"] if p["de"] and p["de"] > por else None
            out.append({"nome": junta(p["nome"]), "det": junta(p["det"]), "dep": dep, "de": de, "por": por,
                        "leve": p["leve"]})
    return out


def coletar(hoje=None):
    """Ofertas no formato do coletar.py. Lista vazia se a revista estiver vencida."""
    hoje = hoje or date.today().isoformat()
    url, ini, fim = revista()
    if fim < hoje:
        print(f"Andreazza: revista vencida em {fim}, sem ofertas", file=sys.stderr)
        return []
    ofertas = []
    for o in extrair(baixar(url)):
        k = f"{o['nome']}|{o['det']}".lower()
        nome = f"{o['nome']} {o['det']}".strip()
        leve = o["leve"].title().replace(" Pague", ", pague")  # "Leve 2, pague R$ x cada" / "Leve 4, pague 3 · ..."
        obs = f"{leve}{' ·' if leve[-1].isdigit() else ''} R$ {o['por']:.2f} cada".replace(".", ",") if leve else ""
        ofertas.append({
            "id": "a" + hashlib.md5(k.encode()).hexdigest()[:10], "k": k, "nome": nome,
            "de": o["de"], "por": o["por"],
            "pct": round((1 - o["por"] / o["de"]) * 100, 1) if o["de"] else 0,
            "ini": ini, "fim": fim, "lim": None, "cats": [o["dep"]] if o["dep"] else [], "img": "",
            "dest": False, "esg": False, "obs": obs, "m": "andreazza",
        })
    return ofertas


if __name__ == "__main__":
    # uso: python andreazza.py [arquivo.pdf]  -> imprime o que extraiu
    if len(sys.argv) > 1:
        itens = extrair(open(sys.argv[1], "rb").read())
    else:
        itens = coletar()
    for o in itens:
        print(o)
    print(len(itens), "ofertas", file=sys.stderr)
