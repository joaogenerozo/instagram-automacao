"""GNZ01 Daily Quotes: renderiza os stories de citação que têm foto licenciada e põe na fila.
Uso: python tools/citacoes.py   (idempotente; itens sem foto ficam de fora com aviso)"""
import json, shutil, sys
from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import editorial as ed

dados = json.load(open(RAIZ / "conteudo/gnz01-citacoes.json"))
creditos = json.load(open(RAIZ / "midia/fotos/creditos.json"))
fila = json.load(open(RAIZ / "fila.json"))
ids = {i["id"] for i in fila}
cont = {}
novos = 0
for it in dados["itens"]:
    n = cont[it["data"]] = cont.get(it["data"], 0) + 1
    pid = f"gnz01_{it['data']}_quote{n}"
    if pid in ids:
        continue
    foto = RAIZ / f"midia/fotos/{it['slug']}.jpg"
    if not foto.exists() or it["slug"] not in creditos:
        print(f"AVISO: {pid} ({it['autor']}) sem foto licenciada; não entra na fila.")
        continue
    rel = f"midia/gnz01/{it['data']}/stories/quote-{n:02d}.jpg"
    ed.story_citacao({**it, "foto": str(foto), "credito": creditos[it["slug"]]["credito"]}, RAIZ / rel)
    entrega = RAIZ / f"GNZ01-MARKETING/STORIES/{it['data']}"
    entrega.mkdir(parents=True, exist_ok=True)
    shutil.copy(RAIZ / rel, entrega / f"story-{n:02d}.jpg")
    c = creditos[it["slug"]]
    (entrega / f"story-{n:02d}.md").write_text(
        f"# Story {n:02d} · {it['data']} {it['hora']}\n\n- Personalidade: {it['autor']}\n- Tema: {it.get('tema','')}\n"
        f"- Citação original: {it['original']}\n- Tradução usada: {it['citacao']}\n- Fonte: {it['fonte_citacao']}\n"
        f"- Link conferido: {it['fonte_url']}\n- Reflexão GNZ01: {it.get('reflexao','-')}\n- Interação: {it.get('interacao','-')}\n"
        f"- Foto: {c.get('autor')} · {c.get('licenca')} · {c.get('pagina_commons')}\n- Crédito: {c['credito']}\n")
    fila.append({"id": pid, "status": "pendente", "quando": f"{it['data']}T{it['hora']}:00-03:00", "tipo": "story",
                 "tema": "citacao", "titulo": f"{it['autor']}: {it['citacao']}", "imagens": [rel], "legenda": ""})
    novos += 1
fila.sort(key=lambda i: i["quando"])
json.dump(fila, open(RAIZ / "fila.json", "w"), ensure_ascii=False, indent=2)
print(f"{novos} story(s) de citação adicionados.")
