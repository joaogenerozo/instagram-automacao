"""Reel de demonstração: "Como fica o seu site" (1080x1920, ~27 s, 30 fps).
Cena 1: abertura. Cena 2: site de exemplo rolando no celular, com legendas explicando cada parte.
Cena 3: o mesmo modelo em três negócios diferentes (monitor). Cena 4: chamada para o WhatsApp.
Tudo com nomes fictícios e aviso de demonstração ilustrativa. Uso: python tools/video_site.py [saida.mp4]"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.render import fonte, quebrar  # noqa: E402
from src import showcase as sc  # noqa: E402

W, H, FPS = 1080, 1920, 30
FUNDO, GRADE = (24, 25, 29), (44, 47, 54)
TEXTO, SUAVE, PRATA = (244, 243, 238), (150, 154, 162), (196, 200, 206)
ESC, CHIP, VERDE = (24, 25, 29), (232, 231, 225), (37, 211, 102)
CFG = json.load(open(RAIZ / "config.json"))


def fundo():
    im = Image.new("RGB", (W, H), FUNDO)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 90):
        d.line([(x, 0), (x, H)], fill=GRADE, width=1)
    for y in range(0, H, 90):
        d.line([(0, y), (W, y)], fill=GRADE, width=1)
    sombra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sombra).rectangle([0, 900, W, H], fill=255)
    sombra = sombra.filter(ImageFilter.GaussianBlur(300))
    return Image.composite(Image.new("RGB", (W, H), FUNDO), im, sombra)


BASE = fundo()


def centro(d, texto, y, f, cor, larg=940, entre=1.12):
    for linha in quebrar(d, texto, f, larg):
        d.text(((W - d.textlength(linha, font=f)) / 2, y), linha, font=f, fill=cor)
        y += int(f.size * entre)
    return y


def marca(d):
    f = fonte("bold", 34)
    d.text((70, 80), "GNZ01", font=f, fill=TEXTO)
    t = "@gnz01_"
    d.text((W - 70 - d.textlength(t, font=fonte("semi", 30)), 84), t, font=fonte("semi", 30), fill=PRATA)


def aviso(d):
    t = "Demonstração ilustrativa · nomes fictícios"
    f = fonte("regular", 24)
    d.text(((W - d.textlength(t, font=f)) / 2, H - 70), t, font=f, fill=SUAVE)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------ site de exemplo (página longa)
def pagina_site(larg=640):
    """Página de celular de um site fictício (salão de beleza), alta para rolar."""
    alt = 3600
    im = Image.new("RGB", (larg, alt), (250, 250, 248))
    d = ImageDraw.Draw(im)
    tom = (190, 170, 160)
    # cabeçalho
    d.rectangle([0, 0, larg, 110], fill=ESC)
    d.text((32, 34), "Studio Aurora", font=fonte("bold", 38), fill=(255, 255, 255))
    for i in range(3):
        d.rounded_rectangle([larg - 76, 40 + i * 14, larg - 32, 47 + i * 14], radius=3, fill=(255, 255, 255))
    # capa (hero)
    y = 110
    d.rectangle([0, y, larg, y + 700], fill=(46, 44, 48))
    d.rounded_rectangle([larg - 300, y + 60, larg - 40, y + 360], radius=26, fill=tom)
    d.ellipse([larg - 210, y + 110, larg - 130, y + 190], fill=(236, 226, 220))
    d.rounded_rectangle([larg - 250, y + 200, larg - 90, y + 360], radius=60, fill=(236, 226, 220))
    yy = y + 400
    for l in quebrar(d, "Seu cabelo do jeito que você sempre quis.", fonte("bold", 50), larg - 64):
        d.text((32, yy), l, font=fonte("bold", 50), fill=(255, 255, 255))
        yy += 58
    d.text((32, yy + 10), "Corte, coloração e tratamentos.", font=fonte("regular", 28), fill=(200, 202, 206))
    fb = fonte("bold", 30)
    d.rounded_rectangle([32, y + 600, 32 + d.textlength("Agendar pelo WhatsApp", font=fb) + 70, y + 668], radius=34, fill=VERDE)
    d.text((67, y + 615), "Agendar pelo WhatsApp", font=fb, fill=(255, 255, 255))
    # serviços
    y += 760
    d.text((32, y), "Serviços", font=fonte("bold", 44), fill=ESC)
    y += 76
    for i, s in enumerate(["Corte feminino", "Coloração", "Hidratação", "Escova"]):
        cy = y + i * 128
        d.rounded_rectangle([32, cy, larg - 32, cy + 108], radius=24, fill=CHIP)
        d.ellipse([56, cy + 26, 112, cy + 82], fill=tom)
        d.text((136, cy + 34), s, font=fonte("semi", 34), fill=ESC)
        d.text((larg - 90, cy + 30), "›", font=fonte("bold", 44), fill=SUAVE)
    # galeria
    y += 4 * 128 + 50
    d.text((32, y), "Nosso trabalho", font=fonte("bold", 44), fill=ESC)
    y += 76
    tons = [(201, 180, 168), (176, 160, 150), (214, 196, 184), (160, 148, 140)]
    cw = (larg - 64 - 20) / 2
    for i in range(4):
        cx, cy = 32 + (i % 2) * (cw + 20), y + (i // 2) * (cw + 20)
        d.rounded_rectangle([cx, cy, cx + cw, cy + cw], radius=22, fill=tons[i])
    y += 2 * (cw + 20) + 40
    # endereço e horários
    d.text((32, y), "Onde estamos", font=fonte("bold", 44), fill=ESC)
    y += 76
    d.rounded_rectangle([32, y, larg - 32, y + 260], radius=24, fill=(222, 226, 222))
    for k in range(6):
        d.line([(32, y + 40 + k * 40), (larg - 32, y + 20 + k * 44)], fill=(240, 242, 240), width=10)
    d.ellipse([larg / 2 - 26, y + 90, larg / 2 + 26, y + 142], fill=(220, 70, 60))
    d.polygon([(larg / 2 - 20, y + 130), (larg / 2 + 20, y + 130), (larg / 2, y + 172)], fill=(220, 70, 60))
    y += 290
    for t in ["Rua Exemplo, 123 · Centro", "Seg a Sáb · 9h às 19h"]:
        d.text((32, y), t, font=fonte("regular", 30), fill=ESC)
        y += 48
    # rodapé com botão fixo
    y += 30
    d.rounded_rectangle([32, y, larg - 32, y + 90], radius=45, fill=VERDE)
    t = "Fale com a gente"
    d.text(((larg - d.textlength(t, font=fonte("bold", 34))) / 2, y + 24), t, font=fonte("bold", 34), fill=(255, 255, 255))
    return im.crop((0, 0, larg, y + 140))


PAG = pagina_site()
TELA_W, TELA_H = 640, 1180
FX, FY = (W - TELA_W) // 2, 470


def celular(frame, scroll):
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle([FX - 26, FY - 26, FX + TELA_W + 26, FY + TELA_H + 26], radius=86, fill=(8, 8, 10),
                        outline=(70, 74, 80), width=3)
    tela = PAG.crop((0, int(scroll), TELA_W, int(scroll) + TELA_H))
    mask = Image.new("L", tela.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, TELA_W - 1, TELA_H - 1], radius=62, fill=255)
    frame.paste(tela, (FX, FY), mask)
    d.rounded_rectangle([W / 2 - 80, FY + 14, W / 2 + 80, FY + 46], radius=16, fill=(8, 8, 10))


def legenda(frame, num, texto, alfa):
    """Etiqueta com número + explicação, acima do celular."""
    if alfa <= 0:
        return
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    a = int(255 * alfa)
    d.ellipse([70, 250, 150, 330], fill=(*TEXTO, a))
    f = fonte("bold", 40)
    d.text((110 - d.textlength(str(num), font=f) / 2, 264), str(num), font=f, fill=(*ESC, a))
    y = 246
    for l in quebrar(d, texto, fonte("bold", 46), 840):
        d.text((176, y), l, font=fonte("bold", 46), fill=(*TEXTO, a))
        y += 56
    frame.paste(camada, (0, 0), camada)


# ------------------------------------------------------------ cenas
def cena_abertura(t, dur):
    fr = BASE.copy()
    d = ImageDraw.Draw(fr)
    marca(d)
    a = ease(t / 0.6)
    y = 640 - int(40 * (1 - a))
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(camada)
    y = centro(dc, "Como fica o", y, fonte("regular", 84), (*PRATA, int(255 * a)))
    y = centro(dc, "SITE DO SEU NEGÓCIO", y + 10, fonte("bold", 104), (*TEXTO, int(255 * a)), entre=1.05)
    centro(dc, "Passo a passo, do jeito que o seu cliente vê no celular.", y + 50, fonte("regular", 40),
           (*SUAVE, int(255 * ease((t - 0.6) / 0.6))))
    fr.paste(camada, (0, 0), camada)
    aviso(d)
    return fr


PASSOS = [
    (0, "Capa com a sua chamada e o botão do WhatsApp"),
    (870, "Seus serviços, claros e fáceis de achar"),
    (1500, "Fotos do seu trabalho"),
    (2000, "Endereço, mapa e horários"),
    (PAG.height - TELA_H, "Botão para o cliente falar com você"),
]


def cena_site(t, dur):
    fr = BASE.copy()
    d = ImageDraw.Draw(fr)
    marca(d)
    seg = dur / len(PASSOS)
    i = min(int(t / seg), len(PASSOS) - 1)
    lt = t - i * seg
    alvo = PASSOS[i][0]
    origem = PASSOS[i - 1][0] if i else 0
    scroll = origem + (alvo - origem) * ease(lt / 0.9)
    celular(fr, min(scroll, PAG.height - TELA_H))
    legenda(fr, i + 1, PASSOS[i][1], ease(lt / 0.35) * ease((seg - lt) / 0.25))
    aviso(d)
    return fr


NEGOCIOS = [
    ("Clínica odontológica", {"tipo": "site", "marca": "Clínica Sorriso", "dominio": "clinicasorriso.com.br",
                              "chamada": "Seu sorriso em boas mãos.", "apoio": "Avaliação, limpeza e clareamento.",
                              "botao": "Agendar pelo WhatsApp", "servicos": ["Avaliação", "Limpeza", "Clareamento"]}),
    ("Pizzaria", {"tipo": "cardapio", "nome": "Forno da Vila", "dominio": "fornodavila.com.br",
                  "chips": ["Pizzas", "Bebidas", "Sobremesas"],
                  "itens": [["Margherita", "", "R$ 49,90"], ["Calabresa", "", "R$ 47,90"], ["Portuguesa", "", "R$ 52,90"],
                            ["Quatro Queijos", "", "R$ 54,90"], ["Frango c/ Catupiry", "", "R$ 51,90"], ["Chocolate", "", "R$ 44,90"]]}),
    ("Barbearia", {"tipo": "agenda", "nome": "Barbearia Navalha", "dominio": "barbearianavalha.com.br"}),
    ("Loja de roupas", {"tipo": "catalogo", "nome": "Ateliê Lume", "dominio": "atelielume.com.br",
                        "chips": ["Novidades", "Vestidos", "Básicos"]}),
]
TELAS = [(n, sc.tela_desktop(v, 1280, 800)) for n, v in NEGOCIOS]


def cena_negocios(t, dur):
    fr = BASE.copy()
    d = ImageDraw.Draw(fr)
    marca(d)
    centro(d, "E fica com a cara do seu negócio", 250, fonte("bold", 62), TEXTO, larg=900)
    seg = dur / len(TELAS)
    i = min(int(t / seg), len(TELAS) - 1)
    lt = t - i * seg
    nome, tela = TELAS[i]
    larg = 960
    alt = int(tela.height * larg / tela.width)
    x, y = (W - larg) // 2, 640
    d.rounded_rectangle([x - 22, y - 22, x + larg + 22, y + alt + 22], radius=26, fill=(8, 8, 10), outline=(70, 74, 80), width=3)
    d.rectangle([W / 2 - 60, y + alt + 22, W / 2 + 60, y + alt + 110], fill=(40, 42, 47))
    d.rounded_rectangle([W / 2 - 200, y + alt + 104, W / 2 + 200, y + alt + 124], radius=10, fill=(40, 42, 47))
    a = ease(lt / 0.35)
    fr.paste(Image.blend(Image.new("RGB", (larg, alt), (8, 8, 10)), tela.resize((larg, alt)), a), (x, y))
    f = fonte("bold", 44)
    lb = d.textlength(nome, font=f)
    d.rounded_rectangle([(W - lb) / 2 - 40, 1360, (W + lb) / 2 + 40, 1444], radius=42, fill=TEXTO)
    d.text(((W - lb) / 2, 1376), nome, font=f, fill=ESC)
    # (legenda do roteiro ocupa esta faixa)
    aviso(d)
    return fr


def cena_cta(t, dur):
    fr = BASE.copy()
    d = ImageDraw.Draw(fr)
    marca(d)
    a = ease(t / 0.5)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(camada)
    y = centro(dc, "Quer um site assim", 620, fonte("bold", 88), (*TEXTO, int(255 * a)))
    y = centro(dc, "para o seu negócio?", y, fonte("bold", 88), (*PRATA, int(255 * a)))
    fb = fonte("bold", 46)
    t1 = "Me chama no WhatsApp"
    lb = dc.textlength(t1, font=fb)
    yb = y + 90
    dc.rounded_rectangle([(W - lb) / 2 - 60, yb, (W + lb) / 2 + 60, yb + 110], radius=55, fill=(*VERDE, int(255 * a)))
    dc.text(((W - lb) / 2, yb + 28), t1, font=fb, fill=(255, 255, 255, int(255 * a)))
    centro(dc, CFG.get("whatsapp", "(19) 97829-9585"), yb + 160, fonte("semi", 48), (*TEXTO, int(255 * a)))
    centro(dc, "ou no direct do @gnz01_", yb + 236, fonte("regular", 40), (*SUAVE, int(255 * a)))
    fr.paste(camada, (0, 0), camada)
    aviso(d)
    return fr


def cena_marca(t, dur):
    fr = BASE.copy()
    d = ImageDraw.Draw(fr)
    a = ease(t / 0.6)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(camada)
    esc = 0.85 + 0.15 * a
    f = fonte("bold", int(220 * esc))
    centro(dc, "GNZ01", 640, f, (*TEXTO, int(255 * a)))
    centro(dc, "Tecnologia, design e experiências digitais.", 900, fonte("semi", 46), (*PRATA, int(255 * ease((t - 0.5) / 0.6))))
    centro(dc, "Seu próximo passo começa aqui.", 1010, fonte("regular", 44), (*SUAVE, int(255 * ease((t - 1.5) / 0.6))))
    fr.paste(camada, (0, 0), camada)
    centro(d, "WhatsApp " + CFG.get("whatsapp", "(19) 97829-9585") + "  ·  @gnz01_", 1300, fonte("semi", 40), TEXTO)
    aviso(d)
    return fr


CENAS = [(cena_abertura, 5.0), (cena_site, 17.0), (cena_negocios, 13.0), (cena_cta, 6.0), (cena_marca, 7.0)]

# Roteiro do João (06/11) em legendas sincronizadas: (início, fim, texto)
ROTEIRO = [
    (0.3, 5.0, "Seu negócio merece uma presença digital à altura da qualidade dos seus serviços."),
    (5.0, 12.0, "Imagine apresentar sua empresa com um site moderno, elegante e que transmite confiança desde o primeiro acesso."),
    (12.0, 22.0, "Seus clientes encontram seus serviços, conhecem seus produtos, agendam e falam direto com você."),
    (22.0, 30.0, "Mais do que um site: uma ferramenta para fortalecer sua marca e criar novas oportunidades."),
    (30.0, 35.0, "Chegou a hora de levar seu negócio para outro nível."),
    (35.0, 41.0, "Entre em contato com a GNZ01 e descubra o que podemos desenvolver para sua empresa."),
]


def legenda_roteiro(fr, tg):
    for ini, fim, txt in ROTEIRO:
        if ini <= tg < fim:
            a = ease((tg - ini) / 0.3) * ease((fim - tg) / 0.3)
            camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(camada)
            f = fonte("bold", 48)
            linhas = quebrar(d, txt, f, 900)
            alt = len(linhas) * 56 + 50
            y0 = H - 190 - alt
            # só letras brancas, sem caixa; degradê escuro suave no rodapé para ler sobre o celular
            for yy in range(y0 - 140, H):
                k = min(1.0, (yy - (y0 - 140)) / 160)
                d.line([(0, yy), (W, yy)], fill=(10, 10, 12, int(215 * k * a)))
            y = y0 + 25 + int(12 * (1 - a))
            for l in linhas:
                d.text(((W - d.textlength(l, font=f)) / 2, y), l, font=f, fill=(255, 255, 255, int(255 * a)),
                       stroke_width=4, stroke_fill=(0, 0, 0, int(200 * a)))
                y += 56
            fr.paste(camada, (0, 0), camada)
            aviso(ImageDraw.Draw(fr))  # aviso de demonstração sempre visível


def main():
    saida = Path(sys.argv[1] if len(sys.argv) > 1 else RAIZ / "midia/gnz01/videos/como-fica-seu-site.mp4")
    saida.parent.mkdir(parents=True, exist_ok=True)
    total = sum(d for _, d in CENAS)
    trilha = RAIZ / "midia/audio/trilha-gnz01.wav"
    if not trilha.exists():
        subprocess.run([sys.executable, str(RAIZ / "tools/trilha.py"), str(total + 1), str(trilha)], check=True)
    narr = RAIZ / "midia/audio/narracao-01.wav"
    if narr.exists():  # narração em primeiro plano, trilha bem baixa
        audio = ["-i", str(trilha), "-i", str(narr), "-filter_complex",
                 "[1:a]volume=0.12[m];[2:a]volume=1.0,adelay=300|300[v];[m][v]amix=inputs=2:duration=first[a]",
                 "-map", "0:v", "-map", "[a]"]
    else:  # sem narração: só a trilha, baixa
        audio = ["-i", str(trilha), "-filter_complex", "[1:a]volume=0.35[a]", "-map", "0:v", "-map", "[a]"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", *audio, "-t", str(total),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", str(saida)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    tg = 0.0
    for cena, dur in CENAS:
        for k in range(int(dur * FPS)):
            fr = cena(k / FPS, dur)
            legenda_roteiro(fr, tg + k / FPS)
            p.stdin.write(fr.tobytes())
        tg += dur
    p.stdin.close()
    p.wait()
    capa = saida.with_suffix(".jpg")
    cena_abertura(2.0, 5.0).save(capa, "JPEG", quality=92)
    print(saida, capa)


if __name__ == "__main__":
    main()
