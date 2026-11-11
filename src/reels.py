"""GNZ01 AI Video Production Studio: motor de Reels (1080x1920, 30 fps, H.264).

Cada Reel nasce de um roteiro JSON (conteudo/reels/*.json) com cenas. Tipos de cena:
  gancho      frase de impacto cinética (1-3 s iniciais) com rótulo do público
  texto       afirmação + apoio
  lista       título + itens que entram um a um
  celular     demonstração no celular (site, cardapio, agenda, catalogo) com destaques flutuantes
  comparacao  "sem" x "com" em dois cartões
  imagem      arte existente do repositório com movimento de câmera (ex.: capa de carrossel)
  cta         chamada para ação
Uma assinatura da marca (2 s) fecha todo vídeo.

Identidade: preto profundo, grafite metálico, off-white; Inter (títulos) + Caladea itálica (destaques).
Movimento: push-in de câmera contínuo, palavras entrando em sequência, transições com zoom e
profundidade, elementos com flutuação sutil, grão de filme e vinheta.
"""
import json
import math
import re
import subprocess
import tempfile
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from src import reels_audio as au

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "fonts"
W, H, FPS = 1080, 1920, 30
TR = 0.32  # duração das transições
BPM = 112  # andamento da trilha; o fundo pulsa junto com a batida

PRETO = (9, 9, 11)
GRAFITE = (30, 32, 37)
GRAFITE2 = (46, 49, 56)
OFF = (244, 243, 238)
PRATA = (190, 195, 202)
SUAVE = (138, 143, 151)
VERDE = (37, 211, 102)
OURO = (197, 164, 109)   # dourado discreto da identidade GNZ01_ (#C5A46D)

TOPO_SEGURO = 250      # abaixo do cabeçalho do Reels
BASE_LEGENDA = 1360    # legendas da narração ficam entre 1360 e 1520 (acima da legenda/botões do app)


# ------------------------------------------------------------------ utilitários
@lru_cache(maxsize=None)
def fonte(nome, tam):
    arq = {"bold": "Inter-ExtraBold.otf", "semi": "Inter-SemiBold.otf", "regular": "Inter-Regular.otf",
           "serif": "Caladea-BoldItalic.ttf", "serif_r": "Caladea-Italic.ttf"}[nome]
    return ImageFont.truetype(str(FONTES / arq), tam)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = max(0.0, min(1.0, t))
    c = 1.4
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def _limpa(p):
    return re.sub(r"[^\wÀ-ÿ]", "", p.lower())


# ------------------------------------------------------------------ fundo e texturas
def _gradiente_vertical(w, h, c1, c2):
    a = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(c1)[None, None, :] * (1 - a) + np.array(c2)[None, None, :] * a)
    return Image.fromarray(np.repeat(arr, w, axis=1).astype("uint8"), "RGB")


def _metal(w, h):
    """Gradiente metálico (off-white -> prata -> grafite claro) para preencher títulos."""
    y = np.linspace(0, 1, h)
    r = np.interp(y, [0, 0.45, 0.62, 1], [252, 236, 176, 214])
    g = np.interp(y, [0, 0.45, 0.62, 1], [251, 236, 181, 218])
    b = np.interp(y, [0, 0.45, 0.62, 1], [247, 238, 190, 224])
    arr = np.stack([r, g, b], axis=1)[:, None, :].repeat(w, axis=1)
    return Image.fromarray(arr.astype("uint8"), "RGB")


def _fundo_base():
    im = _gradiente_vertical(W, H, (14, 14, 17), (7, 7, 9))
    # brilho grafite metálico no alto
    luz = Image.new("L", (W, H), 0)
    ImageDraw.Draw(luz).ellipse([-200, -500, W + 200, 900], fill=120)
    luz = luz.filter(ImageFilter.GaussianBlur(220))
    im = Image.composite(Image.new("RGB", (W, H), (52, 55, 62)), im, luz)
    # grade técnica bem discreta, mais visível no alto
    grade = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(grade)
    for x in range(0, W + 1, 120):
        d.line([(x, 0), (x, H)], fill=26)
    for y in range(0, H + 1, 120):
        d.line([(0, y), (W, y)], fill=26)
    mascara = _gradiente_vertical(W, H, (255, 255, 255), (0, 0, 0)).convert("L")
    grade = Image.fromarray((np.asarray(grade, dtype=float) * np.asarray(mascara) / 255).astype("uint8"))
    im = Image.composite(Image.new("RGB", (W, H), (90, 95, 104)), im, grade)
    return im.convert("RGBA")


def _vinheta():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.7)) ** 2)
    a = np.clip((d - 0.55) * 1.6, 0, 1) ** 1.5 * 200
    v = np.zeros((H, W, 4), dtype="uint8")
    v[..., 3] = a.astype("uint8")
    return Image.fromarray(v, "RGBA")


def _graos(n=4):
    rng = np.random.default_rng(11)
    out = []
    for _ in range(n):
        g = rng.normal(0, 1, (H // 2, W // 2))
        a = np.zeros((H // 2, W // 2, 4), dtype="uint8")
        claro = g > 0
        a[..., :3] = np.where(claro[..., None], 255, 0)
        a[..., 3] = np.clip(np.abs(g) * 6, 0, 14).astype("uint8")
        out.append(Image.fromarray(a, "RGBA").resize((W, H), Image.NEAREST))
    return out


def _faixa_luz():
    """Feixe de luz diagonal suave que atravessa o fundo lentamente."""
    im = Image.new("L", (900, 2600), 0)
    ImageDraw.Draw(im).rectangle([380, 0, 520, 2600], fill=60)
    im = im.filter(ImageFilter.GaussianBlur(70)).rotate(-18, expand=True)
    rgba = Image.new("RGBA", im.size, (200, 205, 214, 0))
    rgba.putalpha(im)
    return rgba


class Recursos:
    def __init__(self):
        self.base = _fundo_base()
        self.vinheta = _vinheta()
        self.graos = _graos()
        self.luz = _faixa_luz()
        self.metal = _metal(W, H)
        self._telas = {}

    def tela(self, cfg, v):
        chave = json.dumps(v, sort_keys=True)
        if chave not in self._telas:
            from src import showcase as sc
            self._telas[chave] = sc.tela_celular(cfg, v)
        return self._telas[chave]


# ------------------------------------------------------------------ texto cinético
def _medir(f, txt):
    b = f.getbbox(txt)
    return b[2] - b[0], b


def layout_frase(texto, destaques, tam, largura, tam_destaque=None):
    """Quebra a frase em linhas com fonte por palavra (destaques em Caladea itálica, maiores)."""
    dest = {_limpa(x) for p in destaques for x in p.split()}
    tam_destaque = tam_destaque or int(tam * 1.12)
    palavras = []
    for p in texto.split():
        eh = _limpa(p) in dest
        f = fonte("serif", tam_destaque) if eh else fonte("bold", tam)
        palavras.append((p, f, eh))
    esp = int(tam * 0.26)
    linhas, atual, larg = [], [], 0
    for p, f, eh in palavras:
        w, _ = _medir(f, p)
        if atual and larg + esp + w > largura:
            linhas.append((atual, larg))
            atual, larg = [], 0
        larg += (esp if atual else 0) + w
        atual.append((p, f, eh, w))
    if atual:
        linhas.append((atual, larg))
    return linhas, esp


def desenhar_frase(camada, metal, texto, destaques, tam, y, t, atraso=0.0, passo=0.06, largura=900,
                   alinhar="centro", x0=90, cor=OFF, sublinhar=True, entrelinha=1.16, dur_entrada=0.32):
    """Desenha a frase palavra por palavra (sobe + aparece). Devolve o y final."""
    linhas, esp = layout_frase(texto, destaques, tam, largura)
    d = ImageDraw.Draw(camada)
    k = 0
    alt_linha = int(tam * entrelinha)
    for palavras, larg in linhas:
        x = (W - larg) / 2 if alinhar == "centro" else x0
        for p, f, eh, w in palavras:
            tk = (t - atraso - k * passo * 0.8) / dur_entrada
            a = ease_out(tk * 1.3)
            k += 1
            if a <= 0:
                x += w + esp
                continue
            dy = int(72 * (1 - ease_back(tk)))
            _, bb = _medir(f, p)
            yy = y + dy + (int(tam * 0.02) if eh else 0)
            if eh:
                # palavra de destaque: preenchimento metálico + fio que cresce por baixo
                caixa = (int(x), int(yy + bb[1] - 4), int(x + w + 6), int(yy + bb[3] + 6))
                m = Image.new("L", (caixa[2] - caixa[0], caixa[3] - caixa[1]), 0)
                ImageDraw.Draw(m).text((-bb[0] + 0, -bb[1] + 4), p, font=f, fill=int(255 * a))
                pedaco = metal.crop(caixa).convert("RGBA")
                pedaco.putalpha(m)
                camada.alpha_composite(pedaco, (caixa[0], caixa[1]))
                if sublinhar:
                    g = ease_out((t - atraso - k * passo - 0.15) / 0.4)
                    if g > 0:
                        yl = yy + bb[3] + 12
                        d.rectangle([x, yl, x + w * g, yl + 5], fill=(*PRATA, int(200 * a)))
            else:
                d.text((x - bb[0], yy), p, font=f, fill=(*cor, int(255 * a)))
            x += w + esp
        y += alt_linha
    return y


def texto_simples(camada, txt, f, y, cor, alfa=1.0, alinhar="centro", x0=90, largura=900, entrelinha=1.3):
    d = ImageDraw.Draw(camada)
    from src.render import quebrar
    for linha in quebrar(d, txt, f, largura):
        w = d.textlength(linha, font=f)
        x = (W - w) / 2 if alinhar == "centro" else x0
        d.text((x, y), linha, font=f, fill=(*cor, int(255 * alfa)))
        y += int(f.size * entrelinha)
    return y


def rotulo(camada, txt, y, alfa, centro=True, x0=90):
    """Etiqueta pequena em caixa alta com fio lateral (ex.: PARA DONOS DE RESTAURANTE)."""
    if not txt or alfa <= 0:
        return y
    d = ImageDraw.Draw(camada)
    f = fonte("semi", 30)
    txt = txt.upper()
    w = d.textlength(txt, font=f) + len(txt) * 3
    x = (W - w) / 2 if centro else x0
    cx = x
    for ch in txt:
        d.text((cx, y), ch, font=f, fill=(*PRATA, int(255 * alfa)))
        cx += d.textlength(ch, font=f) + 3
    fio = 60 * ease_out(alfa)
    d.rectangle([x - 24 - fio, y + 17, x - 24, y + 19], fill=(*PRATA, int(180 * alfa)))
    d.rectangle([x + w + 24, y + 17, x + w + 24 + fio, y + 19], fill=(*PRATA, int(180 * alfa)))
    return y + 70


# ------------------------------------------------------------------ cenas
class Contexto:
    def __init__(self, cfg, rec, com_legenda):
        self.cfg, self.rec = cfg, rec
        self.limite = BASE_LEGENDA - 60 if com_legenda else 1500


def _camada():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def _notificacoes(cam, itens, t, fundo=False):
    """Cartões de notificação que aparecem e somem (abertura 'tela escura com mensagens chegando')."""
    d = ImageDraw.Draw(cam)
    f1, f2 = fonte("semi", 32), fonte("regular", 28)
    n = len(itens)
    ciclo = 0.42 * n + 0.6
    for i, txt in enumerate(itens):
        ti = 0.05 + i * 0.42
        tt = (t - ti) % ciclo if t > ti else -1
        if tt < 0:
            continue
        a = ease_out(tt / 0.22) * (1 - ease((tt - 1.0) / 0.3))
        if fundo:
            a *= 0.3
        if a <= 0.01:
            continue
        b = ease_back(tt / 0.35)
        ww = 760
        x = (W - ww) / 2 + (-90 if i % 2 else 90) + (1 - b) * (60 if i % 2 else -60)
        y = 300 + (i % 4) * 190 + (1 - b) * 40
        d.rounded_rectangle([x + 6, y + 12, x + ww + 6, y + 142], radius=34, fill=(0, 0, 0, int(120 * a)))
        d.rounded_rectangle([x, y, x + ww, y + 130], radius=34, fill=(*GRAFITE2, int(240 * a)),
                            outline=(96, 101, 110, int(255 * a)), width=2)
        d.rounded_rectangle([x + 28, y + 30, x + 98, y + 100], radius=18, fill=(*OURO, int(255 * a)))
        d.rounded_rectangle([x + 46, y + 50, x + 80, y + 76], radius=7, fill=(255, 255, 255, int(255 * a)))
        d.polygon([(x + 50, y + 74), (x + 60, y + 74), (x + 48, y + 86)], fill=(255, 255, 255, int(255 * a)))
        tit, _, corpo = txt.partition("|")
        d.text((x + 124, y + 26), tit.strip(), font=f1, fill=(*OFF, int(255 * a)))
        d.text((x + 124, y + 72), corpo.strip(), font=f2, fill=(*PRATA, int(255 * a)))
        d.text((x + ww - 100, y + 30), "agora", font=fonte("regular", 24), fill=(*SUAVE, int(255 * a)))


def cena_gancho(c, t, dur, ctx):
    cam = _camada()
    if c.get("notificacoes"):
        atraso = c.get("atraso_texto", 1.5)
        _notificacoes(cam, c["notificacoes"], t, fundo=t > atraso)
        t -= atraso
        if t < -0.2:
            return cam
    tam = c.get("tam", 104 if len(c["texto"]) < 48 else 88)
    linhas, _ = layout_frase(c["texto"], c.get("destaque", []), tam, 900)
    alt = len(linhas) * int(tam * 1.16)
    y = int((TOPO_SEGURO + ctx.limite) / 2 - alt / 2) - 40
    rotulo(cam, c.get("rotulo"), y - 110, ease((t + 0.2) / 0.4))
    yf = desenhar_frase(cam, ctx.rec.metal, c["texto"], c.get("destaque", []), tam, y, t + 0.18, passo=0.055,
                        dur_entrada=0.26)
    if c.get("apoio"):
        texto_simples(cam, c["apoio"], fonte("regular", 42), yf + 40, SUAVE, ease((t - 0.7) / 0.5))
    return cam


def cena_texto(c, t, dur, ctx):
    cam = _camada()
    tam = c.get("tam", 92 if len(c["texto"]) < 50 else 78)
    linhas, _ = layout_frase(c["texto"], c.get("destaque", []), tam, 900)
    alt = len(linhas) * int(tam * 1.16) + (160 if c.get("apoio") else 0)
    y = int((TOPO_SEGURO + ctx.limite) / 2 - alt / 2)
    rotulo(cam, c.get("rotulo"), y - 100, ease(t / 0.4))
    yf = desenhar_frase(cam, ctx.rec.metal, c["texto"], c.get("destaque", []), tam, y, t, passo=0.06)
    if c.get("apoio"):
        a = ease((t - 0.25 - 0.06 * len(c["texto"].split())) / 0.5)
        texto_simples(cam, c["apoio"], fonte("regular", 44), yf + 44 + int(16 * (1 - a)), PRATA, a)
    return cam


def _icone_check(d, x, y, r, alfa, ok=True):
    if ok:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*OFF, int(255 * alfa)))
        d.line([(x - r * 0.45, y + r * 0.02), (x - r * 0.1, y + r * 0.38), (x + r * 0.48, y - r * 0.35)],
               fill=(*PRETO, int(255 * alfa)), width=max(3, int(r * 0.22)), joint="curve")
    else:
        d.ellipse([x - r, y - r, x + r, y + r], outline=(*SUAVE, int(255 * alfa)), width=3)
        k = r * 0.38
        d.line([(x - k, y - k), (x + k, y + k)], fill=(*SUAVE, int(255 * alfa)), width=4)
        d.line([(x - k, y + k), (x + k, y - k)], fill=(*SUAVE, int(255 * alfa)), width=4)


def tempos_lista(c):
    n = len(c["itens"])
    return [0.55 + i * c.get("intervalo", 0.62) for i in range(n)]


def cena_lista(c, t, dur, ctx):
    cam = _camada()
    d = ImageDraw.Draw(cam)
    n = len(c["itens"])
    alt_item = 150 if n <= 4 else 124
    titulo = c.get("titulo", "")
    tam_t = 74 if len(titulo) < 40 else 64
    linhas, _ = layout_frase(titulo, c.get("destaque", []), tam_t, 900) if titulo else ([], 0)
    alt_tit = len(linhas) * int(tam_t * 1.16)
    total = alt_tit + (50 if titulo else 0) + n * alt_item
    y = max(TOPO_SEGURO + 30, int((TOPO_SEGURO + ctx.limite) / 2 - total / 2))
    if titulo:
        y = desenhar_frase(cam, ctx.rec.metal, titulo, c.get("destaque", []), tam_t, y, t, passo=0.05) + 50
    tempos = tempos_lista(c)
    f = fonte("semi", 44 if n <= 4 else 40)
    fn = fonte("serif", 54)
    for i, item in enumerate(c["itens"]):
        a = ease_out((t - tempos[i]) / 0.38)
        if a <= 0:
            continue
        x = 90 + int(70 * (1 - a))
        caixa = [x, y + i * alt_item, x + 900, y + i * alt_item + alt_item - 22]
        d.rounded_rectangle(caixa, radius=28, fill=(*GRAFITE, int(235 * a)), outline=(*GRAFITE2, int(255 * a)), width=2)
        # brilho metálico fino no topo do cartão
        d.line([(caixa[0] + 30, caixa[1] + 1), (caixa[2] - 30, caixa[1] + 1)], fill=(120, 126, 136, int(200 * a)), width=2)
        num = f"{i + 1:02d}"
        cy = (caixa[1] + caixa[3]) / 2
        if c.get("negativo"):
            _icone_check(d, caixa[0] + 62, cy, 24, a, ok=False)
        elif c.get("check"):
            _icone_check(d, caixa[0] + 62, cy, 24, a)
        else:
            d.text((caixa[0] + 34, cy - 34), num, font=fn, fill=(*OURO, int(255 * a)))
        tx = caixa[0] + 130
        from src.render import quebrar
        ls = quebrar(d, item, f, 740)
        ty = cy - len(ls) * f.size * 0.62
        for l in ls:
            d.text((tx, ty), l, font=f, fill=(*OFF, int(255 * a)))
            ty += int(f.size * 1.22)
    return cam


def _aparelho(tela, larg):
    """Moldura de celular grafite com borda metálica em volta da tela da demonstração."""
    esc = larg / tela.width
    tw, th = larg, int(tela.height * esc)
    tela = tela.resize((tw, th), Image.LANCZOS)
    b = 18
    im = Image.new("RGBA", (tw + 2 * b, th + 2 * b), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=78, fill=(12, 12, 14, 255),
                        outline=(112, 118, 128, 255), width=3)
    d.rounded_rectangle([5, 5, im.width - 6, im.height - 6], radius=74, outline=(40, 42, 48, 255), width=2)
    im.alpha_composite(tela, (b, b))
    # degradê no pé (a tela é um recorte do topo do aparelho)
    deg = Image.new("RGBA", (im.width, 220), (0, 0, 0, 0))
    a = np.linspace(0, 255, 220).astype("uint8")
    arr = np.zeros((220, im.width, 4), dtype="uint8")
    arr[..., :3] = PRETO
    arr[..., 3] = a[:, None]
    deg = Image.fromarray(arr, "RGBA")
    im.alpha_composite(deg, (0, im.height - 220))
    return im


def _sombra(w, h, raio, blur=40, alfa=170):
    s = Image.new("RGBA", (w + 4 * blur, h + 4 * blur), (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle([2 * blur, 2 * blur, 2 * blur + w, 2 * blur + h], radius=raio,
                                        fill=(0, 0, 0, alfa))
    return s.filter(ImageFilter.GaussianBlur(blur))


@lru_cache(maxsize=16)
def _aparelho_cache(chave, larg):
    tela = _TELAS[chave]
    ap = _aparelho(tela, larg)
    return ap, _sombra(ap.width, ap.height, 78)


_TELAS = {}


def tempos_celular(c):
    return [0.9 + i * c.get("intervalo", 0.75) for i in range(len(c.get("chips", [])))]


def cena_celular(c, t, dur, ctx):
    cam = _camada()
    v = {"tipo": c.get("tela", "site"), **c.get("demo", {})}
    chave = json.dumps(v, sort_keys=True)
    if chave not in _TELAS:
        _TELAS[chave] = ctx.rec.tela(ctx.cfg, v)
    larg = 660 if ctx.limite > 1400 else 600
    ap, sombra = _aparelho_cache(chave, larg)
    y_tit = TOPO_SEGURO + 10
    if c.get("titulo"):
        y_fim = desenhar_frase(cam, ctx.rec.metal, c["titulo"], c.get("destaque", []), 66, y_tit, t, passo=0.05,
                               largura=900)
    else:
        y_fim = y_tit
    a = ease_out(t / 0.7)
    flut = math.sin(t * 1.6) * 8
    x = (W - ap.width) // 2
    y_alvo = y_fim + 40
    y = int(y_alvo + 260 * (1 - a) + flut)
    vis = ctx.limite - y
    sombra_a = sombra.copy()
    sombra_a.putalpha(sombra.getchannel("A").point(lambda p: int(p * a)))
    cam.alpha_composite(sombra_a, (x - 80, y - 50))
    ap_a = ap.crop((0, 0, ap.width, max(10, min(ap.height, vis))))
    if a < 1:
        ap_a = ap_a.copy()
        ap_a.putalpha(ap_a.getchannel("A").point(lambda p: int(p * a)))
    cam.alpha_composite(ap_a, (x, y))
    # destaques flutuantes alternando lados, ligados ao aparelho por um fio
    d = ImageDraw.Draw(cam)
    f = fonte("semi", 36)
    for i, (txt, ti) in enumerate(zip(c.get("chips", []), tempos_celular(c))):
        b = ease_back((t - ti) / 0.45)
        al = ease((t - ti) / 0.3)
        if al <= 0:
            continue
        w = d.textlength(txt, font=f) + 110
        lado = i % 2
        cy = y_alvo + 230 + i * 170 + math.sin(t * 2 + i) * 5
        if cy > ctx.limite - 60:
            cy = ctx.limite - 60 - (len(c["chips"]) - 1 - i) * 110
        cx = 60 if lado == 0 else W - 60 - w
        cx += (1 - b) * (-80 if lado == 0 else 80)
        caixa = [cx, cy, cx + w, cy + 84]
        d.rounded_rectangle([caixa[0] + 6, caixa[1] + 10, caixa[2] + 6, caixa[3] + 10], radius=42,
                            fill=(0, 0, 0, int(110 * al)))
        d.rounded_rectangle(caixa, radius=42, fill=(*OFF, int(250 * al)))
        d.ellipse([caixa[0] + 24, cy + 22, caixa[0] + 64, cy + 62], fill=(*PRETO, int(255 * al)))
        d.line([(caixa[0] + 35, cy + 43), (caixa[0] + 42, cy + 51), (caixa[0] + 55, cy + 34)],
               fill=(*OFF, int(255 * al)), width=5)
        d.text((caixa[0] + 82, cy + 20), txt, font=f, fill=(*PRETO, int(255 * al)))
    if c.get("aviso", True):
        fa = fonte("regular", 24)
        txt = "Demonstração ilustrativa · nomes fictícios"
        d.text(((W - d.textlength(txt, font=fa)) / 2, ctx.limite + 8 if ctx.limite < 1400 else 1530), txt,
               font=fa, fill=(*SUAVE, int(200 * a)))
    return cam


def cena_comparacao(c, t, dur, ctx):
    cam = _camada()
    d = ImageDraw.Draw(cam)
    y = TOPO_SEGURO + 20
    if c.get("titulo"):
        y = desenhar_frase(cam, ctx.rec.metal, c["titulo"], c.get("destaque", []), 70, y, t, passo=0.05) + 30
    f_t = fonte("bold", 42)
    f_i = fonte("semi", 40)
    lados = [(c["sem"], False, 0.35), (c["com"], True, 0.35 + c.get("intervalo", 1.6))]
    alturas = [150 + len(b["itens"]) * 70 for b, _, _ in lados]
    total = sum(alturas) + 40
    y = max(y, int((y + ctx.limite) / 2 - total / 2))
    for k, (bloco, ok, ti) in enumerate(lados):
        a = ease_out((t - ti) / 0.45)
        if a <= 0:
            continue
        top = y + (alturas[0] + 40 if k else 0) + int(60 * (1 - a))
        caixa = [90, top, 990, top + alturas[k]]
        if ok:
            d.rounded_rectangle(caixa, radius=34, fill=(*OFF, int(250 * a)))
            cor_t, cor_i = PRETO, (40, 42, 48)
        else:
            d.rounded_rectangle(caixa, radius=34, fill=(*GRAFITE, int(200 * a)), outline=(*GRAFITE2, int(255 * a)), width=2)
            cor_t, cor_i = SUAVE, (150, 154, 162)
        d.text((caixa[0] + 50, top + 40), bloco["titulo"].upper(), font=f_t, fill=(*cor_t, int(255 * a)))
        yy = top + 115
        for j, item in enumerate(bloco["itens"]):
            aj = ease((t - ti - 0.25 - j * 0.22) / 0.3)
            if aj <= 0:
                yy += 70
                continue
            if ok:
                d.ellipse([caixa[0] + 50, yy + 6, caixa[0] + 86, yy + 42], fill=(*PRETO, int(255 * aj)))
                d.line([(caixa[0] + 59, yy + 25), (caixa[0] + 66, yy + 33), (caixa[0] + 78, yy + 16)],
                       fill=(*OFF, int(255 * aj)), width=4)
            else:
                d.line([(caixa[0] + 56, yy + 12), (caixa[0] + 80, yy + 36)], fill=(*SUAVE, int(255 * aj)), width=4)
                d.line([(caixa[0] + 56, yy + 36), (caixa[0] + 80, yy + 12)], fill=(*SUAVE, int(255 * aj)), width=4)
            d.text((caixa[0] + 110, yy), item, font=f_i, fill=(*cor_i, int(255 * aj)))
            yy += 70
    return cam


_IMGS = {}


def cena_imagem(c, t, dur, ctx):
    cam = _camada()
    arq = RAIZ / c["arquivo"]
    if arq not in _IMGS:
        im = Image.open(arq).convert("RGB")
        larg = 880
        fg = im.resize((larg, int(im.height * larg / im.width)), Image.LANCZOS)
        m = Image.new("L", fg.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, fg.width - 1, fg.height - 1], radius=36, fill=255)
        fg = fg.convert("RGBA")
        fg.putalpha(m)
        _IMGS[arq] = (fg, _sombra(fg.width, fg.height, 36, 50, 200))
    fg, sombra = _IMGS[arq]
    a = ease_out(t / 0.6)
    esc = 0.94 + 0.06 * a + 0.025 * (t / max(dur, 0.1))
    w, h = int(fg.width * esc), int(fg.height * esc)
    img = fg.resize((w, h), Image.BILINEAR)
    x = (W - w) // 2
    y = int((TOPO_SEGURO + ctx.limite) / 2 - h / 2 + 30 * (1 - a))
    if c.get("titulo"):
        y = max(y, TOPO_SEGURO + 200)
        desenhar_frase(cam, ctx.rec.metal, c["titulo"], c.get("destaque", []), 62, TOPO_SEGURO, t, passo=0.05)
    cam.alpha_composite(sombra, (x - 100 + (w - fg.width) // 2, y - 100 + (h - fg.height) // 2))
    if a < 1:
        img.putalpha(img.getchannel("A").point(lambda p: int(p * a)))
    cam.alpha_composite(img, (x, y))
    return cam


def cena_cta(c, t, dur, ctx):
    cam = _camada()
    d = ImageDraw.Draw(cam)
    tam = 84 if len(c["texto"]) < 44 else 72
    linhas, _ = layout_frase(c["texto"], c.get("destaque", []), tam, 900)
    alt = len(linhas) * int(tam * 1.16) + 330
    y = int((TOPO_SEGURO + ctx.limite) / 2 - alt / 2)
    y = desenhar_frase(cam, ctx.rec.metal, c["texto"], c.get("destaque", []), tam, y, t, passo=0.05)
    a = ease_back((t - 0.55) / 0.5)
    al = ease((t - 0.55) / 0.3)
    if al > 0:
        txt = c.get("acao") or f"Comente {c.get('_palavra', 'SITE')}"
        f = fonte("bold", 46)
        for tam_b in (46, 42, 38, 34):
            f = fonte("bold", tam_b)
            if d.textlength(txt, font=f) + 150 <= 960:
                break
        w = d.textlength(txt, font=f) + 150
        pulso = 1 + 0.025 * math.sin(max(0, t - 1.2) * 5)
        hh = 112 * pulso
        ww = w * pulso * (0.7 + 0.3 * a)
        yb = y + 60
        caixa = [W / 2 - ww / 2, yb, W / 2 + ww / 2, yb + hh]
        d.rounded_rectangle([caixa[0], caixa[1] + 12, caixa[2], caixa[3] + 12], radius=56, fill=(0, 0, 0, int(120 * al)))
        d.rounded_rectangle(caixa, radius=56, fill=(*OFF, int(255 * al)))
        cy = yb + hh / 2
        if txt.lower().startswith("comente"):  # balão de comentário
            d.rounded_rectangle([caixa[0] + 36, cy - 17, caixa[0] + 76, cy + 13], radius=9, fill=(*PRETO, int(255 * al)))
            d.polygon([(caixa[0] + 44, cy + 10), (caixa[0] + 56, cy + 10), (caixa[0] + 42, cy + 24)], fill=(*PRETO, int(255 * al)))
        else:
            d.ellipse([caixa[0] + 40, cy - 15, caixa[0] + 70, cy + 15], fill=(*OURO, int(255 * al)))
        d.text((caixa[0] + 92, yb + hh / 2 - f.size * 0.62), txt, font=f, fill=(*PRETO, int(255 * al)))
        a2 = ease((t - 0.9) / 0.4)
        y2 = yb + hh + 50
        linha2 = c.get("detalhe") or ("que eu te mando um exemplo no Direct" if txt.lower().startswith("comente")
                                     else ctx.cfg.get("whatsapp", ""))
        y3 = texto_simples(cam, linha2, fonte("semi", 42), y2, OFF, a2)
        rod = c.get("rodape") or ("WhatsApp no link da bio" if txt.lower().startswith("comente") else "ou no direct do @gnz01_")
        texto_simples(cam, rod, fonte("regular", 36), y3 + 16, SUAVE, a2)
    return cam


def cena_marca(c, t, dur, ctx):
    cam = _camada()
    d = ImageDraw.Draw(cam)
    a = ease_out(t / 0.5)
    f = fonte("bold", int(200 * (0.9 + 0.1 * a)))
    txt = "GNZ01_"
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    x, y = (W - w) // 2, 760
    m = Image.new("L", (w + 20, h + 20), 0)
    ImageDraw.Draw(m).text((10 - bb[0], 10 - bb[1]), txt, font=f, fill=int(255 * a))
    pedaco = ctx.rec.metal.crop((x, y - 160, x + w + 20, y - 160 + h + 20)).convert("RGBA")
    # reflexo metálico que passa pela marca
    s = (t - 0.3) / 0.9
    if 0 < s < 1:
        brilho = Image.new("L", pedaco.size, 0)
        bx = int(-200 + s * (pedaco.width + 400))
        ImageDraw.Draw(brilho).polygon([(bx, 0), (bx + 90, 0), (bx + 30, pedaco.height), (bx - 60, pedaco.height)],
                                       fill=170)
        brilho = brilho.filter(ImageFilter.GaussianBlur(12))
        pedaco = Image.composite(Image.new("RGBA", pedaco.size, (255, 255, 255, 255)), pedaco, brilho)
    pedaco.putalpha(m)
    cam.alpha_composite(pedaco, (x - 10, y - 10))
    a2 = ease((t - 0.35) / 0.5)
    d.rectangle([W / 2 - 160 * a2, y + h + 60, W / 2 + 160 * a2, y + h + 62], fill=(*OURO, int(200 * a2)))
    texto_simples(cam, "DESIGN.  DEVELOPMENT.  DIGITAL.", fonte("semi", 34), y + h + 100, OFF, a2)
    a3 = ease((t - 0.7) / 0.5)
    texto_simples(cam, f"WhatsApp {ctx.cfg.get('whatsapp', '')}  ·  @gnz01_", fonte("semi", 36), y + h + 210, OURO, a3)
    return cam


def _pedacos_cineticos(c, dur):
    """Divide a fala em pedaços de até 3 palavras (quebra na pontuação) com o tempo de entrada de cada um."""
    pals = c.get("_pals")
    if pals:
        atraso = c.get("_atraso", 0.22)
        pals = [{**p, "ini": p["ini"] + atraso} for p in pals]
    else:
        txt = c.get("fala") or c.get("texto", "")
        pals = _palavras_estimadas(txt, max(0.5, dur - 0.8))
        pals = [{**p, "ini": p["ini"] + 0.15} for p in pals]
    out, atual = [], []
    for p in pals:
        atual.append(p)
        if len(atual) >= c.get("palavras_por_vez", 3) or re.search(r"[.,!?:;]$", p["palavra"]):
            out.append((atual[0]["ini"], " ".join(x["palavra"] for x in atual)))
            atual = []
    if atual:
        out.append((atual[0]["ini"], " ".join(x["palavra"] for x in atual)))
    return out


def tempos_cinetico(c, dur):
    return [ti for ti, _ in _pedacos_cineticos(c, dur)]


def tempos_busca(c):
    n0 = 0.35 + 0.035 * len(c.get("busca", "")) + 0.25
    return [n0 + i * c.get("intervalo", 0.5) for i in range(len(c.get("resultados", [])))]


def cena_busca(c, t, dur, ctx):
    """Cliente pesquisando: a busca é digitada e os resultados entram (concorrentes com site x quem não tem)."""
    cam = _camada()
    d = ImageDraw.Draw(cam)
    alt_t = (len(layout_frase(c["titulo"], c.get("destaque", []), 66, 900)[0]) * int(66 * 1.16) + 40) if c.get("titulo") else 0
    total = alt_t + 150 + len(c.get("resultados", [])) * 200
    y = max(TOPO_SEGURO + 20, int((TOPO_SEGURO + ctx.limite) / 2 - total / 2))
    if c.get("titulo"):
        y = desenhar_frase(cam, ctx.rec.metal, c["titulo"], c.get("destaque", []), 66, y, t, passo=0.05) + 40
    a = ease_out(t / 0.35)
    caixa = [80, y + int(40 * (1 - a)), 1000, y + 110 + int(40 * (1 - a))]
    d.rounded_rectangle(caixa, radius=55, fill=(*OFF, int(250 * a)))
    cx, cy = caixa[0] + 58, (caixa[1] + caixa[3]) / 2
    d.ellipse([cx - 18, cy - 18, cx + 12, cy + 12], outline=(*PRETO, int(255 * a)), width=5)
    d.line([(cx + 8, cy + 8), (cx + 22, cy + 22)], fill=(*PRETO, int(255 * a)), width=6)
    q = c.get("busca", "")
    k = int(max(0, (t - 0.35) / 0.035))
    vis = q[:k]
    f = fonte("semi", 40)
    d.text((caixa[0] + 105, cy - 26), vis, font=f, fill=(*PRETO, int(255 * a)))
    if k <= len(q) or int(t * 3) % 2:
        xc = caixa[0] + 108 + d.textlength(vis, font=f)
        d.rectangle([xc, cy - 24, xc + 3, cy + 24], fill=(*PRETO, int(255 * a)))
    y = caixa[3] + 40
    for i, (r, ti) in enumerate(zip(c.get("resultados", []), tempos_busca(c))):
        b = ease_out((t - ti) / 0.4)
        if b <= 0:
            continue
        top = y + i * 200 + int(70 * (1 - b))
        if top + 170 > ctx.limite:
            break
        fraco = r.get("fraco")
        cx0 = 80
        if fraco:
            d.rounded_rectangle([cx0, top, 1000, top + 170], radius=28, fill=(*GRAFITE, int(220 * b)),
                                outline=(*GRAFITE2, int(255 * b)), width=2)
            cor1, cor2 = SUAVE, (110, 114, 122)
        else:
            d.rounded_rectangle([cx0 + 6, top + 12, 1006, top + 182], radius=28, fill=(0, 0, 0, int(110 * b)))
            d.rounded_rectangle([cx0, top, 1000, top + 170], radius=28, fill=(*OFF, int(250 * b)))
            cor1, cor2 = PRETO, (70, 74, 82)
            # miniatura do site
            d.rounded_rectangle([780, top + 26, 970, top + 144], radius=14, fill=(*GRAFITE, int(255 * b)))
            d.rectangle([800, top + 46, 900, top + 58], fill=(*OFF, int(220 * b)))
            d.rectangle([800, top + 70, 940, top + 78], fill=(*SUAVE, int(220 * b)))
            d.rounded_rectangle([800, top + 100, 880, top + 126], radius=13, fill=(*OURO, int(255 * b)))
        d.text((cx0 + 36, top + 26), r.get("url", ""), font=fonte("regular", 28), fill=(*cor2, int(255 * b)))
        d.text((cx0 + 36, top + 66), r["titulo"], font=fonte("bold", 42), fill=(*cor1, int(255 * b)))
        if r.get("linha"):
            d.text((cx0 + 36, top + 120), r["linha"], font=fonte("regular", 28), fill=(*cor2, int(255 * b)))
    if c.get("aviso", True):
        fa = fonte("regular", 24)
        txt = "Demonstração ilustrativa · nomes fictícios"
        d.text(((W - d.textlength(txt, font=fa)) / 2, ctx.limite + 8 if ctx.limite < 1400 else 1530), txt,
               font=fa, fill=(*SUAVE, int(200 * a)))
    return cam


def _tela_cache(ctx, v):
    chave = json.dumps(v, sort_keys=True)
    if chave not in _TELAS:
        _TELAS[chave] = ctx.rec.tela(ctx.cfg, v)
    return chave


def cena_montagem(c, t, dur, ctx):
    """Montagem rápida de modelos de site (um celular por nicho entrando em chicote) com rótulo do nicho."""
    cam = _camada()
    y_tit = TOPO_SEGURO + 10
    y_fim = y_tit
    if c.get("titulo"):
        y_fim = desenhar_frase(cam, ctx.rec.metal, c["titulo"], c.get("destaque", []), 70, y_tit, t, passo=0.08)
    modelos = c["modelos"]
    n = len(modelos)
    passo = max(0.8, (dur - 0.5) / n)
    i = min(n - 1, int(max(0, t - 0.25) / passo))
    tl = max(0, t - 0.25) - i * passo
    m = modelos[i]
    chave = _tela_cache(ctx, m["tela"])
    larg = 560
    ap, sombra = _aparelho_cache(chave, larg)
    e_in = ease_out(tl / 0.28)
    e_out = ease((tl - (passo - 0.2)) / 0.2) if i < n - 1 else 0
    x = (W - ap.width) // 2 + int(700 * (1 - e_in)) - int(700 * e_out)
    y = y_fim + 150 + int(math.sin(t * 1.6) * 6)
    vis = ctx.limite - y
    cam.alpha_composite(sombra, (x - 80, y - 50))
    cam.alpha_composite(ap.crop((0, 0, ap.width, max(10, min(ap.height, vis)))), (x, y))
    d = ImageDraw.Draw(cam)
    f = fonte("bold", 40)
    txt = m["rotulo"].upper()
    w = d.textlength(txt, font=f) + 80
    b = ease_back(tl / 0.35)
    yb = y_fim + 50
    caixa = [W / 2 - w / 2 * b, yb, W / 2 + w / 2 * b, yb + 76]
    if b > 0.05:
        d.rounded_rectangle(caixa, radius=38, fill=(*OFF, 250))
        if b > 0.8:
            d.text((W / 2 - (w - 80) / 2, yb + 16), txt, font=f, fill=(*PRETO, 255))
    for k in range(n):
        cx = W / 2 + (k - (n - 1) / 2) * 34
        d.ellipse([cx - 7, ctx.limite - 30, cx + 7, ctx.limite - 16], fill=(*OFF, 230) if k <= i else (*SUAVE, 90))
    fa = fonte("regular", 24)
    av = "Modelos ilustrativos · nomes fictícios"
    d.text(((W - d.textlength(av, font=fa)) / 2, ctx.limite + 8 if ctx.limite < 1400 else 1530), av, font=fa,
           fill=(*SUAVE, 200))
    return cam


_NOTE = {}


def _notebook(v, larg):
    chave = (json.dumps(v, sort_keys=True), larg)
    if chave not in _NOTE:
        from src.showcase import tela_desktop
        tela = tela_desktop(v)
        tw = larg - 40
        th = int(tw * tela.height / tela.width)
        im = Image.new("RGBA", (larg + 120, th + 40 + 46), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([60, 0, 60 + larg, th + 40], radius=24, fill=(14, 14, 16, 255), outline=(112, 118, 128, 255),
                            width=3)
        im.paste(tela.resize((tw, th), Image.LANCZOS), (80, 20))
        d.polygon([(0, th + 40), (larg + 120, th + 40), (larg + 70, th + 40 + 40), (50, th + 40 + 40)],
                  fill=(150, 154, 160, 255))
        d.rectangle([larg / 2 + 10, th + 40, larg / 2 + 110, th + 48], fill=(110, 114, 120, 255))
        _NOTE[chave] = (im, _sombra(im.width, im.height, 24))
    return _NOTE[chave]


def tempos_dispositivos(c):
    return [1.0 + i * c.get("intervalo", 0.7) for i in range(len(c.get("chips", [])))]


def cena_dispositivos(c, t, dur, ctx):
    """O mesmo site no notebook e no celular, com destaques (serviços, portfólio, WhatsApp...) entrando."""
    cam = _camada()
    v = {"tipo": "site", **c.get("demo", {})}
    nb, snb = _notebook(v, 860)
    alt_t = (len(layout_frase(c["titulo"], c.get("destaque", []), 66, 900)[0]) * int(66 * 1.16) + 20) if c.get("titulo") else 0
    total = alt_t + 60 + nb.height + 10 + len(c.get("chips", [])) * 100
    y = max(TOPO_SEGURO + 10, int((TOPO_SEGURO + ctx.limite) / 2 - total / 2) - 60)
    if c.get("titulo"):
        y = desenhar_frase(cam, ctx.rec.metal, c["titulo"], c.get("destaque", []), 66, y, t, passo=0.05) + 20
    a = ease_out(t / 0.6)
    xn = (W - nb.width) // 2 - 40
    yn = y + 60 + int(200 * (1 - a)) + int(math.sin(t * 1.3) * 5)
    cam.alpha_composite(snb, (xn - 80, yn - 50))
    nb_a = nb.copy()
    if a < 1:
        nb_a.putalpha(nb.getchannel("A").point(lambda p: int(p * a)))
    cam.alpha_composite(nb_a, (xn, yn))
    chave = _tela_cache(ctx, v)
    ap, sombra = _aparelho_cache(chave, 300)
    b = ease_back((t - 0.35) / 0.55)
    xp = W - ap.width - 50 + int(500 * (1 - b))
    yp = yn + nb.height - 260 + int(math.sin(t * 1.7 + 1) * 7)
    vis = ctx.limite - yp
    if b > 0:
        cam.alpha_composite(sombra.resize((sombra.width * 300 // 600, sombra.height * 300 // 600)), (xp - 40, yp - 25))
        cam.alpha_composite(ap.crop((0, 0, ap.width, max(10, min(ap.height, vis)))), (xp, yp))
    d = ImageDraw.Draw(cam)
    f = fonte("semi", 36)
    for i, (txt, ti) in enumerate(zip(c.get("chips", []), tempos_dispositivos(c))):
        bb = ease_back((t - ti) / 0.45)
        al = ease((t - ti) / 0.3)
        if al <= 0:
            continue
        w = d.textlength(txt, font=f) + 110
        cx = 60 + (1 - bb) * -80
        cy = yn + nb.height + 10 + i * 100
        if cy + 84 > ctx.limite:
            cy = ctx.limite - 84 - (len(c["chips"]) - 1 - i) * 96
        caixa = [cx, cy, cx + w, cy + 84]
        d.rounded_rectangle([caixa[0] + 6, caixa[1] + 10, caixa[2] + 6, caixa[3] + 10], radius=42,
                            fill=(0, 0, 0, int(110 * al)))
        verde = "whatsapp" in txt.lower()
        d.rounded_rectangle(caixa, radius=42, fill=(*(OURO if verde else OFF), int(250 * al)))
        d.ellipse([caixa[0] + 24, cy + 22, caixa[0] + 64, cy + 62], fill=(*PRETO, int(255 * al)))
        d.line([(caixa[0] + 35, cy + 43), (caixa[0] + 42, cy + 51), (caixa[0] + 55, cy + 34)],
               fill=(*OFF, int(255 * al)), width=5)
        d.text((caixa[0] + 82, cy + 20), txt, font=f, fill=(*PRETO, int(255 * al)))
    fa = fonte("regular", 24)
    av = "Demonstração ilustrativa · nomes fictícios"
    d.text(((W - d.textlength(av, font=fa)) / 2, ctx.limite + 8 if ctx.limite < 1400 else 1530), av, font=fa,
           fill=(*SUAVE, int(200 * a)))
    return cam


def cena_cinetico(c, t, dur, ctx):
    """Tipografia cinética: a fala aparece em pedaços grandes, batendo junto com a voz (sem legenda embaixo)."""
    cam = _camada()
    if "_pedacos" not in c:
        c["_pedacos"] = _pedacos_cineticos(c, dur)
    ped = c["_pedacos"]
    atual = [x for x in ped if x[0] <= t]
    if not atual:
        rotulo(cam, c.get("rotulo"), 560, ease((t + 0.2) / 0.3))
        return cam
    ti, txt = atual[-1]
    idx = len(atual) - 1
    dt = t - ti
    base = c.get("tam", 132 if len(txt) <= 16 else 112)
    tam = int(round(base * (1 + 0.22 * (1 - ease_out(dt / 0.2))) / 4) * 4)
    linhas, _ = layout_frase(txt, c.get("destaque", []), tam, 920)
    alt = len(linhas) * int(tam * 1.1)
    meio = (TOPO_SEGURO + ctx.limite) / 2
    y = int(meio - alt / 2 + (idx % 2) * 30 - 15)
    rotulo(cam, c.get("rotulo"), y - 120, 1.0)
    yf = desenhar_frase(cam, ctx.rec.metal, txt, c.get("destaque", []), tam, y, 10, entrelinha=1.1, sublinhar=False)
    d = ImageDraw.Draw(cam)
    g = ease_out(dt / 0.35)
    larg = 220 * g
    d.rectangle([W / 2 - larg, yf + 30, W / 2 + larg, yf + 36], fill=(*PRATA, 220))
    # marcadores de progresso da frase
    n = len(ped)
    for k in range(n):
        cx = W / 2 + (k - (n - 1) / 2) * 34
        on = k <= idx
        d.ellipse([cx - 7, yf + 80 - 7, cx + 7, yf + 80 + 7], fill=(*OFF, 230) if on else (*SUAVE, 90))
    return cam


CENAS = {"busca": cena_busca, "montagem": cena_montagem, "dispositivos": cena_dispositivos,
         "cinetico": cena_cinetico, "gancho": cena_gancho, "texto": cena_texto, "lista": cena_lista, "celular": cena_celular,
         "comparacao": cena_comparacao, "imagem": cena_imagem, "cta": cena_cta, "marca": cena_marca}


# ------------------------------------------------------------------ legendas da narração
def blocos_legenda(palavras, max_chars=24, max_palavras=4):
    """Agrupa palavras (com tempos globais) em blocos curtos e equilibrados, sem atravessar pontuação."""
    frases, atual = [], []
    for p in palavras:
        atual.append(p)
        if re.search(r"[.,!?:;]$", p["palavra"]):
            frases.append(atual)
            atual = []
    if atual:
        frases.append(atual)
    blocos = []
    for fr in frases:
        chars = len(" ".join(p["palavra"] for p in fr))
        n = max(1, math.ceil(len(fr) / max_palavras), math.ceil(chars / max_chars))
        tam = len(fr) / n
        for k in range(n):
            pedaco = fr[round(k * tam):round((k + 1) * tam)]
            if pedaco:
                blocos.append(pedaco)
    out = []
    for i, b in enumerate(blocos):
        ini = b[0]["ini"]
        fim = blocos[i + 1][0]["ini"] if i + 1 < len(blocos) and blocos[i + 1][0]["ini"] - b[-1]["fim"] < 0.6 \
            else b[-1]["fim"] + 0.25
        out.append({"ini": ini, "fim": fim, "palavras": b})
    return out


def desenhar_legenda(frame, blocos, tg, destaques):
    for b in blocos:
        if b["ini"] - 0.03 <= tg < b["fim"]:
            break
    else:
        return
    cam = _camada()
    d = ImageDraw.Draw(cam)
    f = fonte("bold", 58)
    esp = 24
    pals = [p["palavra"] for p in b["palavras"]]
    larguras = [d.textlength(p, font=f) for p in pals]
    total = sum(larguras) + esp * (len(pals) - 1)
    linhas = [list(range(len(pals)))]
    if total > 900:
        meio = len(pals) // 2
        linhas = [list(range(meio)), list(range(meio, len(pals)))]
    a = ease((tg - b["ini"]) / 0.12)
    y = BASE_LEGENDA + 30 + int(10 * (1 - a))
    for ln in linhas:
        lw = sum(larguras[i] for i in ln) + esp * (len(ln) - 1)
        x = (W - lw) / 2
        for i in ln:
            p = b["palavras"][i]
            ativa = p["ini"] - 0.02 <= tg < max(p["fim"], p["ini"] + 0.12)
            dest = _limpa(p["palavra"]) in destaques
            if ativa:
                d.rounded_rectangle([x - 12, y - 4, x + larguras[i] + 12, y + 72], radius=14, fill=(*OFF, int(240 * a)))
                d.text((x, y), pals[i], font=f, fill=(*PRETO, int(255 * a)))
            else:
                d.text((x, y), pals[i], font=f, fill=((*PRATA, int(255 * a)) if dest else (255, 255, 255, int(255 * a))),
                       stroke_width=5, stroke_fill=(0, 0, 0, int(170 * a)))
            x += larguras[i] + esp
        y += 82
    frame.alpha_composite(cam)


def srt(blocos):
    def ts(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    return "\n".join(f"{i + 1}\n{ts(b['ini'])} --> {ts(b['fim'])}\n{' '.join(p['palavra'] for p in b['palavras'])}\n"
                     for i, b in enumerate(blocos))


# ------------------------------------------------------------------ montagem
def _palavras_estimadas(texto, dur):
    """Sem tempos da voz: distribui as palavras proporcionalmente ao número de letras."""
    ps = texto.split()
    pesos = np.array([len(p) + 2 for p in ps], dtype=float)
    acum = np.concatenate([[0], np.cumsum(pesos)]) / pesos.sum() * dur
    return [{"palavra": p, "ini": acum[i], "fim": acum[i + 1]} for i, p in enumerate(ps)]


def _alinhar(pals, fala):
    """A voz devolve as palavras sem pontuação; recoloca a grafia do roteiro (vírgulas, pontos, interrogação)."""
    tokens = fala.split()
    j = 0
    out = []
    for p in pals:
        alvo = _limpa(p["palavra"])
        for k in range(j, min(j + 4, len(tokens))):
            tk = _limpa(tokens[k])
            if tk == alvo or (alvo and (tk.startswith(alvo) or alvo.startswith(tk))):
                out.append({**p, "palavra": tokens[k]})
                j = k + 1
                break
        else:
            out.append(p)
    return out


def duracao_leitura(c):
    """Tempo mínimo de tela para quem lê sem som."""
    txt = " ".join(str(c.get(k, "")) for k in ("texto", "titulo", "apoio", "acao"))
    txt += " " + " ".join(c.get("itens", []) + c.get("chips", []))
    for k in ("sem", "com"):
        if k in c:
            txt += " " + " ".join(c[k]["itens"])
    if c["tipo"] == "cinetico":
        return max(2.0, len((c.get("fala") or c.get("texto", "")).split()) * 0.36 + 0.9)
    if c["tipo"] == "busca":
        return max(3.0, tempos_busca(c)[-1] + 1.5 if c.get("resultados") else 3.0)
    if c["tipo"] == "montagem":
        return max(4.0, 1.0 * len(c["modelos"]) + 0.6)
    if c["tipo"] == "dispositivos":
        return max(3.5, (tempos_dispositivos(c) or [0])[-1] + 1.5)
    base = {"gancho": 2.2, "texto": 2.4, "lista": 1.2, "celular": 2.4, "comparacao": 2.6, "imagem": 2.6,
            "cta": 3.2, "marca": 2.2}[c["tipo"]]
    extra = len(txt.split()) * 0.27
    if c["tipo"] == "lista":
        extra = max(extra, tempos_lista(c)[-1] + 1.4)
    if c["tipo"] == "celular":
        extra = max(extra, (tempos_celular(c) or [0])[-1] + 1.5)
    if c["tipo"] == "comparacao":
        extra = max(extra, 0.35 + c.get("intervalo", 1.6) + 0.5 + 0.22 * len(c["com"]["itens"]) + 1.0)
    return max(base, min(extra, 7.5)) if c["tipo"] != "marca" else base


def produzir(roteiro, cfg, saida, pasta_entrega=None, voz=None):
    """Produz o Reel completo. Devolve um dicionário de relatório (duração, narração, legendas...)."""
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    cenas = [dict(c) for c in roteiro["cenas"]]
    if not any(c["tipo"] == "marca" for c in cenas):
        cenas.append({"tipo": "marca"})
    semente = roteiro.get("semente", zlib.crc32(roteiro["id"].encode()) % 997)
    voz = voz or roteiro.get("voz", "masculina")
    rel = {"id": roteiro["id"], "narracao": None, "cenas": []}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # 1) narração por cena (define a duração de cada cena)
        provedor = None
        for c in cenas:
            if c["tipo"] == "cta":
                c["_palavra"] = cfg.get("cta", {}).get("palavras", {}).get(roteiro.get("tema"), "SITE")
        for i, c in enumerate(cenas):
            c["_dur"] = duracao_leitura(c)
            if c.get("fala"):
                arq = tmp / f"fala{i}.mp3"
                prov, pals = au.narrar(c["fala"], arq, voz)
                if prov:
                    provedor = prov
                    dur_fala = float(subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                        capture_output=True, text=True).stdout.strip())
                    c["_fala"] = arq
                    c["_pals"] = _alinhar(pals, c["fala"]) if pals else _palavras_estimadas(c["fala"], dur_fala)
                    c["_dur"] = max(c["_dur"] * 0.8, dur_fala + (1.4 if c["tipo"] == "cta" else 0.5))
                else:
                    provedor = None
                    break
        if provedor is None:  # sem voz: nenhuma cena usa narração (nunca metade com voz, metade sem)
            for c in cenas:
                c.pop("_fala", None)
                c.pop("_pals", None)
                c["_dur"] = duracao_leitura(c)
        rel["narracao"] = provedor
        com_legenda = provedor is not None
        # 2) linha do tempo
        t = 0.0
        falas, eventos, palavras = [], [], []
        destaques = set()
        for i, c in enumerate(cenas):
            c["_ini"] = t
            destaques |= {_limpa(x) for d in c.get("destaque", []) for x in d.split()}
            atraso_fala = 0.12 if i == 0 else 0.22
            c["_atraso"] = atraso_fala
            if c.get("_fala"):
                falas.append((t + atraso_fala, c["_fala"]))
                palavras += [{**p, "ini": p["ini"] + t + atraso_fala, "fim": p["fim"] + t + atraso_fala}
                             for p in c["_pals"]]
            if i == 0:
                eventos.append((0.0, "impacto", 0.9))
            else:
                eventos.append((t - 0.22, "whoosh", 0.8))
            if c["tipo"] == "lista":
                eventos += [(t + x, "clique", 0.9) for x in tempos_lista(c)]
            if c["tipo"] == "celular":
                eventos += [(t + x, "clique", 0.8) for x in tempos_celular(c)]
                eventos.append((t + 0.35, "notificacao", 0.7))
            if c["tipo"] == "busca":
                eventos += [(t + 0.35 + k * 0.035, "clique", 0.25) for k in range(0, len(c.get("busca", "")), 3)]
                eventos += [(t + x, "clique", 0.8) for x in tempos_busca(c)]
            if c["tipo"] == "dispositivos":
                eventos += [(t + x, "clique", 0.8) for x in tempos_dispositivos(c)]
            if c["tipo"] == "montagem":
                n = len(c["modelos"])
                pm = max(0.8, (c["_dur"] - 0.5) / n)
                eventos += [(t + 0.25 + k * pm - 0.1, "whoosh", 0.45) for k in range(1, n)]
            if c.get("notificacoes"):
                eventos += [(t + 0.05 + k * 0.42, "notificacao", 0.55) for k in range(len(c["notificacoes"]))]
            if c["tipo"] == "cinetico":
                eventos += [(t + x, "clique", 0.55) for x in tempos_cinetico(c, c["_dur"])[1:]]
            if c["tipo"] == "comparacao":
                eventos.append((t + 0.35 + c.get("intervalo", 1.6), "clique", 0.9))
            if c["tipo"] == "cta":
                eventos.append((t - 1.2, "riser", 0.7))
                eventos.append((t + 0.55, "impacto", 0.6))
            if c["tipo"] == "marca":
                eventos.append((t + 0.3, "whoosh", 0.5))
            t += c["_dur"]
            rel["cenas"].append({"tipo": c["tipo"], "inicio": round(c["_ini"], 2), "duracao": round(c["_dur"], 2),
                                 "fala": c.get("fala", ""), "texto": c.get("texto") or c.get("titulo", "")})
        total = t
        blocos = []
        if com_legenda:  # blocos por cena: legenda nunca atravessa a troca de cena
            for c in cenas:
                if c.get("_pals") and c["tipo"] != "cinetico":
                    ini = c["_ini"] + (0.12 if c is cenas[0] else 0.22)
                    bs = blocos_legenda([{**p, "ini": p["ini"] + ini, "fim": p["fim"] + ini} for p in c["_pals"]])
                    if bs:
                        bs[-1]["fim"] = min(bs[-1]["fim"] + 0.3, c["_ini"] + c["_dur"])
                    blocos += bs
        # 3) áudio
        audio = tmp / "audio.wav"
        au.mixar(total, falas, eventos, semente, audio, energia=roteiro.get("energia", 1.1), bpm=BPM)
        # 4) vídeo
        rec = Recursos()
        ctx = Contexto(cfg, rec, com_legenda)
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
               "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a", "-t", f"{total:.3f}",
               "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "21", "-maxrate", "6M",
               "-bufsize", "12M", "-pix_fmt", "yuv420p",
               "-r", str(FPS), "-g", str(FPS * 2), "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
               "-movflags", "+faststart", str(saida)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        nframes = int(total * FPS)
        luz_w = rec.luz.width
        capa = None
        for k in range(nframes):
            tg = k / FPS
            i = max(j for j, c in enumerate(cenas) if c["_ini"] <= tg + 1e-6)
            c = cenas[i]
            tl = tg - c["_ini"]
            frame = quadro_cena(c, tl, ctx, rec, tg, luz_w)
            if i > 0 and tl < TR:  # transição: o quadro anterior avança em zoom e se dissolve
                ant = cenas[i - 1]
                if i % 2:
                    q_ant = quadro_cena(ant, ant["_dur"] + tl, ctx, rec, tg, luz_w, extra_zoom=0.07 * ease(tl / TR))
                    a = ease(tl / TR) ** 0.7
                    frame = Image.blend(q_ant, frame, a)
                else:
                    q_ant = quadro_cena(ant, ant["_dur"] + tl, ctx, rec, tg, luz_w)
                    frame = transicao_chicote(q_ant, frame, tl / TR)
            frame = frame.convert("RGBA")
            if com_legenda:
                desenhar_legenda(frame, blocos, tg, destaques)
            marca_fixa(frame, tg, total)
            frame.alpha_composite(rec.graos[(k // 2) % len(rec.graos)])
            rgb = frame.convert("RGB")
            if capa is None and i == 0 and tl >= min(1.6, c["_dur"] - 0.2):
                capa = quadro_cena(c, 2.5, ctx, rec, 0, luz_w).convert("RGBA")
                marca_fixa(capa, 2.0, total)
                capa = capa.convert("RGB")
            proc.stdin.write(rgb.tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("FFmpeg falhou ao exportar o vídeo")
        capa_arq = saida.with_suffix(".jpg")
        (capa or quadro_cena(cenas[0], 2.5, ctx, rec, 0, luz_w).convert("RGB")).save(capa_arq, "JPEG", quality=92)
        rel.update(duracao=round(total, 2), video=str(saida), capa=str(capa_arq), legendas=len(blocos),
                   srt=srt(blocos) if blocos else "", eventos_sfx=[(round(a, 2), b) for a, b, _ in eventos],
                   trilha=f"GNZ01 Tech (original, gerada por código), semente {semente}, {BPM} BPM")
    return rel


def transicao_chicote(a_img, b_img, p):
    """Chicote lateral: a cena atual sai pela esquerda e a nova entra pela direita, com desfoque de movimento."""
    e = ease(p)
    borrao = math.sin(math.pi * min(1.0, max(0.0, p)))
    fr = Image.new("RGB", (W, H), PRETO)
    dx = int(W * e)
    fr.paste(a_img, (-dx, 0))
    fr.paste(b_img, (W - dx, 0))
    if borrao > 0.05:
        k = max(2, int(2 + 30 * borrao))
        fr = fr.resize((max(8, W // k), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
    return fr


def _particulas(n=46, semente=5):
    rng = np.random.default_rng(semente)
    return [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.5, 4.5), rng.uniform(18, 70),
             rng.uniform(0, 6.28), rng.uniform(40, 150)) for _ in range(n)]


_PART = _particulas()


def fundo_animado(fr, tg):
    """Partículas que sobem, anéis que pulsam na batida da trilha e linhas de varredura."""
    cam = _camada()
    d = ImageDraw.Draw(cam)
    for x, y, r, vel, fase, alfa in _PART:
        yy = (y - tg * vel) % (H + 40) - 20
        xx = x + math.sin(tg * 0.8 + fase) * 22
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(*PRATA, int(alfa * (0.6 + 0.4 * math.sin(tg * 2 + fase)))))
    batida = 60 / BPM
    fase_b = (tg % batida) / batida
    pulso = math.exp(-fase_b * 6)
    cx, cy = W / 2, 820
    for k, raio in enumerate((300, 470, 650)):
        rr = raio * (1 + 0.035 * pulso) + 18 * math.sin(tg * 0.6 + k)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*PRATA, int(16 + 26 * pulso)), width=2)
    # linha de varredura horizontal que desce a cada 2 compassos
    yv = int((tg % (batida * 8)) / (batida * 8) * (H + 200)) - 100
    d.rectangle([0, yv, W, yv + 2], fill=(*OFF, 34))
    fr.alpha_composite(cam)
    return pulso


def quadro_cena(c, tl, ctx, rec, tg, luz_w, extra_zoom=0.0):
    """Fundo animado + feixe de luz + conteúdo da cena, com soco de câmera no corte e push-in contínuo."""
    fr = rec.base.copy()
    lx = int(-luz_w + (tg * 60) % (W + luz_w))
    fr.alpha_composite(rec.luz, (lx, -300))
    pulso = fundo_animado(fr, tg)
    conteudo = CENAS[c["tipo"]](c, tl, c["_dur"], ctx)
    fr.alpha_composite(conteudo)
    fr.alpha_composite(rec.vinheta)
    soco = 0.075 * (1 - ease_out(tl / 0.45))
    zoom = 1 + soco + 0.05 * min(1.0, tl / max(c["_dur"], 0.1)) + 0.004 * pulso + extra_zoom
    if zoom > 1.001:
        cw, ch = W / zoom, H / zoom
        x0 = (W - cw) / 2 + math.sin(tg * 0.9) * (W - cw) * 0.35
        y0 = (H - ch) / 2 + math.cos(tg * 0.7) * (H - ch) * 0.25
        fr = fr.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
    return fr.convert("RGB")


def marca_fixa(frame, tg, total):
    """Assinatura discreta no topo (fora do conteúdo que sofre zoom) e barra de progresso fina."""
    cam = _camada()
    d = ImageDraw.Draw(cam)
    f = fonte("bold", 30)
    d.text((70, 150), "GNZ01", font=f, fill=(*OFF, 210))
    d.text((70 + d.textlength("GNZ01", font=f) + 14, 156), "soluções digitais", font=fonte("regular", 24),
           fill=(*SUAVE, 210))
    p = min(1.0, tg / max(total, 0.1))
    d.rectangle([70, 200, W - 70, 202], fill=(255, 255, 255, 40))
    d.rectangle([70, 200, 70 + (W - 140) * p, 202], fill=(*OFF, 200))
    frame.alpha_composite(cam)
