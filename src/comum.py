import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FILA = RAIZ / "fila.json"


def carregar_config():
    return json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


def carregar_fila():
    if FILA.exists():
        return json.loads(FILA.read_text(encoding="utf-8"))
    return []


def salvar_fila(fila):
    fila.sort(key=lambda p: p["quando"])
    FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8")


def montar_legenda(post, cfg):
    texto = post["legenda"]
    tema = post.get("tema")
    if tema in ("cardapio", "agenda") and cfg.get("assinatura_cross_sell"):
        texto += "\n\n" + cfg["assinatura_cross_sell"]
    for chave in ("whatsapp", "marca", "link", "instagram"):
        texto = texto.replace("{" + chave + "}", cfg.get(chave, ""))
    extras = cfg.get("hashtags_tema", {}).get(tema, [])
    tags = list(dict.fromkeys(post.get("hashtags", []) + extras + cfg.get("hashtags_fixas", [])))[:15]
    return f"{texto}\n.\n.\n{' '.join(tags)}"
