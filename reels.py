"""GNZ01 Reels: produz e agenda os vídeos do dia (3 por dia: 07:00, 11:00 e 19:00 de Brasília).

Para cada horário das próximas horas que ainda não tem Reel na fila, pega o próximo roteiro ainda não
usado em conteudo/reels/roteiros-*.json, produz o vídeo (src/reels.py), passa pelo controle de qualidade
automático e, se aprovado, coloca na fila como "pendente". O publicar.py publica no horário.

Entregas de cada vídeo:
  midia/reels/<data>_<hora>_<slug>.mp4 (+ .jpg da capa)
  GNZ01-MARKETING/REELS/<data>_<hora>_<slug>/roteiro.md   roteiro, narração, tempos, trilha e efeitos
  GNZ01-MARKETING/REELS/<data>_<hora>_<slug>/legendas.srt legendas sincronizadas (quando há narração)

Uso:
  python reels.py                 agenda/produz os horários das próximas 48 horas
  python reels.py --horas 72      outra janela
  python reels.py --teste ID      só produz o roteiro ID em midia/reels/teste/ (não agenda)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.comum import RAIZ, carregar_config, carregar_fila, montar_legenda, parecidos, salvar_fila
from src import reels_cinema as motor  # prompt GNZ01_ (motor antigo de textos: src/reels.py)

HORARIOS_PADRAO = ["07:00", "11:00", "19:00"]
PASTA_ROTEIROS = RAIZ / "conteudo" / "reels"


PASTA_JOAO = PASTA_ROTEIROS / "joao"


def roteiros():
    """Roteiros do João (conteudo/reels/joao/*.json) primeiro, depois os gerados (roteiros-*.json)."""
    out = []
    for arq in sorted(PASTA_JOAO.glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        for r in (d["roteiros"] if isinstance(d, dict) and "roteiros" in d else d if isinstance(d, list) else [d]):
            out.append({**r, "origem": "joao"})
    for arq in sorted(PASTA_ROTEIROS.glob("roteiros-*.json")):
        out += json.loads(arq.read_text(encoding="utf-8"))["roteiros"]
    return out


def quando_roteiro(r, tz):
    """'quando' opcional do roteiro: '2026-11-08 11:00' (ou ISO). Devolve datetime no fuso ou None."""
    if not r.get("quando"):
        return None
    q = datetime.fromisoformat(r["quando"].replace(" ", "T"))
    return q if q.tzinfo else q.replace(tzinfo=tz)


def slug(txt):
    import unicodedata
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40]


# ------------------------------------------------------------------ controle de qualidade
def controle_qualidade(video, rel):
    """Checa formato, duração, áudio, volume e quadros pretos. Devolve lista de problemas (vazia = ok)."""
    problemas = []
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                                      str(video)], capture_output=True, text=True).stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if not v or v["codec_name"] != "h264" or (v["width"], v["height"]) != (1080, 1920):
        problemas.append("vídeo fora do padrão 1080x1920 H.264")
    if v and v.get("r_frame_rate") not in ("30/1",):
        problemas.append(f"fps inesperado: {v.get('r_frame_rate')}")
    if not a:
        problemas.append("sem trilha de áudio")
    dur = float(info["format"]["duration"])
    if not 8 <= dur <= 90:
        problemas.append(f"duração fora de 8 a 90 s: {dur:.1f}")
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-af", "ebur128=peak=true", "-vf",
                        "blackdetect=d=0.4:pix_th=0.04", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    pico = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    if lufs and not -16.5 <= float(lufs[-1]) <= -11.5:
        problemas.append(f"volume fora do padrão: {lufs[-1]} LUFS")
    if pico and float(pico[-1]) > -0.5:
        problemas.append(f"pico de áudio alto demais: {pico[-1]} dBFS")
    mb = Path(video).stat().st_size / 1e6
    if mb > 45:
        problemas.append(f"arquivo grande demais: {mb:.0f} MB (limite 45 MB)")
    if "black_start" in r:
        problemas.append("trecho preto no vídeo")
    for c in rel["cenas"]:
        if c["duracao"] < 1.5:
            problemas.append(f"cena {c['tipo']} curta demais ({c['duracao']} s)")
    rel["qa"] = {"lufs": float(lufs[-1]) if lufs else None, "pico_dbtp": float(pico[-1]) if pico else None,
                 "duracao": round(dur, 2)}
    return problemas


# ------------------------------------------------------------------ entregas
def ficha(roteiro, rel, quando, legenda):
    linhas = [f"# Reel · {roteiro['titulo']}", "",
              f"- **Publicação:** {quando.strftime('%d/%m/%Y %H:%M')} (Brasília)",
              f"- **Objetivo:** {roteiro.get('objetivo', '')}",
              f"- **Público:** {roteiro.get('publico', '')}",
              f"- **Tema:** {roteiro.get('tema', '')}",
              f"- **Direção criativa:** {roteiro.get('direcao', '')}",
              f"- **Duração:** {rel['duracao']} s · 1080x1920 · H.264 · 30 fps",
              f"- **Narração:** {({'elevenlabs': 'ElevenLabs', 'edge': 'voz neural Microsoft (edge-tts)'}).get(rel['narracao'], 'sem narração (vídeo para assistir sem som, texto na tela)')}",
              f"- **Trilha:** {rel['trilha']}",
              f"- **Controle de qualidade:** {rel.get('qa')}", "",
              "## Roteiro", "", "| Tempo | Cena | Fala / texto na tela |", "|---|---|---|"]
    for c in rel["cenas"]:
        fala = c["fala"] or c["texto"] or "assinatura GNZ01"
        linhas.append(f"| {c['inicio']:.1f}s–{c['inicio'] + c['duracao']:.1f}s | {c['tipo']} | {fala} |")
    linhas += ["", "## Texto da narração", "", " ".join(c.get("fala", "") for c in roteiro["cenas"] if c.get("fala")),
               "", "## Efeitos sonoros (originais, gerados por código)", "",
               ", ".join(f"{t}s {n}" for t, n in rel["eventos_sfx"]), "", "## Legenda do post", "", legenda, ""]
    return "\n".join(linhas)


def produzir_roteiro(roteiro, cfg, quando, video, pasta):
    rel = motor.produzir(roteiro, cfg, video)
    problemas = controle_qualidade(video, rel)
    post = {"legenda": roteiro["legenda"], "tema": roteiro.get("tema", "sites"),
            "hashtags": roteiro.get("hashtags", []), "gancho": roteiro.get("gancho_legenda"),
            "pergunta": roteiro.get("pergunta"),  # engajamento (diretrizes, seção 26)
            "cta_personalizado": roteiro.get("cta_legenda") or roteiro.get("cta_personalizado")}
    legenda = montar_legenda(post, cfg)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "roteiro.md").write_text(ficha(roteiro, rel, quando, legenda), encoding="utf-8")
    if rel["srt"]:
        (pasta / "legendas.srt").write_text(rel["srt"], encoding="utf-8")
    return rel, problemas, legenda


def rel_path(p):
    return str(Path(p).relative_to(RAIZ)).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas", type=float, default=48)
    ap.add_argument("--teste")
    args = ap.parse_args()
    cfg = carregar_config()
    tz = ZoneInfo(cfg["fuso"])
    todos = roteiros()

    if args.teste:
        r = next(x for x in todos if x["id"] == args.teste)
        pasta = RAIZ / "midia" / "reels" / "teste"
        rel, problemas, _ = produzir_roteiro(r, cfg, datetime.now(tz), pasta / f"{r['id']}.mp4", pasta)
        print(json.dumps({k: v for k, v in rel.items() if k != "srt"}, ensure_ascii=False, indent=1))
        print("Problemas:", problemas or "nenhum")
        return

    agora = datetime.now(tz)
    fila = carregar_fila()
    origem = {r["id"]: r.get("origem") for r in todos}
    usados = {p.get("roteiro") for p in fila if p["tipo"] == "reel"}
    joao = [r for r in todos if r.get("origem") == "joao" and r["id"] not in usados]
    horarios = cfg.get("horarios_reels", HORARIOS_PADRAO)
    limite = agora + timedelta(hours=args.horas)
    cedo = agora + timedelta(minutes=10)
    # roteiros do João têm prioridade: tiram do horário um Reel gerado que ainda não foi publicado
    alvos = {}
    for r in joao:
        q = quando_roteiro(r, tz)
        if q and q > cedo:
            alvos[q.isoformat()] = r
    sem_data = [r for r in joao if not quando_roteiro(r, tz)]
    for d in range(0, int(args.horas // 24) + 2):
        dia = agora.date() + timedelta(days=d)
        for h in horarios:
            q = datetime.combine(dia, datetime.strptime(h, "%H:%M").time(), tz)
            if sem_data and cedo < q <= limite and q.isoformat() not in alvos:
                atual = next((p for p in fila if p["tipo"] == "reel" and p["quando"] == q.isoformat()
                              and p["status"] != "erro"), None)
                if not atual or (atual["status"] == "pendente" and origem.get(atual.get("roteiro")) != "joao"):
                    alvos[q.isoformat()] = sem_data.pop(0)
    for qi, r in alvos.items():
        for p in [p for p in fila if p["tipo"] == "reel" and p["quando"] == qi and p["status"] == "pendente"
                  and p.get("roteiro") != r["id"]]:
            print(f"Roteiro do João {r['id']} substitui {p.get('roteiro')} em {qi}")
            for arq in p.get("imagens", []):
                (RAIZ / arq).unlink(missing_ok=True)
            fila.remove(p)
    salvar_fila(fila)
    usados = {p.get("roteiro") for p in fila if p["tipo"] == "reel"}
    ocupados = {p["quando"] for p in fila if p["tipo"] == "reel" and p["status"] != "erro"}
    # trava de repetição (seção 26): roteiro gerado com título parecido a um Reel já publicado/agendado não entra
    titulos_fila = [p.get("titulo", "") for p in fila if p["tipo"] == "reel" and p["status"] != "erro"]
    disponiveis = [r for r in todos if r["id"] not in usados and r.get("origem") != "joao"
                   and not any(parecidos(r["titulo"], t) for t in titulos_fila)]
    slots = sorted(datetime.fromisoformat(qi) for qi in alvos if qi not in ocupados)
    for d in range(0, int(args.horas // 24) + 2):
        dia = agora.date() + timedelta(days=d)
        for h in horarios:
            q = datetime.combine(dia, datetime.strptime(h, "%H:%M").time(), tz)
            if cedo < q <= limite and q.isoformat() not in ocupados and q.isoformat() not in alvos:
                slots.append(q)
    slots.sort()
    print(f"{len(slots)} horário(s) a produzir ({len(alvos)} com roteiro do João); "
          f"{len(disponiveis)} roteiro(s) gerado(s) disponível(is).")
    falhas = []
    # o motor cinematográfico leva ~10-25 min por Reel; cada execução produz no máximo 2 (os próximos ficam para a seguinte)
    slots = slots[:int(os.environ.get("MAX_REELS", "2"))]
    for q in slots:
        r = alvos.get(q.isoformat())
        if r is None:
            if not disponiveis:
                falhas.append(f"- Sem roteiro novo para o Reel de {q:%d/%m %H:%M}. Rode gerar_reels_ia.py ou escreva roteiros.")
                continue
            r = disponiveis.pop(0)
        nome = f"{q:%Y-%m-%d_%Hh%M}_{slug(r['titulo'])}"
        video = RAIZ / "midia" / "reels" / f"{nome}.mp4"
        pasta = RAIZ / "GNZ01-MARKETING" / "REELS" / nome
        print(f"Produzindo {nome} ...", flush=True)
        try:
            rel, problemas, legenda = produzir_roteiro(r, cfg, q, video, pasta)
        except Exception as e:
            falhas.append(f"- Reel {r['id']} ({q:%d/%m %H:%M}) falhou na produção: {e}")
            continue
        if problemas:
            falhas.append(f"- Reel {r['id']} ({q:%d/%m %H:%M}) reprovado no controle de qualidade: {'; '.join(problemas)}")
            video.unlink(missing_ok=True)
            continue
        fila.append({"id": f"reel_{q:%Y-%m-%d_%H%M}", "status": "pendente", "quando": q.isoformat(), "tipo": "reel",
                     "tema": r.get("tema", "sites"), "titulo": r["titulo"], "roteiro": r["id"],
                     "origem": r.get("origem", "estudio"),
                     "narracao": rel["narracao"], "duracao": rel["duracao"],
                     "imagens": [rel_path(video), rel_path(video.with_suffix(".jpg"))], "legenda": legenda})
        salvar_fila(fila)
        print(f"[ok] {nome}: {rel['duracao']} s, narração={rel['narracao']}, QA={rel['qa']}")
    restantes = len(disponiveis)
    if restantes < 9:
        print(f"Atenção: só {restantes} roteiro(s) de Reel restante(s).")
    if falhas:
        with open(RAIZ / "alerta.txt", "a", encoding="utf-8") as f:
            f.write("Reels:\n" + "\n".join(falhas) + "\n")
        print("\n".join(falhas))
        sys.exit(1)


if __name__ == "__main__":
    main()
