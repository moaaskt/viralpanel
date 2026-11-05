# Requirements: ViralPanel

**Defined:** 2026-11-04  
**Core Value:** Automatizar 100% do ciclo de descoberta, produção e publicação de vídeos curtos de alta qualidade com consistência diária (meta de 6 vídeos por dia) e controle de qualidade supervisionado via Telegram, liberando o criador solo da rotina de produção manual.

## v1 Requirements

### Orquestração & Agendamento (SCHED)
- [x] **SCHED-01**: Sistema executa trigger diário programado às 01:00 (America/Sao_Paulo) via Celery Beat ou cron
- [x] **SCHED-02**: Sistema orquestra a fila assíncrona de processamento com Celery + Redis, garantindo retries com backoff exponencial
- [x] **SCHED-03**: Sistema garante idempotência das etapas, impedindo processamento duplicado de vídeos ou postagens repetidas

### Discovery & Coleta (DISC)
- [x] **DISC-01**: Sistema busca automaticamente os 30 vídeos mais virais no TikTok dentro do nicho de desenvolvimento pessoal e hashtags configuráveis
- [x] **DISC-02**: Módulo de scraping próprio baseado em Playwright + yt-dlp extrai metadados completos (views, likes, comentários, shares, data de postagem) de cada vídeo coletado
- [x] **DISC-03**: Sistema isola a interface de coleta permitindo evolução ou troca de estratégia sem quebrar o pipeline

### Scoring & Seleção (SCOR)
- [x] **SCOR-01**: Sistema calcula score de viralidade a partir de fórmula matemática parametrizável via YAML (considerando views, ratio de engajamento e velocidade de crescimento em 24h)
- [x] **SCOR-02**: Sistema ranqueia os 30 vídeos candidatos e seleciona o melhor candidato não processado para a esteira do dia

### Download & Transcrição de Mídia (MEDIA)
- [x] **MEDIA-01**: Sistema realiza download do vídeo de referência selecionado e extrai faixa de áudio limpa via yt-dlp e FFmpeg
- [x] **MEDIA-02**: Sistema transcreve o áudio com marcações de tempo (timestamps) usando Whisper / faster-whisper

### Roteirização com IA (SCRP)
- [x] **SCRP-01**: Sistema envia a transcrição e diretrizes de persona ao Gemini 2.5 Flash para análise estrutural de ganchos e retenção
- [x] **SCRP-02**: Gemini 2.5 Flash gera roteiro 100% original estruturado obrigatoriamente em: gancho de alta retenção (0–3s), desenvolvimento fluido (4–45s) e chamada para ação (CTA final)

### Produção de Áudio & Vídeo (PROD)
- [x] **PROD-01**: Módulo de síntese de voz (TTS) gera áudio narrado com voz clonada do criador utilizando XTTS v2 / Voice Studio através de interface modular
- [x] **PROD-02**: Módulo gerador de avatar sincroniza movimentos do avatar virtual do criador com o áudio narrado gerado
- [x] **PROD-03**: Módulo de composição via FFmpeg gera o vídeo final vertical 9:16 em formato reaction (vídeo base no centro/fundo, avatar do criador em miniatura na tela, legendas sincronizadas)

### Observabilidade & Supervisão no Telegram (TELE)
- [ ] **TELE-01**: Bot do Telegram envia alerta estruturado a cada conclusão de etapa, início de pipeline e falha técnica
- [ ] **TELE-02**: Modo supervisionado envia preview do vídeo 9:16 renderizado com botões interativos "Aprovar" e "Rejeitar"
- [ ] **TELE-03**: Sistema só avança para agendamento e postagem pública após aprovação explícita no Telegram (quando o modo supervisionado estiver ativo)

### Publicação & Agendamento Oficial (PUBL)
- [ ] **PUBL-01**: Sistema agenda e publica o vídeo aprovado no TikTok através da TikTok Content Posting API oficial
- [ ] **PUBL-02**: Sistema agenda e publica o vídeo aprovado no Instagram Reels via Meta Graph API oficial
- [ ] **PUBL-03**: Sistema agenda e publica o vídeo aprovado no YouTube Shorts via YouTube Data API v3 oficial
- [ ] **PUBL-04**: Sistema gera título, descrição e hashtags otimizadas para cada plataforma conforme o roteiro aprovado

### Persistência & Dados (DATA)
- [x] **DATA-01**: Banco de dados PostgreSQL armazena todo o histórico nos modelos `source_videos`, `scripts`, `assets`, `publications` e `runs`
- [x] **DATA-02**: Sistema gerencia arquivos locais gerados (áudios, vídeos intermediários e renderizações finais) com retenção e limpeza configurável

### Painel Web de Controle (DASH)
- [ ] **DASH-01**: Frontend em React + Chakra UI exibe status da fila de jobs Celery e estado atual da esteira diária
- [ ] **DASH-02**: Frontend exibe histórico de vídeos produzidos, roteiros gerados, métricas e links das publicações realizadas
- [ ] **DASH-03**: Interface com design limpo, moderno e profissional, sem cores neon

## v2 Requirements

### Otimizações & Escala
- **FEED-01**: Coleta automatizada de métricas pós-publicação (views, likes, retenção) após 24h e 7 dias para retroalimentar o algoritmo de scoring
- **AB-01**: Teste A/B automatizado de múltiplos ganchos iniciais para o mesmo tema
- **MULTI-01**: Suporte a múltiplos nichos e múltiplas contas de redes sociais simultâneas
- **THUMB-01**: Geração automática de capas/thumbnails personalizadas para YouTube Shorts e Instagram Reels

## Out of Scope

| Feature | Reason |
|---------|--------|
| API de Pesquisa Oficial do TikTok no v1 | Burocracia extrema de aprovação e limitações de acesso; priorizado scraper próprio Playwright + yt-dlp |
| Agregadores terceiros pagos (Buffer, Ayrshare) | Evitar custos recorrentes por postagem e eliminar intermediários externos de risco |
| Cores e temas neon no Painel | Diretriz explícita de manter visual limpo, corporativo e sóbrio com Chakra UI |
| Painel Web antes do pipeline | Prioridade estratégica de validar a geração de conteúdo e postagem antes do dashboard administrativo |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCHED-01 | Phase 1 | Complete |
| SCHED-02 | Phase 1 | Complete |
| SCHED-03 | Phase 1 | Complete |
| DISC-01 | Phase 2 | Complete |
| DISC-02 | Phase 2 | Complete |
| DISC-03 | Phase 2 | Complete |
| SCOR-01 | Phase 2 | Complete |
| SCOR-02 | Phase 2 | Complete |
| MEDIA-01 | Phase 3 | Complete |
| MEDIA-02 | Phase 3 | Complete |
| SCRP-01 | Phase 3 | Complete |
| SCRP-02 | Phase 3 | Complete |
| PROD-01 | Phase 4 | Complete |
| PROD-02 | Phase 4 | Complete |
| PROD-03 | Phase 4 | Complete |
| TELE-01 | Phase 5 | Pending |
| TELE-02 | Phase 5 | Pending |
| TELE-03 | Phase 5 | Pending |
| PUBL-01 | Phase 6 | Pending |
| PUBL-02 | Phase 6 | Pending |
| PUBL-03 | Phase 6 | Pending |
| PUBL-04 | Phase 6 | Pending |
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DASH-01 | Phase 7 | Pending |
| DASH-02 | Phase 7 | Pending |
| DASH-03 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0 ✓

---
*Requirements defined: 2026-11-04*
*Last updated: 2026-11-04 after initial definition*
