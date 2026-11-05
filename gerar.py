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
from src import vitrine as vt
from src import showcase as sc
from src import editorial as ed


def desenhar_vitrine(cfg, v, destino):
    """Desenha uma demonstração de produto (cardápio, agenda ou catálogo) no formato story."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = {k: v[k] for k in ("titulo", "subtitulo", "sigla", "nome", "chips", "notif", "botao",
                                "itens", "total", "produtos", "dominio", "marca", "chamada", "apoio", "servicos", "tom") if k in v}
    for k in ("itens", "produtos", "notif"):
        if k in campos:
            campos[k] = [tuple(x) for x in campos[k]] if k != "notif" else tuple(campos[k])
    if "tom" in campos:
        campos["tom"] = tuple(campos["tom"])
    fn = {"cardapio": vt.story_cardapio, "agenda": vt.story_agenda_manicure, "catalogo": vt.story_catalogo,
          "site": vt.story_site}[v["tipo"]]
    if v["tipo"] not in ("agenda", "site"):
        campos.pop("botao", None)
    return fn(cfg, destino, **campos)


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
    ap.add_argument("--aprovacao", action="store_true",
                    help="coloca na fila como 'aguardando_aprovacao' (não publica até mudar para 'pendente')")
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
    prefixo = semana.get("prefixo", "")
    status_inicial = "aguardando_aprovacao" if args.aprovacao else "pendente"
    if not args.inicio and semana.get("inicio"):
        inicio = date.fromisoformat(semana["inicio"])

    def adicionar(pid, **campos):
        if pid in ids:
            return
        fila.append({"id": pid, "status": status_inicial, **campos})
        ids.add(pid)
        cont[campos["tipo"]] += 1

    for d, dia in enumerate(semana["dias"]):
        data = inicio + timedelta(days=d)
        pasta_dia = RAIZ / "midia" / (f"{prefixo}/" if prefixo else "") / data.isoformat()
        base_id = f"{prefixo}_{data}" if prefixo else f"{data}"

        # posts do feed
        for n, post in enumerate(dia["posts"]):
            pid = f"{base_id}_{n + 1}"
            if pid in ids:
                continue
            pasta = pasta_dia / str(n + 1)
            if post.get("personalidade") and not (post.get("foto") or post.get("capa", {}).get("foto")):
                print(f"AVISO: {pid} cita {post['personalidade']} e está sem foto real licenciada; não entra na fila.")
                continue
            if post.get("vitrine"):
                pasta.mkdir(parents=True, exist_ok=True)
                imgs = [sc.vitrine_showcase(cfg, post["vitrine"], pasta / "01.jpg", "feed")]
            elif post.get("layout") == "editorial":
                for velho in pasta.glob("*.jpg"):
                    velho.unlink()
                arte = json.loads(json.dumps(post).replace("{whatsapp}", cfg["whatsapp"]))
                imgs = ed.carrossel(arte, pasta) if arte["tipo"] == "carrossel" else [ed.peca(arte, pasta / "01.jpg")]
            elif post["tipo"] == "carrossel":
                imgs = des.carrossel(post, pasta)
            else:
                imgs = [des.post(post, pasta / "01.jpg")]
            adicionar(pid, quando=horario(data, cfg["horarios"][n % len(cfg["horarios"])], tz),
                      tipo=post["tipo"], tema=post["tema"], titulo=post["titulo"],
                      imagens=[rel(i) for i in imgs], legenda=montar_legenda(post, cfg))

        # stories: roteiro do dia (texto, perguntas frequentes e demonstração) ou só perguntas frequentes
        roteiro = dia.get("stories") or [{"tipo": "faq"}] * len(cfg.get("horarios_stories", []))
        for s, (hora, st) in enumerate(zip(cfg.get("horarios_stories", []), roteiro)):
            pid = f"{base_id}_story{s + 1}"
            if pid in ids:
                continue
            destino = pasta_dia / "stories" / f"{s + 1}.jpg"
            if st["tipo"] == "faq":
                item = faq[n_stories % len(faq)]
                n_stories += 1
                img, tema, titulo = des.story(item, destino, numero=None), item["tema"], item["pergunta"]
            elif st["tipo"] in ("cardapio", "agenda", "catalogo", "site"):
                destino.parent.mkdir(parents=True, exist_ok=True)
                img, tema, titulo = sc.vitrine_showcase(cfg, st, destino, "story"), st["tipo"], st["titulo"]
            else:
                item = {**st, "cta": st.get("cta", "").replace("{whatsapp}", cfg["whatsapp"]) or None}
                if not item["cta"]:
                    item.pop("cta")
                img, tema, titulo = des.story_texto(item, destino), st.get("pilar", "marca"), st["titulo"]
            adicionar(pid, quando=horario(data, hora, tz), tipo="story", tema=tema,
                      titulo=titulo, imagens=[rel(img)], legenda="")

        # reels de depoimentos (1 por dia enquanto houver vídeo novo)
        if videos_novos and cfg.get("horario_reels"):
            video = videos_novos.pop(0)
            txt = video.with_suffix(".txt")
            legenda = txt.read_text(encoding="utf-8").strip() if txt.exists() else \
                "Olha o que nosso cliente achou! 🙌\n\nQuer o mesmo resultado? Chama no WhatsApp {whatsapp}"
            adicionar(f"{base_id}_reel", quando=horario(data, cfg["horario_reels"], tz), tipo="reel",
                      tema="depoimento", titulo=video.stem, imagens=[rel(video)],
                      legenda=montar_legenda({"legenda": legenda, "hashtags": ["#depoimento", "#clientesatisfeito"]}, cfg))

    salvar_fila(fila)
    print(f"Fila a partir de {inicio}: {cont}")


if __name__ == "__main__":
    main()
