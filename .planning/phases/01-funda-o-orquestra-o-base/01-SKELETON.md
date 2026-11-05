# Walking Skeleton — ViralPanel

**Phase:** 1  
**Generated:** 2026-11-05  

## Capability Proven End-to-End

> Um comando ou trigger agendado executa uma task de pipeline assíncrona no Celery Worker via Redis, registra o ciclo de execução na tabela `runs` do PostgreSQL com controle de idempotência, e valida a integridade do diretório de armazenamento local.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language & Runtime | Python 3.12 | Suporte moderno a type hints, performance aprimorada e compatibilidade com ecossistema de IA e mídia |
| Orchestration & Queues | Celery + Redis | Padrão robusto para filas distribuídas, retries automáticos com backoff e agendamento preciso via Celery Beat |
| Data Layer | PostgreSQL + SQLAlchemy 2.0 + Alembic | Banco relacional robusto para histórico e estado com migrações versionadas |
| Configuration | Pydantic Settings (`BaseSettings`) | Validação estrita de variáveis de ambiente, tipos e segredos |
| Infrastructure | Docker Compose | Reproducibilidade garantida entre desenvolvimento local e deploy na VPS |
| Storage Manager | Local Filesystem com Pathlib e retenção TTL | Simplicidade na VPS com estrutura limpa de diretórios e isolamento por run |

## Stack Touched in Phase 1

- [ ] Project scaffold (estrutura de pastas `src/viralpanel`, `pyproject.toml`, Dockerfile, `.env.example`)
- [ ] Routing & Services — inicialização da aplicação e módulos centrais
- [ ] Database — PostgreSQL com migrações Alembic e modelos `source_videos`, `scripts`, `assets`, `publications`, `runs`
- [ ] Queue & Worker — Celery worker conectado ao Redis com execução assíncrona de tasks
- [ ] Deployment — `docker-compose.yml` orquestrando postgres, redis, celery_worker e celery_beat

## Out of Scope (Deferred to Later Slices)

- Coleta do TikTok com Playwright/yt-dlp (Fase 2)
- Transcrição Whisper e LLM Gemini 2.5 Flash (Fase 3)
- Síntese de voz XTTS e composição FFmpeg (Fase 4)
- Bot do Telegram e aprovação interativa (Fase 5)
- Publicação nas APIs oficiais (Fase 6)
- Frontend React com Chakra UI (Fase 7)

## Subsequent Slice Plan

Cada fase posterior adicionará uma fatia vertical sobre este esqueleto sem alterar a arquitetura base:

- Phase 2: Discovery & Scoring no TikTok (scraping e cálculo de score)
- Phase 3: Análise, Transcrição & Roteiro Gemini (Whisper + Gemini)
- Phase 4: Produção Studio (XTTS, avatar e FFmpeg 9:16)
- Phase 5: Bot Telegram Supervisionado (notificações e aprovação)
- Phase 6: Publicação Direta Oficial (TikTok, Instagram, YouTube)
- Phase 7: Painel Web de Controle (React + Chakra UI)
