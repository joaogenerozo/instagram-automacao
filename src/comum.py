import json
import re
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FILA = RAIZ / "fila.json"
FEED = ("post", "carrossel")


def carregar_config():
    return json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


def carregar_fila():
    if FILA.exists():
        return json.loads(FILA.read_text(encoding="utf-8"))
    return []


def salvar_fila(fila):
    fila.sort(key=lambda p: p["quando"])
    FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- legenda: um CTA só, foco local e poucas hashtags de quem compra ----------

def _linha_de_cta(linha, cfg):
    """Linhas de chamada antigas (número de WhatsApp solto, cross-sell, CTA padrão já aplicado)."""
    l = linha.strip()
    if not l:
        return False
    numero = re.sub(r"\D", "", cfg.get("whatsapp", ""))
    so_digitos = re.sub(r"\D", "", l)
    if "{whatsapp}" in l or (numero and numero in so_digitos):
        return True
    if l.startswith(("💻 Também crio sites", "💬 Comente ", "📲 Prefere WhatsApp", "📍 GNZ01")):
        return True
    return False


def limpar_cta(texto, cfg):
    linhas = [l for l in texto.split("\n") if not _linha_de_cta(l, cfg)]
    texto = "\n".join(linhas)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def escolher_hashtags(post_tags, tema, cfg):
    bloq = {h.lower() for h in cfg.get("hashtags_bloqueadas", [])}
    local = cfg.get("local", {}).get("hashtags", [])
    proprias = [h for h in post_tags if h.lower() not in bloq and h not in local]
    tema_tags = cfg.get("hashtags_tema", {}).get(tema, [])
    ordem = local + proprias[:2] + tema_tags + proprias[2:] + cfg.get("hashtags_fixas", [])
    tags = list(dict.fromkeys(h for h in ordem if h.lower() not in bloq))
    return tags[: cfg.get("max_hashtags", 5)]


def montar_legenda(post, cfg):
    tema = post.get("tema")
    texto = post["legenda"]
    if post.get("gancho") and not texto.startswith(post["gancho"]):
        texto = post["gancho"] + "\n\n" + texto
    texto = limpar_cta(texto, cfg)
    for chave in ("marca", "link", "instagram"):
        texto = texto.replace("{" + chave + "}", cfg.get(chave, ""))
    if post.get("pergunta") and post["pergunta"] not in texto:
        texto += "\n\n" + post["pergunta"]  # pergunta que puxa comentário (engajamento, 09/11)
    cta = cfg.get("cta", {})
    palavra = cta.get("palavras", {}).get(tema, "SITE")
    if post.get("cta_personalizado"):
        texto += "\n\n" + post["cta_personalizado"]  # quadros como o raio-x pedem outro comentário
    elif cta.get("modelo"):
        texto += "\n\n" + cta["modelo"].format(palavra=palavra)
    local = cfg.get("local", {})
    if cta.get("local") and local.get("regiao"):
        texto += "\n" + cta["local"].format(**local)
    tags = escolher_hashtags(post.get("hashtags", []), tema, cfg)
    return f"{texto}\n.\n.\n{' '.join(tags)}"


def separar_legenda(legenda):
    """Desmonta 'texto\\n.\\n.\\n#tags\\n\\ncréditos' em (texto, tags, créditos)."""
    if "\n.\n.\n" not in legenda:
        return legenda, [], ""
    texto, resto = legenda.split("\n.\n.\n", 1)
    linha_tags, _, creditos = resto.partition("\n")
    return texto, [t for t in linha_tags.split() if t.startswith("#")], creditos.strip()


def remontar_legenda(item, cfg):
    """Aplica as regras atuais de CTA e hashtags a uma legenda que já está na fila."""
    texto, tags, creditos = separar_legenda(item.get("legenda", ""))
    if item.get("cta_personalizado"):
        texto = texto.replace(item["cta_personalizado"], "").rstrip()
    nova = montar_legenda({"legenda": texto, "hashtags": tags, "tema": item.get("tema"),
                           "cta_personalizado": item.get("cta_personalizado")}, cfg)
    return nova + ("\n\n" + creditos if creditos else "")


# ---------- repetição e citações ----------

def normalizar(titulo):
    t = unicodedata.normalize("NFKD", titulo or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"^(checklist|dica|bastidores)\s*:\s*", "", t)
    return re.sub(r"[^a-z0-9 ]+", "", t).strip()


def parecidos(a, b):
    a, b = normalizar(a), normalizar(b)
    if not a or not b:
        return False
    if a == b or (len(min(a, b, key=len)) >= 20 and (a in b or b in a)):
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.85


def eh_citacao(item):
    """Carrossel/post de citação ou de 'Os ensinamentos de' (personalidades)."""
    if item.get("tipo") not in FEED:
        return False
    if item.get("citacao") or re.search(r"_p\d+$", item.get("id", "")):
        return True
    t = item.get("titulo", "")
    return t.startswith("Os ensinamentos de") or (item.get("tema") == "marca" and item.get("legenda", "").startswith('"'))


def semana_iso(quando):
    return datetime.fromisoformat(quando).isocalendar()[:2]


def repetido(item, fila, dias=45):
    """Devolve o item já publicado/agendado antes deste com título parecido (dentro da janela), ou None."""
    if item.get("tipo") not in FEED:
        return None
    q = datetime.fromisoformat(item["quando"])
    for o in fila:
        if o is item or o.get("tipo") not in FEED or o["status"] not in ("publicado", "pendente", "aguardando_aprovacao"):
            continue
        quando_o = datetime.fromisoformat(o.get("publicado_em") or o["quando"])
        if o["status"] != "publicado" and quando_o >= q:
            continue  # só conta o que vem antes
        if abs(q - quando_o) > timedelta(days=dias):
            continue
        if parecidos(item.get("titulo"), o.get("titulo")):
            return o
    return None
