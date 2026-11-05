"""Carrossel "Os ensinamentos de" (referência enviada pelo João, 05/11): uma foto real diferente da personalidade em
cada lâmina, layouts alternados (capa com nome gigante, foto com título dourado, painel bordô, cartão bege, título
duas cores), paleta marinho/bordô/dourado. Só fotos licenciadas, com crédito em cada lâmina."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from src.render import fonte, quebrar
from src.editorial import serif

W, H = 1080, 1350
M = 72
MARINHO = (8, 18, 40)
BORDO = (78, 18, 24)
DOURADO = (204, 168, 104)
BEGE = (206, 170, 118)
BRANCO = (248, 246, 240)
SUAVE = (200, 204, 214)


def _foto(caminho, tam, centro=(0.5, 0.3)):
    return ImageOps.fit(Image.open(caminho).convert("RGB"), tam, Image.LANCZOS, centering=centro)


def _degrade(img, ini, cor, forca=255, topo=0):
    w, h = img.size
    g = Image.new("L", (1, h))
    for y in range(h):
        t = max(0.0, (y - h * ini) / (h * (1 - ini)))
        tp = max(0.0, (topo - y) / topo) if topo else 0
        g.putpixel((0, y), int(max(forca * min(1, t * 1.3) ** 1.1, 170 * tp)))
    return Image.composite(Image.new("RGB", (w, h), cor), img, g.resize((w, h)))


def _texto(d, x, y, texto, f, cor, larg, entre=1.3, alinhar="esq"):
    for l in quebrar(d, texto, f, larg):
        lx = x if alinhar == "esq" else x + larg - d.textlength(l, font=f)
        d.text((lx, y), l, font=f, fill=cor)
        y += int(f.size * entre)
    return y


def _caber(d, texto, peso, tmax, tmin, larg, linhas_max, caixa_alta=False):
    t = texto.upper() if caixa_alta else texto
    for tam in range(tmax, tmin - 1, -2):
        f = fonte(peso, tam)
        if len(quebrar(d, t, f, larg)) <= linhas_max:
            return f, t
    return fonte(peso, tmin), t


def _rodape(d, credito, pagina, cor=(170, 176, 190)):
    f = fonte("regular", 18)
    if credito:
        d.text((M, H - 44), credito, font=f, fill=cor)
    if pagina:
        d.text((W - M - d.textlength(pagina, font=f), H - 44), pagina, font=f, fill=cor)
    fm = fonte("bold", 26)
    d.text((W - M - d.textlength("GNZ01", font=fm), 52), "GNZ01", font=fm, fill=BRANCO)


def _grao(img):
    return Image.blend(img, Image.effect_noise(img.size, 18).convert("RGB"), 0.03)


def capa(foto, nome, papel, credito, pagina, destino, prefixo="OS ENSINAMENTOS DE"):
    img = _degrade(_foto(foto, (W, H), (0.5, 0.25)), 0.42, MARINHO, topo=220)
    d = ImageDraw.Draw(img)
    # arco fino dourado atrás da cabeça
    d.arc([W * 0.12, 120, W * 1.05, 1050], start=200, end=340, fill=DOURADO, width=3)
    y = H - 600
    d.text((M, y), prefixo, font=fonte("semi", 34), fill=BRANCO)
    y += 52
    partes = nome.upper().split()
    for p in partes:
        f, _ = _caber(d, p, "bold", 190, 90, W - 2 * M, 1)
        d.text((M - 6, y), p, font=f, fill=BRANCO)
        y += int(f.size * 0.98)
    d.text((M, y + 10), papel.upper(), font=fonte("semi", 32), fill=SUAVE)
    _rodape(d, credito, pagina)
    return _salvar(img, destino)


def foto_titulo_dourado(foto, titulo, texto, credito, pagina, destino):
    img = _degrade(_foto(foto, (W, H), (0.5, 0.2)), 0.38, MARINHO, topo=200)
    d = ImageDraw.Draw(img)
    larg = W - 2 * M
    ft = serif("bold", 74)
    linhas = quebrar(d, titulo, ft, larg)
    corpo = fonte("regular", 36)
    alt_c = len(quebrar(d, texto, corpo, larg)) * int(36 * 1.35)
    y = H - 120 - alt_c - len(linhas) * 80 - 30
    for l in linhas:
        d.text((M, y), l, font=ft, fill=DOURADO)
        y += 80
    _texto(d, M, y + 26, texto, corpo, BRANCO, larg, 1.35)
    _rodape(d, credito, pagina)
    return _salvar(img, destino)


def painel_bordo(foto, titulo, texto, credito, pagina, destino):
    img = Image.new("RGB", (W, H), BORDO)
    d = ImageDraw.Draw(img)
    # textura sutil
    tex = Image.effect_noise((W, H), 40).convert("L").filter(ImageFilter.GaussianBlur(2))
    img = Image.composite(Image.new("RGB", (W, H), (96, 26, 32)), img, tex.point(lambda v: 60 if v > 150 else 0))
    # foto à esquerda, em baixo, com degradê lateral para o bordô
    fw, fh = 620, 760
    ft = _foto(foto, (fw, fh), (0.5, 0.25))
    g = Image.new("L", (fw, 1))
    for x in range(fw):
        g.putpixel((x, 0), int(255 * max(0, (x - fw * 0.6) / (fw * 0.4)) ** 1.2))
    ft = Image.composite(Image.new("RGB", (fw, fh), BORDO), ft, g.resize((fw, fh)))
    g2 = Image.new("L", (1, fh))
    for y in range(fh):
        g2.putpixel((0, y), int(255 * max(0, (y - fh * 0.75) / (fh * 0.25))))
    ft = Image.composite(Image.new("RGB", (fw, fh), (40, 10, 14)), ft, g2.resize((fw, fh)))
    img.paste(ft, (0, H - fh))
    d = ImageDraw.Draw(img)
    x0 = 500
    f, t = _caber(d, titulo, "semi", 84, 50, W - x0 - M, 3, caixa_alta=True)
    y = 110
    for l in quebrar(d, t, f, W - x0 - M):
        d.text((x0, y), l, font=f, fill=BRANCO)
        y += int(f.size * 1.05)
    y = _texto(d, x0, y + 50, texto, fonte("regular", 34), BRANCO, W - x0 - M, 1.38) + 40
    d.line([(x0 - 30, 0), (x0 - 30, y)], fill=DOURADO, width=2)
    d.line([(x0 - 30, y), (W, y)], fill=DOURADO, width=2)
    _rodape(d, credito, pagina, (210, 170, 170))
    return _salvar(img, destino)


def cartao_bege(foto, titulo, texto, credito, pagina, destino):
    img = Image.new("RGB", (W, H), BORDO)
    d = ImageDraw.Draw(img)
    fx0, fy0, fx1, fy1 = 40, 40, W - 40, 820
    ft = _foto(foto, (fx1 - fx0, fy1 - fy0), (0.5, 0.3))
    mask = Image.new("L", ft.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ft.width - 1, ft.height - 1], radius=26, fill=255)
    img.paste(ft, (fx0, fy0), mask)
    d = ImageDraw.Draw(img)
    cx0, cy0, cx1 = 30, 700, W - 170
    larg = cx1 - cx0 - 2 * 46
    f, _ = _caber(d, titulo, "bold", 60, 40, larg, 2)
    lt = quebrar(d, titulo, f, larg)
    corpo = fonte("regular", 34)
    lc = quebrar(d, texto, corpo, larg)
    cy1 = cy0 + 50 + len(lt) * int(f.size * 1.1) + 30 + len(lc) * int(34 * 1.35) + 50
    d.rounded_rectangle([cx0 + 8, cy0 + 12, cx1 + 8, cy1 + 12], radius=18, fill=(50, 10, 14))
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=18, fill=BEGE)
    y = cy0 + 50
    for l in lt:
        d.text((cx0 + 46, y), l, font=f, fill=(60, 16, 20))
        y += int(f.size * 1.1)
    y += 30
    for l in lc:
        d.text((cx0 + 46, y), l, font=corpo, fill=(52, 30, 24))
        y += int(34 * 1.35)
    _rodape(d, credito, pagina, (210, 170, 170))
    return _salvar(img, destino)


def titulo_duas_cores(foto, destaque, resto, texto, credito, pagina, destino):
    img = _degrade(_foto(foto, (W, H), (0.5, 0.2)), 0.40, MARINHO, topo=200)
    d = ImageDraw.Draw(img)
    larg = W - 2 * M
    f = fonte("semi", 76)
    palavras = [(p, DOURADO) for p in destaque.upper().split()] + [(p, BRANCO) for p in resto.upper().split()]
    linhas, atual = [], []
    for p in palavras:
        teste = " ".join(w for w, _ in atual + [p])
        if atual and d.textlength(teste, font=f) > larg:
            linhas.append(atual)
            atual = [p]
        else:
            atual.append(p)
    linhas.append(atual)
    corpo = fonte("regular", 34)
    lc = quebrar(d, texto, corpo, larg - 60)
    y = H - 110 - len(lc) * int(34 * 1.38) - 30 - len(linhas) * 84
    for ln in linhas:
        total = d.textlength(" ".join(w for w, _ in ln), font=f)
        x = W - M - total
        for w, cor in ln:
            d.text((x, y), w, font=f, fill=cor)
            x += d.textlength(w + " ", font=f)
        y += 84
    y += 30
    for l in lc:
        d.text((W - M - d.textlength(l, font=corpo), y), l, font=corpo, fill=BRANCO)
        y += int(34 * 1.38)
    _rodape(d, credito, pagina)
    return _salvar(img, destino)


def citacao(foto, frase, autor, fonte_cit, credito, pagina, destino):
    img = _degrade(_foto(foto, (W, H), (0.5, 0.2)), 0.36, MARINHO, topo=200)
    d = ImageDraw.Draw(img)
    larg = W - 2 * M
    for tam in range(70, 40, -2):
        f = serif("italic", tam)
        lt = quebrar(d, f"“{frase}”", f, larg)
        if len(lt) * tam * 1.15 <= 460:
            break
    y = H - 230 - int(len(lt) * f.size * 1.15)
    d.text((M - 6, y - 150), "“", font=serif("bold", 220), fill=DOURADO)
    for l in lt:
        d.text((M, y), l, font=f, fill=BRANCO)
        y += int(f.size * 1.15)
    d.line([(M, y + 30), (M + 60, y + 30)], fill=DOURADO, width=3)
    d.text((M + 80, y + 14), autor.upper(), font=fonte("semi", 30), fill=DOURADO)
    d.text((M + 80, y + 54), fonte_cit, font=fonte("regular", 24), fill=SUAVE)
    _rodape(d, credito, pagina)
    return _salvar(img, destino)


def cta_final(foto, titulo, texto, credito, pagina, destino):
    img = _degrade(_foto(foto, (W, H), (0.5, 0.2)), 0.30, MARINHO, topo=200)
    d = ImageDraw.Draw(img)
    larg = W - 2 * M
    f, _ = _caber(d, titulo, "bold", 80, 50, larg, 3)
    lt = quebrar(d, titulo, f, larg)
    corpo = fonte("regular", 34)
    lc = quebrar(d, texto, corpo, larg)
    y = H - 260 - len(lc) * int(34 * 1.38) - len(lt) * int(f.size * 1.05)
    for l in lt:
        d.text(((W - d.textlength(l, font=f)) / 2, y), l, font=f, fill=BRANCO)
        y += int(f.size * 1.05)
    y += 24
    for l in lc:
        d.text(((W - d.textlength(l, font=corpo)) / 2, y), l, font=corpo, fill=SUAVE)
        y += int(34 * 1.38)
    fb = fonte("bold", 32)
    b = "Fale com a GNZ01"
    lb = d.textlength(b, font=fb)
    d.rounded_rectangle([(W - lb) / 2 - 44, y + 30, (W + lb) / 2 + 44, y + 110], radius=40, fill=DOURADO)
    d.text(((W - lb) / 2, y + 50), b, font=fb, fill=MARINHO)
    _rodape(d, credito, pagina)
    return _salvar(img, destino)


def _salvar(img, destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    _grao(img).save(destino, "JPEG", quality=93)
    return destino


LAYOUTS = [foto_titulo_dourado, painel_bordo, cartao_bege, titulo_duas_cores]


def carrossel(p, fotos, pasta):
    """p: dict do post (personalidade, papel, capa{titulo,...}, slides[{titulo, texto}]).
    fotos: lista de (caminho, credito). Cada lâmina usa uma foto diferente (repete só se faltar foto)."""
    pasta = Path(pasta)
    for velho in pasta.glob("*.jpg"):
        velho.unlink()
    total = len(p["slides"]) + 2
    f = lambda i: fotos[i % len(fotos)]
    caminhos = [capa(f(0)[0], p["personalidade"], p.get("papel", ""), f(0)[1], f"1/{total}  Arraste →", pasta / "01.jpg")]
    caminhos.append(citacao(f(1)[0], p["capa"]["titulo"], p["personalidade"], p["capa"].get("fonte_citacao", ""),
                            f(1)[1], f"2/{total}", pasta / "02.jpg"))
    for i, s in enumerate(p["slides"], 2):
        if "ilustrativa" in s.get("rotulo", "").lower():
            s = {**s, "texto": "Situação ilustrativa. " + s["texto"]}
        foto, cred = f(i)
        pag = f"{i + 1}/{total}"
        dest = pasta / f"{i + 1:02d}.jpg"
        if i == len(p["slides"]) + 1:
            caminhos.append(cta_final(foto, s["titulo"], s["texto"], cred, pag, dest))
            continue
        lay = LAYOUTS[(i - 2) % len(LAYOUTS)]
        if lay is titulo_duas_cores:
            pal = s["titulo"].split()
            k = max(1, len(pal) // 3)
            caminhos.append(lay(foto, " ".join(pal[:k]), " ".join(pal[k:]), s["texto"], cred, pag, dest))
        else:
            caminhos.append(lay(foto, s["titulo"], s["texto"], cred, pag, dest))
    return caminhos


def fotos_de(slug, raiz):
    """Fotos licenciadas da pessoa: midia/fotos/<slug>/NN.jpg com crédito em creditos.json["<slug>/NN"]."""
    import json
    cred = json.load(open(raiz / "midia/fotos/creditos.json"))
    pasta = raiz / "midia/fotos" / slug
    return [(str(f), cred[f"{slug}/{f.stem}"]["credito"]) for f in sorted(pasta.glob("*.jpg"))
            if f"{slug}/{f.stem}" in cred] if pasta.exists() else []
