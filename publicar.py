"""Publica no Instagram os posts da fila cujo horário já chegou.

Variáveis de ambiente necessárias:
  IG_USER_ID       ID da conta profissional do Instagram
  IG_ACCESS_TOKEN  token de acesso com permissão instagram_content_publish

Uso:
  python publicar.py            publica o que estiver no horário
  python publicar.py --simular  mostra o que seria publicado, sem publicar
  python publicar.py --testar   só confere se o token e a conta funcionam
"""
import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

import json

from src.comum import RAIZ, FEED, carregar_config, carregar_fila, eh_citacao, repetido, salvar_fila, semana_iso

JANELA_MAX = timedelta(hours=3)  # post atrasado mais que isso é pulado (evita rajada de posts)
ALERTA = RAIZ / "alerta.txt"  # lido pelo workflow para abrir um aviso (issue) no GitHub


def extras_feed(p, cfg):
    """Localização e collab (até 3 contas) para posts, carrosséis e Reels."""
    extras = {}
    loc = p.get("location_id") or cfg.get("local", {}).get("location_id")
    if loc:
        extras["location_id"] = str(loc)
    colab = [c.lstrip("@") for c in p.get("colaboradores", [])][:3]
    if colab:
        extras["collaborators"] = json.dumps(colab)
    return extras


class Instagram:
    def __init__(self, cfg):
        self.base = f"{cfg['graph_api_host']}/{cfg['graph_api_versao']}"
        self.user = os.environ["IG_USER_ID"]
        self.token = os.environ["IG_ACCESS_TOKEN"]

    def _req(self, metodo, caminho, **params):
        params["access_token"] = self.token
        r = requests.request(metodo, f"{self.base}/{caminho}", params=params if metodo == "GET" else None,
                             data=params if metodo == "POST" else None, timeout=60)
        dados = r.json()
        if "error" in dados:
            raise RuntimeError(f"Erro da API: {dados['error'].get('message')} ({caminho})")
        return dados

    def conta(self):
        return self._req("GET", self.user, fields="username,media_count")

    def _esperar(self, container_id, tentativas=30):
        for _ in range(tentativas):
            st = self._req("GET", container_id, fields="status_code")["status_code"]
            if st == "FINISHED":
                return
            if st in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Container {container_id} falhou: {st}")
            time.sleep(5)
        raise RuntimeError("Tempo esgotado esperando o Instagram processar a imagem")

    def publicar_imagem(self, url, legenda, **extras):
        c = self._req("POST", f"{self.user}/media", image_url=url, caption=legenda, **extras)["id"]
        self._esperar(c)
        return self._req("POST", f"{self.user}/media_publish", creation_id=c)["id"]

    def publicar_story(self, url):
        c = self._req("POST", f"{self.user}/media", image_url=url, media_type="STORIES")["id"]
        self._esperar(c)
        return self._req("POST", f"{self.user}/media_publish", creation_id=c)["id"]

    def publicar_reel(self, url, legenda):
        c = self._req("POST", f"{self.user}/media", video_url=url, media_type="REELS",
                      caption=legenda, share_to_feed="true")["id"]
        self._esperar(c, tentativas=120)  # vídeo pode levar alguns minutos para processar
        return self._req("POST", f"{self.user}/media_publish", creation_id=c)["id"]

    def publicar_carrossel(self, urls, legenda, **extras):
        filhos = []
        for u in urls[:10]:  # o Instagram aceita até 10 itens
            filhos.append(self._req("POST", f"{self.user}/media", image_url=u, is_carousel_item="true")["id"])
        for f in filhos:
            self._esperar(f)
        c = self._req("POST", f"{self.user}/media", media_type="CAROUSEL",
                      children=",".join(filhos), caption=legenda, **extras)["id"]
        self._esperar(c)
        return self._req("POST", f"{self.user}/media_publish", creation_id=c)["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--testar", action="store_true")
    args = ap.parse_args()

    cfg = carregar_config()
    if args.testar:
        print("Conta conectada:", Instagram(cfg).conta())
        return

    agora = datetime.now(ZoneInfo(cfg["fuso"]))
    fila = carregar_fila()
    devidos = [p for p in fila if p["status"] == "pendente" and datetime.fromisoformat(p["quando"]) <= agora]
    if not devidos:
        print("Nada para publicar agora.")
        return

    ig = None if args.simular else Instagram(cfg)
    base = cfg["url_base_imagens"].rstrip("/") + "/"
    falhas = 0
    avisos = []
    feed_nesta_rodada = False

    def pular(p, motivo):
        p["status"] = "pulado"
        p["motivo"] = motivo
        avisos.append(f"- {p['id']} ({p['tipo']}, {p['quando'][:16]}) pulado: {motivo} | {p.get('titulo', '')[:70]}")
        print(f"[pulado] {p['id']}: {motivo}")

    for p in devidos:
        if agora - datetime.fromisoformat(p["quando"]) > JANELA_MAX:
            pular(p, "atrasou mais de 3 horas (agendamento do GitHub)")
            continue
        if p["tipo"] in FEED:
            antigo = repetido(p, fila, cfg.get("janela_repeticao_dias", 45))
            if antigo:
                pular(p, f"repetido: parecido com {antigo['id']} ({antigo['titulo'][:50]})")
                continue
            limite = cfg.get("limite_citacoes_semana")
            if limite and eh_citacao(p):
                na_semana = [o for o in fila if o is not p and o["status"] == "publicado" and eh_citacao(o)
                             and semana_iso(o.get("publicado_em") or o["quando"]) == semana_iso(p["quando"])]
                if len(na_semana) >= limite:
                    pular(p, f"limite de {limite} post de citação por semana")
                    continue
            if feed_nesta_rodada:  # dois posts de feed no mesmo horário: o segundo sai na próxima rodada
                print(f"[adiado] {p['id']}: já saiu um post de feed nesta rodada")
                continue
        urls = [base + i for i in p["imagens"]]
        if args.simular:
            print(f"[simulação] {p['id']} {p['tipo']}: {p['titulo']}\n  {urls[0]}")
            feed_nesta_rodada = feed_nesta_rodada or p["tipo"] in FEED
            continue
        try:
            if p["tipo"] == "story":
                media_id = ig.publicar_story(urls[0])
            elif p["tipo"] == "reel":
                media_id = ig.publicar_reel(urls[0], p["legenda"])
            else:
                fn = ig.publicar_carrossel if p["tipo"] == "carrossel" else (lambda u, l, **x: ig.publicar_imagem(u[0], l, **x))
                extras = extras_feed(p, cfg)
                try:
                    media_id = fn(urls, p["legenda"], **extras)
                except RuntimeError as e:
                    if not extras:
                        raise
                    # localização ou collab inválidos não podem derrubar o post: publica sem eles e avisa
                    avisos.append(f"- {p['id']}: saiu sem localização/collab ({e})")
                    media_id = fn(urls, p["legenda"])
            p.update(status="publicado", media_id=media_id, publicado_em=datetime.now(ZoneInfo(cfg["fuso"])).isoformat())
            print(f"[ok] {p['id']} publicado ({media_id})")
            if p["tipo"] in FEED:
                feed_nesta_rodada = True
        except Exception as e:  # registra e tenta de novo na próxima execução
            p["tentativas"] = p.get("tentativas", 0) + 1
            p["ultimo_erro"] = str(e)
            if p["tentativas"] >= 3:
                p["status"] = "erro"
                avisos.append(f"- {p['id']} ({p['tipo']}, {p['quando'][:16]}) falhou 3 vezes: {e}")
            falhas += 1
            print(f"[erro] {p['id']}: {e}")
    if not args.simular:
        salvar_fila(fila)
        if avisos:
            ALERTA.write_text("\n".join(avisos) + "\n", encoding="utf-8")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
