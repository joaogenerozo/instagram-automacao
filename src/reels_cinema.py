"""Motor cinematográfico dos Reels: segue o prompt "GNZ01_ — Cinematic Brand Introduction".

Cada Reel usa as 8 cenas do filme de marca (tools/filme_marca/filme.html), em 9:16 e com 30 s.
Os textos de cada cena vêm do roteiro e ficam todos em português:

  1. revelação: gancho do roteiro sobre o navegador desfocado, anel dourado e clique
  2. símbolo 3D GNZ01_ com órbitas
  3. área de trabalho: o prompt de vidro digita a ideia central
  4. site rolando: título, explicação e três benefícios
  5. card com a mensagem de fechamento
  6. dois cards empilhados (itens da lista ou benefícios)
  7. símbolo metálico com reflexo
  8. assinatura GNZ01_ / DESIGN. DESENVOLVIMENTO. DIGITAL. com a chamada para ação

Áudio: eletrônica a 124 BPM com efeitos sincronizados, sem narração, normalizada em -14 LUFS.
Nada aqui inventa dados: os textos saem do roteiro ou são frases institucionais da GNZ01_.
"""
import json
import subprocess
import zlib
from html import escape
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "tools" / "filme_marca"
MAPA = PASTA / "mapa_reel.json"

# trechos de cada cena no vídeo final (segundos), conforme mapa_reel.json
CENAS = [("revelacao", 0.0, 4.75), ("prompt", 4.75, 10.2), ("site", 10.2, 15.0),
         ("card", 15.0, 19.6), ("cards", 19.6, 24.2), ("metal", 24.2, 26.0), ("assinatura", 26.0, 30.0)]

ROTULOS = {"sites": "SITES PROFISSIONAIS", "sistemas": "SISTEMAS DIGITAIS", "instagram": "PRESENÇA DIGITAL",
           "trafego": "ANÚNCIOS E CLIENTES", "automacao": "AUTOMAÇÃO"}

# frases institucionais usadas quando o roteiro não traz texto suficiente
PADRAO_TILES = [("Sites", "Design e desempenho"), ("Sistemas", "Automação e organização"),
                ("Marca", "Identidade digital consistente")]


# ------------------------------------------------------------------ variação: cada Reel com visual próprio
MAPAS = [PASTA / "mapa_reel.json", PASTA / "mapa_reel_b.json", PASTA / "mapa_reel_c.json"]
LUZES = ["radial-gradient(circle at 50% 18%, rgba(197,164,109,.16), transparent 45%)",
         "radial-gradient(circle at 15% 70%, rgba(197,164,109,.14), transparent 40%), radial-gradient(circle at 90% 10%, rgba(244,242,237,.06), transparent 40%)",
         "radial-gradient(circle at 85% 80%, rgba(197,164,109,.15), transparent 42%)",
         "linear-gradient(160deg, rgba(197,164,109,.10), transparent 35%, transparent 70%, rgba(197,164,109,.08))"]


def _e(t):
    return escape(str(t or ""))


def _nav(nome, links):
    return (f'<div class="nav" style="padding:14px 22px; font-size:12px"><b style="font-size:14px">{_e(nome)}</b>'
            f'<div>{"".join(f"<span>{_e(x)}</span>" for x in links)}</div></div>')


def mock(tema, roteiro, chips):
    """Tela de exemplo dentro do card (cena 5), diferente por tipo de negócio. Sem preços nem dados inventados."""
    c = (chips + ["", "", "", ""])[:4]
    if tema == "agenda":
        dias = ["SEG", "TER", "QUA", "QUI", "SEX"]
        horas = ["09:00", "10:30", "14:00", "16:30"]
        cel = []
        for i, h in enumerate(horas):
            linha = "".join(
                f'<div style="flex:1; height:44px; border-radius:10px; font-size:11px; display:flex; align-items:center; justify-content:center;'
                f'{"background:linear-gradient(180deg,#D8BC88,#A88A57); color:#08090B; font-weight:700" if (i + j) % 3 == 0 else "background:#202227; color:rgba(244,242,237,.5)"}">'
                f'{"Confirmado" if (i + j) % 3 == 0 else h}</div>' for j in range(5))
            cel.append(f'<div style="display:flex; gap:8px; margin-top:8px">{linha}</div>')
        cab = "".join(f'<div style="flex:1; text-align:center; font-size:11px; letter-spacing:.2em" class="gold">{d}</div>' for d in dias)
        return (_nav("Agenda online", ["Horários", "Serviços", "Contato"]) +
                f'<div style="padding:10px 22px"><div style="display:flex; gap:8px">{cab}</div>{"".join(cel)}'
                f'<div style="margin-top:16px; display:flex; gap:12px; align-items:center"><div class="btn" style="height:34px; font-size:12px">Marcar horário</div>'
                f'<div class="muted" style="font-size:12px">Lembrete automático antes do horário</div></div></div>')
    if tema == "cardapio":
        itens = "".join(
            f'<div style="display:flex; align-items:center; gap:14px; padding:10px 0; border-bottom:1px solid rgba(244,242,237,.07)">'
            f'<div class="photo {"ph-arch" if k % 2 else "ph-desk"}" style="width:62px; height:46px"></div>'
            f'<div style="flex:1"><div style="font-size:14px; font-weight:700">{_e(n)}</div><div class="muted" style="font-size:11px">Foto, descrição e opções</div></div>'
            f'<div class="btn ghost" style="height:30px; font-size:11px">Adicionar</div></div>'
            for k, n in enumerate(["Pizzas", "Lanches", "Porções", "Bebidas"]))
        return (_nav("Cardápio digital", ["Cardápio", "Entrega", "Pedido"]) +
                f'<div style="padding:4px 22px">{itens}<div class="btn" style="height:34px; font-size:12px; margin-top:12px">Pedir pelo WhatsApp</div></div>')
    if tema == "catalogo":
        grade = "".join(
            f'<div style="border-radius:12px; background:#15171b; border:1px solid rgba(244,242,237,.07); padding:8px">'
            f'<div class="photo {["ph-arch", "ph-desk", "ph-sys"][k % 3]}" style="height:82px"></div>'
            f'<div style="font-size:11px; margin-top:8px; font-weight:600">Produto {k + 1:02d}</div><div class="gold" style="font-size:10px; margin-top:2px">Ver detalhes</div></div>'
            for k in range(6))
        return (_nav("Catálogo", ["Novidades", "Categorias", "Contato"]) +
                f'<div style="padding:6px 22px; display:grid; grid-template-columns:repeat(3,1fr); gap:10px">{grade}</div>')
    if tema == "landing":
        checks = "".join(f'<div style="font-size:13px; margin-top:8px"><span class="gold">✓</span>&nbsp; {_e(x)}</div>' for x in c[:3] if x)
        return (_nav("Oferta", ["Como funciona", "Dúvidas"]) +
                f'<div style="padding:18px 30px"><div style="font-size:10px; letter-spacing:.3em" class="gold">UMA PÁGINA, UM OBJETIVO</div>'
                f'<div style="font-size:28px; font-weight:800; line-height:1.1; margin-top:10px">{_e(roteiro["titulo"])}</div>{checks}'
                f'<div class="btn" style="height:38px; font-size:13px; margin-top:18px">Quero saber mais</div></div>')
    if tema == "paginas":
        serv = "".join(f'<div style="padding:8px 12px; border-radius:10px; background:#202227; font-size:12px; margin-top:8px">{_e(x)}</div>'
                       for x in (c[:3] if any(c) else ["Serviços", "Experiência", "Contato"]) if x)
        return (_nav("Página profissional", ["Sobre", "Serviços", "Contato"]) +
                f'<div style="padding:14px 22px; display:flex; gap:20px"><div style="width:120px; height:120px; border-radius:50%;'
                f' background:linear-gradient(145deg,#4a4c52,#202227); border:2px solid rgba(197,164,109,.6)"></div>'
                f'<div style="flex:1"><div style="font-size:22px; font-weight:800">Seu nome</div><div class="muted" style="font-size:12px">Sua profissão · sua cidade</div>{serv}'
                f'<div class="btn" style="height:32px; font-size:12px; margin-top:12px">Agendar conversa</div></div></div>')
    return None  # sites/marca: mantém a tela padrão do filme


URLS = {"agenda": "agenda.seunegocio.com.br", "cardapio": "cardapio.seunegocio.com.br", "catalogo": "loja.seunegocio.com.br",
        "landing": "oferta.seunegocio.com.br", "paginas": "seunome.com.br"}


def _curto(txt, lim):
    txt = " ".join(str(txt or "").split())
    if len(txt) <= lim:
        return txt
    corte = txt[:lim].rsplit(" ", 1)[0].rstrip(",;:")
    return corte + "…"


def _frase(c):
    return c.get("texto") or c.get("titulo") or (c.get("demo") or {}).get("chamada") or ""


def textos(roteiro, cfg):
    cenas = roteiro["cenas"]
    tema = roteiro.get("tema", "sites")
    gancho = next((c for c in cenas if c["tipo"] == "gancho"), cenas[0])
    cta = next((c for c in cenas if c["tipo"] == "cta"), None)
    meio = [c for c in cenas if c is not gancho and c is not cta and c["tipo"] != "marca"]

    hook = _frase(gancho) or roteiro["titulo"]
    if hook.isupper():
        hook = hook.capitalize()
    rotulo = (gancho.get("rotulo") or ROTULOS.get(tema, "GNZ01_ ESTÚDIO DIGITAL")).upper()

    # cena 3: o prompt digita a ideia seguinte ao gancho
    seg = meio[0] if meio else gancho
    digitado = " ".join(x for x in (_frase(seg), seg.get("apoio", "")) if x) or roteiro["titulo"]

    # cena 4: a cena de demonstração (celular, dispositivos, busca) ou a segunda ideia
    demo = next((c for c in meio if c["tipo"] in ("celular", "dispositivos", "imagem", "busca")), None)
    base4 = demo or (meio[1] if len(meio) > 1 else seg)
    titulo4 = (base4.get("demo") or {}).get("chamada") or base4.get("titulo") or base4.get("texto") or roteiro["titulo"]
    corpo4 = base4.get("fala") or (base4.get("demo") or {}).get("apoio") or roteiro.get("objetivo", "")
    chips = list(base4.get("chips") or [])
    for c in meio:
        chips += [i for i in c.get("chips", []) + c.get("itens", []) if i not in chips]
    tiles = [(_curto(x, 30), "") for x in chips[:3]]
    tiles += PADRAO_TILES[len(tiles):3]

    # cena 5: frase de fechamento (última ideia antes do CTA)
    fecho = meio[-1] if meio else seg
    card = (_curto(_frase(fecho), 60), _curto(fecho.get("apoio", ""), 70))

    # cena 6: dois itens de lista (ou benefícios)
    lista = next((c for c in meio if c["tipo"] == "lista"), None)
    itens = list(lista["itens"]) if lista else []
    comp = next((c for c in meio if c["tipo"] == "comparacao"), None)
    if comp and len(itens) < 2:
        itens += comp["com"]["itens"]
    itens += [i for i in chips[3:] + chips if i not in itens]
    itens = [i.rstrip(".") for i in itens][:2]
    padrao6 = [("Sites", "Presença digital. Design. Desempenho."), ("Sistemas", "Automação. Organização. Eficiência.")]
    cards = [(_curto(i, 30), "") for i in itens] + padrao6[len(itens):2]

    semente = roteiro.get("variante", zlib.crc32(roteiro["id"].encode()))
    palavra = cfg.get("cta", {}).get("palavras", {}).get(tema, "SITE")
    return {
        "gancho": _curto(hook, 70), "rotulo": _curto(rotulo, 40),
        "digitado": _curto(digitado, 110),
        "secao": ROTULOS.get(tema, "SOLUÇÕES DIGITAIS"), "titulo": _curto(titulo4, 80),
        "corpo": _curto(corpo4, 190), "frase": "GNZ01_ · sites que trabalham pelo seu negócio",
        "tiles": tiles, "card": card, "cards": cards,
        "cta": _curto(_frase(cta) if cta else "Quer um site no nível da sua marca?", 70),
        "botao": f"Comente {palavra}",
        "mock": mock(tema, roteiro, chips), "url": URLS.get(tema, "suaempresa.com.br"),
        "url4": URLS.get(tema, "suaempresa.com.br"),
        "variante": {"cam": semente % 3, "luz": LUZES[(semente // 3) % len(LUZES)],
                     "titulo5": ["left", "center"][(semente // 2) % 2]},
        "_mapa": semente % len(MAPAS),
    }


def produzir(roteiro, cfg, saida, pasta_entrega=None, voz=None):
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    dados = textos(roteiro, cfg)
    mapa = MAPAS[dados["_mapa"]]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "textos.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        subprocess.run(["python3", str(PASTA / "trilha.py"), str(tmp / "trilha.wav"), "30", str(mapa)], check=True)
        subprocess.run(["node", str(PASTA / "render.js"), str(saida), "--w", "1080", "--h", "1920", "--fps", "30",
                        "--audio", str(tmp / "trilha.wav"), "--dados", str(tmp / "textos.json"), "--mapa", str(mapa)],
                       check=True)
    capa = saida.with_suffix(".jpg")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "2.6", "-i", str(saida), "-frames:v", "1", "-q:v", "2",
                    str(capa)], check=True)
    nomes = {"revelacao": dados["gancho"], "prompt": dados["digitado"], "site": dados["titulo"],
             "card": dados["card"][0], "cards": " · ".join(c[0] for c in dados["cards"]),
             "assinatura": f"GNZ01_ · {dados['cta']} · {dados['botao']}"}
    return {"id": roteiro["id"], "narracao": None, "srt": None, "duracao": 30.0, "video": str(saida),
            "capa": str(capa), "legendas": 0, "motor": "cinematografico",
            "trilha": "eletrônica premium 124 BPM, original, gerada por código (-14 LUFS)",
            "eventos_sfx": [(round(a, 1), n) for n, a, _ in CENAS],
            "variante": dados["variante"] | {"mapa": mapa.name},
            "cenas": [{"tipo": "abertura", "inicio": 0.0, "duracao": 5.0, "fala": "", "texto": nomes["revelacao"]},
                      {"tipo": "conteudo", "inicio": 5.0, "duracao": 21.0, "fala": "",
                       "texto": " · ".join(nomes[k] for k in ("prompt", "site", "card", "cards"))},
                      {"tipo": "assinatura", "inicio": 26.0, "duracao": 4.0, "fala": "", "texto": nomes["assinatura"]}]}
