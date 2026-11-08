"""Versões de um Reel (9:16) para outros formatos: Feed 4:5 (1080x1350) e YouTube 16:9 (1920x1080).

  4:5   vídeos do estúdio (src/reels.py): recorte da área útil (conteúdo + legendas ficam dentro da faixa
        y=210..1560 do 9:16). Outros vídeos: moldura (vídeo inteiro ao centro sobre o fundo grafite da marca).
  16:9  moldura: vídeo ao centro sobre o fundo grafite da marca, assinatura GNZ01 à esquerda e
        contato à direita.
Áudio: copiado, ou normalizado para -14 LUFS com --normalizar (vídeos antigos estavam em -26 LUFS).

Uso: python tools/formatos.py VIDEO.mp4 [--saida PASTA] [--moldura] [--normalizar] [--9x16]
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.reels import fonte, OFF, PRATA, SUAVE  # noqa: E402

CFG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
ENC = ["-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "21", "-maxrate", "6M",
       "-bufsize", "12M", "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart"]


def audio_args(normalizar):
    return (["-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "192k", "-ar", "44100"]
            if normalizar else ["-c:a", "copy"])


def fundo(w, h, com_texto, destino):
    """Fundo opaco da marca (gradiente grafite + brilho no alto); no 16:9 leva assinatura e contato nas laterais."""
    import numpy as np
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    base = 9 + 10 * (1 - y) + 22 * np.exp(-((x * 1.2) ** 2 + (y * 2.2) ** 2))
    arr = np.stack([base, base * 1.03, base * 1.12], axis=2).clip(0, 255).astype("uint8")
    im = Image.fromarray(arr, "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    if com_texto:
        lw = (w - int(round(1080 * h / 1920 / 2) * 2)) // 2  # largura de cada lateral
        for x0, linhas in ((0, [("GNZ01", fonte("bold", 72), OFF), ("Soluções digitais", fonte("serif_r", 40), PRATA)]),
                           (w - lw, [("Fale com a gente", fonte("semi", 34), PRATA),
                                     (CFG.get("whatsapp", ""), fonte("bold", 44), OFF),
                                     ("@gnz01_", fonte("regular", 34), SUAVE)])):
            alt = sum(int(f.size * 1.5) for _, f, _ in linhas)
            yy = (h - alt) // 2
            for txt, f, cor in linhas:
                tw = d.textlength(txt, font=f)
                d.text((x0 + (lw - tw) / 2, yy), txt, font=f, fill=(*cor, 255))
                yy += int(f.size * 1.5)
            cx = x0 + lw / 2
            d.rectangle([cx - 70, yy + 10, cx + 70, yy + 12], fill=(*PRATA, 160))
    im.convert("RGB").save(destino)


def moldura(entrada, saida, w, h, normalizar, com_texto):
    fit_w = int(round(1080 * h / 1920 / 2) * 2)
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fundo.png"
        fundo(w, h, com_texto, png)
        filtro = f"[1:v]scale={fit_w}:{h}[fg];[0:v][fg]overlay=(W-w)/2:0,format=yuv420p[v]"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
                        "-i", str(entrada), "-filter_complex", filtro, "-map", "[v]", "-map", "1:a", "-shortest",
                        *ENC, *(["-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "192k", "-ar", "44100"]
                                if normalizar else ["-c:a", "copy"]), str(saida)], check=True)


def recorte_4x5(entrada, saida, normalizar):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(entrada), "-vf", "crop=1080:1350:0:210",
                    *ENC, *audio_args(normalizar), str(saida)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--saida")
    ap.add_argument("--moldura", action="store_true", help="4:5 com moldura em vez de recorte")
    ap.add_argument("--normalizar", action="store_true", help="loudness -14 LUFS")
    ap.add_argument("--9x16", dest="vertical", action="store_true", help="também regrava o 9:16 normalizado")
    a = ap.parse_args()
    v = Path(a.video)
    pasta = Path(a.saida) if a.saida else v.parent
    pasta.mkdir(parents=True, exist_ok=True)
    base = pasta / v.stem
    if a.vertical:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(v), *ENC, *audio_args(a.normalizar),
                        f"{base}_9x16.mp4"], check=True)
    if a.moldura:
        moldura(v, f"{base}_4x5.mp4", 1080, 1350, a.normalizar, False)
    else:
        recorte_4x5(v, f"{base}_4x5.mp4", a.normalizar)
    moldura(v, f"{base}_16x9.mp4", 1920, 1080, a.normalizar, True)
    print(base)


if __name__ == "__main__":
    main()
