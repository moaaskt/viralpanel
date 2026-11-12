---
phase: 08-auditoria-contratos-e-diagn-stico-de-causa-raiz
plan: 01
subsystem: studio
tags: [ffmpeg, ffprobe, celery, contracts, dto, single-pass, audit]

# Dependency graph
requires: []
provides:
  - "Mapeamento exaustivo de contratos e interfaces entre tasks.py, StudioService, StorageManager, voice.py, avatar.py, subtitles.py e renderer.py (Seção 1 de 08-AUDIT-REPORT.md)"
  - "Especificação conceitual de DTOs tipados internos (StudioRenderRequest, AvatarConfig, SubtitleJobConfig, SubtitleCue, ReactionCompositionSpec) preservando StudioService.produce(db, run_id, script) -> Asset"
  - "Inventário completo de passes FFmpeg/FFprobe atuais (Passe 0 fallback, Passe 1 avatar.mp4 yuv420p, Passe 2 final_reaction_9x16.mp4) e especificação do grafo filter_complex single-pass para a Phase 12 (Seção 4 de 08-AUDIT-REPORT.md)"
affects:
  - 08-02
  - 10-motor-de-legendas-zunto-e-desacoplamento
  - 11-avatar-reaction-e-composi-o-visual-org-nica
  - 12-refatora-o-do-video-composer-ffmpeg-e-integra-o

# Actuals (#2632)
actuals:
  tokens: 8739
  tasks: 2
  commits: 2
plan_head_before: 5ad34f69ffaf1aefc1499af8ecff5b29f7e9ef5e
plan_head_after: 8a9bb7d5bb326cecd470b984f6c49a13f74df458

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Preservação estrita da fronteira pública Celery -> StudioService.produce(db, run_id, script) -> Asset (D-01)"
    - "Isolamento de parâmetros de renderização via DTOs imutáveis (StudioRenderRequest, AvatarConfig, ReactionCompositionSpec)"
    - "Composição audiovisual FFmpeg single-pass com canal alfa em memória (yuva420p) e divisão de áudio via asplit"

key-files:
  created:
    - .planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md
  modified: []

key-decisions:
  - "Preservar inalterada a assinatura StudioService.produce(db, run_id, script) -> Asset e a persistência dos 3 registros Asset (audio, avatar, final_video) para compatibilidade retroativa com Celery e dashboard"
  - "Adotar DTOs internos tipados (StudioRenderRequest, AvatarConfig, SubtitleJobConfig, ReactionCompositionSpec) nas Phases 10-12 para eliminar parâmetros Path soltos e chamadas redundantes ao ffprobe"
  - "Unificar Passe 0 (fallback lavfi), Passe 1 (avatar.mp4) e Passe 2 (render final) em um único comando FFmpeg single-pass na Phase 12, preservando canal alfa yuva420p em memória"

patterns-established:
  - "Auditoria diagnóstica não destrutiva (D-15): inspeção via AST/inspect, ffprobe e pytest com zero modificações em src/viralpanel/"

requirements-completed: [COMP-01]

coverage:
  - id: D1
    description: "Mapeamento de contratos e interfaces entre Celery, StudioService e módulos de estúdio com DTOs conceituais (Seção 1 de 08-AUDIT-REPORT.md)"
    requirement: COMP-01
    verification:
      - kind: unit
        ref: ".venv/bin/python -c \"from viralpanel.studio.service import StudioService; import inspect; sig = inspect.signature(StudioService.produce); assert 'db' in sig.parameters and 'run_id' in sig.parameters and 'script' in sig.parameters\""
        status: pass
    human_judgment: false
  - id: D2
    description: "Mapeamento dos 3 passes FFmpeg atuais e proposta de grafo filter_complex single-pass para a Phase 12 (Seção 4 de 08-AUDIT-REPORT.md)"
    requirement: COMP-01
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py"
        status: pass
      - kind: unit
        ref: "tests/test_studio_avatar.py"
        status: pass
    human_judgment: false

# Metrics
duration: 5min
completed: 2026-11-06
status: complete
---

# Phase 08 Plan 01: Auditoria de Contratos, Interfaces e Passes FFmpeg Summary

**Mapeamento exaustivo dos contratos entre Celery e `StudioService`, especificação dos DTOs internos tipados e arquitetura do grafo FFmpeg single-pass (`yuva420p` + `asplit` + `showwaves`) documentados nas Seções 1 e 4 do `08-AUDIT-REPORT.md`**

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-06T08:24:18Z
- **Completed:** 2026-11-06T08:29:05Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Auditada e documentada a assinatura pública obrigatória `StudioService.produce(db: Session, run_id: str, script: Script) -> Asset` e todas as fronteiras internas (`voice.py`, `avatar.py`, `subtitles.py`, `renderer.py`, `storage.py`), identificando acoplamentos temporais, dimensionais (`360x360` vs `340x340`) e chamadas privadas a `storage._safe`.
- Projetados os DTOs conceituais tipados (`StudioRenderRequest`, `AvatarConfig`, `SubtitleJobConfig`, `SubtitleCue`, `ReactionCompositionSpec`) para isolar a complexidade interna nas Phases 10–12 sem alterar `tasks.py`.
- Mapeados todos os subprocessos `ffmpeg` (até 5 chamadas) e `ffprobe` (até 6 chamadas, com 3 leituras redundantes de `narration.wav`) executados por run.
- Formulada a arquitetura e o grafo `filter_complex` **single-pass** para a Phase 12, eliminando os arquivos intermediários `source_visual_bg.mp4` e `avatar.mp4` (`yuv420p`), preservando transparência em memória (`yuva420p`) e garantindo saída 1080x1920 @ 24fps.

## Task Commits

Each task was committed atomically:

1. **Task 1: Auditar contratos e mapear interfaces entre Celery, StudioService e componentes de estúdio** - `2088577` (docs)
2. **Task 2: Mapear passes e grafo de filtros FFmpeg e estruturar proposta single-pass** - `8a9bb7d` (docs)

## Files Created/Modified
- `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` - Relatório técnico de auditoria da Phase 8 iniciado com as Seções 1 (Contratos, Diagrama Sequencial Mermaid e DTOs) e 4 (Inventário de Passes FFmpeg/FFprobe e Proposta Single-Pass) completas.

## Decisions Made
- **Preservação de contrato e persistência de Assets (D-01):** Manter `StudioService.produce(db, run_id, script) -> Asset` intacto e preservar a gravação dos 3 registros `Asset` (`audio`, `avatar`, `final_video`) mesmo após a unificação single-pass na Phase 12.
- **Modelagem de DTOs internos (D-02/D-03):** Adotar `StudioRenderRequest`, `AvatarConfig`, `SubtitleJobConfig`, `SubtitleCue` e `ReactionCompositionSpec` para propagar `voice_duration` (eliminando chamadas repetidas ao `ffprobe`) e parametrizar safe zones e recorte circular sem injeção excessiva.
- **Unificação Single-Pass em memória (D-12/D-13/D-14):** Substituir os passes intermediários (`source_visual_bg.mp4` e `avatar.mp4` em `yuv420p`) por entradas diretas no comando final (`lavfi` quando sem vídeo fonte e `-loop 1 -i creator_avatar.png` com máscara alfa `yuva420p` e `asplit` para `showwaves`).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Seções 1 e 4 de `08-AUDIT-REPORT.md` concluídas e verificadas.
- Pronto para o Plano `08-02-PLAN.md`, que preencherá as Seções 2 (Diagnóstico de Causa Raiz de Legendas Duplicadas), 3 (Diagnóstico de Assets e Formato do Avatar via `ffprobe`), 5 (Matriz de Decisões) e 6 (Verificação de Integridade).

## Self-Check: PASSED
- FOUND: `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md`
- FOUND: `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-01-SUMMARY.md`
- FOUND COMMIT: `2088577`
- FOUND COMMIT: `8a9bb7d`
- VERIFIED: `git status --porcelain src/` vazio (zero modificações em código de produção)

---
*Phase: 08-auditoria-contratos-e-diagn-stico-de-causa-raiz*
*Completed: 2026-11-06*
