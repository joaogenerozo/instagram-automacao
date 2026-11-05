"""Refaz os posts 'normais' pendentes (sem layout editorial, sem vitrine, sem personalidade) no visual atual."""
import json, sys
from datetime import date, timedelta
from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.render import Desenhista
cfg = json.load(open(RAIZ / "config.json"))
des = Desenhista(cfg)
sem = json.load(open(RAIZ / sys.argv[1]))
fila = json.load(open(RAIZ / "fila.json"))
idx = {i["id"]: i for i in fila}
ini = date.fromisoformat(sem["inicio"])
for k, dia in enumerate(sem["dias"]):
    data = (ini + timedelta(days=k)).isoformat()
    for n, post in enumerate(dia["posts"]):
        pid = f"{sem['prefixo']}_{data}_{n + 1}"
        if post.get("layout") == "editorial" or post.get("vitrine") or post.get("personalidade"):
            continue
        if idx.get(pid, {}).get("status") != "pendente":
            continue
        pasta = RAIZ / f"midia/{sem['prefixo']}/{data}/{n + 1}"
        p = json.loads(json.dumps(post).replace("{whatsapp}", cfg["whatsapp"]))
        imgs = des.carrossel(p, pasta) if p["tipo"] == "carrossel" else [des.post(p, pasta / "01.jpg")]
        idx[pid]["imagens"] = [str(Path(i).relative_to(RAIZ)) for i in imgs]
        print(pid, len(imgs))
json.dump(fila, open(RAIZ / "fila.json", "w"), ensure_ascii=False, indent=2)
