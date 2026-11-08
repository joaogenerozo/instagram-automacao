"""Aplica as regras atuais aos posts de feed que ainda estão na fila (idempotente):
- legenda com CTA único, linha local e no máximo 5 hashtags;
- tira posts repetidos (título parecido com algo já publicado ou agendado antes);
- no máximo N posts de citação por semana (config "limite_citacoes_semana"); devolve o post original do horário;
- um post de feed por horário.
Stories e Reels não são tocados. Uso: python tools/limpar_fila.py [--simular]"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.comum import (FEED, carregar_config, carregar_fila, eh_citacao, remontar_legenda,  # noqa: E402
                       repetido, salvar_fila, semana_iso)

ATIVOS = ("pendente", "aguardando_aprovacao")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true")
    args = ap.parse_args()
    cfg = carregar_config()
    fila = carregar_fila()
    fila.sort(key=lambda p: p["quando"])
    por_id = {p["id"]: p for p in fila}
    mudancas = defaultdict(list)

    def pular(p, motivo):
        p["status"] = "pulado"
        p["motivo"] = motivo
        mudancas["pulados"].append(f"{p['id']}: {motivo}")

    # 1) citações: no máximo N por semana (as que já saíram contam primeiro)
    limite = cfg.get("limite_citacoes_semana")
    if limite:
        contagem = defaultdict(int)
        for p in fila:
            if eh_citacao(p) and p["status"] == "publicado":
                contagem[semana_iso(p.get("publicado_em") or p["quando"])] += 1
        for p in fila:
            if eh_citacao(p) and p["status"] in ATIVOS:
                s = semana_iso(p["quando"])
                if contagem[s] >= limite:
                    pular(p, f"limite de {limite} post de citação por semana")
                    orig = por_id.get(p["id"].rsplit("_p", 1)[0] + f"_{int(p['id'].rsplit('_p', 1)[1]) + 1}") \
                        if "_p" in p["id"] else None
                    if orig and orig["status"] == "pulado" and "Substituído" in orig.get("observacao", ""):
                        orig["status"] = "pendente"
                        orig.pop("observacao", None)
                        mudancas["devolvidos"].append(orig["id"])
                else:
                    contagem[s] += 1

    # 2) repetidos e 3) dois posts de feed no mesmo horário
    for p in fila:
        if p["tipo"] not in FEED or p["status"] not in ATIVOS:
            continue
        antigo = repetido(p, fila, cfg.get("janela_repeticao_dias", 45))
        if antigo:
            pular(p, f"repetido: parecido com {antigo['id']} ({antigo['titulo'][:50]})")
            continue
        mesmo_horario = [o for o in fila if o is not p and o["tipo"] in FEED and o["status"] in ATIVOS
                         and o["quando"] == p["quando"] and fila.index(o) < fila.index(p)]
        if mesmo_horario:
            pular(p, f"mesmo horário de {mesmo_horario[0]['id']}")

    # 4) legendas
    for p in fila:
        if p["tipo"] in FEED and p["status"] in ATIVOS and p.get("legenda"):
            nova = remontar_legenda(p, cfg)
            if nova != p["legenda"]:
                p["legenda"] = nova
                mudancas["legendas"].append(p["id"])

    for k, v in mudancas.items():
        print(f"{k}: {len(v)}")
        for x in v if k != "legendas" else []:
            print("  ", x)
    if not args.simular:
        salvar_fila(fila)


if __name__ == "__main__":
    main()
