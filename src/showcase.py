"""GNZ01 Product Showcase: peça publicitária de produto (feed 1080x1350 e story 1080x1920).
Topo com título forte, nome do produto e benefício; 3 a 5 funcionalidades com ícones; celular + monitor
mostrando a tela da demonstração; faixa de CTA. Fotografia de cenário opcional (midia/fotos/cenarios/<slug>.jpg).
As telas são demonstrações com nomes fictícios e a peça diz isso."""
import json
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from src.render import fonte, quebrar
from src import vitrine as vt

RAIZ = Path(__file__).resolve().parent.parent
PRATA = (196, 200, 206)
OFF = (244, 243, 238)
PRETO = (12, 12, 14)
GRAFITE = (36, 38, 43)
ESC = (24, 25, 29)
SUAVE = (110, 114, 120)
CHIP = (232, 231, 225)
VERDE = (37, 211, 102)


# ------------------------------------------------------------------ telas
def tela_celular(cfg, v):
    """Renderiza a tela do celular da vitrine (sem a notificação) e devolve só o aparelho."""
    original = vt._notificacao
    vt._notificacao = lambda *a, **k: None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "s.jpg"
            chaves = ("titulo", "subtitulo", "sigla", "nome", "chips", "notif", "botao", "itens", "total",
                      "produtos", "dominio", "marca", "chamada", "apoio", "servicos", "tom")
            args = {k: (tuple(x) if isinstance(x, list) and k in ("chips", "servicos", "notif", "tom") else x)
                    for k, x in v.items() if k in chaves}
            if v["tipo"] not in ("agenda", "site"):
                args.pop("botao", None)
            if "itens" in args:
                args["itens"] = [tuple(i) for i in args["itens"]]
            if "produtos" in args:
                args["produtos"] = tuple(tuple(i) for i in args["produtos"])
            {"cardapio": vt.story_cardapio, "agenda": vt.story_agenda_manicure,
             "catalogo": vt.story_catalogo, "site": vt.story_site}[v["tipo"]](cfg, dest, **args)
            im = Image.open(dest).convert("RGB").crop((170, 700, 910, 1560))
    finally:
        vt._notificacao = original
    # cantos arredondados transparentes
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=70, fill=255)
    im.putalpha(mask)
    return im


def tela_desktop(v, w=1280, h=800):
    """Versão desktop da mesma demonstração (layout simples e legível)."""
    im = Image.new("RGB", (w, h), (250, 250, 248))
    d = ImageDraw.Draw(im)
    nome = v.get("nome") or v.get("marca") or "Seu Negócio"
    dominio = v.get("dominio") or nome.lower().replace(" ", "") + ".com.br"
    # barra do navegador
    d.rectangle([0, 0, w, 56], fill=(228, 228, 224))
    for i, c in enumerate([(236, 106, 94), (244, 191, 79), (98, 197, 84)]):
        d.ellipse([20 + i * 26, 20, 36 + i * 26, 36], fill=c)
    d.rounded_rectangle([130, 12, w - 130, 44], radius=16, fill=(250, 250, 248))
    fd = fonte("regular", 20)
    d.text((w / 2 - d.textlength(dominio, font=fd) / 2, 17), dominio, font=fd, fill=SUAVE)
    # cabeçalho do site
    d.rectangle([0, 56, w, 140], fill=ESC)
    d.text((48, 80), nome, font=fonte("bold", 34), fill=(255, 255, 255))
    tipo = v["tipo"]
    menu = {"cardapio": ["Cardápio", "Promoções", "Contato"], "agenda": ["Serviços", "Agendar", "Contato"],
            "catalogo": ["Novidades", "Coleção", "Contato"], "site": ["Serviços", "Sobre", "Contato"]}[tipo]
    fm = fonte("semi", 22)
    x = w - 48
    for m in reversed(menu):
        x -= d.textlength(m, font=fm)
        d.text((x, 92), m, font=fm, fill=(210, 212, 216))
        x -= 40
    y0 = 172
    if tipo in ("cardapio", "catalogo"):
        cats = list(v.get("chips") or ["Destaques", "Mais pedidos", "Bebidas"])
        for i, c in enumerate(cats):
            d.rounded_rectangle([48, y0 + i * 64, 300, y0 + i * 64 + 50], radius=25, fill=ESC if i == 0 else CHIP)
            d.text((74, y0 + i * 64 + 12), c, font=fonte("semi", 22), fill=(255, 255, 255) if i == 0 else ESC)
        padrao = {"cardapio": [("Burger da Casa", "", "R$ 32,90"), ("Batata Rústica", "", "R$ 21,00"), ("Smash Duplo", "", "R$ 36,50")],
                  "catalogo": [("Vestido Linho", "", "R$ 189,90"), ("Blusa Seda", "", "R$ 119,90"),
                               ("Calça Alfaiataria", "", "R$ 159,90"), ("Camisa Off", "", "R$ 99,90")]}[tipo]
        itens = v.get("itens") or [(n, "", p) for n, p in (v.get("produtos") or [])] or padrao
        itens = list(itens)[:6] or [("Produto", "", "R$ 0,00")]
        while len(itens) < 6:
            itens += itens[:6 - len(itens)]
        cw, chh = (w - 360 - 48 - 2 * 24) / 3, 270
        tons = [(214, 168, 108), (201, 190, 172), (176, 181, 186), (150, 140, 128)]
        for i, it in enumerate(itens[:6]):
            cx, cy = 340 + (i % 3) * (cw + 24), y0 + (i // 3) * (chh + 24)
            d.rounded_rectangle([cx, cy, cx + cw, cy + chh], radius=18, fill=(255, 255, 255), outline=(226, 226, 222))
            d.rounded_rectangle([cx + 14, cy + 14, cx + cw - 14, cy + 150], radius=14, fill=tons[i % 4])
            d.text((cx + 18, cy + 166), it[0], font=fonte("bold", 24), fill=ESC)
            d.text((cx + 18, cy + 206), it[-1], font=fonte("semi", 22), fill=SUAVE)
            d.ellipse([cx + cw - 58, cy + 196, cx + cw - 18, cy + 236], fill=ESC)
            d.text((cx + cw - 46, cy + 196), "+", font=fonte("bold", 30), fill=(255, 255, 255))
    elif tipo == "agenda":
        d.text((48, y0), "Escolha o dia", font=fonte("bold", 28), fill=ESC)
        for i in range(7):
            for j in range(5):
                cx, cy = 48 + i * 82, y0 + 54 + j * 70
                num = j * 7 + i + 1
                if num > 30:
                    continue
                sel = num == 14
                d.rounded_rectangle([cx, cy, cx + 70, cy + 58], radius=12, fill=ESC if sel else CHIP)
                t = str(num)
                ft = fonte("semi", 22)
                d.text((cx + 35 - d.textlength(t, font=ft) / 2, cy + 16), t, font=ft, fill=(255, 255, 255) if sel else ESC)
        d.text((700, y0), "Horários livres · Sex 14", font=fonte("bold", 28), fill=ESC)
        for i, hh in enumerate(["09:00", "10:30", "13:00", "14:30", "16:00", "17:30"]):
            cx, cy = 700 + (i % 2) * 260, y0 + 54 + (i // 2) * 84
            sel = hh == "14:30"
            d.rounded_rectangle([cx, cy, cx + 240, cy + 68], radius=14, fill=ESC if sel else CHIP)
            d.text((cx + 84, cy + 20), hh, font=fonte("semi", 24), fill=(255, 255, 255) if sel else ESC)
        d.rounded_rectangle([700, y0 + 330, 1200, y0 + 400], radius=35, fill=ESC)
        d.text((800, y0 + 350), "Confirmar · Sex 14:30", font=fonte("bold", 24), fill=(255, 255, 255))
    else:  # site
        d.rounded_rectangle([48, y0, w - 48, y0 + 330], radius=24, fill=GRAFITE)
        ch = v.get("chamada", "Seu negócio, do jeito que o cliente procura.")
        fh = fonte("bold", 46)
        yy = y0 + 50
        for l in quebrar(d, ch, fh, 620):
            d.text((96, yy), l, font=fh, fill=(255, 255, 255))
            yy += 56
        d.text((96, yy + 14), v.get("apoio", ""), font=fonte("regular", 22), fill=(190, 194, 200))
        bt = v.get("botao", "Fale pelo WhatsApp")
        fb = fonte("bold", 24)
        d.rounded_rectangle([96, y0 + 250, 96 + d.textlength(bt, font=fb) + 60, y0 + 300], radius=25, fill=VERDE)
        d.text((126, y0 + 260), bt, font=fb, fill=(255, 255, 255))
        d.rounded_rectangle([w - 460, y0 + 40, w - 96, y0 + 290], radius=18, fill=tuple(v.get("tom", (176, 181, 186))))
        for i, s in enumerate(list(v.get("servicos", ["Serviço 1", "Serviço 2", "Serviço 3"]))[:3]):
            cx = 48 + i * ((w - 96 - 48) / 3 + 24)
            d.rounded_rectangle([cx, y0 + 360, cx + (w - 96 - 48) / 3, y0 + 520], radius=18, fill=CHIP)
            d.text((cx + 28, y0 + 460), s, font=fonte("semi", 26), fill=ESC)
    return im


# ------------------------------------------------------------------ ícones
def _icone(d, nome, cx, cy, r, cor):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=cor, width=3)
    s = r * 0.5
    if nome == "menu":
        for k in (-1, 0, 1):
            d.line([(cx - s, cy + k * s * 0.6), (cx + s, cy + k * s * 0.6)], fill=cor, width=4)
    elif nome == "whatsapp":
        d.ellipse([cx - s, cy - s, cx + s, cy + s * 0.9], outline=cor, width=4)
        d.polygon([(cx - s * 0.9, cy + s * 1.1), (cx - s * 0.4, cy + s * 0.5), (cx - s * 0.1, cy + s * 0.8)], fill=cor)
    elif nome == "celular":
        d.rounded_rectangle([cx - s * 0.6, cy - s, cx + s * 0.6, cy + s], radius=6, outline=cor, width=4)
        d.line([(cx - s * 0.2, cy + s * 0.7), (cx + s * 0.2, cy + s * 0.7)], fill=cor, width=3)
    elif nome == "calendario":
        d.rounded_rectangle([cx - s, cy - s * 0.8, cx + s, cy + s], radius=5, outline=cor, width=4)
        d.line([(cx - s, cy - s * 0.3), (cx + s, cy - s * 0.3)], fill=cor, width=4)
        d.ellipse([cx - 4, cy + s * 0.2, cx + 4, cy + s * 0.2 + 8], fill=cor)
    elif nome == "relogio":
        d.ellipse([cx - s, cy - s, cx + s, cy + s], outline=cor, width=4)
        d.line([(cx, cy), (cx, cy - s * 0.6)], fill=cor, width=4)
        d.line([(cx, cy), (cx + s * 0.5, cy)], fill=cor, width=4)
    elif nome == "link":
        d.rounded_rectangle([cx - s, cy - s * 0.35, cx + s * 0.2, cy + s * 0.35], radius=10, outline=cor, width=4)
        d.rounded_rectangle([cx - s * 0.2, cy - s * 0.35, cx + s, cy + s * 0.35], radius=10, outline=cor, width=4)
    elif nome == "busca":
        d.ellipse([cx - s, cy - s, cx + s * 0.4, cy + s * 0.4], outline=cor, width=4)
        d.line([(cx + s * 0.25, cy + s * 0.25), (cx + s, cy + s)], fill=cor, width=5)
    elif nome == "grade":
        for i in (-1, 1):
            for j in (-1, 1):
                d.rounded_rectangle([cx + i * s * 0.55 - s * 0.4, cy + j * s * 0.55 - s * 0.4,
                                     cx + i * s * 0.55 + s * 0.4, cy + j * s * 0.55 + s * 0.4], radius=3, outline=cor, width=3)
    else:  # check
        d.line([(cx - s * 0.7, cy), (cx - s * 0.15, cy + s * 0.55), (cx + s * 0.8, cy - s * 0.6)], fill=cor, width=5)


# ------------------------------------------------------------------ composição
def _fundo(tam, cenario):
    w, h = tam
    if cenario and Path(cenario).exists():
        im = ImageOps.fit(Image.open(cenario).convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.5))
        im = ImageOps.grayscale(im).convert("RGB")
        im = Image.blend(im, Image.new("RGB", (w, h), (18, 19, 22)), 0.45)
    else:
        im = Image.new("RGB", (w, h), (20, 21, 25))
        luz = Image.new("L", (w, h), 0)
        ImageDraw.Draw(luz).ellipse([w * 0.1, h * 0.35, w * 1.1, h * 1.05], fill=90)
        luz = luz.filter(ImageFilter.GaussianBlur(160))
        im = Image.composite(Image.new("RGB", (w, h), (70, 74, 82)), im, luz)
    # topo escuro para o título
    g = Image.new("L", (1, h))
    for y in range(h):
        t = max(0.0, 1 - y / (h * 0.5))
        g.putpixel((0, y), int(250 * t ** 0.9))
    return Image.composite(Image.new("RGB", (w, h), PRETO), im, g.resize((w, h)))


def _sombra(base, caixa, raio=40, blur=30, opac=170):
    sh = Image.new("L", base.size, 0)
    x0, y0, x1, y1 = caixa
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 14, y0 + 24, x1 + 14, y1 + 24], radius=raio, fill=opac)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    return Image.composite(Image.new("RGB", base.size, (0, 0, 0)), base, sh)


def _monitor(base, x, y, larg, tela):
    alt = int(larg * 0.625)
    base = _sombra(base, (x, y, x + larg, y + alt + 20), raio=20)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([x, y, x + larg, y + alt + 20], radius=20, fill=(14, 14, 16))
    base.paste(tela.resize((larg - 28, alt - 8), Image.LANCZOS), (x + 14, y + 14))
    # pé
    px = x + larg / 2
    d.polygon([(px - 50, y + alt + 20), (px + 50, y + alt + 20), (px + 70, y + alt + 90), (px - 70, y + alt + 90)], fill=(150, 154, 160))
    d.rounded_rectangle([px - 150, y + alt + 86, px + 150, y + alt + 100], radius=7, fill=(170, 174, 180))
    return base


def _titulo(d, texto, x, y, larg, tmax, tmin, cor=(255, 255, 255), max_linhas=3):
    for t in range(tmax, tmin - 1, -2):
        f = fonte("bold", t)
        linhas = quebrar(d, texto.upper(), f, larg)
        if len(linhas) <= max_linhas:
            break
    for l in linhas:
        d.text((x, y), l, font=f, fill=cor)
        y += int(t * 1.02)
    return y


def peca(cfg, s, destino, formato="feed"):
    """s: {tipo, produto, titulo, subtitulo, funcionalidades:[[icone, texto]], beneficio, cta, cenario, vitrine:{...}}"""
    w, h = (1080, 1350) if formato == "feed" else (1080, 1920)
    m = 72
    img = _fundo((w, h), RAIZ / s["cenario"] if s.get("cenario") else None)
    d = ImageDraw.Draw(img)
    # assinatura GNZ01
    d.text((m, 56), "GNZ01", font=fonte("bold", 34), fill=(255, 255, 255))
    d.text((m + 120, 64), "SOLUÇÕES DIGITAIS", font=fonte("semi", 20), fill=PRATA)
    y = 128 if formato == "feed" else 190
    y = _titulo(d, s["titulo"], m, y, w - 2 * m, 74 if formato == "feed" else 100, 50,
                max_linhas=3 if formato == "feed" else 4)
    y += 26
    # produto (pílula prata) + subtítulo
    fp = fonte("bold", 26)
    pt = s["produto"].upper()
    lp = d.textlength(pt, font=fp)
    d.rounded_rectangle([m, y, m + lp + 44, y + 50], radius=25, fill=PRATA)
    d.text((m + 22, y + 11), pt, font=fp, fill=PRETO)
    y += 66
    fs = fonte("regular", 30 if formato == "feed" else 36)
    for l in quebrar(d, s["subtitulo"], fs, w - 2 * m):
        d.text((m, y), l, font=fs, fill=(225, 227, 230))
        y += int(fs.size * 1.3)
    y += 14
    # funcionalidades
    ff = fonte("semi", 28 if formato == "feed" else 34)
    r = 24 if formato == "feed" else 30
    funcs = s["funcionalidades"][:5]
    if formato == "feed":
        for icone, texto in funcs[:3]:
            _icone(d, icone, m + r, y + r, r, PRATA)
            d.text((m + 2 * r + 20, y + r - ff.size * 0.62), texto, font=ff, fill=(255, 255, 255))
            y += 2 * r + 16
    else:
        for icone, texto in funcs:
            _icone(d, icone, m + r, y + r, r, PRATA)
            d.text((m + 2 * r + 22, y + r - ff.size * 0.62), texto, font=ff, fill=(255, 255, 255))
            y += 2 * r + 22
    # dispositivos
    faixa = 168 if formato == "feed" else 250
    topo_disp = y + 20
    base_disp = h - faixa - 20
    cel = tela_celular(cfg, s["vitrine"])
    desk = tela_desktop(s["vitrine"])
    if formato == "feed":
        lm = 600
        my = max(topo_disp + 30, base_disp - int(lm * 0.625) - 110)
        img = _monitor(img, w - m - lm + 30, my, lm, desk)
        ch = base_disp - topo_disp + 10
        cw = int(ch * cel.width / cel.height)
        cx, cy = m - 10, topo_disp
    else:
        lm = 760
        my = topo_disp + 60
        img = _monitor(img, w - lm - 30, my, lm, desk)
        ch = base_disp - topo_disp + 10
        cw = int(ch * cel.width / cel.height)
        cx, cy = m - 10, topo_disp
    celr = cel.resize((cw, ch), Image.LANCZOS)
    img = _sombra(img, (cx, cy, cx + cw, cy + ch), raio=60, blur=36, opac=200)
    img.paste(celr, (cx, cy), celr)
    d = ImageDraw.Draw(img)
    # selo de demonstração
    fn = fonte("regular", 20)
    nota = "Demonstração ilustrativa · nomes fictícios"
    # faixa CTA
    d.rectangle([0, h - faixa, w, h], fill=OFF)
    fb = fonte("bold", 28 if formato == "feed" else 34)
    d.text((m, h - faixa + 22), s["beneficio"], font=fonte("semi", 22 if formato == "feed" else 28), fill=SUAVE)
    cta = s["cta"].replace("{whatsapp}", cfg["whatsapp"])
    d.text((m, h - faixa + (58 if formato == "feed" else 70)), cta, font=fb, fill=ESC)
    seta = "→"
    d.text((w - m - 30, h - faixa + (54 if formato == "feed" else 66)), seta, font=fonte("bold", 40), fill=ESC)
    rod = "@gnz01_ · " + nota if formato == "story" else nota
    d.text((m, h - (40 if formato == "feed" else 64)), rod, font=fn, fill=SUAVE)
    img = Image.blend(img, Image.effect_noise((w, h), 16).convert("RGB"), 0.025)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=93)
    return destino


PADROES = {
    "cardapio": {"produto": "Cardápio digital", "titulo": "Seu restaurante mais organizado. Seus pedidos mais simples.",
                 "funcionalidades": [["menu", "Cardápio com fotos, opções e preços"], ["whatsapp", "Pedido pronto no seu WhatsApp"],
                                     ["link", "Um link para bio, Google e status"], ["celular", "Funciona no celular e no computador"]],
                 "beneficio": "Menos áudio, menos erro, mais pedidos organizados.", "cenario": "cozinha-profissional"},
    "agenda": {"produto": "Agenda online", "titulo": "Facilite a agenda. Melhore a experiência do seu cliente.",
               "funcionalidades": [["calendario", "Cliente escolhe dia e serviço"], ["relogio", "Só aparecem horários livres"],
                                   ["link", "Link de agendamento na bio"], ["celular", "Funciona no celular e no computador"]],
               "beneficio": "Menos mensagem para marcar horário, mais tempo para atender.", "cenario": "barbearia"},
    "catalogo": {"produto": "Catálogo digital", "titulo": "Seus produtos apresentados de forma profissional.",
                 "funcionalidades": [["grade", "Produtos organizados por categoria"], ["whatsapp", "Pedido ou orçamento pelo WhatsApp"],
                                     ["link", "Um link para enviar a qualquer cliente"], ["celular", "Funciona no celular e no computador"]],
                 "beneficio": "Seu cliente vê tudo, escolhe e chama você pronto para comprar.", "cenario": "loja"},
    "site": {"produto": "Site profissional", "titulo": "Sua empresa merece uma presença digital à altura.",
             "funcionalidades": [["busca", "Estrutura pensada para ser encontrado"], ["whatsapp", "Botão direto para o WhatsApp"],
                                 ["celular", "Versão mobile e desktop"], ["check", "Serviços, endereço e horários"]],
             "beneficio": "Mais credibilidade para quem pesquisa antes de chamar.", "cenario": "escritorio"},
}


def vitrine_showcase(cfg, v, destino, formato="feed"):
    """Peça de produto a partir de uma vitrine. Campos opcionais em v.get('showcase') sobrescrevem os padrões."""
    p = dict(PADROES[v["tipo"]])
    p.update(v.get("showcase", {}))
    cen = p.get("cenario")
    caminho = RAIZ / f"midia/fotos/cenarios/{cen}.jpg" if cen else None
    s = {**p, "subtitulo": p.get("subtitulo") or v.get("subtitulo", ""), "cta": p.get("cta", "Peça o seu: WhatsApp {whatsapp}"),
         "cenario": str(caminho.relative_to(RAIZ)) if caminho and caminho.exists() else None, "vitrine": v}
    return peca(cfg, s, destino, formato)
