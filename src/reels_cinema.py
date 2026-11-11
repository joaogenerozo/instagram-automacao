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
    itens += [i for i in chips[3:] if i not in itens]
    itens = [i.rstrip(".") for i in itens][:2]
    padrao6 = [("Sites", "Presença digital. Design. Desempenho."), ("Sistemas", "Automação. Organização. Eficiência.")]
    cards = [(_curto(i, 30), "") for i in itens] + padrao6[len(itens):2]

    palavra = cfg.get("cta", {}).get("palavras", {}).get(tema, "SITE")
    return {
        "gancho": _curto(hook, 70), "rotulo": _curto(rotulo, 40),
        "digitado": _curto(digitado, 110),
        "secao": ROTULOS.get(tema, "SOLUÇÕES DIGITAIS"), "titulo": _curto(titulo4, 80),
        "corpo": _curto(corpo4, 190), "frase": "GNZ01_ · sites que trabalham pelo seu negócio",
        "tiles": tiles, "card": card, "cards": cards,
        "cta": _curto(_frase(cta) if cta else "Quer um site no nível da sua marca?", 70),
        "botao": f"Comente {palavra}",
    }


def produzir(roteiro, cfg, saida, pasta_entrega=None, voz=None):
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    dados = textos(roteiro, cfg)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "textos.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        subprocess.run(["python3", str(PASTA / "trilha.py"), str(tmp / "trilha.wav"), "30", str(MAPA)], check=True)
        subprocess.run(["node", str(PASTA / "render.js"), str(saida), "--w", "1080", "--h", "1920", "--fps", "30",
                        "--audio", str(tmp / "trilha.wav"), "--dados", str(tmp / "textos.json"), "--mapa", str(MAPA)],
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
            "cenas": [{"tipo": n, "inicio": a, "duracao": round(b - a, 2), "fala": "", "texto": nomes.get(n, "")}
                      for n, a, b in CENAS]}
