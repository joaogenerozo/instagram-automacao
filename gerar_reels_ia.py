"""Escreve uma semana nova de roteiros de Reels (21 vídeos: 3 por dia) com o Claude.

Segue conteudo/reels/diretrizes-video.md (prompt do estúdio de vídeo) + conteudo/diretrizes-gnz01.md (marca).
Precisa de ANTHROPIC_API_KEY. Sem a chave, sai sem erro e avisa.

Uso:
  python gerar_reels_ia.py                 escreve conteudo/reels/roteiros-semana-NN.json
  python gerar_reels_ia.py --se-faltar 9   só escreve se restarem menos de 9 roteiros não usados
"""
import argparse
import json
import os
import re
import sys
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from src.comum import RAIZ, carregar_config, carregar_fila

MODELO = "claude-opus-5-5"
PASTA = RAIZ / "conteudo" / "reels"


class Lado(BaseModel):
    titulo: str = Field(description="Até 24 caracteres")
    itens: List[str] = Field(description="3 itens de até 28 caracteres")


class Cena(BaseModel):
    tipo: Literal["gancho", "texto", "lista", "celular", "comparacao", "cta"]
    fala: str = Field(description="Narração da cena, natural e falada, 4 a 22 palavras")
    texto: Optional[str] = Field(default=None, description="gancho/texto/cta: frase na tela, até 55 caracteres")
    rotulo: Optional[str] = Field(default=None, description="gancho: público em caixa baixa, até 32 caracteres (ex.: Para barbearias)")
    apoio: Optional[str] = Field(default=None, description="texto/gancho: complemento curto, até 60 caracteres")
    titulo: Optional[str] = Field(default=None, description="lista/celular/comparacao: título, até 40 caracteres")
    destaque: List[str] = Field(default_factory=list, description="1 palavra do texto ou título (copiada igual, com pontuação)")
    itens: List[str] = Field(default_factory=list, description="lista: 3 a 5 itens de até 30 caracteres")
    check: Optional[bool] = Field(default=None, description="lista: true para usar ✓ em vez de números")
    tela: Optional[Literal["site", "cardapio", "agenda", "catalogo"]] = Field(default=None, description="celular")
    chips: List[str] = Field(default_factory=list, description="celular: 2 ou 3 destaques de até 26 caracteres")
    sem: Optional[Lado] = Field(default=None, description="comparacao: situação atual")
    com: Optional[Lado] = Field(default=None, description="comparacao: com a solução")


class Roteiro(BaseModel):
    id: str = Field(description="kebab-case curto e único")
    titulo: str
    tema: Literal["sites", "cardapio", "agenda", "paginas", "catalogo", "landing", "solucoes", "marca"]
    objetivo: str
    publico: str
    direcao: str = Field(description="Direção criativa específica deste vídeo, 1 frase")
    cenas: List[Cena] = Field(description="4 a 6 cenas: começa com gancho e termina com cta")
    gancho_legenda: str = Field(description="Primeira linha da legenda, começa pelo problema do cliente")
    legenda: str = Field(description="Corpo da legenda, sem número de WhatsApp e sem chamada final")
    hashtags: List[str] = Field(description="2 ou 3 hashtags de nicho")


class Semana(BaseModel):
    roteiros: List[Roteiro] = Field(description="Exatamente 21 roteiros, na ordem de publicação (07h, 11h, 19h de cada dia)")


def existentes():
    return sorted(PASTA.glob("roteiros-*.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--se-faltar", type=int)
    args = ap.parse_args()
    todos = [r for a in existentes() for r in json.loads(a.read_text(encoding="utf-8"))["roteiros"]]
    usados = {p.get("roteiro") for p in carregar_fila() if p["tipo"] == "reel"}
    restantes = [r for r in todos if r["id"] not in usados]
    if args.se_faltar is not None and len(restantes) >= args.se_faltar:
        print(f"Ainda há {len(restantes)} roteiros. Nada a fazer.")
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Sem ANTHROPIC_API_KEY: não dá para escrever roteiros novos automaticamente.")
        return
    import anthropic
    cfg = carregar_config()
    video = (PASTA / "diretrizes-video.md").read_text(encoding="utf-8")
    marca = (RAIZ / "conteudo" / "diretrizes-gnz01.md").read_text(encoding="utf-8")
    exemplos = json.dumps(todos[:2], ensure_ascii=False)
    prompt = f"""Você é o estúdio de vídeo da GNZ01. Siga à risca as duas diretrizes abaixo.

=== DIRETRIZ DO ESTÚDIO DE VÍDEO ===
{video}

=== DIRETRIZ DA MARCA ===
{marca}

TAREFA: escreva 21 roteiros de Reels (3 por dia, 7 dias) para {cfg['instagram']}, que serão produzidos
automaticamente por um motor de motion design (texto cinético, demonstrações em celular, listas, comparações),
com narração por IA e legendas sincronizadas. Duração alvo: 20 a 35 segundos (60 a 85 palavras de fala no total).

Regras:
- Gancho (1ª cena) começa pelo problema ou pela cena real do cliente num nicho concreto (pizzaria, barbearia,
  clínica, manicure, loja, profissional liberal). Nunca abra com a marca.
- Cerca de metade sobre sites (sites, paginas, landing); o resto distribuído entre cardapio, agenda, catalogo,
  solucoes e 1 ou 2 de marca.
- Foco local: público de {cfg['local']['regiao']}. Cite {cfg['local']['cidade']} de forma natural em 2 ou 3 roteiros.
  Nunca invente negócios reais da cidade.
- CTA final: "Comente PALAVRA" onde PALAVRA é SITE, CARDÁPIO, AGENDA, CATÁLOGO ou PÁGINA conforme o tema.
- Não invente números, pesquisas, preços, prazos, clientes ou depoimentos. Demonstrações são exemplos.
- A fala é falada: frases curtas, ritmo natural, sem siglas difíceis. O texto na tela é mais curto que a fala.
- Varie os tipos de cena entre os vídeos; não repita a mesma sequência em todos.
- Não repita temas destes títulos já usados: {json.dumps([r['titulo'] for r in todos][-60:], ensure_ascii=False)}

Formato de referência (2 roteiros já aprovados): {exemplos}
"""
    client = anthropic.Anthropic()
    with client.messages.stream(model=MODELO, max_tokens=64000, thinking={"type": "adaptive"},
                                output_config={"effort": "medium"},
                                messages=[{"role": "user", "content": prompt}], output_format=Semana) as stream:
        resposta = stream.get_final_message()
    if resposta.stop_reason in ("refusal", "max_tokens"):
        sys.exit(f"Resposta incompleta ({resposta.stop_reason}). Tente de novo.")
    semana = resposta.parsed_output
    numero = 1 + max([int(re.findall(r"\d+", a.stem)[0]) for a in existentes()] or [0])
    ids = {r["id"] for r in todos}
    roteiros = []
    for r in semana.roteiros:
        d = r.model_dump(exclude_none=True)
        d["id"] = f"s{numero:02d}-{d['id']}" if d["id"] in ids or not d["id"].startswith(f"s{numero:02d}") else d["id"]
        d["cenas"] = [{k: v for k, v in c.items() if v not in ([], None)} for c in d["cenas"]]
        roteiros.append(d)
    destino = PASTA / f"roteiros-semana-{numero:02d}.json"
    destino.write_text(json.dumps({"semana": numero, "roteiros": roteiros}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(destino.relative_to(RAIZ))


if __name__ == "__main__":
    main()
