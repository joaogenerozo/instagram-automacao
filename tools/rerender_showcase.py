"""Refaz no padrão Product Showcase as peças de produto ainda pendentes da semana (mesmos arquivos e ids)."""
import json, sys
from datetime import date, timedelta
from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import showcase as sc
cfg = json.load(open(RAIZ / "config.json"))
sem = json.load(open(RAIZ / sys.argv[1]))
fila = {i["id"]: i for i in json.load(open(RAIZ / "fila.json"))}
ini = date.fromisoformat(sem["inicio"])
for k, dia in enumerate(sem["dias"]):
    data = (ini + timedelta(days=k)).isoformat()
    for n, post in enumerate(dia["posts"]):
        pid = f"{sem['prefixo']}_{data}_{n + 1}"
        if post.get("vitrine") and fila.get(pid, {}).get("status") == "pendente":
            for img in fila[pid]["imagens"]:
                sc.vitrine_showcase(cfg, post["vitrine"], RAIZ / img, "feed"); print("feed", pid, img)
    for s, st in enumerate(dia.get("stories", [])):
        pid = f"{sem['prefixo']}_{data}_story{s + 1}"
        if st["tipo"] in sc.PADROES and fila.get(pid, {}).get("status") == "pendente":
            sc.vitrine_showcase(cfg, st, RAIZ / fila[pid]["imagens"][0], "story"); print("story", pid)
