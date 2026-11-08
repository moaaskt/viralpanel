---
phase: 11-avatar-reaction-e-composicao-visual-organica
plan: 02
subsystem: studio
tags:
  - ffmpeg
  - renderer
  - reaction
  - overlay
  - safezones
  - branding
  - subtitles
  - alpha
requires:
  - phase: 11-avatar-reaction-e-composicao-visual-organica
    plan: "01"
    provides: AudioReactiveAvatarAnimator com recorte circular, canal alfa e SafeZones9x16 calibrada
provides:
  - ReactionVideoRenderer atualizado com avatar_size=300 padrão alinhado a SafeZones9x16.AVATAR_SIZE
  - Remoção definitiva do filtro pad de moldura retangular branca (Cenário 3 do 08-AUDIT-REPORT.md)
  - Calibração do overlay em W-w-54:H-h-320 estritamente dentro da safe zone vertical (faixa Y=1300..1600px)
  - Composição PIP preservando transparência do canal alfa e anel amarelo ZUNTO! (#FACC15)
  - Teste empírico de composição em fundo contrastante magenta com amostragem de pixels rawvideo rgb24
  - Suíte completa do repositório com 86/86 testes verdes (100% sem regressão)
affects:
  - src/viralpanel/studio/renderer.py
  - tests/test_studio_renderer.py
actuals:
  tokens: 2850
  tasks: 2
  commits: 2
plan_head_before: 6d6da0ae0e5eecbb8a389f87608d1b2a07af9724
plan_head_after: 69d45e5c1d23f88f94a02e1532b0f520ded35ae3
tech-stack:
  added: []
  patterns:
    - FFmpeg PIP overlay with alpha channel preservation
    - Rawvideo RGB24 composition pixel sampling assertions
key-files:
  created: []
  modified:
    - src/viralpanel/studio/renderer.py
    - tests/test_studio_renderer.py
key-decisions:
  - "Eliminação total do filtro pad de moldura retangular branca em ReactionVideoRenderer, resolvendo Cenário 3 da auditoria"
  - "Posicionamento do overlay PIP em W-w-54:H-h-320 (X=726..1026, Y=1300..1600), isolando a zona de legendas (1080..1280px) e desobstruindo a barra inferior mobile (Y>=1600px)"
  - "Decodificação direta do avatar com codec png/rgba sobre o background mantendo o canal alfa contínuo sem caixas opacas"
patterns-established:
  - "Composição 9:16 com preservação de alfa via overlay=W-w-54:H-h-320:shortest=1 sem filtros opacos intermediários"
  - "Verificação empírica de ausência de caixas e molduras através de renderização sobre fundo magenta contrastante e análise de pixels RGB"
requirements-completed:
  - AVTR-01
  - AVTR-02
  - BRND-01
  - BRND-02
coverage:
  - id: D1
    description: "ReactionVideoRenderer adota avatar_size=300 padrão de SafeZones9x16 per D-03 e BRND-02"
    requirement: "BRND-02"
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py#test_reaction_renderer_single_ass_layer_and_path_escape"
        status: pass
    human_judgment: false
  - id: D2
    description: "Filtro pad retangular branco completamente removido de filter_complex per D-02 e AVTR-01"
    requirement: "AVTR-01"
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py#test_reaction_renderer_single_ass_layer_and_path_escape"
        status: pass
      - kind: unit
        ref: "tests/test_studio_renderer.py#test_avatar_reaction_overlay_pixel_transparency_and_no_white_box"
        status: pass
    human_judgment: false
  - id: D3
    description: "Overlay posicionado em W-w-54:H-h-320 sem colidir com legendas ou barra inferior de plataformas per D-03 e AVTR-02"
    requirement: "AVTR-02"
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py#test_reaction_renderer_single_ass_layer_and_path_escape"
        status: pass
      - kind: unit
        ref: "tests/test_studio_renderer.py#test_avatar_reaction_overlay_pixel_transparency_and_no_white_box"
        status: pass
    human_judgment: false
  - id: D4
    description: "Preservação de canal alfa contínuo e anel amarelo ZUNTO! (#FACC15) no vídeo composto final per D-01 e BRND-01"
    requirement: "BRND-01"
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py#test_avatar_reaction_overlay_pixel_transparency_and_no_white_box"
        status: pass
    human_judgment: false
duration: 4min
completed: 2026-11-07
status: complete
---

# Phase 11 Plan 02: Integração do Avatar Reaction e Composição Visual 9:16 Summary

**Integração do avatar reaction circular orgânico em ReactionVideoRenderer com avatar_size=300, remoção definitiva da moldura retangular branca (Cenário 3 da auditoria), overlay posicionado em W-w-54:H-h-320 estritamente dentro da safe zone vertical e validação empírica de pixels em frame 1080x1920 com 86 testes verdes.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-07T23:25:20-03:00
- **Completed:** 2026-11-07T23:29:10-03:00
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- **ReactionVideoRenderer alinhado com SafeZones9x16:** Importação oficial de `SafeZones9x16` de `viralpanel.branding`, calibrando `avatar_size=300` como parâmetro padrão do construtor e garantindo proporção e posicionamento harmoniosos com o design system ZUNTO!.
- **Remoção definitiva da moldura retangular branca:** O filtro `pad={self.avatar_size + 12}:{self.avatar_size + 12}:6:6:color=white` foi completamente eliminado do `filter_complex`, sanando definitivamente o Cenário 3 do `08-AUDIT-REPORT.md`.
- **Posicionamento calibrado na safe zone vertical:** Overlay posicionado em `W-w-54:H-h-320` (`[bg][pip]overlay=W-w-54:H-h-320:shortest=1`), enquadrando o PIP de 300x300 nas coordenadas cartesianas X entre 726px e 1026px e Y entre 1300px e 1600px, mantendo margem segura de 20px com a zona de legendas ZUNTO! (Y=1080..1280px) e desobstruindo integralmente os 320px inferiores para a interface mobile de TikTok, Reels e Shorts.
- **Preservação de canal alfa em composição de vídeo:** Decodificação de `avatar.mp4` (codec png / pix_fmt rgba) sobre o vídeo base preserva a transparência nativa dos cantos externos sem artefatos ou caixas pretas/opacas.
- **Teste empírico de composição de pixels:** `test_avatar_reaction_overlay_pixel_transparency_and_no_white_box` implementado em `tests/test_studio_renderer.py`, renderizando vídeo final completo sobre fundo magenta puro (#FF00FF) e inspecionando pixels em `rawvideo rgb24`:
  * Cantos superior esquerdo (736, 1310) e inferior externo (736, 1590): Magenta puro preservado (Alpha transparente).
  * Ponto da antiga moldura (726, 1300): Não é branco puro e exibe o fundo magenta transparente.
  * Borda circular anelar nos 4 pontos cardeais (topo, base, esquerda, direita): Amarelo de Impacto ZUNTO! (#FACC15 / R>210, G>170, B<70) contínuo.
  * Centro do avatar (876, 1450): Exibe a figura do avatar sem vazamento do fundo.
- **Zero regressões na suíte global:** Todos os 86 testes do repositório passam com 100% de sucesso.

## Task Commits

Cada task foi executada e commitada atomicamente:

1. **Task 1: Atualizar ReactionVideoRenderer para avatar_size=300, remover pad branco e calibrar overlay em safe zone** - `0c54675` (feat)
2. **Task 2: Atualizar testes do renderer com validação empírica de pixels da composição e garantir zero regressão** - `69d45e5` (test)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. A composição 9:16 com avatar reaction circular e legendas ASS está totalmente integrada e operacional em produção.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| None | N/A | Nenhuma nova superfície de ataque externa introduzida. Filtro FFmpeg estruturado a partir de constantes numéricas validadas e tipadas em SafeZones9x16. |

## Verification Results

- `tests/test_studio_renderer.py`: 5/5 passed
- Total suíte do projeto: 86/86 passed (0 regressões)

## Self-Check: PASSED
- `src/viralpanel/studio/renderer.py`: FOUND
- `tests/test_studio_renderer.py`: FOUND
- Commit `0c54675`: FOUND
- Commit `69d45e5`: FOUND
