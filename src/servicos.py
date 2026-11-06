"""Apresentação de serviço no formato carrossel GNZ01 (substitui a peça vitrine/showcase no feed)."""
from pathlib import Path
from src import sistema as ss

LAMINAS = {
    "cardapio": ([{"titulo": "Cardápio com **fotos, opções e preços**", "texto": "Tudo organizado por categoria. O cliente vê o que tem **sem pedir foto do cardápio** no WhatsApp."},
                  {"titulo": "O pedido chega **pronto no WhatsApp**", "texto": "Itens, observações e total montados na conversa. **Você só confirma.**"},
                  {"titulo": "**Um link** para tudo", "texto": "Na bio do Instagram, no Google e no status. **O mesmo cardápio em todo lugar.**"},
                  {"titulo": "No celular **e no computador**", "texto": "Abre no navegador de qualquer aparelho, **sem instalar nada.**"}],
                 "pizzaria", "Quer o cardápio digital **do seu negócio?**"),
    "agenda": ([{"titulo": "O cliente escolhe **dia e serviço**", "texto": "Sem troca de mensagens para achar um horário. **Ele marca sozinho.**"},
                {"titulo": "Só aparecem **horários livres**", "texto": "O que já está ocupado nem aparece. **Nada de choque de agenda.**"},
                {"titulo": "**Link de agendamento** na bio", "texto": "Seu cliente agenda pelo Instagram, **a qualquer hora.**"},
                {"titulo": "No celular **e no computador**", "texto": "Você acompanha a agenda de onde estiver, **sem instalar nada.**"}],
               "barbearia", "Quer a agenda online **do seu negócio?**"),
    "catalogo": ([{"titulo": "Produtos organizados **por categoria**", "texto": "Seu cliente encontra o que procura **sem rolar o feed inteiro.**"},
                  {"titulo": "Pedido ou orçamento **pelo WhatsApp**", "texto": "O cliente escolhe e chama você **pronto para comprar.**"},
                  {"titulo": "**Um link** para enviar a qualquer cliente", "texto": "Na bio, no status e na conversa. **Sempre atualizado.**"},
                  {"titulo": "No celular **e no computador**", "texto": "Abre no navegador de qualquer aparelho, **sem instalar nada.**"}],
                 "loja", "Quer o catálogo digital **da sua loja?**"),
    "site": ([{"titulo": "Estrutura pensada **para ser encontrado**", "texto": "Seu negócio aparece para quem **pesquisa o seu serviço.**"},
              {"titulo": "Botão direto **para o WhatsApp**", "texto": "Quem gostou chama você **em um toque.**"},
              {"titulo": "Serviços, endereço **e horários**", "texto": "As respostas que o cliente procura, **antes de ele perguntar.**"},
              {"titulo": "Versão **mobile e desktop**", "texto": "Bonito e rápido em qualquer tela, **do jeito que o cliente acessa.**"}],
             "escritorio", "Quer um site profissional **para o seu negócio?**"),
}



def carrossel_servico(post, pasta, cfg):
    v = post["vitrine"]
    slides, cen, cta = LAMINAS[v["tipo"]]
    p = {"titulo": v.get("titulo") or post["titulo"], "subtitulo": v.get("subtitulo", ""), "tema": post.get("tema"),
         "hashtags": post.get("hashtags") or [], "slides": post.get("slides") or slides,
         "cta_final": post.get("cta_final") or cta, "cenario": post.get("cenario") or cen,
         "prompt_capa": post.get("prompt_capa")}
    return ss.carrossel(p, pasta, cfg, permitir_ia=True)  # único lugar onde capa com IA é permitida
