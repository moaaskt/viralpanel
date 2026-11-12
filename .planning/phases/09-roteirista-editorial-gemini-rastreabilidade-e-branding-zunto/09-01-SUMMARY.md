---
phase: 09-roteirista-editorial-gemini-rastreabilidade-e-branding-zunto
plan: 01
subsystem: branding
tags: [branding, palette, safe-zones, ass, color-converter, libass, 9x16]

# Dependency graph
requires: []
provides:
  - "Módulo central de identidade visual ZUNTO! em src/viralpanel/branding.py (ZuntoPalette, ZuntoTypography, SafeZones9x16, BrandGuidelines)"
  - "Conversor matemático testado hex_to_ass_color (&HAABBGGRR&) para prevenir inversão de canais no libass/FFmpeg"
  - "Safe zones 9:16 calibradas para 1080x1920 (MarginV=640 para legendas e avatar em Y=1320-1660px)"
affects:
  - 09-02
  - 10-motor-de-legendas-zunto-e-desacoplamento
  - 11-avatar-reaction-e-composi-o-visual-org-nica
  - 12-refatora-o-do-video-composer-ffmpeg-e-integra-o

# Actuals (#2632)
actuals:
  tokens: 2142
  tasks: 2
  commits: 2
plan_head_before: 192eba506c18af48780567468d7afc4d1cd80e2b
plan_head_after: 5f1e7ad0c609ddb5fea51467c90a637e164e0d68

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Constantes de marca em dataclasses imutáveis (frozen=True) e atributos Final"
    - "Conversão de espaço de cores Hex (#RRGGBB) para ASS BGR (&HAABBGGRR&) com validação rigorosa"
    - "Centralização de safe zones 9:16 calibradas para TikTok, Instagram Reels e YouTube Shorts"

key-files:
  created:
    - src/viralpanel/branding.py
    - tests/test_branding.py
  modified: []

key-decisions:
  - "Centralizar a paleta oficial ZUNTO! (#0A0A0A, #FACC15, #FFFFFF, #1A1A1A) e safe zones em src/viralpanel/branding.py como fonte única de verdade (D-09, D-10)"
  - "Utilizar classes imutáveis com tipos Final para prevenir mutações acidentais em tempo de execução"
  - "Implementar e testar hex_to_ass_color com suporte a canais alpha e tratamento estrito de exceção ValueError para strings hex inválidas (D-11, T-09-01)"

patterns-established:
  - "Conversão BGR segura para ASS: &HAABBGGRR& evitando inversão de amarelo para ciano no libass"
  - "SafeZones9x16 alinhadas com as margens mobile da Phase 8 (MarginV=640 para legendas em Y=1080-1280px)"

requirements-completed:
  - BRND-01
  - BRND-02

coverage:
  - id: D1
    description: "Paleta de cores oficial ZUNTO! (ZuntoPalette) e conversor matemático hex_to_ass_color"
    requirement: BRND-01
    verification:
      - kind: unit
        ref: "tests/test_branding.py::test_zunto_palette_constants"
        status: pass
      - kind: unit
        ref: "tests/test_branding.py::test_hex_to_ass_color_zunto_palette"
        status: pass
      - kind: unit
        ref: "tests/test_branding.py::test_hex_to_ass_color_alpha_support"
        status: pass
      - kind: unit
        ref: "tests/test_branding.py::test_hex_to_ass_color_invalid_input"
        status: pass
    human_judgment: false
  - id: D2
    description: "SafeZones9x16 para 1080x1920 (MarginV=640), ZuntoTypography e BrandGuidelines com slogan oficial"
    requirement: BRND-02
    verification:
      - kind: unit
        ref: "tests/test_branding.py::test_safe_zones_9x16_constants"
        status: pass
      - kind: unit
        ref: "tests/test_branding.py::test_zunto_typography_constants"
        status: pass
      - kind: unit
        ref: "tests/test_branding.py::test_brand_guidelines_constants"
        status: pass
    human_judgment: false

# Metrics
duration: 4min
completed: 2026-11-06
status: complete
---

# Phase 09 Plan 01: Identidade Visual ZUNTO! e Conversão ASS Summary

**Centralização da identidade de marca ZUNTO! em `src/viralpanel/branding.py` com paleta oficial, safe zones 9:16 calibradas (MarginV=640) e conversor de cores ASS BGR prevenindo bugs de libass.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-06T06:17:16Z
- **Completed:** 2026-11-06T06:21:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Criada suíte completa de testes unitários TDD em `tests/test_branding.py` cobrindo paleta, tipografia, safe zones 9:16, diretrizes de marca e conversão de cores ASS BGR com validação contra entradas inválidas.
- Implementado `src/viralpanel/branding.py` contendo `ZuntoPalette`, `ZuntoTypography`, `SafeZones9x16`, `BrandGuidelines` e `hex_to_ass_color`.
- Validada a inversão de canais BGR do libass (`#FACC15` -> `&H0015CCFA&`), prevenindo a distorção visual onde o amarelo característico da marca se tornaria ciano no FFmpeg.
- 100% de sucesso nos testes da suíte (`pytest tests/test_branding.py -v` e `pytest tests/ -v`, com 62 testes aprovados sem regressões).

## Task Commits

Cada tarefa foi commitada individualmente seguindo a convenção de commits semânticos:

1. **Task 1: Criar suíte de testes unitários de Branding e Conversão ASS (`tests/test_branding.py`)** - `29b8ff1` (test)
2. **Task 2: Implementar módulo central de identidade visual ZUNTO! (`src/viralpanel/branding.py`)** - `5f1e7ad` (feat)

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] Arquivo criado: `src/viralpanel/branding.py`
- [x] Arquivo criado: `tests/test_branding.py`
- [x] Commit verificado: `29b8ff1`
- [x] Commit verificado: `5f1e7ad`
- [x] 62 testes unitários passando no pytest sem regressões
