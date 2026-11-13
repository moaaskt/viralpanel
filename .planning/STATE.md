---
gsd_state_version: "1.0"
milestone: v1.1
milestone_name: ZUNTO! Visual Engine
current_phase: 13
current_phase_name: Validação Técnica Automatizada e Inspeção Audiovisual E2E
current_plan: 2
status: executing
stopped_at: Completed 13-01-PLAN.md
last_updated: "2026-11-12T03:10:35.579Z"
last_activity: 2026-11-11
last_activity_desc: Phase 13 execution started
state_head: ef0230208f58b50e2f8b1b79ec52933e3319e467
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 12
  completed_plans: 12
  percent: 83
---

# Project State

## Project Reference

See: [.planning/PROJECT.md](file:///.planning/PROJECT.md) (updated 2026-11-06)

**Core value:** Refatorar e aprimorar o pipeline de geração e composição audiovisual, elevando a qualidade dos vídeos produzidos automaticamente pelo sistema com a identidade visual ZUNTO!.  
**Current focus:** Phase 13 — Validação Técnica Automatizada e Inspeção Audiovisual E2E

## Current Position

Phase: 13 (Validação Técnica Automatizada e Inspeção Audiovisual E2E) — EXECUTING
Current Plan: 2
Total Plans in Phase: 2
Status: Ready to execute
Last activity: 2026-11-11 — Phase 13 execution started

Progress: [████████░░] 83%

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
- [Phase 12-refatoracao-do-video-composer-ffmpeg-e-integracao]: Definição de StudioRenderRequest (frozen) encapsulando run_id, caminhos de assets e durações com conversão automática para Path em __post_init__
- [Phase 12-refatoracao-do-video-composer-ffmpeg-e-integracao]: Preservação integral da assinatura pública StudioService.produce(self, db: Session, run_id: str, script: Script) -> Asset e persistência atômica dos 3 assets ('audio', 'avatar', 'final_video')
- [Phase 12-refatoracao-do-video-composer-ffmpeg-e-integracao]: Ordenação de camadas FFmpeg mantida: base [0:v] -> overlay avatar PIP [1:v] -> legendas ASS com caixa opaca [composed] -> saída [vout] com -shortest

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

### Roadmap Evolution

- Phase 14 added: Formalização da Coleta e Scraper (Retrospectiva)

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session

**Last session:** 2026-11-12T03:10:35.498Z
**Stopped at:** Completed 13-01-PLAN.md
**Resume file:** None
