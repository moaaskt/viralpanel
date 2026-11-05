# Roadmap: ViralPanel

## Overview

O ViralPanel é construído através de uma abordagem Vertical MVP, dividida em 7 fases progressivas. O projeto começa estruturando a fundação de containers e persistência, avança para o motor de discovery e scoring no TikTok, implementa o pipeline de análise e roteirização com Gemini 2.5 Flash, integra a produção de voz clonada e avatar reaction com FFmpeg, estabelece o fluxo de supervisão humana via Telegram, ativa a publicação automatizada nas APIs oficiais das três redes e coroa o ecossistema com um painel de controle moderno em React + Chakra UI.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3...): Planned milestone work
- Decimal phases (e.g. 2.1): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Fundação & Orquestração Base** - Ambiente Docker Compose, PostgreSQL com migrations, Redis e Celery assíncrono
- [ ] **Phase 2: Discovery & Scoring no TikTok** - Scraper próprio (Playwright + yt-dlp) com algoritmo de ranking configurável via YAML
- [ ] **Phase 3: Análise, Transcrição & Roteiro Gemini** - Download, transcrição com Whisper e criação de roteiros estruturados via Gemini 2.5 Flash
- [ ] **Phase 4: Produção Studio (Voz, Avatar & Vídeo Reaction)** - Clonagem de voz com XTTS, avatar virtual e montagem 9:16 com legendas via FFmpeg
- [ ] **Phase 5: Observabilidade & Bot Telegram Supervisionado** - Notificações em tempo real e modo supervisionado com preview de vídeo e aprovação
- [ ] **Phase 6: Publicação Direta nas APIs Oficiais** - Integração direta com TikTok Content Posting API, Meta Graph API e YouTube Data API v3
- [ ] **Phase 7: Painel Web de Controle** - Interface React + Chakra UI (sem neon) para monitoramento de filas, histórico e métricas

## Phase Details

### Phase 1: Fundação & Orquestração Base
**Goal**: Subir a infraestrutura Docker Compose completa com PostgreSQL, Redis, Celery Worker/Beat e modelos de banco de dados
**Mode:** mvp
**Depends on**: Nothing (primeira fase)
**Requirements**: SCHED-01, SCHED-02, SCHED-03, DATA-01, DATA-02
**Success Criteria** (what must be TRUE):
  1. Docker Compose sobe PostgreSQL, Redis, Celery Worker e Celery Beat sem falhas de conexão
  2. Modelos relacionais (`source_videos`, `scripts`, `assets`, `publications`, `runs`) aplicados no PostgreSQL via migrações
  3. Job de teste executado de forma assíncrona pelo Celery com log e status gravados no banco
**Plans**: TBD

Plans:
- [ ] 01-01: Setup do repositório, Docker Compose, PostgreSQL, Redis e configurações de ambiente
- [ ] 01-02: Modelagem do banco de dados (SQLAlchemy / Alembic) e persistência de runs
- [ ] 01-03: Configuração da fila Celery com retry, idempotência e Celery Beat agendado para 01:00

### Phase 2: Discovery & Scoring no TikTok
**Goal**: Coletar os 30 vídeos virais mais relevantes no nicho de desenvolvimento pessoal e ranquear o melhor candidato via fórmula YAML
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: DISC-01, DISC-02, DISC-03, SCOR-01, SCOR-02
**Success Criteria** (what must be TRUE):
  1. Scraper autônomo baseado em Playwright + yt-dlp busca e extrai metadados dos 30 vídeos do nicho sem quebrar
  2. Fórmula matemática parametrizada via arquivo YAML calcula score de viralidade considerando views, likes/views ratio e velocidade em 24h
  3. O melhor candidato não processado é selecionado e persistido no banco com status pendente de análise
**Plans**: TBD

Plans:
- [ ] 02-01: Implementação da interface e módulo de scraping próprio (Playwright + yt-dlp) para coleta dos 30 vídeos
- [ ] 02-02: Módulo de cálculo de viralidade baseado em regras YAML e rotina de seleção e deduplicação no banco

### Phase 3: Análise, Transcrição & Roteiro Gemini
**Goal**: Baixar o vídeo candidato, extrair áudio, transcrever com Whisper e produzir um roteiro original e persuasivo via Gemini 2.5 Flash
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: MEDIA-01, MEDIA-02, SCRP-01, SCRP-02
**Success Criteria** (what must be TRUE):
  1. Download do vídeo e extração de áudio isolado executados com sucesso via yt-dlp e FFmpeg
  2. Áudio transcrito com precisão incluindo marcações de tempo (timestamps) pelo Whisper / faster-whisper
  3. Gemini 2.5 Flash analisa a estrutura e gera roteiro original rigorosamente com gancho (0–3s), desenvolvimento (4–45s) e CTA final
**Plans**: TBD

Plans:
- [ ] 03-01: Pipeline de download de mídia e extração de áudio com persistência de assets
- [ ] 03-02: Módulo de transcrição com Whisper e formatação de timestamps
- [ ] 03-03: Integração com Gemini 2.5 Flash para geração de roteiros originais e ganchos estruturados

### Phase 4: Produção Studio (Voz, Avatar & Vídeo Reaction)
**Goal**: Gerar narração clonada com XTTS, animar avatar do criador e renderizar o vídeo vertical 9:16 final com legendas via FFmpeg
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: PROD-01, PROD-02, PROD-03
**Success Criteria** (what must be TRUE):
  1. Interface modular de voz sintetiza o roteiro gerado utilizando a voz clonada do criador (XTTS / Voice Studio)
  2. Módulo de avatar gera vídeo do criador reagindo ou apresentando em sincronia labial com a narração
  3. FFmpeg realiza a composição final em formato 9:16 vertical (vídeo de referência, avatar do criador em overlay e legendas animadas sincronizadas)
**Plans**: TBD

Plans:
- [ ] 04-01: Módulo modular de síntese de voz (TTS) com suporte a XTTS v2
- [ ] 04-02: Módulo de geração e animação do avatar virtual sincronizado
- [ ] 04-03: Pipeline de renderização FFmpeg para layout reaction 9:16 e burning de legendas sincronizadas

### Phase 5: Observabilidade & Bot Telegram Supervisionado
**Goal**: Configurar bot do Telegram com monitoramento em tempo real e modo supervisionado interativo para aprovação/rejeição do vídeo antes da publicação
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: TELE-01, TELE-02, TELE-03
**Success Criteria** (what must be TRUE):
  1. Bot do Telegram envia notificações detalhadas de sucesso, erros e status de cada etapa da pipeline
  2. Bot envia arquivo ou streaming de preview do vídeo final montado com botões de callback "Aprovar" e "Rejeitar"
  3. O pipeline aguarda a resposta humana no Telegram antes de liberar o agendamento de publicação quando o modo supervisionado estiver ligado
**Plans**: TBD

Plans:
- [ ] 05-01: Setup do Telegram Bot com mensageria assíncrona e logs estruturados
- [ ] 05-02: Implementação do fluxo interativo de aprovação humana com envio de preview de vídeo e handlers de Aprovar/Rejeitar

### Phase 6: Publicação Direta nas APIs Oficiais
**Goal**: Realizar a postagem e agendamento automático nas três plataformas oficiais (TikTok, Instagram Reels e YouTube Shorts)
**Mode:** mvp
**Depends on**: Phase 5
**Requirements**: PUBL-01, PUBL-02, PUBL-03, PUBL-04
**Success Criteria** (what must be TRUE):
  1. Integração com TikTok Content Posting API autentica e agenda a postagem do vídeo
  2. Integração com Meta Graph API publica vídeo vertical no Instagram Reels com legendas e hashtags
  3. Integração com YouTube Data API v3 publica vídeo como Shorts e registra o ID e URL no banco
**Plans**: TBD

Plans:
- [ ] 06-01: Módulo de autenticação OAuth2 e gerenciamento de tokens das três plataformas
- [ ] 06-02: Publicador TikTok Content Posting API
- [ ] 06-03: Publicador Meta Graph API (Instagram Reels) e YouTube Data API v3 (Shorts) com geração de metadados

### Phase 7: Painel Web de Controle
**Goal**: Criar o painel web minimalista e profissional em React + Chakra UI para monitorar a esteira diária, filas Celery, histórico de vídeos e métricas
**Mode:** mvp
**Depends on**: Phase 6
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. Frontend React construído com Chakra UI com design sóbrio, limpo e profissional (sem cores neon)
  2. Painel exibe visão em tempo real da fila Celery, jobs ativos e agendamento da próxima execução
  3. Seção de histórico permite navegar pelos vídeos gerados, roteiros, logs de execução e links publicados
**Plans**: TBD

Plans:
- [ ] 07-01: Setup do frontend React com Chakra UI e integração de API com o backend
- [ ] 07-02: Telas de monitoramento de fila Celery, status dos jobs e disparo manual
- [ ] 07-03: Tela de histórico de publicações, biblioteca de roteiros/assets e visualização de métricas

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Fundação & Orquestração Base | 0/3 | Not started | - |
| 2. Discovery & Scoring no TikTok | 0/2 | Not started | - |
| 3. Análise, Transcrição & Roteiro Gemini | 0/3 | Not started | - |
| 4. Produção Studio (Voz, Avatar & Vídeo Reaction) | 0/3 | Not started | - |
| 5. Observabilidade & Bot Telegram Supervisionado | 0/2 | Not started | - |
| 6. Publicação Direta nas APIs Oficiais | 0/3 | Not started | - |
| 7. Painel Web de Controle | 0/3 | Not started | - |
