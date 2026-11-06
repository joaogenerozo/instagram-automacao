"""Converte os posts de apresentação de serviço (vitrine) pendentes em carrosséis do design system
GNZ01 Carrossel (capa com foto + lâminas + CTA). Uso: python tools/servicos_carrossel.py <semana.json>"""
import json, sys
from datetime import date, timedelta
from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import sistema as ss

from src.servicos import LAMINAS, carrossel_servico


def main():
    cfg = json.load(open(RAIZ / "config.json"))
    sem = json.load(open(RAIZ / sys.argv[1]))
    fila = json.load(open(RAIZ / "fila.json"))
    idx = {i["id"]: i for i in fila}
    ini = date.fromisoformat(sem["inicio"])
    for k, dia in enumerate(sem["dias"]):
        data = (ini + timedelta(days=k)).isoformat()
        for n, post in enumerate(dia["posts"]):
            pid = f"{sem['prefixo']}_{data}_{n + 1}"
            v = post.get("vitrine")
            if not v or idx.get(pid, {}).get("status") != "pendente" or v["tipo"] not in LAMINAS:
                continue
            imgs = carrossel_servico(post, RAIZ / f"midia/{sem['prefixo']}/{data}/{n + 1}", cfg)
            idx[pid]["tipo"] = "carrossel"
            idx[pid]["imagens"] = [str(Path(i).relative_to(RAIZ)) for i in imgs]
            print(pid, v["tipo"], len(imgs))
    json.dump(fila, open(RAIZ / "fila.json", "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
