"""Layout editorial (padrão revista): serifada para frases de impacto, Inter para apoio,
fotografia real opcional (campo "foto": caminho local + "credito"), grão fotográfico sutil."""
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
    caminhos = [peca({**p["capa"], "citacao": True}, pasta / "01.jpg", pagina=f"1/{total}  Arraste →")]
    for i, s in enumerate(p["slides"], 2):
        caminhos.append(peca({"rotulo": s.get("rotulo", ""), "titulo": s["titulo"], "subtitulo": s.get("texto"),
                              "apoio": s.get("apoio", []), "escuro": s.get("escuro", False),
                              "rodape": p["capa"].get("autor", "")}, pasta / f"{i:02d}.jpg", pagina=f"{i}/{total}"))
    return caminhos
