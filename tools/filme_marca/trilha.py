"""Trilha do filme de marca GNZ01_ (12 s, 124 BPM, eletrônica premium + efeitos).

Determinística (semente fixa). Os efeitos seguem os quadros da timeline a 29,97 fps
definidos em filme.html. A normalização para -14 LUFS / -1 dBTP é feita com o loudnorm do FFmpeg.

Uso: python3 tools/filme_marca/trilha.py saida.wav [duração em s, padrão 12]
"""
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 48000
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
ESC = DUR / 12.0  # o filme é esticado de forma uniforme quando DUR > 12
BPM = 124
BEAT = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(1240)
t_all = np.arange(N) / SR


def q(f):  # quadro da timeline (29,97) -> segundos
    return f / 29.97 * ESC


def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
    return e


def put(buf, x, t0, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += g * x[: j - i]


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    fq = 45 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(fq) / SR
    return np.sin(ph) * np.exp(-t / 0.16) + 0.15 * np.sin(ph * 2) * np.exp(-t / 0.02)


def hat(d=0.04):
    n = int(0.12 * SR)
    x = rng.standard_normal(n)
    x = np.diff(x, prepend=0)  # passa-alta simples
    return x * env(n, 0.0005, d) * 0.5


def click():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 3200 * t) * 0.6 + rng.standard_normal(n) * 0.3) * np.exp(-t / 0.006)


def tick():
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return (rng.standard_normal(n) * 0.5 + np.sin(2 * np.pi * 1800 * t) * 0.3) * np.exp(-t / 0.004)


def whoosh(dur, up=True):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    k = np.linspace(0, 1, n)
    shape = np.sin(np.pi * k) ** 2
    # filtro passa-baixa variável (um polo) para dar movimento
    cut = (0.02 + 0.35 * (k if up else 1 - k))
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += cut[i] * (x[i] - acc)
        y[i] = acc
    return y * shape * 1.6


def shimmer(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = np.linspace(0, 1, n)
    s = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate([2637, 3136, 3951, 5274]))
    return s * np.sin(np.pi * k) ** 1.5 * 0.08


def impact():
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    fq = 38 + 70 * np.exp(-t / 0.08)
    sub = np.sin(2 * np.pi * np.cumsum(fq) / SR) * np.exp(-t / 0.9)
    noise = rng.standard_normal(n)
    acc, y = 0.0, np.zeros(n)
    for i in range(n):
        acc += 0.05 * (noise[i] - acc)
        y[i] = acc
    return sub * 0.9 + y * np.exp(-t / 0.5) * 1.2


def pad():
    # acordes menores suaves (Am9 -> Fmaj7 -> Cmaj7 -> Em7), um por compasso
    chords = [[220, 261.6, 329.6, 493.9], [174.6, 220, 261.6, 329.6],
              [130.8, 196, 246.9, 329.6], [164.8, 196, 246.9, 293.7]]
    out = np.zeros(N)
    bar = 4 * BEAT
    for b in range(int(DUR / bar) + 1):
        t0 = b * bar
        n = int(min(bar + 0.4, DUR - t0) * SR)
        if n <= 0:
            break
        t = np.arange(n) / SR
        e = np.minimum(1, t / 0.4) * np.minimum(1, (n / SR - t) / 0.4)
        x = sum(np.sin(2 * np.pi * f * t * (1 + d)) for f in chords[b % 4] for d in (-0.003, 0.003))
        put(out, x * e * 0.035, t0)
    return out


def bass():
    notes = [55, 43.65, 65.4, 41.2]
    out = np.zeros(N)
    for i in range(int(DUR / (BEAT / 2))):
        t0 = i * BEAT / 2
        if i % 2 == 0:
            continue  # baixo no contratempo
        n = int(BEAT / 2 * 0.9 * SR)
        t = np.arange(n) / SR
        f = notes[int(t0 / (4 * BEAT)) % 4]
        x = np.tanh(2.2 * np.sin(2 * np.pi * f * t)) * env(n, 0.004, 0.12)
        put(out, x * 0.32, t0)
    return out


def main(saida):
    mus = pad() + bass()
    k, h = kick(), hat()
    final = q(301)
    for i in range(int(DUR / BEAT)):
        t0 = i * BEAT
        if t0 > final - 0.05:
            break
        g = 0.55 if t0 < 2 * BEAT * 2 else 0.85  # entra mais leve
        put(mus, k, t0, g)
        put(mus, h, t0 + BEAT / 2, 0.35)
        if i >= 8:
            put(mus, hat(0.015), t0 + BEAT / 4, 0.18)
            put(mus, hat(0.015), t0 + 3 * BEAT / 4, 0.18)
    # sidechain leve a partir dos bumbos
    sc = np.ones(N)
    for i in range(int(DUR / BEAT)):
        i0 = int(i * BEAT * SR)
        n = int(0.25 * SR)
        j = min(N, i0 + n)
        sc[i0:j] = np.minimum(sc[i0:j], 1 - 0.45 * np.exp(-np.arange(j - i0) / SR / 0.09))
    mus *= sc
    # fade da música no final, só a assinatura sustenta
    mus *= np.clip((DUR - t_all) / 1.6, 0, 1) ** 0.7

    sfx = np.zeros(N)
    put(sfx, whoosh(1.2), 0.0, 0.5)                 # abertura
    put(sfx, shimmer(1.4), q(4), 1.0)               # anel desenhando
    put(sfx, click(), q(55), 0.9)                   # clique na marca
    put(sfx, whoosh(0.6), q(62), 0.7)               # passagem para o símbolo
    put(sfx, click(), q(92), 0.5)                   # órbitas travam
    put(sfx, whoosh(0.4, False), q(96), 0.5)
    put(sfx, click(), q(117), 0.9)                  # clique no ícone
    for f in range(128, 146, 2):                    # digitação
        put(sfx, tick(), q(f + (f * 7 % 3) * 0.3), 0.45)
    put(sfx, click(), q(147), 1.0)                  # botão
    put(sfx, whoosh(0.7), q(148), 1.0)              # subida rápida
    put(sfx, shimmer(0.5), q(152), 1.4)             # feixe dourado
    put(sfx, whoosh(0.5), q(184), 0.6)              # card sobe
    put(sfx, shimmer(0.6), q(196), 0.9)             # reflexo
    put(sfx, whoosh(0.5), q(214), 0.6)              # cards empilhados
    put(sfx, click(), q(222), 0.4)
    put(sfx, click(), q(230), 0.4)
    put(sfx, whoosh(0.8, False), q(242), 0.6)       # para o símbolo metálico
    put(sfx, shimmer(1.0), q(255), 1.2)             # reflexo metálico
    put(sfx, whoosh(0.9), q(282), 0.8)              # riser para a assinatura
    put(sfx, impact(), final, 0.9)                  # assinatura
    put(sfx, shimmer(1.6), final + 0.1, 0.8)

    mix = mus + sfx * 0.55
    # estéreo leve: atraso curto no canal direito para os efeitos
    d = int(0.011 * SR)
    L = mix
    R = mus + np.concatenate([np.zeros(d), sfx[:-d]]) * 0.55
    st = np.stack([L, R], 1)
    st /= np.max(np.abs(st)) * 1.12
    st[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))[:, None]

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((st * 32767).astype("<i2").tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name,
                        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", saida], check=True)


if __name__ == "__main__":
    main(sys.argv[1])
