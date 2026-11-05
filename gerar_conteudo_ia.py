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
    tema: Literal["sites", "cardapio", "agenda"]
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
    prompt = f"""Você é o social media de "{cfg['marca']}" ({cfg['instagram']}), que vende três serviços
para pequenos negócios e profissionais autônomos no Brasil:
1. Criação de sites (tema "sites")
2. Cardápio digital para restaurantes, lanchonetes e delivery (tema "cardapio")
3. Agenda online para profissionais que atendem com hora marcada: barbeiros, salões, clínicas,
   psicólogos, personal trainers etc. (tema "agenda")

Crie o conteúdo de UMA SEMANA para o Instagram: 7 dias, 5 posts por dia.
- Em cada dia, o post de índice 1 é um carrossel (5 ou 6 slides) e os outros 4 são posts de imagem única.
- O objetivo principal é VENDER SITES: cerca de metade dos posts deve ser do tema "sites"
  (inclusive pelo menos 3 dos 7 carrosséis). Os outros temas aparecem todo dia, mas nunca os 5 posts do mesmo tema.
- Cada post deve atrair o dono de negócio que pode virar cliente: fale da dor dele e mostre o resultado.
- Varie os formatos: dor do cliente, dica prática, mito x verdade, checklist, conta de quanto ele perde,
  nicho específico (ex.: barbearia, pizzaria, dentista), bastidores e oferta direta.
- Linguagem simples, direta, em português do Brasil, falando com o dono do negócio.
- Toda legenda termina com uma chamada para ação usando o marcador {{whatsapp}} (ele será trocado
  pelo número real). Pode usar também {{link}}.
- Hashtags: use as que o CLIENTE em potencial segue ou pesquisa (nicho do negócio + serviço),
  por exemplo #barbearia, #donoderestaurante, #sitesparaempresas. Evite hashtags genéricas demais.
- Não invente números de pesquisas ou estatísticas; use exemplos e contas simples.
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
