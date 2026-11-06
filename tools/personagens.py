"""Põe na fila os carrosséis de personagem (conteudo/gnz01-personagens.json) que já têm foto licenciada.
slot = índice do post do dia (3 = 18:30, 4 = 21:00). O post original desse horário vira "pulado" (substituído).
Com 4+ fotos da pessoa usa o layout "Os ensinamentos de" (foto diferente por lâmina); com 1-3, capa central.
Idempotente. Uso: python tools/personagens.py"""
import json, sys
from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src import editorial as ed, ensinamentos as en

cfg = json.load(open(RAIZ / "config.json"))
dados = json.load(open(RAIZ / "conteudo/gnz01-personagens.json"))
cred = json.load(open(RAIZ / "midia/fotos/creditos.json"))
fila = json.load(open(RAIZ / "fila.json"))
ids = {i["id"]: i for i in fila}
horas = cfg["horarios"]
fixas = ["#gnz01", "#solucoesdigitais"]
novos = 0
for n, it in enumerate(dados["itens"], 1):
    pid = f"gnz01_{it['data']}_p{it['slot']}"
    existente = ids.get(pid)
    if existente and existente.get("motivo") == "fotos sem nitidez suficiente":
        existente["status"] = "pendente"  # tenta de novo: pode ter chegado foto nova
    if existente and existente["status"] != "pendente":
        continue
    fotos = en.fotos_de(it["slug"], RAIZ)
    unica = RAIZ / f"midia/fotos/{it['slug']}.jpg"
    if not fotos and unica.exists() and it["slug"] in cred:
        fotos = [(str(unica), cred[it["slug"]]["credito"])]
    from src import qualidade as q
    fotos = [f for f in fotos if q.aprovada(f[0], (1080, 1350))[0]]  # só fotos nítidas (pedido do João, 06/11)
    if not fotos:
        print(f"AVISO: {pid} ({it['personalidade']}) sem foto licenciada e nítida; horário mantém o post original.")
        if existente:  # já estava na fila: tira e devolve o post original do horário
            existente["status"] = "pulado"
            existente["motivo"] = "fotos sem nitidez suficiente"
            orig = ids.get(f"gnz01_{it['data']}_{it['slot'] + 1}")
            if orig and orig["status"] == "pulado" and "Substituído" in orig.get("observacao", ""):
                orig["status"] = "pendente"
                orig.pop("observacao", None)
        continue
    w = cfg["whatsapp"]
    p = json.loads(json.dumps({
        "tipo": "carrossel", "personalidade": it["personalidade"], "papel": it["papel"],
        "capa": {"titulo": it["titulo"], "autor": it["personalidade"], "fonte_citacao": it["fonte_citacao"],
                 "foto": fotos[0][0], "credito": fotos[0][1]},
        "slides": it["slides"]}).replace("{whatsapp}", w))
    pasta = RAIZ / f"midia/gnz01/{it['data']}/p{it['slot']}"
    imgs = en.carrossel(p, fotos, pasta) if len(fotos) >= 4 else ed.carrossel(p, pasta)
    legenda = it["legenda"].replace("{whatsapp}", w) + "\n.\n.\n" + " ".join(it["hashtags"] + fixas)
    if len(fotos) == 1:
        legenda += "\n\n📷 " + fotos[0][1]
    else:
        legenda += "\n\n📷 Fotos: " + "; ".join(sorted({c for _, c in fotos}))
    if existente:  # pendente: re-renderizado só com fotos nítidas e realce
        existente["imagens"] = [str(Path(i).relative_to(RAIZ)) for i in imgs]
        existente["legenda"] = legenda
        existente["fotos_por_lamina"] = len(fotos) >= 4
        continue
    orig = ids.get(f"gnz01_{it['data']}_{it['slot'] + 1}")
    if orig and orig["status"] == "pendente" and orig["quando"].startswith(it["data"]):
        orig["status"] = "pulado"
        orig["observacao"] = f"Substituído pelo carrossel de {it['personalidade']} (pedido do João, 05/11)."
    hora = horas[it["slot"] % len(horas)]
    fila.append({"id": pid, "status": "pendente", "quando": f"{it['data']}T{hora}:00-03:00", "tipo": "carrossel",
                 "tema": "marca", "titulo": f"Os ensinamentos de {it['personalidade']}",
                 "imagens": [str(Path(i).relative_to(RAIZ)) for i in imgs], "legenda": legenda,
                 "fotos_por_lamina": len(fotos) >= 4})
    novos += 1
fila.sort(key=lambda i: i["quando"])
json.dump(fila, open(RAIZ / "fila.json", "w"), ensure_ascii=False, indent=2)
print(f"{novos} carrossel(is) de personagem adicionados.")
