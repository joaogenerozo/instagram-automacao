# Automação do Instagram: 5 posts por dia

Todo dia, no automático:

| Horário (Brasília) | Formato |
|---|---|
| 08:00 | Post |
| 12:00 | **Carrossel** |
| 15:00 | Post |
| 18:30 | Post |
| 21:00 | Post |

E mais **7 stories por dia** com perguntas frequentes (07:30, 09:30, 11:00, 13:30, 16:30, 19:30 e 22:00), mais **1 Reels por dia às 19:00** quando houver vídeo de depoimento na pasta `videos/`.

Temas: **criação de sites** (foco principal), **cardápio digital** e **agenda online para profissionais**. Os posts de cardápio e agenda terminam oferecendo também a criação de site.

## Como funciona

1. **Toda sábado** o robô prepara a semana seguinte: cria 35 posts novos com IA (Claude), desenha as imagens e coloca tudo na fila (`fila.json`). Sem chave de IA, ele reaproveita as semanas já escritas em `conteudo/`.
2. **A cada 30 minutos** o robô olha a fila e publica os posts, stories e Reels daquele horário pela API oficial do Instagram.
3. Tudo roda de graça no **GitHub Actions**. Você não precisa deixar computador ligado.

A semana 1 já está escrita em `conteudo/semana-01.json` e as imagens de exemplo estão em `midia/`.

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
| `fila.json` | Fila de posts com status: pendente, publicado, pulado ou erro |

## Instalação (uma vez só)

### 1. Conta do Instagram
- A conta precisa ser **Profissional** (Comercial ou Criador de conteúdo).
- Ligue a conta a uma **Página do Facebook** (Instagram > Configurações > Central de Contas).

### 2. Token da API (Meta for Developers)
1. Acesse developers.facebook.com, crie um app do tipo **Empresa**.
2. Adicione o produto **Instagram** (API com login do Facebook).
3. No **Gerenciador de Negócios** (business.facebook.com > Configurações > Usuários do sistema), crie um **usuário do sistema** administrador, dê acesso à sua Página e ao app e gere um token com as permissões:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`.
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
