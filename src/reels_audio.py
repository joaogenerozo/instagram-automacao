"""Áudio dos Reels GNZ01: trilha original, efeitos sonoros, narração com IA e mixagem.

Tudo o que é música e efeito é sintetizado aqui por código (sem direitos de terceiros).
Narração: ElevenLabs (se houver ELEVENLABS_API_KEY) -> vozes neurais do Edge (edge-tts, grátis)
-> sem narração. Nunca finge: se nenhuma voz funcionar, o vídeo sai sem narração e o relatório diz isso.
"""
import asyncio
import base64
import json
import os
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100


# ------------------------------------------------------------------ utilitários
def _env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)


def _lowpass(x, corte):
    """Filtro passa-baixa de 1 polo; corte pode ser escalar ou um array (varredura)."""
    corte = np.broadcast_to(np.asarray(corte, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * corte / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _lp_rapido(x, corte):
    """Passa-baixa fixo via FFT (para sinais longos)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / corte) ** 4)
    return np.fft.irfft(X, len(x))


def _nota(m):
    return 440 * 2 ** ((m - 69) / 12)


def salvar_wav(caminho, x, sr=SR):
    x = np.clip(x, -1, 1)
    est = np.stack([x, x], axis=1) if x.ndim == 1 else x
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((est * 32767).astype("<i2").tobytes())


def ler_audio(caminho):
    """Lê qualquer áudio (mp3/wav) como mono 44.1 kHz float."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(caminho), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<f4").astype(float)


# ------------------------------------------------------------------ trilha
TONS = {  # tônica (MIDI) e progressão menor i-VI-III-VII em graus
    "A": 57, "D": 62, "E": 52, "F#": 54, "C#": 61,
}


def trilha(dur, semente=1, bpm=100, energia=1.0):
    """Trilha eletrônica sofisticada: pad escuro, sub-baixo pulsante, kick suave, hats e arpejo com eco.
    Abre só com pad + arpejo (gancho limpo), a batida entra no 2º compasso, fecha com fade."""
    rng = np.random.default_rng(semente)
    tom = list(TONS.values())[semente % len(TONS)]
    n = int((dur + 2) * SR)
    mix = np.zeros(n)
    b = 60 / bpm
    beat = int(b * SR)
    prog = [[0, 3, 7], [-4, 0, 3], [3, 7, 10], [-2, 2, 5]]  # i VI III VII
    total = int(dur / b) + 2
    t_beat = np.arange(beat) / SR
    for k in range(total):
        i = k * beat
        if i + beat >= n:
            break
        comp = k // 4
        ac = [tom + x for x in prog[comp % 4]]
        intro = k < 4
        # pad: 3 osciladores levemente desafinados por nota, 1 bloco por compasso
        if k % 4 == 0:
            dur_pad = min(4 * beat, n - i)
            tt = np.arange(dur_pad) / SR
            pad = np.zeros(dur_pad)
            for m in ac:
                for det in (-0.12, 0, 0.11):
                    f = _nota(m - 12 + det)
                    pad += np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt)
            env = np.minimum(1, tt / 0.6) * np.minimum(1, (dur_pad / SR - tt) / 0.5 + 0.05)
            mix[i:i + dur_pad] += pad * env * 0.022
        # sub-baixo em colcheias com "sidechain"
        if not intro:
            for h in range(2):
                j = i + h * beat // 2
                m = beat // 2
                tt = np.arange(m) / SR
                f = _nota(ac[0] - 24)
                sc = np.minimum(1, tt / 0.09)
                mix[j:j + m] += np.sin(2 * np.pi * f * tt) * sc * np.exp(-tt * 3) * 0.20 * energia
        # kick suave em todos os tempos
        if not intro:
            fk = 48 + 70 * np.exp(-t_beat * 28)
            mix[i:i + beat] += np.sin(2 * np.pi * np.cumsum(fk) / SR) * np.exp(-t_beat * 9) * 0.42 * energia
        # clap discreto nos tempos 2 e 4
        if not intro and k % 2 == 1:
            m = beat // 2
            ruido = rng.standard_normal(m)
            mix[i:i + m] += _lp_rapido(ruido, 5000) * np.exp(-np.arange(m) / SR * 22) * 0.07 * energia
        # hats em semicolcheias
        for h in range(4):
            j = i + h * beat // 4
            m = beat // 4
            if j + m > n:
                break
            hh = np.diff(np.concatenate([[0], rng.standard_normal(m)]))
            vol = (0.05 if h % 2 else 0.028) * (0.5 if intro else 1)
            mix[j:j + m] += hh * np.exp(-np.arange(m) / SR * 70) * vol
        # arpejo pluck (colcheias) com eco
        for h in range(2):
            j = i + h * beat // 2
            m = int(beat * 0.45)
            nota = ac[(k * 2 + h) % 3] + 12
            tt = np.arange(m) / SR
            f = _nota(nota)
            pl = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(6 * np.pi * f * tt)) * _env(m, 0.002, 0.09)
            mix[j:j + m] += pl * 0.05
    # eco do arpejo / ambiência: atraso de 3/8 de tempo
    atraso = int(b * 0.75 * SR)
    eco = np.zeros(n)
    eco[atraso:] = mix[:-atraso] * 0.22
    mix += _lp_rapido(eco, 3500)
    mix = mix[: int(dur * SR)]
    # fade de entrada curto e saída longa
    fi, fo = int(0.05 * SR), int(1.6 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo) ** 1.5
    return mix / (np.max(np.abs(mix)) + 1e-9) * 0.8


# ------------------------------------------------------------------ efeitos
def sfx_whoosh(dur=0.55, semente=0):
    rng = np.random.default_rng(100 + semente)
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    corte = 300 + 5200 * np.sin(np.pi * t) ** 2
    x = _lowpass(rng.standard_normal(n), corte)
    x = x - _lowpass(x, 180)
    env = np.sin(np.pi * t) ** 1.6
    return x * env / (np.max(np.abs(x * env)) + 1e-9) * 0.55


def sfx_impacto(dur=1.1):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = 42 + 60 * np.exp(-tt * 18)
    corpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4.5)
    rng = np.random.default_rng(3)
    estalo = _lp_rapido(rng.standard_normal(n), 2400) * np.exp(-tt * 30) * 0.5
    x = corpo + estalo
    return x / np.max(np.abs(x)) * 0.6


def sfx_clique(dur=0.06):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * 2300 * tt) * np.exp(-tt * 140) + np.sin(2 * np.pi * 1200 * tt) * np.exp(-tt * 90) * 0.5
    return x / np.max(np.abs(x)) * 0.35


def sfx_riser(dur=1.2, semente=0):
    rng = np.random.default_rng(200 + semente)
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = _lowpass(rng.standard_normal(n), 200 + 7000 * t ** 2)
    tom = np.sin(2 * np.pi * np.cumsum(300 + 900 * t ** 2) / SR) * 0.15
    env = t ** 2.2
    y = (x + tom) * env
    return y / (np.max(np.abs(y)) + 1e-9) * 0.4


def sfx_notificacao():
    n = int(0.45 * SR)
    tt = np.arange(n) / SR
    x = np.zeros(n)
    for k, (f, ini) in enumerate(((1318.5, 0.0), (1760.0, 0.11))):
        j = int(ini * SR)
        m = n - j
        x[j:] += np.sin(2 * np.pi * f * tt[:m]) * np.exp(-tt[:m] * 9) * (0.8 if k else 0.6)
    return x / np.max(np.abs(x)) * 0.35


SFX = {"whoosh": sfx_whoosh, "impacto": sfx_impacto, "clique": sfx_clique, "riser": sfx_riser,
       "notificacao": sfx_notificacao}


# ------------------------------------------------------------------ narração
VOZES_EDGE = {"masculina": "pt-BR-AntonioNeural", "feminina": "pt-BR-FranciscaNeural"}


def _edge(texto, destino, voz, taxa="+6%"):
    import edge_tts

    async def run():
        com = edge_tts.Communicate(texto, VOZES_EDGE.get(voz, voz), rate=taxa, boundary="WordBoundary")
        palavras = []
        with open(destino, "wb") as f:
            async for ch in com.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    palavras.append({"palavra": ch["text"], "ini": ch["offset"] / 1e7,
                                     "fim": (ch["offset"] + ch["duration"]) / 1e7})
        return palavras

    palavras = asyncio.run(run())
    if not Path(destino).exists() or Path(destino).stat().st_size < 2000:
        raise RuntimeError("edge-tts não devolveu áudio")
    return palavras


def _elevenlabs(texto, destino, voz):
    import requests
    chave = os.environ["ELEVENLABS_API_KEY"]
    voz_id = os.environ.get("ELEVENLABS_VOICE_ID") or "onwK4e9ZLuTAKqWW03F9"  # "Daniel": grave, confiante
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voz_id}/with-timestamps",
                      headers={"xi-api-key": chave, "Content-Type": "application/json"},
                      json={"text": texto, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
                            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35,
                                               "use_speaker_boost": True}},
                      timeout=120)
    r.raise_for_status()
    dados = r.json()
    Path(destino).write_bytes(base64.b64decode(dados["audio_base64"]))
    al = dados.get("alignment") or {}
    chars, ini, fim = al.get("characters", []), al.get("character_start_times_seconds", []), \
        al.get("character_end_times_seconds", [])
    palavras, atual, t0 = [], "", None
    for c, a, z in zip(chars, ini, fim):
        if c.isspace():
            if atual:
                palavras.append({"palavra": atual, "ini": t0, "fim": z})
            atual, t0 = "", None
        else:
            atual += c
            t0 = a if t0 is None else t0
            ult = z
    if atual:
        palavras.append({"palavra": atual, "ini": t0, "fim": ult})
    return palavras


def provedor_disponivel():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return "elevenlabs"
    if os.environ.get("REELS_SEM_NARRACAO") == "1":
        return None
    try:
        import edge_tts  # noqa: F401
        return "edge"
    except ImportError:
        return None


def narrar(texto, destino, voz="masculina"):
    """Gera a fala. Devolve (provedor, palavras com tempos) ou (None, None) se não houver voz."""
    tentativas = []
    if os.environ.get("ELEVENLABS_API_KEY"):
        tentativas.append(("elevenlabs", lambda: _elevenlabs(texto, destino, voz)))
    if os.environ.get("REELS_SEM_NARRACAO") != "1":
        tentativas.append(("edge", lambda: _edge(texto, destino, voz)))
    erros = []
    for nome, fn in tentativas:
        try:
            return nome, fn()
        except Exception as e:  # tenta o próximo provedor
            erros.append(f"{nome}: {e}")
    if erros:
        print("Narração indisponível:", " | ".join(erros))
    return None, None


# ------------------------------------------------------------------ mixagem
def mixar(dur, falas, eventos, semente, destino, energia=1.0, bpm=100):
    """falas: [(inicio_s, caminho_audio)], eventos: [(inicio_s, nome_sfx, volume)].
    Voz tratada (passa-alta, presença, compressão), trilha com ducking automático sob a voz,
    efeitos por cima, loudness final -14 LUFS (padrão de Reels) com pico máximo -1.5 dBTP."""
    n = int(dur * SR)
    voz = np.zeros(n)
    for ini, arq in falas:
        x = ler_audio(arq)
        j = int(ini * SR)
        m = min(len(x), n - j)
        if m > 0:
            voz[j:j + m] += x[:m]
    musica = trilha(dur, semente=semente, bpm=bpm, energia=energia)[:n]
    if len(musica) < n:
        musica = np.pad(musica, (0, n - len(musica)))
    tem_voz = np.max(np.abs(voz)) > 0.01
    if tem_voz:
        # envelope da voz (janela de 50 ms, ataque rápido e liberação lenta) controla a trilha
        bloco = int(0.05 * SR)
        rms = np.sqrt(np.convolve(voz ** 2, np.ones(bloco) / bloco, mode="same"))
        alvo = (rms > 0.02).astype(float)
        env = np.zeros(n)
        acc = 0.0
        sub = alvo[::100]
        out = np.empty(len(sub))
        for i, v in enumerate(sub):
            acc += (0.35 if v > acc else 0.02) * (v - acc)
            out[i] = acc
        env = np.repeat(out, 100)[:n]
        musica *= 0.55 * (1 - 0.72 * env)  # ~ -11 dB sob a voz
    else:
        musica *= 0.9
    efeitos = np.zeros(n)
    for ini, nome, vol in eventos:
        x = SFX[nome]() * vol
        j = int(ini * SR)
        if j < 0:
            x, j = x[-j:], 0
        m = min(len(x), n - j)
        if m > 0:
            efeitos[j:j + m] += x[:m]
    with tempfile.TemporaryDirectory() as tmp:
        fv, fm = Path(tmp) / "voz.wav", Path(tmp) / "resto.wav"
        salvar_wav(fv, voz / (np.max(np.abs(voz)) + 1e-9) * 0.8 if tem_voz else voz)
        salvar_wav(fm, (musica + efeitos * (0.75 if tem_voz else 1.0)) * 0.7)
        cadeia_voz = ("highpass=f=85,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.4:g=3,"
                      "equalizer=f=9000:t=q:w=1:g=1.5,acompressor=threshold=-20dB:ratio=3.5:attack=8:release=120:makeup=4dB,"
                      "alimiter=limit=0.9")
        filtro = (f"[0:a]{cadeia_voz}[v];[1:a]volume=1.0[m];[v][m]amix=inputs=2:normalize=0:duration=longest,"
                  "loudnorm=I=-14:TP=-1.5:LRA=9[a]")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(fv), "-i", str(fm), "-filter_complex", filtro,
                        "-map", "[a]", "-ar", str(SR), "-ac", "2", str(destino)], check=True)
    return tem_voz
