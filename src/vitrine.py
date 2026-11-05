"""Stories de vitrine: mostram um serviço funcionando dentro de um celular (demonstração)."""
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


def story_cardapio(cfg, destino):
    img, draw = _fundo(cfg)
    _topo(draw, cfg, "CARDÁPIO DIGITAL", "Pare de anotar pedido na mão.",
          "Veja como fica o cardápio digital do seu restaurante.")
    x, y, larg = _celular(draw, 170, 700, 740, 860)
    _cabecalho_app(draw, x, y, "SR", "Seu Restaurante", "Aberto agora · entrega 30-40 min")
    _chips(draw, x, y + 120, ["Lanches", "Porções", "Bebidas"])
    itens = [("Burger da Casa", "Brioche, blend 180g e cheddar", "R$ 32,90"),
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
    t = "Enviar pedido · R$ 90,40"
    ft = fonte("bold", 32)
    draw.text((x + larg / 2 - draw.textlength(t, font=ft) / 2, yy + 34), t, font=ft, fill=(255, 255, 255))
    _notificacao(draw, 0, 625, "Novo pedido no WhatsApp", "#0427 · R$ 90,40 · Pix")
    _rodape(draw, cfg, "Imagem ilustrativa para demonstração.")
    img.save(destino, "JPEG", quality=92)
    return destino


def story_agenda_manicure(cfg, destino):
    img, draw = _fundo(cfg)
    _topo(draw, cfg, "AGENDA ONLINE", "Sua cliente marca a unha sozinha.",
          "Veja como fica a agenda online de um studio de manicure.")
    x, y, larg = _celular(draw, 170, 700, 740, 860)
    _cabecalho_app(draw, x, y, "SN", "Seu Studio de Unhas", "Agende seu horário")
    _chips(draw, x, y + 120, ["Mão", "Pé e mão", "Gel"], ativo=1)
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
    t = "Confirmar · Sex 14:30"
    ft = fonte("bold", 32)
    draw.text((x + larg / 2 - draw.textlength(t, font=ft) / 2, yy + 24), t, font=ft, fill=(255, 255, 255))
    _notificacao(draw, 0, 625, "Novo agendamento", "Pé e mão · Sex 14:30 · lembrete enviado")
    _rodape(draw, cfg, "Imagem ilustrativa para demonstração.")
    img.save(destino, "JPEG", quality=92)
    return destino
