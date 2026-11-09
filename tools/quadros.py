"""Quadros fixos de engajamento (pesquisa de perfis semelhantes, 09/11/2026).

Cada item do JSON ocupa o horário de um post pendente mais fraco ("substitui"). O post antigo não é apagado:
fica com status "pulado" e motivo, e pode voltar trocando o status para "pendente".
Idempotente: rodar de novo não duplica nada.

Uso:  python tools/quadros.py conteudo/engajamento/quadros-semana-02.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.comum import RAIZ, carregar_config, carregar_fila, salvar_fila, montar_legenda  # noqa: E402
from src.render import Desenhista  # noqa: E402
from src import sistema as ss  # noqa: E402


def main(arquivo):
    cfg = carregar_config()
    dados = json.loads((RAIZ / arquivo).read_text(encoding="utf-8"))
    fila = carregar_fila()
    por_id = {i["id"]: i for i in fila}
    des = Desenhista(cfg)
    novos = 0
    for q in dados["itens"]:
        pid = f"quadro_{q['quando'][:10]}_{q['quadro']}"
        if pid in por_id:
            continue
        antigo = por_id.get(q.get("substitui"))
        if antigo and antigo["status"] == "publicado":
            print(f"AVISO: {antigo['id']} já foi publicado; {pid} não entra.")
            continue
        pasta = RAIZ / "midia" / "quadros" / q["quando"][:10] / q["quadro"]
        if q["tipo"] == "carrossel":
            imgs = ss.carrossel(q, pasta, cfg)
        else:
            pasta.mkdir(parents=True, exist_ok=True)
            imgs = [des.post(q, pasta / "01.jpg")]
        if antigo:
            antigo["status"] = "pulado"
            antigo["motivo"] = f"substituído pelo quadro de engajamento {pid} (09/11)"
        item = {"id": pid, "status": "pendente", "quando": q["quando"], "tipo": q["tipo"], "tema": q["tema"],
                "titulo": q["titulo"].replace("**", ""), "quadro": q["quadro"],
                "imagens": [str(i.relative_to(RAIZ)).replace("\\", "/") for i in imgs],
                "legenda": montar_legenda(q, cfg)}
        if q.get("cta_personalizado"):
            item["cta_personalizado"] = q["cta_personalizado"]
        fila.append(item)
        por_id[pid] = item
        novos += 1
        print(f"{pid}: {len(imgs)} imagem(ns) no lugar de {q.get('substitui')}")
    fila.sort(key=lambda i: i["quando"])
    salvar_fila(fila)
    print(f"{novos} quadro(s) na fila.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "conteudo/engajamento/quadros-semana-02.json")
