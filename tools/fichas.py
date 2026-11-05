"""Gera uma ficha .md por publicação em GNZ01-MARKETING/ (legenda, roteiro, CTA, instruções visuais).
Uso: python tools/fichas.py conteudo/gnz01-semana-01.json"""
import json, shutil, sys
from datetime import date, datetime, timedelta
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.comum import RAIZ, carregar_config, carregar_fila, montar_legenda

PILAR = {"educacao": "Educação", "demonstracao": "Demonstração", "autoridade": "Autoridade",
         "conexao": "Conexão", "vendas": "Vendas"}
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
cfg = carregar_config()
semana = json.loads((RAIZ / sys.argv[1]).read_text(encoding="utf-8"))
fila = {p["id"]: p for p in carregar_fila()}
pref = semana.get("prefixo", "")
M = RAIZ / "GNZ01-MARKETING"
for pasta in ("POSTS", "CARROSSEIS", "STORIES", "LEGENDAS", "CRIATIVOS"):
    (M / pasta).mkdir(parents=True, exist_ok=True)
indice = ["# Semana " + semana["semana"] + " · fichas de publicação\n",
          "Status: **aguardando aprovação** (nada desta semana foi publicado ainda).\n",
          "| Data | Hora | Formato | Pilar | Título | Ficha |", "|---|---|---|---|---|---|"]


def quando(pid):
    q = datetime.fromisoformat(fila[pid]["quando"])
    return q, f"{q:%d/%m} ({DIAS[q.weekday()]})", f"{q:%H:%M}"


for d, dia in enumerate(semana["dias"]):
    for n, p in enumerate(dia["posts"]):
        data = date.fromisoformat(semana["inicio"]) + timedelta(days=d)
        pid = f"{pref}_{data}_{n + 1}"
        q, dtxt, hora = quando(pid)
        nome = f"{data}_{hora.replace(':', 'h')}_{p['tipo']}_{p['tema']}"
        imgs = fila[pid]["imagens"]
        destino_cri = M / "CRIATIVOS" / nome
        destino_cri.mkdir(exist_ok=True)
        for i in imgs:
            shutil.copy(RAIZ / i, destino_cri / (i.split("/")[-1]))
        legenda = montar_legenda(p, cfg)
        (M / "LEGENDAS" / f"{nome}.txt").write_text(legenda, encoding="utf-8")
        L = [f"# {p['titulo']}", "",
             f"- **Data e hora:** {dtxt}, {hora}",
             f"- **Formato:** {'Carrossel (' + str(len(imgs)) + ' slides)' if p['tipo'] == 'carrossel' else 'Post único 1080x1350'}",
             f"- **Serviço:** {cfg['temas'][p['tema']]['rotulo'].capitalize()}",
             f"- **Pilar:** {PILAR.get(p.get('pilar'), p.get('pilar', ''))}",
             f"- **Nicho:** {p.get('nicho', '')}",
             f"- **Público-alvo:** {p.get('publico_alvo', '')}",
             f"- **Objetivo:** {p.get('objetivo', '')}",
             f"- **Técnica de copy:** {p.get('tecnica', '')}",
             f"- **Palavras-chave (SEO):** {', '.join(p.get('palavras_chave', []))}",
             f"- **CTA:** {p.get('cta', '')}",
             f"- **Status:** aguardando aprovação", "",
             "## Texto da arte", ""]
        if p["tipo"] == "carrossel":
            L.append(f"1. **Capa:** {p['titulo']}" + (f" / {p['subtitulo']}" if p.get("subtitulo") else ""))
            for i, s in enumerate(p["slides"], 1):
                L.append(f"{i + 1}. **{s['titulo']}**: {s['texto']}")
            L.append(f"{len(p['slides']) + 2}. **Final:** {p.get('cta_final', '')} + botão WhatsApp")
        elif p.get("vitrine"):
            v = p["vitrine"]
            L += [f"Demonstração de {v['tipo']} em celular: **{v['titulo']}** / {v['subtitulo']}",
                  f"Nome fictício: {v['nome']} (marcado como imagem ilustrativa)"]
        else:
            L.append(f"**{p.get('numero', '') + ' ' if p.get('numero') else ''}{p['titulo']}**")
            if p.get("subtitulo"):
                L.append(p["subtitulo"])
            L += [f"- {i}" for i in p.get("itens", [])]
        L += ["", "## Direção de arte", "", p.get("direcao_visual", ""),
              f"Layout: {'vitrine (mockup de celular)' if p.get('vitrine') else p.get('layout', 'padrão')}, fundo {'claro (off-white)' if p.get('claro') else 'escuro (preto/grafite)'}.",
              "", "## Legenda completa", "", "```", legenda, "```", "",
              "## Criativos", ""] + [f"![]({'../CRIATIVOS/' + nome + '/' + i.split('/')[-1]})" for i in imgs]
        pasta = "CARROSSEIS" if p["tipo"] == "carrossel" else "POSTS"
        (M / pasta / f"{nome}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        indice.append(f"| {dtxt} | {hora} | {p['tipo']} | {PILAR.get(p.get('pilar'), '')} | {p['titulo']} | [{pasta}/{nome}.md]({pasta}/{nome}.md) |")

    # stories do dia
    data = date.fromisoformat(semana["inicio"]) + timedelta(days=d)
    S = [f"# Stories de {data:%d/%m} ({DIAS[data.weekday()]})", "",
         "Funil do dia: conexão de manhã, dúvidas frequentes ao longo do dia, pergunta para o Direct, demonstração à noite e chamada para orçamento antes de dormir.", ""]
    cri = M / "CRIATIVOS" / f"{data}_stories"
    cri.mkdir(exist_ok=True)
    for s, st in enumerate(dia.get("stories", []), 1):
        pid = f"{pref}_{data}_story{s}"
        q, dtxt, hora = quando(pid)
        img = fila[pid]["imagens"][0]
        shutil.copy(RAIZ / img, cri / f"{s}_{hora.replace(':', 'h')}.jpg")
        tipo = {"faq": "Pergunta frequente", "cardapio": "Demonstração: cardápio digital",
                "agenda": "Demonstração: agenda online", "catalogo": "Demonstração: catálogo digital"}.get(st["tipo"], "Texto")
        S += [f"## {hora} · {tipo}", "", f"**{fila[pid]['titulo']}**"]
        if st.get("texto"):
            S.append(st["texto"])
        if st.get("subtitulo"):
            S.append(st["subtitulo"])
        S += [f"CTA: {st.get('cta', 'WhatsApp').replace('{whatsapp}', cfg['whatsapp']) if st['tipo'] not in ('faq',) and st.get('cta') else ('Quer um assim? WhatsApp' if st['tipo'] in ('cardapio','agenda','catalogo') else 'Dúvidas? WhatsApp')}",
              "Dica ao publicar manualmente: adicione a figurinha de enquete ou caixa de perguntas por cima (a API não permite figurinhas)." if s in (4,) else "",
              f"![](../CRIATIVOS/{data}_stories/{s}_{hora.replace(':', 'h')}.jpg)", ""]
    (M / "STORIES" / f"{data}_stories.md").write_text("\n".join(S) + "\n", encoding="utf-8")
    indice.append(f"| {data:%d/%m} ({DIAS[data.weekday()]}) | 07:30 a 22:00 | 7 stories | Funil | Stories do dia | [STORIES/{data}_stories.md](STORIES/{data}_stories.md) |")

(M / "INDICE-SEMANA-01.md").write_text("\n".join(indice) + "\n", encoding="utf-8")
print("ok")
