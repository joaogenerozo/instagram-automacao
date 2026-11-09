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

from src.comum import RAIZ, carregar_config, carregar_fila

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
    titulo: str = Field(description="Gancho da imagem, até 60 caracteres: começa pela dor ou pela cena do cliente "
                        "(nicho, situação concreta ou pergunta), nunca pela marca nem por frase genérica")
    gancho: str = Field(description="Primeira linha da legenda, até 90 caracteres: o problema do cliente em uma frase "
                        "que faça parar de rolar (pergunta direta ou cena do dia a dia do negócio)")
    subtitulo: str = Field(description="Complemento da imagem, até 110 caracteres")
    itens: List[str] = Field(default_factory=list, description="Só em post: 3 benefícios curtos (até 40 caracteres cada)")
    slides: List[Slide] = Field(default_factory=list, description="Só em carrossel: 5 ou 6 slides")
    cta_final: Optional[str] = Field(default=None, description="Só em carrossel: chamada do último slide")
    legenda: str = Field(description="Corpo da legenda (sem repetir o gancho), com quebras de linha, SEM número de "
                         "WhatsApp e SEM chamada final: a chamada padrão é acrescentada automaticamente")
    mecanismo: Literal["salvar", "compartilhar", "comentar"] = Field(
        description="A ação principal que o post provoca. Salvar: checklist/passo a passo útil. Compartilhar: "
                    "o seguidor manda para um dono de negócio que ele conhece. Comentar: escolha A/B, número ou opinião")
    quadro: Optional[Literal["raio-x", "isso-ou-aquilo", "salvavel", "compartilhavel", "antes-e-depois", "bastidores"]] = Field(
        default=None, description="Quadro fixo da semana, se o post for um deles (veja a seção 26 das diretrizes)")
    pergunta: str = Field(description="Pergunta curta e fácil de responder que fecha a legenda antes do CTA "
                          "(ex.: 'Qual dessas você mais recebe? Comenta o número.'). Nada de pergunta genérica")
    hashtags: List[str] = Field(description="2 a 3 hashtags de nicho que o DONO do negócio pesquisa "
                                "(ex.: #pizzaria, #barbearia, #clinicaodontologica), começando com #")


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
    titulos += [p["titulo"] for p in carregar_fila() if p.get("tipo") in ("post", "carrossel")]
    return list(dict.fromkeys(titulos))


def desempenho():
    """Resumo dos posts que mais e menos funcionaram (gerado por tools/relatorio.py)."""
    arq = PASTA / "desempenho.json"
    if not arq.exists():
        return "Ainda não há dados de desempenho."
    d = json.loads(arq.read_text(encoding="utf-8"))
    linhas = [f"Seguidores: {d.get('seguidores')}. Posts que MAIS funcionaram (repita o formato e o nicho):"]
    linhas += [f"  - {m['titulo']} ({m['tipo']}): alcance {m['alcance']}, salvos {m['salvos']}, "
               f"compartilhamentos {m['compartilhamentos']}" for m in d.get("melhores", [])]
    linhas.append("Posts que MENOS funcionaram (evite o formato):")
    linhas += [f"  - {m['titulo']} ({m['tipo']}): alcance {m['alcance']}" for m in d.get("piores", [])]
    return "\n".join(linhas)


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
- GANCHO: título e primeira linha da legenda começam pelo problema ou pela cena real do cliente, num nicho
  concreto (pizzaria, barbearia, clínica, manicure, loja). Ex.: "Sua pizzaria ainda manda foto do cardápio no
  WhatsApp?". Proibido abrir com a marca ou com frases vagas como "Sua empresa merece uma presença digital".
- FOCO LOCAL: o público são negócios de {cfg['local']['regiao']} ({cfg['local']['cidade']}-{cfg['local']['uf']}).
  Em cerca de 1 a cada 3 publicações, cite a cidade de forma natural (ex.: "quem procura barbearia em
  {cfg['local']['cidade']} no Google..."). Nunca invente negócios reais da cidade.
- NÃO escreva número de WhatsApp nem chamada final na legenda: o sistema acrescenta um CTA único
  ("Comente SITE que eu te mando um exemplo").
- Hashtags: só 2 ou 3 de nicho que o dono do negócio pesquisa. As hashtags da cidade entram automaticamente.
- Não crie posts de citação de personalidades (já existe 1 por semana à parte).
- ENGAJAMENTO (seção 26): cada publicação tem um mecanismo (salvar, compartilhar ou comentar) e uma pergunta
  final fácil de responder. Na semana, inclua os quadros fixos: 1 raio-x (comente o @ do seu negócio),
  2 isso-ou-aquilo (A ou B), 2 salvaveis (checklist prático), 2 compartilhaveis ("manda para o dono de ... que
  você conhece") e 1 antes-e-depois (situação ilustrativa). Distribua ~1/3 de cada mecanismo.
- Alterne nichos: no mesmo dia, nunca dois posts para o mesmo nicho; na semana, pelo menos 6 nichos diferentes.
- Desempenho real da conta até agora:
{desempenho()}
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
