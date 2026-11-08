# Automação do Instagram: 5 posts por dia

Todo dia, no automático:

| Horário (Brasília) | Formato |
|---|---|
| 08:00 | Post |
| 12:00 | **Carrossel** |
| 15:00 | Post |
| 18:30 | Post |
| 21:00 | Post |

E mais **3 Reels por dia (07:00, 11:00 e 19:00)** produzidos pelo estúdio de vídeo (veja abaixo), **7 stories por dia** com perguntas frequentes (07:30, 09:30, 11:00, 13:30, 16:30, 19:30 e 22:00), mais **1 Reels por dia às 19:00** quando houver vídeo de depoimento na pasta `videos/`.

Temas: **criação de sites** (foco principal), **cardápio digital** e **agenda online para profissionais**. Os posts de cardápio e agenda terminam oferecendo também a criação de site.

## Como funciona

1. **Toda sábado** o robô prepara a semana seguinte: cria 35 posts novos com IA (Claude), desenha as imagens e coloca tudo na fila (`fila.json`). Sem chave de IA, ele reaproveita as semanas já escritas em `conteudo/`.
2. **A cada 30 minutos** o robô olha a fila e publica os posts, stories e Reels daquele horário pela API oficial do Instagram.
3. Tudo roda de graça no **GitHub Actions**. Você não precisa deixar computador ligado.

A semana 1 já está escrita em `conteudo/semana-01.json` e as imagens de exemplo estão em `midia/`.

## Aprovação antes de publicar
Por decisão do dono da conta, cada semana nova entra na fila já como `pendente` e é publicada sem aprovação prévia. Para voltar a exigir aprovação, defina a variável `PEDIR_APROVACAO=1` no workflow semanal; aí as semanas entram como `aguardando_aprovacao` até o status ser trocado para `pendente`. Toda a semana fica organizada para revisão em `GNZ01-MARKETING/` (índice em `GNZ01-MARKETING/INDICE-SEMANA-01.md`). Para gerar as fichas de uma semana: `python tools/fichas.py conteudo/gnz01-semana-01.json`.

## Alcance e conversão (desde 08/11/2026)
- **Legenda com CTA único** ("Comente SITE que eu te mando um exemplo") + WhatsApp pelo link da bio + linha local. O número solto e o cross-sell repetido saíram. Responda os comentários com a palavra-chave pelo Direct no mesmo dia.
- **No máximo 5 hashtags**: 2 da cidade (`config.json > local.hashtags`) + 2 a 3 de nicho. Lista negra em `hashtags_bloqueadas`.
- **Localização nos posts**: preencha `config.json > local.location_id` com o ID da página de lugar da cidade no Facebook (procure "Andradas, Minas Gerais" no Facebook, abra a página do lugar e copie o número do endereço). Vazio = sai sem localização.
- **Collab**: em qualquer post/carrossel da fila, `"colaboradores": ["@conta"]` (até 3). Se o convite falhar, o post sai sem collab e você recebe aviso. Modelo de estudo de caso em `conteudo/casos-reais.md`.
- **Citações**: no máximo 1 post de personalidade por semana (`limite_citacoes_semana`).
- **Sem repetição**: título parecido com algo dos últimos 45 dias (`janela_repeticao_dias`) não entra na fila nem é publicado. Para aplicar as regras na fila atual: `python tools/limpar_fila.py`.
- **Um post de feed por horário**: se dois coincidirem, o segundo sai na rodada seguinte (30 min depois).
- **Avisos**: post pulado (com motivo gravado em `fila.json`), erro definitivo ou semana sem conteúdo novo abrem uma *issue* no GitHub, que chega por e-mail.
- **Relatório semanal**: todo sábado `tools/relatorio.py` grava `GNZ01-MARKETING/RELATORIOS/kpis-AAAA-MM-DD.md` e `conteudo/desempenho.json`, que a IA usa para repetir o que funcionou. O token precisa também da permissão `instagram_manage_insights`.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `config.json` | Nome da marca, @, WhatsApp, cores, horários |
| `conteudo/semana-XX.json` | Textos de cada semana (você pode editar à vontade) |
| `gerar.py` | Desenha as imagens e agenda uma semana |
| `gerar_conteudo_ia.py` | Escreve uma semana nova com o Claude |
| `semanal.py` | Faz os dois passos acima de uma vez (usado no sábado) |
| `publicar.py` | Publica o que estiver no horário |
| `conteudo/stories-faq.json` | 49 perguntas frequentes usadas nos stories (edite ou adicione) |
| `videos/` | Coloque aqui os vídeos de depoimento (veja `videos/ROTEIROS-DEPOIMENTOS.md`) |
| `fila.json` | Fila de posts com status: aguardando_aprovacao, pendente, publicado, pulado ou erro |
| `GNZ01-MARKETING/` | Calendário, fichas por publicação, legendas, criativos, Reels e relatórios |
| `conteudo/diretrizes-gnz01.md` | Prompt Master da marca, usado pela IA ao escrever conteúdo |

## Instalação (uma vez só)

### 1. Conta do Instagram
- A conta precisa ser **Profissional** (Comercial ou Criador de conteúdo).
- Ligue a conta a uma **Página do Facebook** (Instagram > Configurações > Central de Contas).

### 2. Token da API (Meta for Developers)
1. Acesse developers.facebook.com, crie um app do tipo **Empresa**.
2. Adicione o produto **Instagram** (API com login do Facebook).
3. No **Gerenciador de Negócios** (business.facebook.com > Configurações > Usuários do sistema), crie um **usuário do sistema** administrador, dê acesso à sua Página e ao app e gere um token com as permissões:
   `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_show_list`, `pages_read_engagement`, `business_management`.
   Token de usuário do sistema **não expira**, por isso é o recomendado.
4. Descubra o **ID da conta do Instagram**: abra no navegador
   `https://graph.facebook.com/v21.0/me/accounts?fields=instagram_business_account&access_token=SEU_TOKEN`
   e copie o número em `instagram_business_account.id`.

### 3. GitHub
1. Crie um repositório **público** (ex.: `instagram-automacao`) e envie estes arquivos para ele.
   Precisa ser público porque o Instagram baixa as imagens e vídeos pelo link.
2. Ative o **GitHub Pages**: Settings > Pages > Source "Deploy from a branch", branch `main`, pasta `/ (root)`.
   Em `config.json`, troque `url_base_imagens` por `https://SEU_USUARIO.github.io/instagram-automacao/`
   e preencha marca, @, WhatsApp e cores.
3. Em **Settings > Secrets and variables > Actions**, crie os segredos:
   - `IG_USER_ID`: o ID da conta do passo 2.4
   - `IG_ACCESS_TOKEN`: o token do passo 2.3
   - `ANTHROPIC_API_KEY` (opcional): chave da API do Claude para criar conteúdo novo toda semana
4. Em **Actions**, rode manualmente "Preparar semana" uma vez. Depois disso, tudo segue sozinho.

## Comandos úteis (no computador)

```bash
pip install -r requirements.txt
python gerar.py conteudo/semana-01.json --inicio 2026-11-09   # agenda uma semana a partir da data
python publicar.py --testar      # confere token e conta (precisa de IG_USER_ID e IG_ACCESS_TOKEN)
python publicar.py --simular     # mostra o que seria publicado agora
python gerar_conteudo_ia.py      # escreve uma semana nova com IA
```

## Bom saber
- O Instagram permite até **50 publicações por dia** pela API; usamos 12 a 13.
- Pela API, stories saem como imagem, sem figurinhas interativas (enquete, caixa de perguntas). Por isso cada story termina com o convite para chamar no WhatsApp.
- O GitHub pode atrasar o agendamento alguns minutos. Se um post atrasar mais de 3 horas, ele é pulado para não sair tudo de uma vez.
- Se der erro, o robô tenta de novo nas próximas execuções (até 3 vezes) e o motivo fica em `fila.json`.
- Para mudar um post já agendado, edite `conteudo/semana-XX.json`, apague as linhas daquela semana em `fila.json` e rode `gerar.py` de novo.

## Estúdio de Reels (3 vídeos por dia)

Pedido do João (08/11): vídeos às **07:00, 11:00 e 19:00**, publicados sem aprovação prévia, seguindo o prompt
"GNZ01 AI Video Production Studio" (guardado em `conteudo/reels/diretrizes-video.md`).

Como funciona:
1. Os roteiros ficam em `conteudo/reels/roteiros-semana-NN.json` (gancho, desenvolvimento, CTA; fala e texto de cada cena).
2. Duas vezes por dia (03:00 e 12:00) o workflow **Produzir Reels** pega o próximo roteiro para cada horário livre
   das próximas 30 horas, produz o vídeo com `reels.py` e coloca na fila. O `publicar.py` publica no horário, com capa.
3. Produção (`src/reels.py` + `src/reels_audio.py`, FFmpeg): 1080x1920, H.264, 30 fps; texto cinético com destaque
   metálico, push-in de câmera, transições com zoom, demonstrações no celular, listas e comparações animadas;
   trilha eletrônica e efeitos (whoosh, impacto, cliques, notificação) **originais, gerados por código** (sem direitos de terceiros);
   narração com IA e legendas palavra por palavra; música abaixa sozinha sob a voz; volume final -14 LUFS.
4. Controle de qualidade automático antes de agendar (formato, duração, áudio, volume, picos, quadros pretos).
   Vídeo reprovado não entra na fila e abre uma issue de aviso.
5. Entregas de cada vídeo: `midia/reels/*.mp4` (+ capa .jpg) e `GNZ01-MARKETING/REELS/<data>_<hora>_<titulo>/`
   com `roteiro.md` (roteiro com tempos, narração, trilha e efeitos, legenda do post) e `legendas.srt`.
6. Quando faltarem menos de 9 roteiros, `gerar_reels_ia.py` escreve mais 21 com o Claude (precisa do segredo `ANTHROPIC_API_KEY`).

Narração (nessa ordem):
- **ElevenLabs**, se existir o segredo `ELEVENLABS_API_KEY` (plano pago a partir do Starter permite uso comercial;
  voz opcional na variável `ELEVENLABS_VOICE_ID`). É a voz mais natural.
- Senão, **vozes neurais da Microsoft via edge-tts** (pt-BR Antonio). Grátis e sem chave, mas é um serviço não oficial
  que pode parar de funcionar sem aviso.
- Se nenhuma funcionar, o vídeo sai **sem narração** (texto na tela, feito para assistir sem som) e a ficha diz isso.

Comandos:
```bash
python reels.py --teste r01-google-andradas   # produz um roteiro em midia/reels/teste/ sem agendar
python reels.py --horas 30                     # produz e agenda os próximos horários
REELS_SEM_NARRACAO=1 python reels.py --teste r02-cardapio-whatsapp   # força versão sem voz
```

### Roteiros do João (prioridade)

Roteiros escritos pelo João ficam em `conteudo/reels/joao/*.json` (mesmo formato dos roteiros do estúdio).
Com `"quando": "AAAA-MM-DD HH:MM"` o vídeo vai exatamente para esse horário; sem data, entra no próximo horário livre.
Um roteiro do João sempre tira do horário um Reel gerado que ainda não foi publicado. Os roteiros gerados por IA
só preenchem os horários que sobrarem. Cenas novas: `cinetico` (fala em tipografia cinética), `busca`,
`montagem` (modelos de site por nicho), `dispositivos` (notebook + celular) e `notificacoes` no gancho.
