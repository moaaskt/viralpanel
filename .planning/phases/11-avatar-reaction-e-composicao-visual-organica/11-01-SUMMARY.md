---
phase: 11-avatar-reaction-e-composicao-visual-organica
plan: 01
subsystem: studio
tags:
  - ffmpeg
  - avatar
  - reaction
  - showwaves
  - alpha
  - geq
  - safezones
  - branding
requires:
  - phase: 08-auditoria-contratos-e-diagn-stico-de-causa-raiz
    provides: Diagnóstico de causas raiz de enquadramento e transparência
  - phase: 09-padronizacao-identidade-visual-e-safe-zones
    provides: Módulo central de branding ZUNTO! e SafeZones9x16
provides:
  - Calibração de SafeZones9x16 com AVATAR_SIZE=300, AVATAR_MARGIN_RIGHT=54 e AVATAR_MARGIN_BOTTOM=320
  - DTO imutável AvatarConfig em avatar.py
  - AudioReactiveAvatarAnimator com recorte circular anti-aliased em filtro geq e anel amarelo ZUNTO! (#FACC15)
  - Confinamento interno da onda sonora reativa showwaves
  - Preservação de canal alfa em avatar.mp4 intermediário com codec png em pix_fmt rgba
  - Suíte de testes empíricos de amostragem de pixels e metadados de stream
affects:
  - 11-02-PLAN.md
  - src/viralpanel/studio/renderer.py
actuals:
  tokens: 4193
  tasks: 3
  commits: 3
plan_head_before: 853f8a85f48a62158f05f24b31fba0f9fc3b7aa1
plan_head_after: edf8a798e59f2dd4f140b850df81778ac4bdeff3
tech-stack:
  added: []
  patterns:
    - FFmpeg radial geq alpha masking
    - Rawvideo RGBA pixel sampling assertions
key-files:
  created: []
  modified:
    - src/viralpanel/branding.py
    - src/viralpanel/studio/avatar.py
    - tests/test_branding.py
    - tests/test_studio_avatar.py
key-decisions:
  - "Calibração de SafeZones9x16 com size=300, margin_right=54 e margin_bottom=320 para isolar a zona vertical de legendas (1080..1280px)"
  - "Utilização do codec de vídeo png em pix_fmt rgba dentro do container MP4 para transporte sem perdas de canal alfa"
  - "Confinamento geométrico de showwaves (#FACC15@0.85) antes da máscara circular geq, prevenindo vazamento e caixas pretas opacas"
patterns-established:
  - "Filtro geq com equações radiais para r, g, b, a para renderização sub-pixel de anel colorido e canal alfa"
  - "Inspeção empírica de bytes rawvideo RGBA para validação de transparência e cores de renderização"
requirements-completed:
  - AVTR-01
  - AVTR-03
  - BRND-01
  - BRND-02
coverage:
  - id: D1
    description: "SafeZones9x16 calibrada com AVATAR_SIZE=300, MARGIN_RIGHT=54 e MARGIN_BOTTOM=320 per D-03"
    requirement: "BRND-02"
    verification:
      - kind: unit
        ref: "tests/test_branding.py#test_safe_zones_9x16_constants"
        status: pass
    human_judgment: false
  - id: D2
    description: "DTO tipado e imutável AvatarConfig implementado com valores padrão da paleta ZUNTO! per D-05"
    requirement: "BRND-01"
    verification:
      - kind: unit
        ref: "tests/test_studio_avatar.py#test_avatar_config_defaults_and_immutability"
        status: pass
    human_judgment: false
  - id: D3
    description: "AudioReactiveAvatarAnimator gera avatar.mp4 com codec png em pix_fmt rgba preservando canal alfa per D-01 e AVTR-03"
    requirement: "AVTR-03"
    verification:
      - kind: unit
        ref: "tests/test_studio_avatar.py#test_avatar_video_codec_and_pixel_format"
        status: pass
    human_judgment: false
  - id: D4
    description: "Recorte circular anti-aliased com borda amarela ZUNTO! (#FACC15) e onda sonora confinada sem retângulo preto per D-01, D-02 e D-04"
    requirement: "AVTR-01"
    verification:
      - kind: unit
        ref: "tests/test_studio_avatar.py#test_avatar_circular_alpha_and_yellow_border_pixels"
        status: pass
      - kind: unit
        ref: "tests/test_studio_avatar.py#test_showwaves_background_transparency"
        status: pass
    human_judgment: false
duration: 7min
completed: 2026-11-07
status: complete
---

# Phase 11 Plan 01: Núcleo do Avatar Reaction Orgânico e Safe Zones Summary

**Recorte circular programático com canal alfa contínuo, anel de borda de 4px em Amarelo de Impacto (#FACC15), confinamento de onda reativa e codec png/rgba implementados em AudioReactiveAvatarAnimator com calibração de SafeZones9x16 e cobertura empírica de amostragem de pixels.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-07T23:15:58-03:00
- **Completed:** 2026-11-07T23:23:00-03:00
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- **SafeZones9x16 calibrada:** Constantes de posicionamento do avatar atualizadas para `AVATAR_SIZE=300`, `AVATAR_MARGIN_RIGHT=54` e `AVATAR_MARGIN_BOTTOM=320` em `src/viralpanel/branding.py`, enquadrando a reação na faixa vertical Y=1300..1600px sem obstruir legendas ou a UI móvel.
- **DTO AvatarConfig imutável:** Introduzido em `src/viralpanel/studio/avatar.py` com tipagem estrita, congelamento de instância e valores padrão oficiais ZUNTO!.
- **Recorte circular anti-aliased e anel amarelo (#FACC15):** Filtro matemático radial `geq` no pipeline FFmpeg renderiza contorno nítido de 4px no raio 146..150px e canal alfa contínuo com atenuação sub-pixel de 1px nos 300x300 pixels.
- **Confinamento da onda sonora reativa:** `showwaves` integrado diretamente sobre a base em espaço `format=rgba` antes da aplicação do recorte circular, eliminando caixas pretas opacas e vazamentos para fora do círculo.
- **Stream transparente intermediário:** `avatar.mp4` gerado com codec de vídeo `png` em `pix_fmt rgba`, garantindo canal alfa íntegro para downstream compositors.
- **Bateria de testes empíricos de pixels:** Validações em `rawvideo rgba` comprovando Alpha == 0 nos cantos externos, Alpha > 200 e coloração Amarelo ZUNTO! na borda anelar, preservação de fundo azul sem degradação na região do showwaves e 85 testes globais verdes no repositório.

## Task Commits

Cada task foi executada e commitada atomicamente:

1. **Task 1: Sincronizar SafeZones9x16 em branding.py, definir DTO AvatarConfig em avatar.py e estabelecer teste tracer** - `0ea994d` (feat)
2. **Task 2: Implementar recorte circular com canal alfa, borda amarela ZUNTO! e codec png em AudioReactiveAvatarAnimator** - `e63f710` (feat)
3. **Task 3: Desenvolver testes empíricos de pixels, canal alfa e confinamento do showwaves em test_studio_avatar.py** - `edf8a79` (test)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. Todos os métodos, classes e configurações estão plenamente implementados e integrados.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| None | N/A | Nenhuma nova superfície de ataque externa introduzida. Resolução e sanitização estrita de caminhos (`Path.resolve()`) e invocação segura sem shell (`shell=False`) mantidas. |

## Verification Results

- `tests/test_branding.py`: 7/7 passed
- `tests/test_studio_avatar.py`: 7/7 passed
- Total suíte do projeto: 85/85 passed (0 regressões)

## Self-Check: PASSED
- `src/viralpanel/branding.py`: FOUND
- `src/viralpanel/studio/avatar.py`: FOUND
- `tests/test_branding.py`: FOUND
- `tests/test_studio_avatar.py`: FOUND
- Commit `0ea994d`: FOUND
- Commit `e63f710`: FOUND
- Commit `edf8a79`: FOUND
