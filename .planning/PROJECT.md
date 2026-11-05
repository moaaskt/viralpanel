# ViralPanel

## What This Is

ViralPanel é um pipeline autônomo de geração e publicação de conteúdo viral para criadores solo. Ele automatiza 100% do ciclo de produção: descobre diariamente os vídeos em maior ascensão no TikTok dentro do nicho de desenvolvimento pessoal e motivação, extrai o tema e estrutura com Whisper, cria roteiros originais e persuasivos via Gemini 2.5 Flash, produz áudio com voz clonada (XTTS), monta o vídeo final vertical (9:16) com avatar virtual em formato reaction e legendas via FFmpeg, e agenda a publicação diretamente nas APIs oficiais do TikTok, Instagram Reels e YouTube Shorts.

## Core Value

Automatizar 100% do ciclo de descoberta, produção e publicação de vídeos curtos de alta qualidade com consistência diária (meta de 6 vídeos por dia) e controle de qualidade supervisionado via Telegram, liberando o criador solo da rotina de produção manual.

## Business Context

- **Customer**: Criador de conteúdo solo focado em desenvolvimento pessoal, produtividade e motivação
- **Revenue model**: Monetização de plataformas sociais, tráfego orgânico, visualizações e parcerias/patrocínios
- **Success metric**: 6 vídeos originais publicados por dia com retenção alta e zero intervenção além da aprovação no Telegram
- **Strategy notes**: Baseado nas especificações arquiteturais documentadas em `docs/Arquitetura Sistema Autônomo de Geração de Conteúdo Viral.pdf`

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] RF01: Execução agendada diária às 01:00 (America/Sao_Paulo) e orquestração de tarefas distribuídas via Celery + Redis
- [ ] RF02: Módulo Discovery de vídeos virais no TikTok no nicho de desenvolvimento pessoal via scraper próprio (Playwright + yt-dlp)
- [ ] RF03: Algoritmo de cálculo de score de viralidade configurável via YAML (views mínimas, likes/views ratio, taxa de crescimento em 24h)
- [ ] RF04: Seleção do melhor vídeo candidato por score com filtro de descarte para itens já processados
- [ ] RF05: Download automatizado do vídeo candidato e extração de áudio isolado via yt-dlp e FFmpeg
- [ ] RF06: Transcrição de áudio com marcação de tempo (timestamps) usando Whisper / faster-whisper
- [ ] RF07: Geração de roteiro original com Gemini 2.5 Flash com estrutura rígida (gancho 0–3s, desenvolvimento 4–45s, CTA final)
- [ ] RF08: Módulo de voz com interface modular para voz clonada do criador utilizando XTTS / Voice Studio
- [ ] RF09: Geração do avatar virtual (formato reaction em overlay) e composição do vídeo final 9:16 com legendas automáticas via FFmpeg
- [ ] RF10: Integração de publicação direta com APIs oficiais: TikTok Content Posting API, Meta Graph API (Instagram Reels) e YouTube Data API v3
- [ ] RF11: Bot no Telegram para observabilidade em tempo real e modo supervisionado (aprovação/rejeição com preview de vídeo antes da postagem)
- [ ] RF12: Persistência relacional em PostgreSQL (modelos: source_videos, scripts, assets, publications, runs)
- [ ] RF13: Painel web administrativo em React + Chakra UI (design limpo, profissional, sem neon) para monitoramento de filas, histórico e métricas

### Out of Scope

- Uso da API Oficial de Pesquisa do TikTok para discovery no v1 — evitado devido a restrições de aprovação burocrática; priorizado scraper próprio com Playwright + yt-dlp
- Ferramentas agregadoras terceiras de agendamento (Buffer, Ayrshare, Hootsuite) — substituídas por integrações diretas nas APIs oficiais
- Cores neon e layout sobrecarregado no frontend — restrição explícita de UI moderna, minimalista e limpa com Chakra UI
- Painel Web antes do pipeline — prioridade imediata é validar a esteira de vídeo ponta a ponta (CLI/Telegram) antes de construir o dashboard administrativo completo

## Context

- **Ambiente de Execução**: VPS Linux rodando Docker Compose com PostgreSQL, Redis, Celery Worker, Celery Beat, backend Python 3.12 e frontend React
- **Arquitetura em Módulos**: Módulos independentes com contratos claros de entrada e saída (Scheduler, Discovery, Scoring, Downloader, Transcriber, Scriptwriter, Voice, Avatar, Composer, Publisher, Notifier) para permitir evolução ou troca de ferramentas sem reescrever o sistema
- **Direitos Autorais e Políticas**: O vídeo de origem serve estritamente para extração analítica de temas e ganchos; o roteiro gerado é 100% original e transformado para evitar penalidades de conteúdo reciclado e reivindicações de direitos autorais

## Constraints

- **Tech Stack**: Python 3.12, PostgreSQL, Redis, Celery, FFmpeg, React, Chakra UI, Docker Compose
- **LLM**: Google Gemini 2.5 Flash para geração de roteiros originais e estruturados
- **Áudio & Vídeo**: XTTS v2 para clonagem de voz, Whisper para transcrição, FFmpeg para renderização 9:16 e composição
- **Publicação**: APIs oficiais diretas (TikTok, Meta Graph API, YouTube Data API v3)
- **Design de UI**: Chakra UI com paleta limpa e profissional, estritamente sem neon

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Scraper próprio com Playwright + yt-dlp | Controle total sobre métricas e velocidade sem custo de serviços terceiros ou burocracia de aprovação | — Pending |
| Gemini 2.5 Flash para geração de roteiros | Custo reduzido, latência baixa e alta criatividade com aderência à estrutura (gancho 3s + desenvolvimento + CTA) | — Pending |
| Modo supervisionado via Telegram no início | Permite validar a qualidade dos vídeos e ganchos gerados antes de liberar publicação 100% autônoma | — Pending |
| Interface modular para síntese de Voz e Avatar | Facilita uso de mock/APIs em nuvem durante o desenvolvimento inicial e suporte a XTTS/SadTalker locais na VPS | — Pending |
| Publicação direta via APIs oficiais | Reduz custo de intermediários (Ayrshare/Buffer) e previne pontos únicos de falha externos | — Pending |
| Pipeline primeiro (CLI/Telegram), Painel web em seguida | Valida o núcleo de valor do negócio e o pipeline funcional antes do esforço de interface frontend | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-04 after initialization*

