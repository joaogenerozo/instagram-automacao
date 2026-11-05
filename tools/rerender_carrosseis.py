"""Refaz no design system GNZ01 Carrossel (src/sistema.py) os carrosséis comuns pendentes.
Uso: python tools/rerender_carrosseis.py <semana.json>"""
import json, sys
from datetime import date, timedelta
from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import sistema as ss
cfg = json.load(open(RAIZ / "config.json"))
sem = json.load(open(RAIZ / sys.argv[1]))
fila = json.load(open(RAIZ / "fila.json"))
idx = {i["id"]: i for i in fila}
ini = date.fromisoformat(sem["inicio"])
for k, dia in enumerate(sem["dias"]):
    data = (ini + timedelta(days=k)).isoformat()
    for n, post in enumerate(dia["posts"]):
        pid = f"{sem['prefixo']}_{data}_{n + 1}"
        comum = post.get("tipo") == "carrossel" and post.get("slides") and not post.get("vitrine") \
            and post.get("layout") != "editorial" and not post.get("personalidade") and not post.get("papel")
        if comum and idx.get(pid, {}).get("status") == "pendente":
            imgs = ss.carrossel(post, RAIZ / f"midia/{sem['prefixo']}/{data}/{n + 1}", cfg)
            idx[pid]["imagens"] = [str(Path(i).relative_to(RAIZ)) for i in imgs]
            print(pid, len(imgs))
json.dump(fila, open(RAIZ / "fila.json", "w"), ensure_ascii=False, indent=2)
