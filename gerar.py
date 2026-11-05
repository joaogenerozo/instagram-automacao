"""Gera as imagens e coloca na fila de publicação uma semana de:
  - 5 posts por dia (1 carrossel + 4 posts)
  - 7 stories por dia com perguntas frequentes
  - 1 Reels por dia, se houver vídeos novos na pasta videos/

Uso:  python gerar.py conteudo/semana-01.json --inicio 2026-11-09
"""
import argparse
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.comum import RAIZ, carregar_config, carregar_fila, salvar_fila, montar_legenda
from src.render import Desenhista


def proxima_segunda():
    hoje = date.today()
    return hoje + timedelta(days=(7 - hoje.weekday()) % 7 or 7)


def horario(data, hora, tz):
    return datetime.combine(data, datetime.strptime(hora, "%H:%M").time(), tz).isoformat()


def rel(caminho):
    return str(caminho.relative_to(RAIZ)).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo", help="JSON da semana, ex.: conteudo/semana-01.json")
    ap.add_argument("--inicio", help="primeiro dia (AAAA-MM-DD). Padrão: próxima segunda")
    args = ap.parse_args()

    cfg = carregar_config()
    tz = ZoneInfo(cfg["fuso"])
    inicio = date.fromisoformat(args.inicio) if args.inicio else proxima_segunda()
    semana = json.loads((RAIZ / args.arquivo).read_text(encoding="utf-8"))
    faq = json.loads((RAIZ / "conteudo" / "stories-faq.json").read_text(encoding="utf-8"))["perguntas"]
    des = Desenhista(cfg)
    fila = carregar_fila()
    ids = {p["id"] for p in fila}
    n_stories = sum(1 for p in fila if p["tipo"] == "story")
    videos_usados = {p["imagens"][0] for p in fila if p["tipo"] == "reel"}
    videos_novos = [v for v in sorted((RAIZ / "videos").glob("*.mp4")) if rel(v) not in videos_usados]
    cont = {"post": 0, "carrossel": 0, "story": 0, "reel": 0}

    def adicionar(pid, **campos):
        if pid in ids:
            return
        fila.append({"id": pid, "status": "pendente", **campos})
        ids.add(pid)
        cont[campos["tipo"]] += 1

    for d, dia in enumerate(semana["dias"]):
        data = inicio + timedelta(days=d)
        pasta_dia = RAIZ / "midia" / data.isoformat()

        # posts do feed
        for n, post in enumerate(dia["posts"]):
            pid = f"{data}_{n + 1}"
            if pid in ids:
                continue
            pasta = pasta_dia / str(n + 1)
            imgs = des.carrossel(post, pasta) if post["tipo"] == "carrossel" else [des.post(post, pasta / "01.jpg")]
            adicionar(pid, quando=horario(data, cfg["horarios"][n % len(cfg["horarios"])], tz),
                      tipo=post["tipo"], tema=post["tema"], titulo=post["titulo"],
                      imagens=[rel(i) for i in imgs], legenda=montar_legenda(post, cfg))

        # stories de perguntas frequentes (rodízio pelo banco)
        for s, hora in enumerate(cfg.get("horarios_stories", [])):
            pid = f"{data}_story{s + 1}"
            if pid in ids:
                continue
            item = faq[n_stories % len(faq)]
            n_stories += 1
            img = des.story(item, pasta_dia / "stories" / f"{s + 1}.jpg", numero=None)
            adicionar(pid, quando=horario(data, hora, tz), tipo="story", tema=item["tema"],
                      titulo=item["pergunta"], imagens=[rel(img)], legenda="")

        # reels de depoimentos (1 por dia enquanto houver vídeo novo)
        if videos_novos and cfg.get("horario_reels"):
            video = videos_novos.pop(0)
            txt = video.with_suffix(".txt")
            legenda = txt.read_text(encoding="utf-8").strip() if txt.exists() else \
                "Olha o que nosso cliente achou! 🙌\n\nQuer o mesmo resultado? Chama no WhatsApp {whatsapp}"
            adicionar(f"{data}_reel", quando=horario(data, cfg["horario_reels"], tz), tipo="reel",
                      tema="depoimento", titulo=video.stem, imagens=[rel(video)],
                      legenda=montar_legenda({"legenda": legenda, "hashtags": ["#depoimento", "#clientesatisfeito"]}, cfg))

    salvar_fila(fila)
    print(f"Fila a partir de {inicio}: {cont}")


if __name__ == "__main__":
    main()
