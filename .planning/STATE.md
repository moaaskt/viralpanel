---
gsd_state_version: "1.0"
milestone: v1.1
milestone_name: ZUNTO! Visual Engine
current_phase: 08
current_phase_name: Auditoria, Contratos e Diagnóstico de Causa Raiz
status: verifying
stopped_at: Completed 08-02-PLAN.md
last_updated: "2026-11-06T08:42:09.568Z"
last_activity: 2026-11-06
last_activity_desc: Phase 08 execution started
state_head: 4fcbd3523994efbc4a8dc77ee177277d5bbd871a
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 2
  completed_plans: 2
  percent: 0
---

# Project State

## Project Reference

See: [.planning/PROJECT.md](file:///.planning/PROJECT.md) (updated 2026-11-06)

**Core value:** Refatorar e aprimorar o pipeline de geração e composição audiovisual, elevando a qualidade dos vídeos produzidos automaticamente pelo sistema com a identidade visual ZUNTO!.  
**Current focus:** Phase 08 — Auditoria, Contratos e Diagnóstico de Causa Raiz

## Current Position

Phase: 08 (Auditoria, Contratos e Diagnóstico de Causa Raiz) — EXECUTING
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-11-06 — Phase 08 execution started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 08 P01 | 5min | 2 tasks | 1 files |
| Phase 08 P02 | 10min | 2 tasks | 1 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session

**Last session:** 2026-11-06T08:42:09.543Z
**Stopped at:** Completed 08-02-PLAN.md
**Resume file:** None
