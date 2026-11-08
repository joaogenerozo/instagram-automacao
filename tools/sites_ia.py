"""Carrosséis de SITES por nicho com capa feita por IA (pedido do João, 08/11/2026).

Para cada item de conteudo/gnz01-sites-ia.json:
1. gera a capa em midia/fotos/ia/<cenario>.jpg se ainda não existir
   (Gemini se houver GEMINI_API_KEY; as capas atuais vieram do Canva via tools/baixar_capas.py);
2. desenha o carrossel no design system (src/servicos.py, capa com IA permitida);
3. coloca na fila no horário do item, no lugar do post de feed que estava ali (vira "pulado" com observação).
Idempotente: o que já está na fila ou já passou do horário não é refeito,
a não ser com --refazer (redesenha os pendentes, por exemplo depois de trocar a capa).
Uso: python tools/sites_ia.py [--refazer]"""
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.comum import FEED, carregar_config, carregar_fila, montar_legenda, salvar_fila  # noqa: E402
from src import servicos as sv  # noqa: E402

CONTEUDO = RAIZ / "conteudo" / "gnz01-sites-ia.json"
CREDITOS = RAIZ / "midia" / "fotos" / "creditos.json"


def gerar_capa(prompt, destino, seed):
    import os
    chave = os.environ.get("GEMINI_API_KEY")
    if chave:
        from tools.capas_ia import gerar  # noqa: E402
        m = gerar(prompt, destino, chave)
        if m:
            return f"Gemini ({m})"
    return None  # sem fallback gratuito: o Pollinations sai com marca d'água e baixa resolução


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refazer", action="store_true", help="redesenha os carrosséis ainda pendentes")
    refazer = ap.parse_args().refazer
    cfg = carregar_config()
    tz = ZoneInfo(cfg["fuso"])
    agora = datetime.now(tz)
    dados = json.loads(CONTEUDO.read_text(encoding="utf-8"))
    cred = json.loads(CREDITOS.read_text(encoding="utf-8"))
    fila = carregar_fila()
    ids = {p["id"]: p for p in fila}
    hora = dados.get("hora", "15:00")

    for n, it in enumerate(dados["itens"]):
        pid = f"gnz01_{it['data']}_site_ia"
        quando = datetime.fromisoformat(f"{it['data']}T{hora}:00").replace(tzinfo=tz)
        if quando <= agora or (pid in ids and not (refazer and ids[pid]["status"] == "pendente")):
            continue
        slug = it["cenario"]
        foto = RAIZ / f"midia/fotos/ia/{slug}.jpg"
        if not foto.exists():
            origem = gerar_capa(it["prompt_capa"], foto, seed=1000 + n)
            if not origem:
                print(f"AVISO: {pid} sem capa de IA (geração falhou); fica de fora por enquanto.")
                continue
            cred[f"ia/{slug}"] = {"arquivo": str(foto.relative_to(RAIZ)), "modelo": origem,
                                  "credito": "Imagem ilustrativa gerada por IA"}
            CREDITOS.write_text(json.dumps(cred, ensure_ascii=False, indent=2), encoding="utf-8")
            print("capa ok", slug, origem)
        post = {"tipo": "carrossel", "tema": "sites", "titulo": it["titulo"].replace("**", ""),
                "vitrine": {"tipo": "site", "titulo": it["titulo"], "subtitulo": it["subtitulo"]},
                "slides": it["slides"], "cta_final": it["cta_final"], "cenario": slug,
                "hashtags": it.get("hashtags", []), "legenda": it["legenda"]}
        pasta = RAIZ / f"midia/gnz01/{it['data']}/site_ia"
        pasta.mkdir(parents=True, exist_ok=True)
        imgs = sv.carrossel_servico(post, pasta, cfg)
        iso = quando.isoformat()
        for o in fila:  # libera o horário: o post que estava ali sai (pode voltar trocando o status)
            if o.get("id") != pid and o["tipo"] in FEED and o["quando"] == iso \
                    and o["status"] in ("pendente", "aguardando_aprovacao"):
                o["status"] = "pulado"
                o["observacao"] = "Substituído pelo carrossel de site com capa de IA (pedido do João, 08/11)."
        item = {"id": pid, "status": "pendente", "quando": iso, "tipo": "carrossel", "tema": "sites",
                "titulo": post["titulo"], "imagens": [str(Path(i).relative_to(RAIZ)) for i in imgs],
                "legenda": montar_legenda(post, cfg) + "\n\n🖼️ Capa: imagem ilustrativa gerada por IA.",
                "capa_ia": True}
        if pid in ids:
            ids[pid].update(item)
            print("redesenhado", pid, iso)
            continue
        fila.append(item)
        ids[pid] = item
        print("agendado", pid, iso)
    salvar_fila(fila)


if __name__ == "__main__":
    main()
