"""GNZ01 Carrossel: design system dos carrosséis (1080x1350).

Tokens
- Cores: FUNDO grafite #18191D, GRADE #2A2D33, TEXTO off-white #F4F3EE, SUAVE #8C9097, ATIVO prata #C4C8CE.
- Tipos: Inter Regular (corpo) + Inter ExtraBold (destaque) misturados na mesma frase; DejaVu Sans Mono no rodapé.
- Grade quadriculada no topo, sumindo para baixo. Margem 150, coluna de leitura de 780.
- Rodapé: PAG | 01 02 03 ... | GNZ01, com a página atual em prata.

Destaque: trechos entre **asteriscos** saem em ExtraBold. Sem asteriscos, o sistema destaca as
duas últimas palavras do título e as três últimas do texto.

Lâminas (campo "layout" do slide, ou rodízio automático):
- capa: foto opcional (licenciada, com crédito) + título gigante misto, linha "© 2026 | #tags", selo @gnz01_
- abertura: frase grande à esquerda + apoio menor (como a página 02 da referência)
- paragrafos: blocos de texto com destaques (página 03)
- duas_colunas: pergunta grande à esquerda, resposta à direita (página 04)
- centro: texto centralizado (página 05)
- cta: texto centralizado + pílula com Instagram e WhatsApp e o selo GNZ01 (página 06)
"""
import re
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from src.render import fonte

W, H = 1080, 1350
FUNDO = (24, 25, 29)
GRADE = (58, 62, 70)
TEXTO = (244, 243, 238)
SUAVE = (120, 124, 132)
ATIVO = (196, 200, 206)
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
LIGACAO = {"o", "a", "os", "as", "e", "de", "do", "da", "dos", "das", "no", "na", "nos", "nas", "em", "por",
           "ou", "com", "nem", "um", "uma", "que", "se", "seu", "sua", "ao", "para", "pra"}
LAYOUTS = ["abertura", "paragrafos", "duas_colunas", "centro"]


def _mono(t):
    from PIL import ImageFont
    return ImageFont.truetype(MONO, t)


# ------------------------------------------------------------------ texto misto
def _tokens(texto, auto=0):
    """Lista de (palavra, negrito). auto=N destaca as N últimas palavras quando não houver **."""
    if "**" not in texto and auto:
        p = texto.split()
        k = max(0, len(p) - auto)
        while k < len(p) - 1 and p[k].lower() in LIGACAO:
            k += 1
        texto = (" ".join(p[:k]) + " **" + " ".join(p[k:]) + "**").strip()
    out, neg = [], False
    for parte in re.split(r"(\*\*)", texto):
        if parte == "**":
            neg = not neg
            continue
        for w in parte.split():
            out.append((w, neg))
    return out


def _linhas(d, toks, tam, larg):
    fr, fb = fonte("regular", tam), fonte("bold", tam)
    esp = d.textlength(" ", font=fr)
    linhas, atual, lw = [], [], 0
    for w, b in toks:
        f = fb if b else fr
        tw = d.textlength(w, font=f)
        if atual and lw + esp + tw > larg:
            linhas.append((atual, lw))
            atual, lw = [], 0
        lw += (esp if atual else 0) + tw
        atual.append((w, b, tw))
    if atual:
        linhas.append((atual, lw))
    return linhas


def misto(d, texto, x, y, larg, tam, alinhar="esq", auto=0, entre=1.16, cor=TEXTO, medir=False):
    """Escreve texto com destaques. Parágrafos separados por \n\n. Devolve o y final."""
    fr, fb = fonte("regular", tam), fonte("bold", tam)
    esp = d.textlength(" ", font=fr)
    for k, par in enumerate(texto.split("\n\n")):
        if k:
            y += int(tam * 0.9)
        for linha, lw in _linhas(d, _tokens(par, auto), tam, larg):
            xx = x + (larg - lw) / 2 if alinhar == "centro" else x
            for w, b, tw in linha:
                if not medir:
                    d.text((xx, y), w, font=fb if b else fr, fill=cor)
                xx += tw + esp
            y += int(tam * entre)
    return y


def _cabe(d, texto, larg, tmax, tmin, altura, auto=0, entre=1.16):
    for t in range(tmax, tmin - 1, -2):
        if misto(d, texto, 0, 0, larg, t, auto=auto, entre=entre, medir=True) <= altura:
            return t
    return tmin


# ------------------------------------------------------------------ base
def _fundo():
    img = Image.new("RGB", (W, H), FUNDO)
    grade = Image.new("RGB", (W, H), FUNDO)
    g = ImageDraw.Draw(grade)
    passo = 46
    for x in range(-passo // 2, W, passo):
        g.line([(x, 0), (x, H)], fill=GRADE, width=1)
    for y in range(0, H, passo):
        g.line([(0, y), (W, y)], fill=GRADE, width=1)
    m = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(m)
    for y in range(H):
        t = max(0.0, 1 - y / 560)
        md.line([(0, y), (W, y)], fill=int(255 * t ** 1.4))
    lateral = Image.new("L", (W, 1))
    for x in range(W):
        lateral.putpixel((x, 0), int(255 * max(0.0, min(1.0, min(x, W - x) / 220))))
    m = Image.composite(m, Image.new("L", (W, H), 0), lateral.resize((W, H)))
    return Image.composite(grade, img, m)


def rodape(d, i, n, marca="GNZ01"):
    f = _mono(22)
    partes = [("PAG", SUAVE), ("|", SUAVE)] + [(f"{k:02d}", ATIVO if k == i else (88, 92, 99)) for k in range(1, n + 1)] \
        + [("|", SUAVE), (marca, SUAVE)]
    gap = 22
    total = sum(d.textlength(t, font=f) for t, _ in partes) + gap * (len(partes) - 1) + 30
    x, y = (W - total) / 2, H - 120
    for j, (t, c) in enumerate(partes):
        if t == "|" or (j and partes[j - 1][0] == "|"):
            x += 15
        d.text((x, y), t, font=f, fill=c)
        x += d.textlength(t, font=f) + gap


def _selo(img, x, y, cfg, centro=False):
    """Selo @gnz01_ com monograma (substitui a foto de perfil da referência)."""
    d = ImageDraw.Draw(img)
    r = 30
    nome = "@gnz01_"
    sub = "Soluções digitais  |  WhatsApp " + cfg["whatsapp"]
    f1, f2 = fonte("bold", 30), fonte("regular", 19)
    larg = 2 * r + 16 + max(d.textlength(nome, font=f1), d.textlength(sub, font=f2))
    if centro:
        x = (W - larg) / 2
    d.ellipse([x, y, x + 2 * r, y + 2 * r], fill=TEXTO)
    fm = fonte("bold", 18)
    d.text((x + r - d.textlength("G01", font=fm) / 2, y + r - 12), "G01", font=fm, fill=FUNDO)
    d.text((x + 2 * r + 16, y + 2), nome, font=f1, fill=TEXTO)
    d.text((x + 2 * r + 16, y + 40), sub, font=f2, fill=SUAVE)


def _pilula(img, y):
    d = ImageDraw.Draw(img)
    wq, hq = 300, 68
    x = (W - wq) / 2
    d.rounded_rectangle([x, y, x + wq, y + hq], radius=34, fill=(14, 15, 18), outline=(70, 74, 82), width=2)
    cx = x + 40
    # instagram
    d.rounded_rectangle([cx - 13, y + 21, cx + 13, y + 47], radius=8, outline=TEXTO, width=3)
    d.ellipse([cx - 6, y + 28, cx + 6, y + 40], outline=TEXTO, width=3)
    # whatsapp
    cx += 52
    d.ellipse([cx - 13, y + 21, cx + 13, y + 46], outline=TEXTO, width=3)
    d.polygon([(cx - 14, y + 50), (cx - 8, y + 39), (cx - 2, y + 44)], fill=TEXTO)
    # link
    cx += 52
    d.rounded_rectangle([cx - 15, y + 28, cx + 2, y + 40], radius=6, outline=TEXTO, width=3)
    d.rounded_rectangle([cx - 2, y + 28, cx + 15, y + 40], radius=6, outline=TEXTO, width=3)
    # monograma
    r = 25
    cx = x + wq - 44
    d.ellipse([cx - r, y + 34 - r, cx + r, y + 34 + r], fill=TEXTO)
    fm = fonte("bold", 16)
    d.text((cx - d.textlength("G01", font=fm) / 2, y + 23), "G01", font=fm, fill=FUNDO)


def _salvar(img, destino):
    img = Image.blend(img, Image.effect_noise((W, H), 18).convert("RGB"), 0.018)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=93)
    return destino


# ------------------------------------------------------------------ lâminas
def capa(p, cfg, destino, foto=None, credito=None):
    img = _fundo()
    cena = None
    if not (foto and Path(foto).exists()) and cfg.get("_cena_capa", True):
        try:
            cena = cena_capa(p, cfg)
        except Exception:
            cena = None
    if (foto and Path(foto).exists()) or cena is not None:
        if cena is not None:
            ft = cena
            credito = "Demonstração ilustrativa · nomes fictícios"
        else:
            ft = ImageOps.fit(Image.open(foto).convert("RGB"), (W, H - 360), Image.LANCZOS, centering=(0.5, 0.25))
            ft = Image.blend(ft, Image.new("RGB", ft.size, (10, 10, 12)), 0.25)
        topo_f = 360 if cena is None else H - 640 - 110
        img.paste(ft, (0, topo_f))
        fim = 1060 if cena is None else H - 250
        g = Image.new("L", (1, H))
        for y in range(H):
            t = max(1 - (y - topo_f) / 200 if y >= topo_f else 1, (y - fim) / 200, 0)
            g.putpixel((0, y), int(255 * min(1, t)))
        img = Image.composite(Image.new("RGB", (W, H), FUNDO), img, g.resize((W, H)))
    d = ImageDraw.Draw(img)
    tags = "  ".join((p.get("hashtags") or [])[:2])
    topo = f"©  {date.today().year}    |    {tags}" if tags else f"©  {date.today().year}    |    GNZ01"
    fs = fonte("regular", 24)
    d.text(((W - d.textlength(topo, font=fs)) / 2, 150), topo, font=fs, fill=(200, 203, 208))
    titulo = p.get("titulo_capa") or p["titulo"]
    larg = W - 160
    a = 0 if "**" in titulo else 2
    t = _cabe(d, titulo, larg, 112, 56, 460 if not (foto or cena is not None) else (300 if p.get("subtitulo") else 340), auto=a, entre=1.0)
    y0 = 220 if (foto or cena is not None) else max(230, (H - misto(d, titulo, 0, 0, larg, t, auto=a, entre=1.0, medir=True)) / 2 - 120)
    y = misto(d, titulo, 80, y0, larg, t, alinhar="centro", auto=a, entre=1.0)
    if p.get("subtitulo"):
        misto(d, p["subtitulo"], 80, y + 34, larg, 36, alinhar="centro", cor=(200, 203, 208))
    # aba lateral com seta (convite para arrastar)
    d.rounded_rectangle([W - 70, H / 2 - 90, W + 60, H / 2 + 90], radius=60, fill=(36, 38, 43), outline=(70, 74, 82), width=2)
    d.line([(W - 40, H / 2 - 16), (W - 24, H / 2), (W - 40, H / 2 + 16)], fill=TEXTO, width=5)
    _selo(img, 0, H - 230 if cena is None else H - 140, cfg, centro=True)
    if credito:
        d = ImageDraw.Draw(img)
        d.text((60, H - 46), credito if cena is not None else "Foto: " + credito, font=fonte("regular", 17), fill=SUAVE)
    return _salvar(img, destino)


def lamina(s, i, n, destino, layout):
    img = _fundo()
    d = ImageDraw.Draw(img)
    tit, txt = s.get("titulo", ""), s.get("texto", "")
    at = 0 if "**" in tit else 2
    ax = 0 if "**" in txt else 3
    if layout == "abertura":
        x, larg = 230, 620
        t1 = _cabe(d, tit, larg, 76, 48, 380, auto=at, entre=1.02)
        h1 = misto(d, tit, 0, 0, larg, t1, auto=at, entre=1.02, medir=True)
        h2 = misto(d, txt, 0, 0, larg, 38, auto=ax, entre=1.3, medir=True) if txt else 0
        y = (H - 120 - (h1 + 40 + h2)) / 2 + 30
        y = misto(d, tit, x, y, larg, t1, auto=at, entre=1.02)
        if txt:
            misto(d, txt, x, y + 40, larg, 38, auto=ax, entre=1.3)
    elif layout == "paragrafos":
        x, larg = 150, 780
        corpo = f"**{tit}.**\n\n{txt}" if tit else txt
        t = _cabe(d, corpo, larg, 44, 32, 700, auto=ax, entre=1.32)
        h = misto(d, corpo, 0, 0, larg, t, auto=ax, entre=1.32, medir=True)
        misto(d, corpo, x, (H - 120 - h) / 2 + 20, larg, t, auto=ax, entre=1.32)
    elif layout == "duas_colunas":
        t1 = _cabe(d, tit, 360, 70, 42, 520, auto=at, entre=1.02)
        h1 = misto(d, tit, 0, 0, 360, t1, auto=at, entre=1.02, medir=True)
        misto(d, tit, 90, (H - 120 - h1) / 2 + 10, 360, t1, auto=at, entre=1.02)
        t2 = _cabe(d, txt, 420, 40, 30, 620, auto=ax, entre=1.3)
        h2 = misto(d, txt, 0, 0, 420, t2, auto=ax, entre=1.3, medir=True)
        misto(d, txt, 520, (H - 120 - h2) / 2 + 10, 420, t2, auto=ax, entre=1.3)
    else:  # centro
        larg = 760
        corpo = f"**{tit}**\n\n{txt}" if tit else txt
        t = _cabe(d, corpo, larg, 46, 32, 640, auto=ax, entre=1.3)
        h = misto(d, corpo, 0, 0, larg, t, auto=ax, entre=1.3, medir=True)
        misto(d, corpo, (W - larg) / 2, (H - 120 - h) / 2 + 10, larg, t, alinhar="centro", auto=ax, entre=1.3)
    rodape(d, i, n)
    return _salvar(img, destino)


def cta(texto, i, n, destino, cfg):
    img = _fundo()
    d = ImageDraw.Draw(img)
    larg = 760
    t = _cabe(d, texto, larg, 50, 34, 520, auto=0 if "**" in texto else 3, entre=1.24)
    h = misto(d, texto, 0, 0, larg, t, auto=0 if "**" in texto else 3, entre=1.24, medir=True)
    y = (H - h) / 2 - 120
    y = misto(d, texto, (W - larg) / 2, y, larg, t, alinhar="centro", auto=0 if "**" in texto else 3, entre=1.24)
    _pilula(img, y + 60)
    d = ImageDraw.Draw(img)
    w = "WhatsApp " + cfg["whatsapp"]
    fw = fonte("semi", 26)
    d.text(((W - d.textlength(w, font=fw)) / 2, y + 156), w, font=fw, fill=ATIVO)
    rodape(d, i, n)
    return _salvar(img, destino)


CENARIO_TEMA = {"sites": "escritorio", "paginas": "loja", "agenda": "salao-de-beleza", "cardapio": "restaurante",
                "catalogo": "loja", "marca": "escritorio"}


def foto_capa(p):
    """Foto profissional licenciada para a capa: campo "cenario" do post ou padrão do tema.
    Procura midia/fotos/cenarios/<slug>.jpg e o crédito em creditos.json ("cenarios/<slug>")."""
    import json
    raiz = Path(__file__).resolve().parent.parent
    slug = p.get("cenario") or CENARIO_TEMA.get(p.get("tema", ""))
    f = raiz / f"midia/fotos/cenarios/{slug}.jpg" if slug else None
    if not f or not f.exists():
        return None, None
    cred = json.load(open(raiz / "midia/fotos/creditos.json")).get(f"cenarios/{slug}")
    if not cred:
        return None, None  # sem crédito registrado não publica
    return str(f), cred if isinstance(cred, str) else cred.get("credito") or cred.get("texto")


TIPO_TEMA = {"cardapio": "cardapio", "agenda": "agenda", "catalogo": "catalogo"}
NOME_TIPO = {"cardapio": "Seu Restaurante", "agenda": "Seu Salão", "catalogo": "Sua Loja", "site": "Sua Empresa"}


def cena_capa(p, cfg, tam=(W, 640)):
    """Capa sem foto: cena criada no código (balcão, monitor, celular e tablet com a demonstração do tema).
    Sem pessoas e sem rostos gerados."""
    from src import showcase as sc
    w, h = tam
    tipo = TIPO_TEMA.get(p.get("tema", ""), "site")
    v = dict(p.get("vitrine_capa") or ({"tipo": tipo, "marca": NOME_TIPO[tipo]} if tipo == "site"
                                       else {"tipo": tipo, "nome": NOME_TIPO[tipo]}))
    yb = h - 150
    img = sc._fundo_balcao(w, h, yb)
    larg = 620
    img = sc._monitor(img, (w - larg) // 2 + 40, yb - 100 - int(larg * 0.625), larg, sc.tela_desktop(v))
    if tipo in ("cardapio", "catalogo"):
        img = sc._aparelho(img, sc.tela_tablet(v), w - 290, yb - 250, 200, raio=26, borda=12)
    cel = sc.tela_celular(cfg, v).convert("RGB")
    img = sc._aparelho(img, cel, 110, yb - 190, 210, raio=36, borda=11)
    return img


def carrossel(p, pasta, cfg, foto=None, credito=None):
    """p: {titulo, subtitulo, hashtags, slides:[{titulo, texto, layout?}], cta_final}. Devolve a lista de arquivos."""
    if not foto:
        foto, credito = foto_capa(p)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for velho in pasta.glob("*.jpg"):
        velho.unlink()
    slides = p["slides"]
    n = len(slides) + 2
    arqs = [capa(p, cfg, pasta / "01.jpg", foto, credito)]
    for k, s in enumerate(slides):
        lay = s.get("layout") or LAYOUTS[k % len(LAYOUTS)]
        arqs.append(lamina(s, k + 2, n, pasta / f"{k + 2:02d}.jpg", lay))
    fim = (p.get("cta_final") or "Quer isso no seu negócio?").replace("{whatsapp}", cfg["whatsapp"])
    texto = fim + "\n\nMe chama no WhatsApp ou no direct **para conversarmos.**"
    arqs.append(cta(texto, n, n, pasta / f"{n:02d}.jpg", cfg))
    return arqs
