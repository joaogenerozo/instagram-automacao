"""Stories de vitrine: mostram um serviço funcionando dentro de um celular (demonstração)."""
from pathlib import Path
from PIL import Image, ImageDraw

from src.render import fonte, hex_rgb, bloco, escrever, MARGEM

SW, SH = 1080, 1920
CREME = (251, 250, 247)
CINZA_CHIP = (232, 231, 225)
ESCURO = (24, 25, 29)
SUAVE_ESC = (110, 114, 120)


def _fundo(cfg):
    c = cfg["cores"]
    f1, f2 = hex_rgb(c["fundo"]), hex_rgb(c["fundo2"])
    img = Image.new("RGB", (SW, SH), f1)
    d = ImageDraw.Draw(img)
    for y in range(SH):
        t = y / SH
        d.line([(0, y), (SW, y)], fill=tuple(int(f1[i] * (1 - t) + f2[i] * t) for i in range(3)))
    return img, ImageDraw.Draw(img)


def _topo(draw, cfg, rotulo, titulo, subtitulo):
    f = fonte("semi", 32)
    lr = draw.textlength(rotulo, font=f)
    draw.rounded_rectangle([MARGEM, 230, MARGEM + lr + 56, 294], radius=32, fill=(48, 52, 59))
    draw.text((MARGEM + 28, 243), rotulo, font=f, fill=(255, 255, 255))
    larg = SW - 2 * MARGEM
    ft, lt, tt, at = bloco(draw, titulo, "bold", 78, 54, larg, 200)
    y = escrever(draw, MARGEM, 330, lt, ft, tt, (255, 255, 255)) + 14
    fs, ls, ts, as_ = bloco(draw, subtitulo, "regular", 38, 30, larg, 110, 1.3)
    escrever(draw, MARGEM, y, ls, fs, ts, hex_rgb(cfg["cores"]["texto_suave"]), 1.3)


def _celular(draw, x, y, w, h):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=70, fill=(10, 10, 12))
    draw.rounded_rectangle([x + 16, y + 16, x + w - 16, y + h - 16], radius=56, fill=CREME)
    draw.rounded_rectangle([x + w / 2 - 80, y + 34, x + w / 2 + 80, y + 70], radius=18, fill=(10, 10, 12))
    return x + 50, y + 110, w - 100  # área útil: x, y, largura


def _notificacao(draw, _x, y, titulo, detalhe):
    w = 150 + max(draw.textlength(titulo, font=fonte("bold", 32)), draw.textlength(detalhe, font=fonte("regular", 26)))
    x = SW - 50 - w
    draw.rounded_rectangle([x + 6, y + 8, x + w + 6, y + 158], radius=28, fill=(0, 0, 0))
    draw.rounded_rectangle([x, y, x + w, y + 150], radius=28, fill=(255, 255, 255))
    draw.ellipse([x + 28, y + 40, x + 98, y + 110], fill=(37, 211, 102))
    draw.text((x + 46, y + 52), "✓", font=fonte("bold", 40), fill=(255, 255, 255))
    draw.text((x + 120, y + 34), titulo, font=fonte("bold", 32), fill=ESCURO)
    draw.text((x + 120, y + 84), detalhe, font=fonte("regular", 26), fill=SUAVE_ESC)


def _rodape(draw, cfg, aviso):
    cta = f"Quer um assim? WhatsApp {cfg['whatsapp']}"
    fb = fonte("bold", 38)
    lb = draw.textlength(cta, font=fb)
    yb = SH - 330
    draw.rounded_rectangle([(SW - lb) / 2 - 45, yb, (SW + lb) / 2 + 45, yb + 96], radius=48, fill=hex_rgb(cfg["cores"]["destaque"]))
    draw.text(((SW - lb) / 2, yb + 26), cta, font=fb, fill=ESCURO)
    fa = fonte("regular", 24)
    draw.text(((SW - draw.textlength(aviso, font=fa)) / 2, yb + 124), aviso, font=fa, fill=SUAVE_ESC)


def _cabecalho_app(draw, x, y, sigla, nome, status):
    draw.ellipse([x, y, x + 84, y + 84], fill=CINZA_CHIP)
    fs = fonte("bold", 30)
    draw.text((x + 42 - draw.textlength(sigla, font=fs) / 2, y + 24), sigla, font=fs, fill=ESCURO)
    draw.text((x + 104, y + 6), nome, font=fonte("bold", 36), fill=ESCURO)
    draw.text((x + 104, y + 52), status, font=fonte("regular", 26), fill=SUAVE_ESC)


def _chips(draw, x, y, nomes, ativo=0):
    f = fonte("semi", 28)
    for i, n in enumerate(nomes):
        lw = draw.textlength(n, font=f) + 48
        draw.rounded_rectangle([x, y, x + lw, y + 60], radius=30, fill=ESCURO if i == ativo else CINZA_CHIP)
        draw.text((x + 24, y + 14), n, font=f, fill=(255, 255, 255) if i == ativo else ESCURO)
        x += lw + 14


def story_cardapio(cfg, destino, titulo="Pare de anotar pedido na mão.",
                   subtitulo="Veja como fica o cardápio digital do seu restaurante.",
                   sigla="SR", nome="Seu Restaurante", chips=("Lanches", "Porções", "Bebidas"),
                   itens=None, total="R$ 90,40", notif=("Novo pedido no WhatsApp", "#0427 · R$ 90,40 · Pix")):
    img, draw = _fundo(cfg)
    _topo(draw, cfg, "CARDÁPIO DIGITAL", titulo, subtitulo)
    x, y, larg = _celular(draw, 170, 700, 740, 860)
    _cabecalho_app(draw, x, y, sigla, nome, "Aberto agora · entrega 30-40 min")
    _chips(draw, x, y + 120, list(chips))
    itens = itens or [("Burger da Casa", "Brioche, blend 180g e cheddar", "R$ 32,90"),
             ("Batata Rústica", "Porção 400g com alecrim", "R$ 21,00"),
             ("Smash Duplo", "Dois smash, bacon e picles", "R$ 36,50")]
    yy = y + 220
    for nome, desc, preco in itens:
        draw.rounded_rectangle([x, yy, x + 110, yy + 110], radius=22, fill=(214, 168, 108))
        draw.ellipse([x + 18, yy + 30, x + 92, yy + 82], fill=(150, 90, 45))
        draw.text((x + 136, yy + 4), nome, font=fonte("bold", 32), fill=ESCURO)
        draw.text((x + 136, yy + 46), desc, font=fonte("regular", 24), fill=SUAVE_ESC)
        draw.text((x + 136, yy + 78), preco, font=fonte("semi", 28), fill=ESCURO)
        draw.ellipse([x + larg - 56, yy + 30, x + larg, yy + 86], fill=ESCURO)
        draw.text((x + larg - 40, yy + 30), "+", font=fonte("bold", 40), fill=(255, 255, 255))
        yy += 128
    draw.rounded_rectangle([x, yy + 10, x + larg, yy + 100], radius=45, fill=ESCURO)
    t = f"Enviar pedido · {total}"
    ft = fonte("bold", 32)
    draw.text((x + larg / 2 - draw.textlength(t, font=ft) / 2, yy + 34), t, font=ft, fill=(255, 255, 255))
    _notificacao(draw, 0, 625, *notif)
    _rodape(draw, cfg, "Imagem ilustrativa para demonstração.")
    img.save(destino, "JPEG", quality=92)
    return destino


def story_agenda_manicure(cfg, destino, titulo="Sua cliente marca a unha sozinha.",
                          subtitulo="Veja como fica a agenda online de um studio de manicure.",
                          sigla="SN", nome="Seu Studio de Unhas", chips=("Mão", "Pé e mão", "Gel"),
                          notif=("Novo agendamento", "Pé e mão · Sex 14:30 · lembrete enviado"),
                          botao="Confirmar · Sex 14:30"):
    img, draw = _fundo(cfg)
    _topo(draw, cfg, "AGENDA ONLINE", titulo, subtitulo)
    x, y, larg = _celular(draw, 170, 700, 740, 860)
    _cabecalho_app(draw, x, y, sigla, nome, "Agende seu horário")
    _chips(draw, x, y + 120, list(chips), ativo=1)
    # dias
    dias = [("SEG", "10"), ("TER", "11"), ("QUA", "12"), ("QUI", "13"), ("SEX", "14")]
    dw = (larg - 4 * 12) / 5
    for i, (sem, num) in enumerate(dias):
        dx = x + i * (dw + 12)
        sel = i == 4
        draw.rounded_rectangle([dx, y + 220, dx + dw, y + 330], radius=24, fill=ESCURO if sel else CINZA_CHIP)
        cor = (255, 255, 255) if sel else ESCURO
        f1, f2 = fonte("semi", 22), fonte("bold", 38)
        draw.text((dx + dw / 2 - draw.textlength(sem, font=f1) / 2, y + 236), sem, font=f1, fill=cor)
        draw.text((dx + dw / 2 - draw.textlength(num, font=f2) / 2, y + 268), num, font=f2, fill=cor)
    # horários
    draw.text((x, y + 360), "Horários livres", font=fonte("bold", 30), fill=ESCURO)
    horas = ["09:00", "10:30", "13:00", "14:30", "16:00", "17:30"]
    ocupados = {"10:30", "16:00"}
    hw = (larg - 2 * 14) / 3
    for i, h in enumerate(horas):
        hx = x + (i % 3) * (hw + 14)
        hy = y + 420 + (i // 3) * 90
        if h in ocupados:
            fill, cor = (240, 239, 234), (190, 190, 190)
        elif h == "14:30":
            fill, cor = ESCURO, (255, 255, 255)
        else:
            fill, cor = CINZA_CHIP, ESCURO
        draw.rounded_rectangle([hx, hy, hx + hw, hy + 72], radius=20, fill=fill)
        fh = fonte("semi", 30)
        draw.text((hx + hw / 2 - draw.textlength(h, font=fh) / 2, hy + 18), h, font=fh, fill=cor)
    yy = y + 620
    draw.rounded_rectangle([x, yy, x + larg, yy + 90], radius=45, fill=ESCURO)
    t = botao
    ft = fonte("bold", 32)
    draw.text((x + larg / 2 - draw.textlength(t, font=ft) / 2, yy + 24), t, font=ft, fill=(255, 255, 255))
    _notificacao(draw, 0, 625, *notif)
    _rodape(draw, cfg, "Imagem ilustrativa para demonstração.")
    img.save(destino, "JPEG", quality=92)
    return destino


def story_catalogo(cfg, destino, titulo="Seus produtos num link só.",
                   subtitulo="Veja como fica o catálogo digital de uma loja.",
                   sigla="SL", nome="Sua Loja", chips=("Novidades", "Vestidos", "Blusas"),
                   produtos=(("Vestido Linho", "R$ 189,90"), ("Blusa Seda", "R$ 119,90"),
                             ("Calça Alfaiataria", "R$ 159,90"), ("Camisa Off", "R$ 99,90")),
                   notif=("Novo pedido no WhatsApp", "2 itens · R$ 309,80")):
    img, draw = _fundo(cfg)
    _topo(draw, cfg, "CATÁLOGO DIGITAL", titulo, subtitulo)
    x, y, larg = _celular(draw, 170, 700, 740, 860)
    _cabecalho_app(draw, x, y, sigla, nome, "Catálogo · pedido pelo WhatsApp")
    _chips(draw, x, y + 120, list(chips))
    cw = (larg - 20) / 2
    tons = [(201, 190, 172), (176, 181, 186), (150, 140, 128), (214, 210, 200)]
    for i, (n, preco) in enumerate(produtos[:4]):
        cx = x + (i % 2) * (cw + 20)
        cy = y + 220 + (i // 2) * 250
        draw.rounded_rectangle([cx, cy, cx + cw, cy + 160], radius=22, fill=tons[i % 4])
        draw.text((cx + 6, cy + 172), n, font=fonte("bold", 28), fill=ESCURO)
        draw.text((cx + 6, cy + 208), preco, font=fonte("regular", 26), fill=SUAVE_ESC)
    _notificacao(draw, 0, 625, *notif)
    _rodape(draw, cfg, "Imagem ilustrativa para demonstração.")
    img.save(destino, "JPEG", quality=92)
    return destino


def para_feed(caminho_story, destino):
    """Recorta um story de vitrine no formato do feed (1080x1350)."""
    im = Image.open(caminho_story)
    feed = im.crop((0, 215, 1080, 1590)).resize((1080, 1350))
    feed.save(destino, "JPEG", quality=92)
    return destino


def story_site(cfg, destino, titulo="Seu site, do jeito que o cliente procura.",
               subtitulo="Veja como fica o site de uma clínica odontológica.",
               dominio="suaclinica.com.br", marca="Sua Clínica", chamada="Seu sorriso em boas mãos.",
               apoio="Avaliação, limpeza, clareamento e implantes.", botao="Agendar pelo WhatsApp",
               servicos=("Avaliação", "Limpeza", "Clareamento"), tom=(176, 181, 186),
               notif=("Nova mensagem pelo site", "Quero agendar uma avaliação")):
    """Prévia de um site institucional (demonstração com nome fictício)."""
    img, draw = _fundo(cfg)
    _topo(draw, cfg, "CRIAÇÃO DE SITES", titulo, subtitulo)
    x, y, larg = _celular(draw, 170, 700, 740, 860)
    x0, larg0 = x - 12, larg + 24  # o site ocupa quase toda a tela
    # barra do navegador
    draw.rounded_rectangle([x0, y - 20, x0 + larg0, y + 44], radius=32, fill=CINZA_CHIP)
    fd = fonte("regular", 26)
    draw.text((x0 + larg0 / 2 - draw.textlength("🔒 " + dominio, font=fd) / 2 + 10, y - 4), dominio, font=fd, fill=SUAVE_ESC)
    # menu
    yy = y + 66
    draw.text((x0 + 10, yy), marca, font=fonte("bold", 32), fill=ESCURO)
    for i in range(3):
        draw.rounded_rectangle([x0 + larg0 - 54, yy + 8 + i * 12, x0 + larg0 - 14, yy + 14 + i * 12], radius=3, fill=ESCURO)
    # destaque (hero)
    yy += 58
    draw.rounded_rectangle([x0, yy, x0 + larg0, yy + 300], radius=30, fill=ESCURO)
    draw.rounded_rectangle([x0 + larg0 - 200, yy + 28, x0 + larg0 - 28, yy + 170], radius=22, fill=tom)
    mx, my = x0 + larg0 - 200, yy + 28
    draw.ellipse([mx + 110, my + 22, mx + 146, my + 58], fill=(255, 255, 255))
    draw.polygon([(mx + 18, my + 126), (mx + 70, my + 60), (mx + 112, my + 110), (mx + 134, my + 86), (mx + 158, my + 126)], fill=ESCURO)
    fh, lh, th, ah = bloco(draw, chamada, "bold", 40, 28, larg0 - 270, 140)
    escrever(draw, x0 + 28, yy + 30, lh, fh, th, (255, 255, 255))
    fa, la, ta, aa = bloco(draw, apoio, "regular", 24, 20, larg0 - 56, 34, 1.3)
    escrever(draw, x0 + 28, yy + 186, la, fa, ta, (190, 194, 200), 1.3)
    fb = fonte("bold", 26)
    lb = draw.textlength(botao, font=fb)
    draw.rounded_rectangle([x0 + 28, yy + 228, x0 + 28 + lb + 60, yy + 280], radius=27, fill=(37, 211, 102))
    draw.text((x0 + 58, yy + 239), botao, font=fb, fill=(255, 255, 255))
    # serviços
    yy += 322
    draw.text((x0 + 10, yy), "Serviços", font=fonte("bold", 30), fill=ESCURO)
    yy += 46
    cw = (larg0 - 2 * 16) / 3
    for i, s in enumerate(servicos[:3]):
        cx = x0 + i * (cw + 16)
        draw.rounded_rectangle([cx, yy, cx + cw, yy + 124], radius=22, fill=CINZA_CHIP)
        draw.ellipse([cx + 20, yy + 18, cx + 62, yy + 60], fill=tom)
        fs = fonte("semi", 24)
        while draw.textlength(s, font=fs) > cw - 30 and fs.size > 16:
            fs = fonte("semi", fs.size - 2)
        draw.text((cx + 20, yy + 80), s, font=fs, fill=ESCURO)
    # rodapé do site
    yy += 146
    draw.text((x0 + 10, yy), "Endereço  ·  Horários  ·  Contato", font=fonte("regular", 24), fill=SUAVE_ESC)
    _notificacao(draw, 0, 625, *notif)
    _rodape(draw, cfg, "Imagem ilustrativa para demonstração.")
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=92)
    return destino
