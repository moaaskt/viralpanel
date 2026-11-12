---
phase: 13-valida-o-t-cnica-automatizada-e-inspe-o-audiovisual-e2e
plan: 01
subsystem: studio
tags:
  - ffprobe
  - ffmpeg
  - validator
  - quality-gate
  - pixel-sampling
  - alpha-transparency
  - fractions
requires:
  - phase: 11-avatar-reaction-e-composicao-visual-organica
    provides: AudioReactiveAvatarAnimator com codec png em pix_fmt rgba e borda #FACC15
  - phase: 12-refatoracao-do-video-composer-ffmpeg-e-integracao
    provides: ReactionVideoRenderer single-pass 1080x1920 24fps H.264/AAC
provides:
  - MediaQualityValidator determinístico com probe JSON estruturado via FFprobe
  - parse_frame_rate baseado em fractions.Fraction para interpretação matemática de avg_frame_rate e r_frame_rate
  - resolve_duration com fallback documentado (stream -> format) e reprovação estrita quando indeterminável
  - validate_avatar_asset auditando o formato real da Phase 11 (png / rgba 300x300)
  - inspect_composed_avatar_transparency com amostragem dos 4 cantos + malha distribuída (~108 pontos externos ao círculo) e verificação da borda amarela ZUNTO! (#FACC15)
affects:
  - 13-02-PLAN.md
  - src/viralpanel/studio/inspection.py
actuals:
  tokens: 8350
  tasks: 2
  commits: 2
plan_head_before: 2f1dd68c42869aaa0445c60c39f3643509ac3aef
plan_head_after: ef02302
tech-stack:
  added: []
  patterns:
    - Rational frame rate parsing via fractions.Fraction
    - Cascading duration resolution with fail-closed validation
    - Multi-point exterior spandrel mesh pixel sampling in rawvideo rgb24
key-files:
  created:
    - src/viralpanel/studio/validator.py
    - tests/test_media_validator.py
  modified: []
key-decisions:
  - "Interpretação racional de FPS via fractions.Fraction com suporte a avg_frame_rate e fallback para r_frame_rate, evitando comparações simplistas de strings"
  - "Resolução de duração em cascata (stream.duration -> format.duration) levantando ValueError explícito quando ausente, impedindo aprovações silenciosas"
  - "Validação do asset intermediário de avatar alinhada ao formato real da Phase 11 (codec png e pix_fmt rgba em 300x300)"
  - "Amostragem combinada dos 4 cantos de linha de base + malha distribuída (~108 pontos na região externa ao círculo dentro da bounding box 300x300) para detectar tanto caixas opacas inteiras quanto defeitos parciais localizados"
patterns-established:
  - "Inspeção de pixels pós-composição via FFmpeg rawvideo rgb24 com tolerância documentada para absorver quantização YUV420p sem mascarar artefatos"
requirements-completed:
  - QUAL-01
coverage:
  - id: D1
    description: "MediaQualityValidator valida container MP4 1080x1920 (9:16), H.264/yuv420p, AAC >= 44100Hz, FPS racional via Fraction e coerência de duração com fallback estrito"
    requirement: "QUAL-01"
    verification:
      - kind: unit
        ref: "tests/test_media_validator.py#test_parse_frame_rate"
        status: pass
      - kind: unit
        ref: "tests/test_media_validator.py#test_resolve_duration_fallback_and_error"
        status: pass
      - kind: integration
        ref: "tests/test_media_validator.py#test_validate_rendered_video_with_real_ffmpeg"
        status: pass
    human_judgment: false
  - id: D2
    description: "Auditoria do asset de avatar (png/rgba) e inspeção de pixels na composição final (4 cantos + malha distribuída externa + anel #FACC15)"
    requirement: "QUAL-01"
    verification:
      - kind: integration
        ref: "tests/test_media_validator.py#test_validate_avatar_asset_format"
        status: pass
      - kind: integration
        ref: "tests/test_media_validator.py#test_inspect_composed_avatar_transparency"
        status: pass
    human_judgment: false
duration: 8min
completed: 2026-11-12
status: complete
---

# Phase 13 Plan 01: MediaQualityValidator e Suíte de Validação de Mídia Summary

**Validador determinístico `MediaQualityValidator` implementado com parsing racional de FPS via `Fraction`, resolução de duração em cascata sem aprovação silenciosa, auditoria do formato real do avatar (`png`/`rgba`) e amostragem multi-ponto de pixels na composição final.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-12T00:01:00-03:00
- **Completed:** 2026-11-12T00:09:34-03:00
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- **Parsing Racional de FPS (`parse_frame_rate`):** Converte strings racionais do FFprobe (`"24/1"`, `"24000/1001"`) usando `fractions.Fraction`, avaliando `avg_frame_rate` e `r_frame_rate` numericamente com tolerância controlada.
- **Resolução Estrita de Duração (`resolve_duration`):** Prioriza `stream.duration` com fallback documentado para `format.duration` e levanta `ValueError` caso ambos estejam ausentes ou inválidos, eliminando aprovações silenciosas.
- **Auditoria do Formato Real do Avatar (`validate_avatar_asset`):** Verifica que o asset gerado pelo `AudioReactiveAvatarAnimator` da Phase 11 preserva `codec_name="png"`, `pix_fmt="rgba"` e dimensões `300x300`.
- **Inspeção de Pixels em Malha Distribuída (`inspect_composed_avatar_transparency`):** Extrai frame em `rawvideo rgb24` do vídeo final composto e inspeciona tanto os 4 cantos da bounding box `[726..1026, 1300..1600]` quanto uma malha espacial distribuída de ~108 pontos externos ao círculo (`hypot >= 155`), detectando tanto caixas opacas inteiras quanto defeitos opacos parciais localizados entre os cantos, além de confirmar o anel amarelo ZUNTO! (`#FACC15`).

## Task Commits

Cada task foi executada e commitada atomicamente:

1. **Task 1: Implementar MediaQualityValidator com parsing fracionário, fallback estrito de duração e inspeção de pixels** - `ab944db` (feat)
2. **Task 2: Desenvolver testes unitários e de integração com cobertura de anomalias e frame sampling** - `ef02302` (test)

## Files Created/Modified

- `src/viralpanel/studio/validator.py` - Implementação de `MediaQualityValidator`, `ValidationResult`, `MediaStreamInfo`, `PixelInspectionResult`, `parse_frame_rate` e `resolve_duration`.
- `tests/test_media_validator.py` - 5 testes unitários e de integração cobrindo frações de FPS, cascata de duração, validação de avatar `png`/`rgba`, anomalias de stream e amostragem de pixels (incluindo detecção de defeito parcial localizado).

## Decisions Made

- **Malha distribuída externa confinada à bounding box do avatar (`Y in [1300, 1600]`):** Como a caixa opaca de legendas ASS (`#0A0A0A` em `MarginV=640` com `Outline=16`) se estende até `Y=1296px`, a amostragem externa do avatar opera estritamente dentro da bounding box `X in [726, 1026], Y in [1300, 1600]` com `hypot >= 155px`, inspecionando 108 pontos distribuídos nos 4 quadrantes externos ao círculo sem colidir com a zona de legendas.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Instalação do FFmpeg 9.0.2 no ambiente local para execução real dos testes de mídia**
- **Found during:** Task 2 (`tests/test_media_validator.py`)
- **Issue:** O binário `ffmpeg`/`ffprobe` não estava disponível no PATH do ambiente Windows, causando skip nos testes empíricos de FFprobe e amostragem de pixels.
- **Fix:** Instalado `Gyan.FFmpeg` via Winget e disponibilizados `ffmpeg.exe` e `ffprobe.exe` para o ambiente virtual `.venv\Scripts\`.
- **Files modified:** Ambiente local (`.venv/Scripts/ffmpeg.exe`, `.venv/Scripts/ffprobe.exe` - ignorados pelo git)
- **Verification:** Todos os 5 testes de `tests/test_media_validator.py` executaram de ponta a ponta sem nenhum skip (`5 passed in 3.78s`).

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking environment tool)
**Impact on plan:** Essencial para execução real de FFmpeg/FFprobe sem mocks artificiais. Nenhum desvio de escopo.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `MediaQualityValidator` pronto e validado para ser consumido pelo `InspectionRunner`, CLI `validate-e2e` e suíte de regressão no Plan `13-02`.

## Self-Check: PASSED
- `src/viralpanel/studio/validator.py`: FOUND
- `tests/test_media_validator.py`: FOUND
- Commit `ab944db`: FOUND
- Commit `ef02302`: FOUND

