"""Trilha instrumental original (gerada por código, sem direitos de terceiros): pop eletrônico animado, 120 BPM.
Uso: python tools/trilha.py <segundos> <saida.wav>"""
import sys, wave
import numpy as np

SR, BPM = 44100, 120
B = 60 / BPM


def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def kick(n):
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)


def snare(n):
    t = np.arange(n) / SR
    return (np.random.randn(n) * 0.6 + np.sin(2 * np.pi * 190 * t) * 0.4) * np.exp(-t * 18)


def hat(n):
    t = np.arange(n) / SR
    x = np.random.randn(n)
    x = np.diff(np.concatenate([[0], x]))
    return x * np.exp(-t * 60) * 0.35


def saw(f, n):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 7))


def nota(m):
    return 440 * 2 ** ((m - 69) / 12)


def main():
    dur = float(sys.argv[1]); out = sys.argv[2]
    N = int(dur * SR)
    mix = np.zeros(N + SR * 2)
    np.random.seed(7)
    # progressão I-V-vi-IV em Dó (C G Am F), 1 compasso (4 tempos) por acorde
    acordes = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    baixos = [36, 31, 33, 29]
    beat = int(B * SR)
    total_beats = int(dur / B) + 1
    for b in range(total_beats):
        i = b * beat
        compasso = b // 4
        ac = acordes[compasso % 4]
        intro = b < 8
        # bateria
        if not intro or b % 2 == 0:
            mix[i:i + beat] += kick(beat) * 0.9
        if b % 2 == 1 and not intro:
            mix[i:i + beat] += snare(beat) * 0.35
        for h in range(2):
            j = i + h * beat // 2 + beat // 4
            mix[j:j + beat // 2] += hat(beat // 2) * (0.5 if not intro else 0.3)
        # baixo em colcheias
        for h in range(2):
            j = i + h * beat // 2
            n = beat // 2
            mix[j:j + n] += np.sin(2 * np.pi * nota(baixos[compasso % 4]) * np.arange(n) / SR) * env(n, 0.003, 0.15) * 0.45
        # acordes "pluck" sincopados
        for off in (0, 0.75):
            j = i + int(off * beat)
            n = int(beat * 0.6)
            mix[j:j + n] += sum(saw(nota(m), n) for m in ac) * env(n, 0.004, 0.12) * 0.06
        # melodia simples nos compassos pares depois da intro
        if not intro and compasso % 2 == 0:
            mel = [ac[2] + 12, ac[1] + 12, ac[0] + 12, ac[1] + 12]
            m = mel[b % 4]
            n = beat // 2
            mix[i:i + n] += np.sin(2 * np.pi * nota(m) * np.arange(n) / SR) * env(n, 0.01, 0.25) * 0.12
    mix = mix[:N]
    # fade in/out
    f = int(1.5 * SR)
    mix[:f] *= np.linspace(0, 1, f); mix[-f:] *= np.linspace(1, 0, f)
    mix = mix / np.max(np.abs(mix)) * 0.9
    st = np.stack([mix, np.roll(mix, 200)], axis=1)
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    main()
