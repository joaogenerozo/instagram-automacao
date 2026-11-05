"""Cria o conteúdo de uma nova semana (7 dias x 5 posts) usando o Claude.

Precisa da variável de ambiente ANTHROPIC_API_KEY.
Uso:  python gerar_conteudo_ia.py            -> cria conteudo/semana-NN.json (próximo número)
"""
import json
import re
import sys
from typing import List, Literal, Optional

import anthropic
from pydantic import BaseModel, Field

from src.comum import RAIZ, carregar_config

MODELO = "claude-opus-5-5"
PASTA = RAIZ / "conteudo"


class Slide(BaseModel):
    titulo: str = Field(description="Título curto do slide, até 6 palavras")
    texto: str = Field(description="Explicação de 1 a 2 frases, até 160 caracteres")


class Post(BaseModel):
    tipo: Literal["post", "carrossel"]
    tema: Literal["sites", "cardapio", "agenda", "paginas", "catalogo", "landing", "solucoes", "marca"]
    pilar: Literal["educacao", "demonstracao", "autoridade", "conexao", "vendas"]
    objetivo: str = Field(description="Objetivo estratégico da publicação, 1 frase")
    publico_alvo: str = Field(description="Quem é o público dessa publicação")
    tecnica: str = Field(description="Técnica de copy usada: AIDA, PAS, storytelling, quebra de objeção etc.")
    palavras_chave: List[str] = Field(description="3 a 5 palavras-chave para SEO do Instagram")
    direcao_visual: str = Field(description="Direção visual em 1 ou 2 frases, dentro da identidade preto/grafite/off-white")
    titulo: str = Field(description="Frase de impacto para a imagem, até 70 caracteres")
    subtitulo: str = Field(description="Complemento da imagem, até 110 caracteres")
    itens: List[str] = Field(default_factory=list, description="Só em post: 3 benefícios curtos (até 40 caracteres cada)")
    slides: List[Slide] = Field(default_factory=list, description="Só em carrossel: 5 ou 6 slides")
    cta_final: Optional[str] = Field(default=None, description="Só em carrossel: chamada do último slide")
    legenda: str = Field(description="Legenda com emojis, quebras de linha e chamada final com {whatsapp}")
    hashtags: List[str] = Field(description="4 a 6 hashtags em português, começando com #")


class Dia(BaseModel):
    posts: List[Post] = Field(description="Exatamente 5 posts; o segundo (índice 1) é o carrossel")


class Semana(BaseModel):
    dias: List[Dia] = Field(description="Exatamente 7 dias")


def semanas_existentes():
    return sorted(PASTA.glob("semana-*.json"))


def titulos_usados():
    titulos = []
    for arq in semanas_existentes():
        for dia in json.loads(arq.read_text(encoding="utf-8"))["dias"]:
            titulos += [p["titulo"] for p in dia["posts"]]
    return titulos


def main():
    cfg = carregar_config()
    usados = titulos_usados()
    diretrizes = (PASTA / "diretrizes-gnz01.md").read_text(encoding="utf-8")
    prompt = f"""Siga estas diretrizes da marca à risca:

{diretrizes}

TAREFA: crie o conteúdo de UMA SEMANA para o Instagram {cfg['instagram']}: 7 dias, 5 publicações por dia.
- Em cada dia, a publicação de índice 1 é um carrossel (5 ou 6 slides); as outras 4 são posts de imagem única.
- Respeite a distribuição de pilares na semana (35 publicações): ~10 educação, ~9 demonstração,
  ~7 autoridade, ~5 conexão e ~4 vendas.
- Cerca de metade das publicações deve levar à venda de SITES (temas sites, paginas ou landing).
  Os demais serviços (cardapio, agenda, catalogo, solucoes) aparecem ao longo da semana.
- Linguagem do Brasil, profissional e objetiva, falando com o dono do negócio ou o profissional liberal.
- Toda legenda termina com uma chamada para ação usando o marcador {{whatsapp}} (ou convite para o Direct).
- Hashtags que o cliente em potencial segue ou pesquisa (nicho + serviço), nada genérico demais.
- Não invente números de pesquisas, clientes ou depoimentos. Demonstrações devem ser apresentadas
  como exemplos ("veja como fica"), nunca como cliente real.
- Não repita estes títulos já usados: {json.dumps(usados[-140:], ensure_ascii=False)}
"""
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=MODELO,
        max_tokens=64000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": prompt}],
        output_format=Semana,
    ) as stream:
        resposta = stream.get_final_message()

    if resposta.stop_reason == "refusal":
        sys.exit("O modelo recusou o pedido. Tente rodar de novo.")
    if resposta.stop_reason == "max_tokens":
        sys.exit("Resposta cortada por limite de tamanho. Tente rodar de novo.")
    semana = resposta.parsed_output

    numero = 1 + max([int(re.findall(r"\d+", a.stem)[0]) for a in semanas_existentes()] or [0])
    dados = {"semana": numero, **semana.model_dump(exclude_none=True)}
    destino = PASTA / f"semana-{numero:02d}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(destino.relative_to(RAIZ))


if __name__ == "__main__":
    main()
