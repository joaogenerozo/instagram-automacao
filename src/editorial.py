"""Layout editorial (padrão revista): serifada para frases de impacto, Inter para apoio,
fotografia real opcional (campo "foto": caminho local + "credito"), grão fotográfico sutil."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from src.render import W, H, MARGEM, fonte, quebrar, hex_rgb

FONTES = Path(__file__).resolve().parent.parent / "fonts"
PAPEL, PAPEL2 = (244, 243, 238), (236, 234, 227)
TINTA, TINTA_SUAVE = (24, 25, 29), (92, 96, 104)
NOITE, NOITE2 = (24, 25, 29), (30, 33, 38)


def serif(peso, tam):
    arq = {"regular": "Caladea-Regular.ttf", "bold": "Caladea-Bold.ttf",
           "italic": "Caladea-Italic.ttf", "bolditalic": "Caladea-BoldItalic.ttf"}[peso]
    return ImageFont.truetype(str(FONTES / arq), tam)


def _bloco_serif(draw, texto, peso, tmax, tmin, larg, alt_max, entre=1.12):
    for t in range(tmax, tmin - 1, -2):
        f = serif(peso, t)
        linhas = quebrar(draw, texto, f, larg)
        if len(linhas) * t * entre <= alt_max:
            return f, linhas, t
    f = serif(peso, tmin)
    return f, quebrar(draw, texto, f, larg), tmin


def _escrever(draw, x, y, linhas, f, tam, cor, entre=1.12):
    for l in linhas:
        draw.text((x, y), l, font=f, fill=cor)
        y += int(tam * entre)
    return y


def _fundo(escuro):
    a, b = (NOITE, NOITE2) if escuro else (PAPEL, PAPEL2)
    img = Image.new("RGB", (W, H), a)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
    return img


def _foto(caminho, gradiente=True):
    """Foto real em tela cheia, recorte central 4:5, cor suave e degradê escuro embaixo."""
    im = ImageOps.fit(Image.open(caminho).convert("RGB"), (W, H), Image.LANCZOS, centering=(0.5, 0.35))
    im = Image.blend(im, Image.new("RGB", (W, H), (28, 28, 30)), 0.08)  # tira o excesso de contraste
    if gradiente:
        g = Image.new("L", (1, H))
        for y in range(H):
            t = max(0, (y - H * 0.36) / (H * 0.64))
            topo = max(0, (260 - y) / 260)  # sombra no topo para o cabeçalho
            g.putpixel((0, y), int(max(248 * t ** 1.1, 150 * topo)))
        g = g.resize((W, H))
        im = Image.composite(Image.new("RGB", (W, H), (14, 14, 16)), im, g)
    return im


def _cabecalho(draw, rotulo, cor, cor_linha):
    f = fonte("semi", 24)
    draw.text((MARGEM, 84), rotulo.upper(), font=f, fill=cor)
    m = "GNZ01"
    draw.text((W - MARGEM - draw.textlength(m, font=f), 84), m, font=f, fill=cor)
    draw.line([(MARGEM, 128), (W - MARGEM, 128)], fill=cor_linha, width=2)


def _rodape(draw, esquerda, direita, cor, cor_linha):
    f = fonte("regular", 24)
    draw.line([(MARGEM, H - 120), (W - MARGEM, H - 120)], fill=cor_linha, width=2)
    draw.text((MARGEM, H - 96), esquerda, font=f, fill=cor)
    draw.text((W - MARGEM - draw.textlength(direita, font=f), H - 96), direita, font=f, fill=cor)


def peca(p, destino, pagina=None):
    """Post editorial. Campos: rotulo, titulo (serifada), subtitulo, apoio (lista), escuro, foto, credito,
    citacao (bool: título em itálico com aspas), autor, fonte_citacao."""
    larg = W - 2 * MARGEM
    if p.get("foto"):
        img = _foto(p["foto"])
        cor_t, cor_s, cor_l = (250, 249, 245), (214, 214, 210), (120, 120, 120)
    else:
        img = _fundo(p.get("escuro", False))
        if p.get("escuro"):
            cor_t, cor_s, cor_l = (250, 249, 245), (178, 183, 189), (70, 74, 80)
        else:
            cor_t, cor_s, cor_l = TINTA, TINTA_SUAVE, (200, 198, 190)
    draw = ImageDraw.Draw(img)
    _cabecalho(draw, p.get("rotulo", "GNZ01 · Negócios"), cor_s, cor_l)

    citacao = p.get("citacao")
    peso = "italic" if citacao else "bold"
    texto = f"“{p['titulo']}”" if citacao else p["titulo"]
    tem_foto = bool(p.get("foto"))
    area = 420 if tem_foto else 640
    f, linhas, t = _bloco_serif(draw, texto, peso, 112 if not citacao else 84, 52, larg, area)
    alt = int(len(linhas) * t * 1.12)
    apoio = p.get("apoio", [])
    if tem_foto:
        y = H - 210 - alt - (90 if p.get("subtitulo") or p.get("autor") else 0)
    else:
        y = 230 if apoio else max(230, (H - alt) // 2 - 120)
        if citacao and not apoio:
            draw.text((MARGEM - 10, y - 40), "“", font=serif("bold", 260), fill=cor_l)
            y += 150
    y = _escrever(draw, MARGEM, y, linhas, f, t, cor_t) + 26
    if p.get("autor"):
        draw.line([(MARGEM, y + 12), (MARGEM + 60, y + 12)], fill=cor_t, width=3)
        draw.text((MARGEM + 80, y), p["autor"], font=fonte("semi", 32), fill=cor_t)
        if p.get("fonte_citacao"):
            draw.text((MARGEM + 80, y + 44), p["fonte_citacao"], font=fonte("regular", 26), fill=cor_s)
        y += 100
    if p.get("subtitulo"):
        fs = fonte("regular", 36 if apoio or tem_foto else 42)
        for l in quebrar(draw, p["subtitulo"], fs, larg):
            draw.text((MARGEM, y), l, font=fs, fill=cor_s)
            y += int(fs.size * 1.35)
        y += 30
    if apoio and not tem_foto:
        y += 20
        for i, item in enumerate(apoio, 1):
            draw.line([(MARGEM, y), (W - MARGEM, y)], fill=cor_l, width=1)
            draw.text((MARGEM, y + 22), f"{i:02d}", font=serif("italic", 40), fill=cor_s)
            fi = fonte("semi", 34)
            ly = y + 26
            for l in quebrar(draw, item, fi, larg - 110):
                draw.text((MARGEM + 100, ly), l, font=fi, fill=cor_t)
                ly += 44
            y = ly + 22
    esq = p.get("rodape", "@gnz01_ · Soluções digitais")
    if p.get("credito"):
        draw.text((MARGEM, H - 156), p["credito"], font=fonte("regular", 20), fill=cor_s)
    _rodape(draw, esq, pagina or p.get("cta_imagem", "Salve e compartilhe"), cor_s, cor_l)
    img = Image.blend(img, Image.effect_noise((W, H), 18).convert("RGB"), 0.035)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=93)
    return destino


def carrossel(p, pasta):
    """Carrossel editorial: capa (citação) + slides de texto + CTA. slides: [{rotulo, titulo, texto}]."""
    pasta = Path(pasta)
    total = len(p["slides"]) + 1
    capa = p["capa"]
    if capa.get("foto"):
        caminhos = [capa_central(capa["foto"], capa["titulo"], pasta / "01.jpg", autor=capa.get("autor"),
                                 citacao=capa.get("citacao_estilo", True),
                                 fonte_citacao=capa.get("fonte_citacao"), credito=capa.get("credito"),
                                 pagina=f"1/{total}  Arraste →")]
    else:
        caminhos = [peca({**capa, "citacao": True}, pasta / "01.jpg", pagina=f"1/{total}  Arraste →")]
    for i, s in enumerate(p["slides"], 2):
        caminhos.append(peca({"rotulo": s.get("rotulo", ""), "titulo": s["titulo"], "subtitulo": s.get("texto"),
                              "apoio": s.get("apoio", []), "escuro": s.get("escuro", False),
                              "rodape": p["capa"].get("autor", "")}, pasta / f"{i:02d}.jpg", pagina=f"{i}/{total}"))
    return caminhos


# ---------------------------------------------------------------- stories de citação (1080x1920)
SW, SH = 1080, 1920
MARINHO = (16, 22, 36)


def _gradiente(img, ini, cor, forca=250, topo=0):
    w, h = img.size
    g = Image.new("L", (1, h))
    for y in range(h):
        t = max(0, (y - h * ini) / (h * (1 - ini)))
        tp = max(0, (topo - y) / topo) if topo else 0
        g.putpixel((0, y), int(max(forca * t ** 1.15, 160 * tp)))
    return Image.composite(Image.new("RGB", (w, h), cor), img, g.resize((w, h)))


def story_citacao(p, destino):
    return capa_central(p["foto"], p["citacao"], destino, tam=(SW, SH), autor=p["autor"],
                        fonte_citacao=p["fonte_citacao"], credito=p["credito"],
                        reflexao=p.get("reflexao") or p.get("interacao"))


def story_citacao_antigo(p, destino):
    """Story de citação. Campos: foto, credito, citacao (PT), autor, fonte_citacao, reflexao (GNZ01, opcional),
    interacao (opcional), variante "a" (foto em tela cheia, texto embaixo) ou "b" (foto no alto, painel marinho)."""
    var = p.get("variante", "a")
    foto = Image.open(p["foto"]).convert("RGB")
    m = 84
    larg = SW - 2 * m
    if var == "a":
        img = ImageOps.fit(foto, (SW, SH), Image.LANCZOS, centering=(0.5, 0.25))
        img = Image.blend(img, Image.new("RGB", (SW, SH), (20, 20, 22)), 0.06)
        img = _gradiente(img, 0.40, (10, 11, 13), topo=300)
        y_base, cor_t, cor_s = SH - 200, (250, 249, 245), (205, 207, 210)
    else:
        img = Image.new("RGB", (SW, SH), MARINHO)
        alt_foto = int(SH * 0.66)
        ft = ImageOps.fit(foto, (SW, alt_foto), Image.LANCZOS, centering=(0.5, 0.22))
        ft = _gradiente(ft, 0.62, MARINHO, forca=255, topo=260)
        img.paste(ft, (0, 0))
        y_base, cor_t, cor_s = SH - 200, (246, 244, 238), (186, 194, 208)
    d = ImageDraw.Draw(img)
    # cabeçalho
    f = fonte("semi", 26)
    d.text((m, 110), "GNZ01 · DAILY QUOTES", font=f, fill=cor_s)
    d.line([(m, 156), (SW - m, 156)], fill=(150, 152, 158), width=2)
    # blocos de baixo para cima
    blocos = []
    fr = fonte("regular", 22)
    rodape_y = SH - 120
    d.text((m, rodape_y), p["credito"], font=fr, fill=(160, 163, 170))
    d.text((m, rodape_y + 34), "@gnz01_ · Soluções digitais", font=fr, fill=(160, 163, 170))
    y = rodape_y - 40
    if p.get("interacao"):
        fi = fonte("semi", 30)
        linhas = quebrar(d, p["interacao"], fi, larg - 60)
        alt = 30 + len(linhas) * 40 + 24
        y -= alt
        d.rounded_rectangle([(m, y), (SW - m, y + alt)], radius=28, outline=(200, 202, 208), width=2)
        yy = y + 28
        for l in linhas:
            d.text((m + 30, yy), l, font=fi, fill=cor_t); yy += 40
        y -= 40
    if p.get("reflexao"):
        fl = fonte("regular", 30)
        linhas = quebrar(d, p["reflexao"], fl, larg)
        y -= len(linhas) * 42 + 46
        d.text((m, y), "REFLEXÃO GNZ01", font=fonte("semi", 22), fill=cor_s)
        yy = y + 40
        for l in linhas:
            d.text((m, yy), l, font=fl, fill=cor_t); yy += 42
        y -= 50
        d.line([(m, y + 20), (SW - m, y + 20)], fill=(120, 124, 132), width=1)
    # autor
    y -= 90
    d.line([(m, y + 20), (m + 60, y + 20)], fill=cor_t, width=3)
    d.text((m + 80, y), p["autor"].upper(), font=fonte("semi", 34), fill=cor_t)
    d.text((m + 80, y + 46), p["fonte_citacao"], font=fonte("regular", 26), fill=cor_s)
    y -= 40
    # citação
    fq, linhas, t = _bloco_serif(d, f"“{p['citacao']}”", "italic", 80, 50, larg, 520, 1.15)
    alt = int(len(linhas) * t * 1.15)
    _escrever(d, m, y - alt, linhas, fq, t, cor_t, 1.15)
    img = Image.blend(img, Image.effect_noise((SW, SH), 18).convert("RGB"), 0.03)
    destino = Path(destino); destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=93)
    return destino


# ---------------------------------------------------------------- estilo "capa central" (foto cheia + degradê marinho + serifada centralizada)
MARINHO_PROF = (10, 22, 48)


def capa_central(foto, titulo, destino, tam=(1080, 1350), autor=None, fonte_citacao=None, credito=None,
                 pagina=None, citacao=True, reflexao=None):
    """Foto real em tela cheia, degradê azul-marinho embaixo, frase em serifada caixa alta centralizada,
    assinatura GNZ01 centralizada. Serve para capa de carrossel (1080x1350) e story (1080x1920)."""
    w, h = tam
    if h > 1350:  # story: foto ocupa ~70% de cima, o resto é marinho
        hf = int(h * 0.70)
        img = Image.new("RGB", (w, h), MARINHO_PROF)
        img.paste(ImageOps.fit(Image.open(foto).convert("RGB"), (w, hf), Image.LANCZOS, centering=(0.5, 0.2)), (0, 0))
        ini, fim = 0.40, 0.70
    else:
        img = ImageOps.fit(Image.open(foto).convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.2))
        ini, fim = 0.38, 1.0
    g = Image.new("L", (1, h))
    for y in range(h):
        t = max(0.0, (y - h * ini) / (h * (fim - ini) / 1.25 if h > 1350 else h * 0.62))
        g.putpixel((0, y), int(255 * min(1, t * 1.25) ** 1.2))
    img = Image.composite(Image.new("RGB", (w, h), MARINHO_PROF), img, g.resize((w, h)))
    d = ImageDraw.Draw(img)
    m = 70
    larg = w - 2 * m
    texto = (f"“{titulo}”" if citacao else titulo).upper()
    area = 430 if h <= 1350 else 520
    f, linhas, t = _bloco_serif(d, texto, "bold", 72 if h <= 1350 else 78, 40, larg, area, 1.08)
    alt = int(len(linhas) * t * 1.08)
    base = h - (230 if h <= 1350 else 300)
    extra = (100 if autor else 0) + (len(quebrar(d, reflexao, fonte("regular", 30), larg)) * 42 + 40 if reflexao else 0)
    y = base - extra - alt
    for l in linhas:
        d.text(((w - d.textlength(l, font=f)) / 2, y), l, font=f, fill=(255, 255, 255))
        y += int(t * 1.08)
    if autor:
        y += 22
        fa = fonte("semi", 30)
        a = autor.upper()
        d.text(((w - d.textlength(a, font=fa)) / 2, y), a, font=fa, fill=(255, 255, 255))
        if fonte_citacao:
            fs = fonte("regular", 24)
            d.text(((w - d.textlength(fonte_citacao, font=fs)) / 2, y + 42), fonte_citacao, font=fs, fill=(186, 196, 214))
        y += 90
    if reflexao:
        y += 16
        d.line([(w / 2 - 40, y), (w / 2 + 40, y)], fill=(186, 196, 214), width=2)
        y += 22
        fr = fonte("regular", 30)
        for l in quebrar(d, reflexao, fr, larg):
            d.text(((w - d.textlength(l, font=fr)) / 2, y), l, font=fr, fill=(226, 230, 238))
            y += 42
    # assinatura GNZ01 centralizada
    fm = fonte("bold", 40)
    yl = h - (150 if h <= 1350 else 210)
    d.text(((w - d.textlength("GNZ01", font=fm)) / 2, yl), "GNZ01", font=fm, fill=(255, 255, 255))
    rod = []
    if credito:
        rod.append(credito)
    if pagina:
        rod.append(pagina)
    if rod:
        fc = fonte("regular", 19)
        tx = "  ·  ".join(rod)
        d.text(((w - d.textlength(tx, font=fc)) / 2, h - 60), tx, font=fc, fill=(150, 162, 186))
    img = Image.blend(img, Image.effect_noise((w, h), 16).convert("RGB"), 0.025)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=93)
    return destino


def render_editorial(arte, pasta):
    """Post editorial. Com foto de cenário licenciada (campo cenario -> midia/fotos/cenarios/<slug>.jpg) usa a capa central
    (foto + degradê marinho + serifada caixa alta); sem foto, o layout tipográfico."""
    pasta = Path(pasta)
    raiz = Path(__file__).resolve().parent.parent
    if arte.get("personalidade") and arte["tipo"] == "carrossel":
        from src import ensinamentos as en
        slug = arte.get("slug_foto") or arte["personalidade"].lower().replace(" ", "-")
        fotos = en.fotos_de(slug, raiz)
        if len(fotos) >= 4:  # uma foto diferente por lâmina (pedido do João); com menos, capa central
            return en.carrossel(arte, fotos, pasta)
    cen = arte.get("cenario")
    foto = raiz / f"midia/fotos/cenarios/{cen}.jpg" if cen else None
    if foto and foto.exists() and not arte.get("capa", {}).get("foto"):
        cred = json.load(open(raiz / "midia/fotos/creditos.json")).get(f"cenarios/{cen}", {}).get("credito")
        if arte["tipo"] == "carrossel":
            arte = {**arte, "capa": {**arte["capa"], "foto": str(foto), "credito": cred, "citacao_estilo": False}}
        else:
            return [capa_central(foto, arte["titulo"], pasta / "01.jpg", credito=cred, citacao=False,
                                 reflexao=arte.get("subtitulo"))]
    if arte["tipo"] == "carrossel":
        return carrossel(arte, pasta)
    return [peca(arte, pasta / "01.jpg")]
