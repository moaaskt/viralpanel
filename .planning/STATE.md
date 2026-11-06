---
gsd_state_version: "1.0"
milestone: v1.1
milestone_name: ZUNTO! Visual Engine
current_phase: 10
current_phase_name: Motor de Legendas ZUNTO! e Desacoplamento
current_plan: 0
status: ready
stopped_at: Completed Phase 09 and verification
last_updated: "2026-11-06T09:38:00.000Z"
last_activity: 2026-11-06
last_activity_desc: Phase 09 verified and complete (14/14 checks passed, 67 tests passing)
state_head: 7a1879a
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 33
---

# Project State

## Project Reference

See: [.planning/PROJECT.md](file:///.planning/PROJECT.md) (updated 2026-11-06)

**Core value:** Refatorar e aprimorar o pipeline de geração e composição audiovisual, elevando a qualidade dos vídeos produzidos automaticamente pelo sistema com a identidade visual ZUNTO!.  
**Current focus:** Phase 10 — Motor de Legendas ZUNTO! e Desacoplamento

## Current Position

Phase: 10 — Motor de Legendas ZUNTO! e Desacoplamento
Current Plan: 0
Total Plans in Phase: TBD
Status: Ready for discuss/plan phase 10
Last activity: 2026-11-06 — Completed Phase 09 (Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO!)

Progress: [████░░░░░░] 33%

## Performance Metrics

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 08 P01 | 5min | 2 tasks | 1 files |
| Phase 08 P02 | 10min | 2 tasks | 1 files |
| Phase 09 P01 | 4min | 2 tasks | 2 files |
| Phase 09 P02 | 6m | 3 tasks | 4 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session

**Last session:** 2026-11-06T09:30:56.977Z
**Stopped at:** Completed 09-02-PLAN.md
**Resume file:** None
