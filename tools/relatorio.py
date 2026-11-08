"""Relatório semanal de desempenho com dados reais da API do Instagram.

Gera GNZ01-MARKETING/RELATORIOS/kpis-AAAA-MM-DD.md e conteudo/desempenho.json
(lido pelo gerar_conteudo_ia.py para repetir o que funcionou).
Precisa de IG_USER_ID e IG_ACCESS_TOKEN com a permissão instagram_manage_insights.
Uso: python tools/relatorio.py [--dias 7]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.comum import carregar_config, carregar_fila  # noqa: E402

METRICAS = ["reach", "saved", "shares", "views", "profile_visits", "follows", "total_interactions"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=7)
    args = ap.parse_args()
    cfg = carregar_config()
    user, token = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
    if not (user and token):
        sys.exit("Sem IG_USER_ID/IG_ACCESS_TOKEN: relatório não gerado.")
    base = f"{cfg['graph_api_host']}/{cfg['graph_api_versao']}"

    def get(caminho, **params):
        r = requests.get(f"{base}/{caminho}", params={**params, "access_token": token}, timeout=60).json()
        if "error" in r:
            raise RuntimeError(r["error"].get("message"))
        return r

    conta = get(user, fields="username,followers_count,follows_count,media_count")
    desde = datetime.now(timezone.utc) - timedelta(days=args.dias)
    midias, url = [], f"{user}/media"
    params = {"fields": "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count", "limit": 50}
    while url:
        r = get(url, **params)
        for m in r.get("data", []):
            if datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")) >= desde:
                midias.append(m)
        nxt = r.get("paging", {}).get("next")
        url = None
        if nxt and r.get("data") and datetime.fromisoformat(r["data"][-1]["timestamp"].replace("+0000", "+00:00")) >= desde:
            url, params = nxt.replace(base + "/", ""), {}

    titulos = {p.get("media_id"): p.get("titulo") for p in carregar_fila() if p.get("media_id")}
    linhas = []
    for m in midias:
        valores = {}
        for met in METRICAS:  # pede uma a uma: nem toda métrica existe para todo formato
            try:
                d = get(f"{m['id']}/insights", metric=met)["data"]
                valores[met] = d[0]["values"][0]["value"] if d and "values" in d[0] else (d[0].get("total_value", {}).get("value") if d else None)
            except RuntimeError:
                valores[met] = None
        titulo = titulos.get(m["id"]) or (m.get("caption") or "").split("\n")[0][:70]
        linhas.append({"titulo": titulo, "tipo": m.get("media_product_type", m["media_type"]).lower(),
                       "data": m["timestamp"][:10], "link": m.get("permalink"),
                       "alcance": valores["reach"] or 0, "salvos": valores["saved"] or 0,
                       "compartilhamentos": valores["shares"] or 0, "visitas_perfil": valores["profile_visits"],
                       "seguiram": valores["follows"], "curtidas": m.get("like_count", 0),
                       "comentarios": m.get("comments_count", 0)})

    def nota(x):  # salvar/compartilhar/comentar pesa mais que alcance puro
        return x["alcance"] + 5 * (x["salvos"] + x["compartilhamentos"]) + 3 * x["comentarios"]

    ordem = sorted(linhas, key=nota, reverse=True)
    hoje = datetime.now().date().isoformat()
    resumo = {"gerado_em": hoje, "seguidores": conta.get("followers_count"), "seguindo": conta.get("follows_count"),
              "melhores": ordem[:5], "piores": ordem[-5:] if len(ordem) > 5 else []}
    (RAIZ / "conteudo" / "desempenho.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    def soma(k):
        return sum(x[k] or 0 for x in linhas)

    md = [f"# KPIs da semana · {hoje}", "",
          f"Conta @{conta.get('username')}: **{conta.get('followers_count')} seguidores**, seguindo "
          f"{conta.get('follows_count')}, {conta.get('media_count')} publicações.", "",
          f"Últimos {args.dias} dias: {len(linhas)} publicações no feed/Reels, alcance somado {soma('alcance')}, "
          f"{soma('salvos')} salvamentos, {soma('compartilhamentos')} compartilhamentos, {soma('comentarios')} comentários.", "",
          "| Data | Tipo | Publicação | Alcance | Salvos | Compart. | Coment. | Visitas perfil | Seguiram |",
          "|---|---|---|---|---|---|---|---|---|"]
    for x in ordem:
        md.append(f"| {x['data']} | {x['tipo']} | [{x['titulo']}]({x['link']}) | {x['alcance']} | {x['salvos']} | "
                  f"{x['compartilhamentos']} | {x['comentarios']} | {x['visitas_perfil'] if x['visitas_perfil'] is not None else '-'} | "
                  f"{x['seguiram'] if x['seguiram'] is not None else '-'} |")
    md += ["", "Ordem: alcance + 5 × (salvos + compartilhamentos) + 3 × comentários. "
           "Os 5 primeiros orientam a IA na próxima semana (conteudo/desempenho.json)."]
    destino = RAIZ / "GNZ01-MARKETING" / "RELATORIOS" / f"kpis-{hoje}.md"
    destino.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(destino.relative_to(RAIZ))


if __name__ == "__main__":
    main()
