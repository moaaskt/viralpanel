---
gsd_state_version: "1.0"
milestone: v1.1
milestone_name: ZUNTO! Visual Engine
current_phase: 15
current_plan: 15-01
status: completed
stopped_at: Milestone v1.1 complete — archived to .planning/milestones/v1.1-ROADMAP.md
last_updated: "2026-11-22T21:49:00.000Z"
last_activity: 2026-11-22
state_head: 318a2cdb42b1528780ad875cf058280ead850394
progress:
  total_phases: 11
  completed_phases: 11
  total_plans: 17
  completed_plans: 17
  percent: 100
last_activity_desc: Milestone v1.1 complete and archived
---

# Project State

## Project Reference

See: [.planning/PROJECT.md](file:///.planning/PROJECT.md) (updated 2026-11-22)

**Core value:** Refatorar e aprimorar o pipeline de geração e composição audiovisual, elevando a qualidade dos vídeos produzidos automaticamente pelo sistema com a identidade visual ZUNTO!.  
**Current focus:** Milestone v1.1 Complete (Archived)

## Current Position

Phase: 15 (Concluída)
Current Plan: 15-01 (Concluído)
Total Plans in Phase: 1
Status: Milestone v1.1 Shipped / Completed
Last activity: 2026-11-22

Progress: [██████████] 100%

## Performance Metrics

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 08 P01 | 5min | 2 tasks | 1 files |
| Phase 08 P02 | 10min | 2 tasks | 1 files |
| Phase 09 P01 | 4min | 2 tasks | 2 files |
| Phase 09 P02 | 6m | 3 tasks | 4 files |
| Phase 10 P01 | 8m | 3 tasks | 3 files |
| Phase 10 P02 | 4m | 2 tasks | 2 files |
| Phase 11 P01 | 7m | 3 tasks | 4 files |
| Phase 11 P02 | 4min | 2 tasks | 2 files |
| Phase 12 P01 | 6m | 3 tasks | 2 files |
| Phase 12 P02 | 7m | 2 tasks | 3 files |
| Phase 13 P01 | 8min | 2 tasks | 2 files |
| Phase 13 P02 | 8min | 4 tasks | 5 files |
| Phase 13.1 P01 | 7min | 4 tasks | 4 files |
| Phase 13.2 P01 | 8min | 5 tasks | 4 files |
| Phase 13.3 P01 | 6min | 5 tasks | 5 files |
| Phase 14 P01 | 5min | 3 tasks | 3 files |
| Phase 15 P01 | 6min | 4 tasks | 4 files |

## Accumulated Context

### Decisions

- [v1.1]: Investigação prévia obrigatória da causa raiz dos problemas visuais e mapeamento de contratos antes de qualquer alteração de código.
- [v1.1]: Sem adoção a priori de máscaras de avatar; definição da técnica dependerá do formato dos assets reais diagnosticados na Phase 8.
- [v1.1]: Single-pass no renderer definido como composição integrada em grafo único e codificação única sempre que viável, sem passes intermediários.
- [v1.1]: CTA contextual e opcional sem imposição de repetição mecânica do slogan em todos os vídeos; rastreabilidade de fontes para precisão factual.
- [v1.1]: Validação dupla obrigatória na Phase 13 (testes automatizados + inspeção visual humana de vídeos reais).
- [Phase 08]: Preservar inalterada a assinatura StudioService.produce(db, run_id, script) -> Asset e os 3 registros Asset (audio, avatar, final_video) para compatibilidade com Celery
- [Phase 08]: Adotar DTOs internos tipados (StudioRenderRequest, AvatarConfig, SubtitleJobConfig, ReactionCompositionSpec) nas Phases 10-12 para eliminar chamadas redundantes ao ffprobe
- [Phase 08]: Unificar passes FFmpeg em grafo single-pass na Phase 12 com canal alfa em memoria (yuva420p) e asplit para showwaves, eliminando avatar.mp4 e source_visual_bg.mp4 intermediarios
- [Phase 08]: Adotar caixa opaca ASS (BorderStyle=3 com fundo #0A0A0A) em MarginV=640 na Phase 10 para cobrir diretamente hard-subs nativos dos videos baixados do TikTok
- [Phase 08]: Tratar simultaneamente nas Phases 11 e 12 os 4 cenarios do artefato quadrado do avatar: (1) asset rgb24 opaco com drawbox, (2) format=yuv420p em avatar.py destruindo alfa, (3) pad=white em renderer.py:128 e (4) limitacao de avatar.mp4 (libx264/yuv420p) sem canal alfa via Single-Pass
- [Phase 08]: Reposicionar o avatar circular (280-300px) para a safe zone Y=1320..1600px (H-h-320), eliminando colisao com legendas ASS e com a UI do TikTok/Reels/Shorts
- [Phase 09]: Centralizar paleta oficial ZUNTO! (#0A0A0A, #FACC15, #FFFFFF, #1A1A1A) e safe zones em classes imutáveis com Final em src/viralpanel/branding.py
- [Phase 09]: Implementar hex_to_ass_color para conversão segura de Hex para ASS BGR (&HAABBGGRR&) prevenindo inversão de cores no libass
- [Phase 09]: D-01/D-02: Persona ZUNTO! orientada por 'Você não sabia. Agora sabe.' com ganchos de 0-3s e sem encerramentos forçados
- [Phase 09]: D-03/D-04: Separação estrita de closing_thought e cta opcional nullable em GeneratedScriptSchema e full_text limpo sem linhas órfãs
- [Phase 09]: D-06/D-07: FactualClaim com preservação rigorosa da transcrição original sem inventar fontes externas
- [Phase 09]: D-08: Script.metadata_json armazena factual_claims e metadados de roteirização preservando compatibilidade com o banco
- [Phase 10]: Adotar BorderStyle=3 com Outline=16 e MarginV=640 em preto profundo #0A0A0A para cobertura nativa de hard-subs preexistentes do TikTok
- [Phase 10]: Implementar DTO imutável SubtitleJobConfig e desacoplar lógica temporal/estilística de subtitles.py de qualquer dependência direta do FFmpeg
- [Phase 10]: Implementar segmentação orientada a pausas (. , ! ? ; :) com 3 a 5 palavras por cue e temporização proporcional contígua sem gaps/overlaps
- [Phase 10]: Sanitização ASS de {} para () e quebras para \N, com destaque amarelo ZUNTO! {\c&H0015CCFA&} e fechamento compulsório em branco {\c&H00FFFFFF&}
- [Phase 10]: D-01: Integração de SubtitleJobConfig em StudioService.produce preservando contratos de Asset e DB
- [Phase 10]: D-04: Burn-in de legenda aplicado estritamente em camada única no passe final do ReactionVideoRenderer
- [Phase 10]: D-05: Posição geométrica nominal de legendas com MarginV=640 e alinhamento inferior central (Alignment=2)
- [Phase 10]: D-06: Validação de renderização empírica via amostragem de pixels rawvideo e delegação formal da validação visual final de UIs móveis para a Phase 13
- [Phase 11-avatar-reaction-e-composicao-visual-organica]: Calibração de SafeZones9x16 com size=300, margin_right=54 e margin_bottom=320 para isolar a zona vertical de legendas (1080..1280px)
- [Phase 11-avatar-reaction-e-composicao-visual-organica]: Utilização do codec de vídeo png em pix_fmt rgba dentro do container MP4 para transporte sem perdas de canal alfa
- [Phase 11-avatar-reaction-e-composicao-visual-organica]: Confinamento geométrico de showwaves (#FACC15@0.85) antes da máscara circular geq, prevenindo vazamento e caixas pretas opacas
- [Phase 11-avatar-reaction-e-composicao-visual-organica]: Eliminação total do filtro pad de moldura retangular branca em ReactionVideoRenderer (Cenário 3 da auditoria)
- [Phase 11-avatar-reaction-e-composicao-visual-organica]: Posicionamento do overlay PIP em W-w-54:H-h-320 (X=726..1026, Y=1300..1600), isolando a zona de legendas (1080..1280px) e desobstruindo a barra inferior mobile (Y>=1600px)
- [Phase 12-refatoracao-do-video-composer-ffmpeg-e-integracao]: Injeção de color=c=#0f172a:s=1080x1920:r=24:d={duration} via lavfi inline na entrada [0:v] do FFmpeg quando has_video_stream() for falso, eliminando 100% de source_visual_bg.mp4 em disco e seu subprocesso
- [Phase 12-refatoracao-do-video-composer-ffmpeg-e-integracao]: Definição de ReactionCompositionSpec (frozen) com defaults oficiais (1080x1920, 24fps, libx264, veryfast, crf 20, yuv420p, aac 192k)
- [Phase 13-validacao-tecnica-automatizada-e-inspecao-audiovisual-e2e]: MediaQualityValidator com verificação de specs A/V e inspeção humana formalmente aprovada
- [Phase 13.1-word-by-word-karaoke-captions]: Active Word Highlight palavra a palavra com sincronia WordBoundary
- [Phase 13.2-cinematic-backdrop-and-subtitle-stage-composition]: Backdrop desfocado (boxblur) e escurecido (colorlevels) para 16:9, legendas em MarginV=420 e safe zone de botões (X<=940)
- [Phase 13.3-subtitle-vertical-realignment-and-static-mascot-avatar]: MarginV=365, MarginR=440 e mascote estático ZUNTO!
- [Phase 14-formalizacao-da-coleta-e-scraper]: Deduplicação canônica de URLs do TikTok e tolerância a falhas yt-dlp
- [Phase 15-database-schema-integrity-postgresql-migration-tests]: Migração 002 com 001 imutável, injeção de conexão no Alembic e zero drift verificado

### Roadmap Evolution

- Milestone v1.0 MVP: Shipped (Phases 1-7)
- Milestone v1.1 ZUNTO! Visual Engine: Shipped (Phases 8-15)

### Deferred Items / Overrides

| Item | Category | Description | Status | Target |
|---|---|---|---|---|
| `POSTGRES-16-CI-EXECUTION` | CI Evidence | Execução real de `test_postgres_real_migration_and_strict_zero_drift` no runner do GitHub Actions com `postgres:16` (homologada localmente com 100% de sucesso na Quick Task 261120-2u1) | Pending Push | GitHub Actions CI Run |

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 261119-12d | Render first real ZUNTO! Great White Shark Short in run_google_flow_shark_001 | 2026-11-19 | none | complete | .planning/quick/261119-12d-render-first-real-zunto-great-white-shar |
| 261119-1pv | Enforce strict two-line subtitle limit with width-aware reflow and font fallback | 2026-11-19 | none | complete | .planning/quick/261119-1pv-enforce-strict-two-line-subtitle-limit-w |
| 261119-r52 | Correção da sincronização do estado GSD (formato numérico no ROADMAP.md) | 2026-11-19 | none | complete | .planning/quick/261119-r52-fix-gsd-state-sync |
| 261120-2u1 | Validação local de migrações e zero schema drift em PostgreSQL 16 descartável | 2026-11-20 | 318a2cd | complete | .planning/quick/261120-2u1-validate-postgres16-zero-drift |

## Session

**Last session:** 2026-11-22T21:49:00Z
**Stopped at:** Milestone v1.1 complete — archived to .planning/milestones/v1.1-ROADMAP.md
**Resume file:** None
