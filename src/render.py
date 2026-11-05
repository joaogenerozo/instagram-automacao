"""Desenha as imagens dos posts (1080x1350, formato 4:5) com a identidade da marca."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
MARGEM = 90
FONTES = Path(__file__).resolve().parent.parent / "fonts"


def fonte(peso, tamanho):
    arquivo = {"regular": "Inter-Regular.otf", "semi": "Inter-SemiBold.otf", "bold": "Inter-ExtraBold.otf"}[peso]
    return ImageFont.truetype(str(FONTES / arquivo), tamanho)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def quebrar(draw, texto, f, largura):
    linhas = []
    for paragrafo in texto.split("\n"):
        atual = ""
        for palavra in paragrafo.split():
            teste = f"{atual} {palavra}".strip()
            if draw.textlength(teste, font=f) <= largura:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas


def bloco(draw, texto, peso, tam_max, tam_min, largura, altura_max, entrelinha=1.18):
    """Escolhe o maior tamanho de fonte em que o texto cabe na área."""
    for tam in range(tam_max, tam_min - 1, -4):
        f = fonte(peso, tam)
        linhas = quebrar(draw, texto, f, largura)
        alt = int(len(linhas) * tam * entrelinha)
        if alt <= altura_max:
            return f, linhas, tam, alt
    f = fonte(peso, tam_min)
    linhas = quebrar(draw, texto, f, largura)
    return f, linhas, tam_min, int(len(linhas) * tam_min * entrelinha)


def escrever(draw, x, y, linhas, f, tam, cor, entrelinha=1.18):
    for linha in linhas:
        draw.text((x, y), linha, font=f, fill=cor)
        y += int(tam * entrelinha)
    return y


class Desenhista:
    def __init__(self, config):
        self.cfg = config
        c = config["cores"]
        self.fundo, self.fundo2 = hex_rgb(c["fundo"]), hex_rgb(c["fundo2"])
        self.destaque = hex_rgb(c["destaque"])
        self.texto, self.suave = hex_rgb(c["texto"]), hex_rgb(c["texto_suave"])

    # ---------- base ----------
    def _base(self, tema):
        cor_tema = hex_rgb(self.cfg["temas"][tema]["cor"])
        img = Image.new("RGB", (W, H), self.fundo)
        px = ImageDraw.Draw(img)
        for y in range(H):  # degradê vertical
            t = y / H
            cor = tuple(int(self.fundo[i] * (1 - t) + self.fundo2[i] * t) for i in range(3))
            px.line([(0, y), (W, y)], fill=cor)
        # círculos decorativos translúcidos
        camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(camada)
        claro = sum(self.fundo) > 600
        d.ellipse([W - 380, -220, W + 220, 380], fill=cor_tema + ((35,) if claro else (110,)))
        d.ellipse([-260, H - 330, 260, H + 190], fill=self.destaque + (28,))
        img = Image.alpha_composite(img.convert("RGBA"), camada)
        draw = ImageDraw.Draw(img)
        # selo do tema
        rotulo = self.cfg["temas"][tema]["rotulo"]
        f = fonte("semi", 30)
        larg = draw.textlength(rotulo, font=f)
        draw.rounded_rectangle([MARGEM, 90, MARGEM + larg + 56, 150], radius=30, fill=cor_tema)
        draw.text((MARGEM + 28, 102), rotulo, font=f, fill=(255, 255, 255))
        return img, draw, cor_tema

    def _rodape(self, draw, extra=None):
        draw.line([(MARGEM, H - 150), (W - MARGEM, H - 150)], fill=self.suave + (90,), width=2)
        draw.text((MARGEM, H - 118), self.cfg["marca"], font=fonte("bold", 32), fill=self.texto)
        draw.text((MARGEM, H - 74), self.cfg["instagram"], font=fonte("regular", 28), fill=self.suave)
        if extra:
            f = fonte("semi", 30)
            draw.text((W - MARGEM - draw.textlength(extra, font=f), H - 100), extra, font=f, fill=self.destaque)

    # ---------- post único ----------
    def post(self, p, destino):
        img, draw, cor_tema = self._base(p["tema"])
        larg = W - 2 * MARGEM
        y = 230
        f, linhas, tam, alt = bloco(draw, p["titulo"], "bold", 96, 56, larg, 520)
        y = escrever(draw, MARGEM, y, linhas, f, tam, self.texto) + 30
        draw.rectangle([MARGEM, y, MARGEM + 120, y + 10], fill=self.destaque)
        y += 50
        if p.get("subtitulo"):
            f, linhas, tam, alt = bloco(draw, p["subtitulo"], "regular", 44, 32, larg, 260, 1.3)
            y = escrever(draw, MARGEM, y, linhas, f, tam, self.suave, 1.3) + 30
        for item in p.get("itens", [])[:4]:
            if y > H - 260:
                break
            draw.ellipse([MARGEM, y + 6, MARGEM + 40, y + 46], fill=self.destaque)
            draw.line([(MARGEM + 10, y + 27), (MARGEM + 18, y + 35), (MARGEM + 31, y + 17)], fill=self.fundo, width=5)
            f, linhas, tam, alt = bloco(draw, item, "semi", 42, 30, larg - 70, 110)
            y = escrever(draw, MARGEM + 64, y, linhas, f, tam, self.texto) + 22
        self._rodape(draw, p.get("cta_imagem", "Chame no WhatsApp"))
        return self._salvar(img, destino)

    # ---------- carrossel ----------
    def carrossel(self, p, pasta):
        slides = p["slides"]
        total = len(slides) + 2
        caminhos = []
        larg = W - 2 * MARGEM

        # capa
        img, draw, cor_tema = self._base(p["tema"])
        f, linhas, tam, alt = bloco(draw, p["titulo"], "bold", 104, 60, larg, 640)
        y = escrever(draw, MARGEM, 260, linhas, f, tam, self.texto) + 40
        if p.get("subtitulo"):
            f, linhas, tam, alt = bloco(draw, p["subtitulo"], "regular", 44, 32, larg, 240, 1.3)
            escrever(draw, MARGEM, y, linhas, f, tam, self.suave, 1.3)
        self._rodape(draw, "Arraste  →")
        caminhos.append(self._salvar(img, pasta / "01.jpg"))

        # slides de conteúdo
        for i, s in enumerate(slides, start=1):
            img, draw, cor_tema = self._base(p["tema"])
            draw.text((MARGEM, 210), f"{i:02d}", font=fonte("bold", 150), fill=self.destaque)
            f, linhas, tam, alt = bloco(draw, s["titulo"], "bold", 84, 50, larg, 360)
            y = escrever(draw, MARGEM, 420, linhas, f, tam, self.texto) + 36
            f, linhas, tam, alt = bloco(draw, s["texto"], "regular", 54, 32, larg, H - 220 - y, 1.35)
            escrever(draw, MARGEM, y, linhas, f, tam, self.suave, 1.35)
            self._rodape(draw, f"{i + 1}/{total}")
            caminhos.append(self._salvar(img, pasta / f"{i + 1:02d}.jpg"))

        # slide final (chamada para ação)
        img, draw, cor_tema = self._base(p["tema"])
        cta = p.get("cta_final", "Quer isso no seu negócio?")
        f, linhas, tam, alt = bloco(draw, cta, "bold", 96, 56, larg, 420)
        y = escrever(draw, MARGEM, 300, linhas, f, tam, self.texto) + 50
        caixa = f"WhatsApp {self.cfg['whatsapp']}"
        fb = fonte("bold", 42)
        lb = draw.textlength(caixa, font=fb)
        draw.rounded_rectangle([MARGEM, y, MARGEM + lb + 80, y + 100], radius=50, fill=self.destaque)
        draw.text((MARGEM + 40, y + 24), caixa, font=fb, fill=self.fundo)
        y += 160
        for linha in ["Salve este post", "Compartilhe com quem precisa"]:
            draw.text((MARGEM, y), "•  " + linha, font=fonte("semi", 38), fill=self.suave)
            y += 64
        self._rodape(draw, f"{total}/{total}")
        caminhos.append(self._salvar(img, pasta / f"{total:02d}.jpg"))
        return caminhos

    @staticmethod
    def _salvar(img, destino):
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(destino, "JPEG", quality=92)  # a API do Instagram só aceita JPEG
        return destino


# ---------- stories (1080x1920) ----------
SW, SH = 1080, 1920


def desenhar_story(self, item, destino, numero=None):
    tema = item["tema"]
    cor_tema = hex_rgb(self.cfg["temas"][tema]["cor"])
    img = Image.new("RGB", (SW, SH), self.fundo)
    d0 = ImageDraw.Draw(img)
    for y in range(SH):
        t = y / SH
        d0.line([(0, y), (SW, y)], fill=tuple(int(self.fundo[i] * (1 - t) + self.fundo2[i] * t) for i in range(3)))
    camada = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    dc = ImageDraw.Draw(camada)
    dc.ellipse([SW - 420, -200, SW + 260, 480], fill=cor_tema + (110,))
    dc.ellipse([-300, SH - 520, 320, SH + 100], fill=self.destaque + (30,))
    img = Image.alpha_composite(img.convert("RGBA"), camada)
    draw = ImageDraw.Draw(img)
    larg = SW - 2 * MARGEM

    # topo (abaixo da área da barra do Instagram)
    y = 260
    rotulo = "PERGUNTA FREQUENTE" + (f"  #{numero}" if numero else "")
    f = fonte("semi", 34)
    lr = draw.textlength(rotulo, font=f)
    draw.rounded_rectangle([MARGEM, y, MARGEM + lr + 60, y + 70], radius=35, fill=cor_tema)
    draw.text((MARGEM + 30, y + 14), rotulo, font=f, fill=(255, 255, 255))
    y += 130

    # pergunta em balão
    fq, lq, tq, aq = bloco(draw, item["pergunta"], "bold", 84, 52, larg - 80, 520)
    draw.rounded_rectangle([MARGEM, y, SW - MARGEM, y + aq + 90], radius=40, fill=(255, 255, 255))
    escrever(draw, MARGEM + 40, y + 45, lq, fq, tq, self.fundo)
    y += aq + 90 + 70

    # resposta
    draw.rectangle([MARGEM, y, MARGEM + 10, y + 60], fill=self.destaque)
    draw.text((MARGEM + 30, y + 6), "Resposta", font=fonte("semi", 40), fill=self.suave)
    y += 100
    fr, lr_, tr, ar = bloco(draw, item["resposta"], "regular", 58, 38, larg, SH - 560 - y, 1.35)
    escrever(draw, MARGEM, y, lr_, fr, tr, self.texto, 1.35)

    # chamada (acima da área de resposta do story)
    cta = f"Dúvidas? WhatsApp {self.cfg['whatsapp']}"
    fb = fonte("bold", 40)
    lb = draw.textlength(cta, font=fb)
    yb = SH - 440
    draw.rounded_rectangle([(SW - lb) / 2 - 45, yb, (SW + lb) / 2 + 45, yb + 100], radius=50, fill=self.destaque)
    draw.text(((SW - lb) / 2, yb + 26), cta, font=fb, fill=self.fundo)
    marca = f"{self.cfg['marca']}  ·  {self.cfg['instagram']}"
    fm = fonte("semi", 32)
    draw.text(((SW - draw.textlength(marca, font=fm)) / 2, yb + 140), marca, font=fm, fill=self.suave)
    return self._salvar(img, destino)


Desenhista.story = desenhar_story


# ---------- variações de layout (para não repetir o visual) ----------
from contextlib import contextmanager

CLARO = {"fundo": "#F4F3EE", "fundo2": "#E9E8E2", "destaque": "#18191D", "texto": "#18191D", "texto_suave": "#5B6068"}


@contextmanager
def _paleta(self, clara):
    if not clara:
        yield
        return
    salvo = (self.fundo, self.fundo2, self.destaque, self.texto, self.suave)
    self.fundo, self.fundo2 = hex_rgb(CLARO["fundo"]), hex_rgb(CLARO["fundo2"])
    self.destaque, self.texto, self.suave = hex_rgb(CLARO["destaque"]), hex_rgb(CLARO["texto"]), hex_rgb(CLARO["texto_suave"])
    try:
        yield
    finally:
        self.fundo, self.fundo2, self.destaque, self.texto, self.suave = salvo


def _grade_pontos(self, draw, x0, y0, colunas=6, linhas=6, passo=34):
    for i in range(colunas):
        for j in range(linhas):
            r = 4
            draw.ellipse([x0 + i * passo - r, y0 + j * passo - r, x0 + i * passo + r, y0 + j * passo + r], fill=self.suave)


def _post_pergunta(self, p, destino):
    img, draw, _ = self._base(p["tema"])
    larg = W - 2 * MARGEM
    _grade_pontos(self, draw, W - MARGEM - 170, 230)
    f, linhas, tam, alt = bloco(draw, p["titulo"], "bold", 110, 60, larg, 640)
    y = (H - alt) // 2 - 60
    y = escrever(draw, MARGEM, y, linhas, f, tam, self.texto) + 40
    if p.get("subtitulo"):
        f, linhas, tam, _ = bloco(draw, p["subtitulo"], "regular", 42, 30, larg, 200, 1.3)
        escrever(draw, MARGEM, y, linhas, f, tam, self.suave, 1.3)
    self._rodape(draw, p.get("cta_imagem", "Responda no Direct"))
    return self._salvar(img, destino)


def _post_numero(self, p, destino):
    img, draw, _ = self._base(p["tema"])
    larg = W - 2 * MARGEM
    _grade_pontos(self, draw, W - MARGEM - 170, 230, 6, 4)
    f = fonte("bold", 260)
    draw.text((MARGEM - 8, 200), p["numero"], font=f, fill=self.destaque)
    y = 520
    f, linhas, tam, alt = bloco(draw, p["titulo"], "bold", 80, 50, larg, 330)
    y = escrever(draw, MARGEM, y, linhas, f, tam, self.texto) + 30
    if p.get("subtitulo"):
        f, linhas, tam, _ = bloco(draw, p["subtitulo"], "regular", 42, 30, larg, H - 260 - y, 1.3)
        escrever(draw, MARGEM, y, linhas, f, tam, self.suave, 1.3)
    self._rodape(draw, p.get("cta_imagem", "Chame no WhatsApp"))
    return self._salvar(img, destino)


_post_original = Desenhista.post
_carrossel_original = Desenhista.carrossel


def _post_variado(self, p, destino):
    layout = p.get("layout", "padrao")
    with _paleta(self, p.get("claro", False)):
        if layout == "pergunta":
            return _post_pergunta(self, p, destino)
        if layout == "numero":
            return _post_numero(self, p, destino)
        return _post_original(self, p, destino)


def _carrossel_variado(self, p, pasta):
    with _paleta(self, p.get("claro", False)):
        return _carrossel_original(self, p, pasta)


Desenhista.post = _post_variado
Desenhista.carrossel = _carrossel_variado


def story_texto(self, item, destino):
    """Story de texto (bastidor, pergunta para o Direct, chamada para orçamento)."""
    with _paleta(self, item.get("claro", False)):
        img = Image.new("RGB", (SW, SH), self.fundo)
        d = ImageDraw.Draw(img)
        for y in range(SH):
            t = y / SH
            d.line([(0, y), (SW, y)], fill=tuple(int(self.fundo[i] * (1 - t) + self.fundo2[i] * t) for i in range(3)))
        draw = ImageDraw.Draw(img)
        larg = SW - 2 * MARGEM
        f = fonte("semi", 32)
        rot = item.get("rotulo", "GNZ01")
        lr = draw.textlength(rot, font=f)
        draw.rounded_rectangle([MARGEM, 260, MARGEM + lr + 56, 324], radius=32, fill=(48, 52, 59))
        draw.text((MARGEM + 28, 273), rot, font=f, fill=(255, 255, 255))
        _grade_pontos(self, draw, SW - MARGEM - 170, 280, 6, 4)
        ft, lt, tt, at = bloco(draw, item["titulo"], "bold", 100, 60, larg, 640)
        y = 560
        y = escrever(draw, MARGEM, y, lt, ft, tt, self.texto) + 50
        if item.get("texto"):
            fr, lr_, tr, _ = bloco(draw, item["texto"], "regular", 52, 36, larg, SH - 560 - y, 1.35)
            escrever(draw, MARGEM, y, lr_, fr, tr, self.suave, 1.35)
        cta = item.get("cta", f"WhatsApp {self.cfg['whatsapp']}")
        fb = fonte("bold", 40)
        lb = draw.textlength(cta, font=fb)
        yb = SH - 440
        draw.rounded_rectangle([(SW - lb) / 2 - 45, yb, (SW + lb) / 2 + 45, yb + 100], radius=50, fill=self.destaque)
        draw.text(((SW - lb) / 2, yb + 26), cta, font=fb, fill=self.fundo)
        marca = f"{self.cfg['marca']}  ·  {self.cfg['instagram']}"
        fm = fonte("semi", 32)
        draw.text(((SW - draw.textlength(marca, font=fm)) / 2, yb + 140), marca, font=fm, fill=self.suave)
        return self._salvar(img, destino)


Desenhista.story_texto = story_texto
