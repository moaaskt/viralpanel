---
phase: 08-auditoria-contratos-e-diagn-stico-de-causa-raiz
plan: 02
subsystem: studio
tags: [ffmpeg, ffprobe, subtitles, libass, avatar, alpha-channel, safe-zones, audit]

# Dependency graph
requires:
  - phase: 08-auditoria-contratos-e-diagn-stico-de-causa-raiz
    provides: "Mapeamento de contratos e passes FFmpeg (08-01)"
provides:
  - "Diagnóstico técnico e empírico conclusivo da causa raiz de legendas duplicadas (hard-subs em vídeos baixados do TikTok vs filtro ASS único) com estratégia de cobertura ZUNTO! BorderStyle=3 (Seção 2 de 08-AUDIT-REPORT.md)"
  - "Laudo empírico via ffprobe/file/RGB de todos os assets reais (assets/creator_avatar.png e storage/runs/*/assets/avatar.mp4 + final_reaction_9x16.mp4) distinguindo os 4 cenários técnicos simultâneos do artefato de caixa quadrada do avatar e mapeando safe zones 9:16 (Seção 3 de 08-AUDIT-REPORT.md)"
  - "Relatório Técnico Oficial 08-AUDIT-REPORT.md consolidado integralmente (Sumário Executivo + Seções 1 a 6) com roteiro de implementação e matriz de salvaguardas para as Phases 9 a 13"
affects:
  - 09-roteirista-editorial-gemini-rastreabilidade-e-branding-zunto
  - 10-motor-de-legendas-zunto-e-desacoplamento
  - 11-avatar-reaction-e-composi-o-visual-org-nica
  - 12-refatora-o-do-video-composer-ffmpeg-e-integra-o
  - 13-valida-o-t-cnica-automatizada-e-inspe-o-audiovisual-e2e

# Actuals (#2632)
actuals:
  tokens: 14110
  tasks: 2
  commits: 2
plan_head_before: ad64f0cbeee264a5b3c61a04c3c346cab85a5370
plan_head_after: 4fcbd3523994efbc4a8dc77ee177277d5bbd871a

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cobertura de hard-subs nativos do vídeo fonte via caixa opaca ASS (BorderStyle=3) na zona focal (MarginV=640, Y=1080..1280px)"
    - "Resolução conjunta dos 4 cenários de opacidade/caixa quadrada do avatar (asset RGBA circular + subgrafo yuva420p + remoção de pad branco + composição single-pass sem MP4 intermediário)"
    - "Zoneamento espacial 9:16 (1080x1920) isolando legendas (Y=1060..1280px), avatar reaction (Y=1320..1600px) e UI de plataformas (Y>1600px, X>880px)"

key-files:
  created: []
  modified:
    - .planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md

key-decisions:
  - "Adotar caixa opaca ASS (BorderStyle=3 com fundo #0A0A0A) posicionada em MarginV=640 (Y=1080..1280px) na Phase 10 para cobrir diretamente hard-subs nativos dos vídeos baixados do TikTok sem custo de OCR/blur"
  - "Tratar simultaneamente nas Phases 11 e 12 os 4 cenários técnicos do artefato quadrado do avatar: (1) asset fonte rgb24 opaco com drawbox, (2) format=yuv420p em avatar.py destruindo alfa e alterando a cor do showwaves para verde, (3) pad=352:352:6:6:color=white em renderer.py:128, e (4) limitação estrutural do container/codec avatar.mp4 (libx264/yuv420p) sem canal alfa"
  - "Reposicionar o avatar circular (diâmetro 280-300px) para a safe zone Y=1320..1600px (H-h-320), eliminando a colisão com as legendas ASS e com os ícones/descrições da interface do TikTok, Reels e Shorts"

patterns-established:
  - "Diagnóstico forense de mídia baseado em evidências reais (ffprobe, amostragem de pixels RGB e inspeção de frames de storage/runs/) antes de refatoração"

requirements-completed: [SUB-01, AVTR-01]

coverage:
  - id: D1
    description: "Diagnóstico de causa raiz de duplicação de legendas (hard-subs preexistentes em storage/runs/ vs filtro ASS único) e estratégia ZUNTO! (Seção 2 de 08-AUDIT-REPORT.md)"
    requirement: SUB-01
    verification:
      - kind: unit
        ref: "tests/test_studio_renderer.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Diagnóstico empírico dos 4 cenários técnicos de caixa quadrada do avatar via ffprobe em assets/creator_avatar.png e storage/runs/ e mapeamento de safe zones 9:16 (Seção 3 de 08-AUDIT-REPORT.md)"
    requirement: AVTR-01
    verification:
      - kind: other
        ref: "ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt,width,height -of json assets/creator_avatar.png"
        status: pass
      - kind: unit
        ref: "tests/test_studio_avatar.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Consolidação integral do relatório oficial 08-AUDIT-REPORT.md (Sumário Executivo e Seções 1 a 6) com zero modificações em src/viralpanel/"
    requirement: SUB-01
    verification:
      - kind: unit
        ref: ".venv/bin/pytest tests/test_studio_renderer.py tests/test_studio_avatar.py && test -z \"$(git status --porcelain src/)\""
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-11-06
status: complete
---

# Phase 08 Plan 02: Diagnóstico de Causa Raiz de Legendas e Avatar & Relatório Final Summary

**Diagnóstico empírico da colisão de hard-subs em vídeos reais do TikTok, desmontagem técnica dos 4 cenários simultâneos da caixa quadrada do avatar (`rgb24`, `avatar.py yuv420p`, `pad=white` e barreira `libx264/mp4`) e consolidação integral do `08-AUDIT-REPORT.md`**

## Performance

- **Duration:** 10 min
- **Started:** 2026-11-06T08:31:23Z
- **Completed:** 2026-11-06T08:40:56Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Comprovado que `ReactionVideoRenderer.render` aplica o filtro `ass` uma única vez (`renderer.py:130`), que `captions.ass` possui intervalos disjuntos e que os vídeos baixados não possuem trilhas soft-sub (`nb_streams: 2`); demonstrado empiricamente nos runs reais (`14f4a7a1` e `ca28df90` em `storage/runs/`) que a duplicação decorre de **hard-subs nativos queimados nos vídeos do TikTok** (`"tu tá"` em `Y≈1080px` e `"a si mesmo"` em `Y≈1144px`) exibidos simultaneamente com a legenda ASS (`MarginV=480`, `Y≈1310–1440px`), agravada pelo fatiamento cego de 6 palavras e divisão temporal linear em `subtitles.py`.
- Inspecionados todos os assets reais (`assets/creator_avatar.png` e `storage/runs/*/assets/avatar.mp4` + `final_reaction_9x16.mp4`) via `ffprobe`, `file`, amostragem RGB de pixels e extração de frames, distinguindo e comprovando os **4 cenários técnicos simultâneos** responsáveis pelo aspecto de "caixa quadrada" no avatar:
  1. **Cenário 1:** Ausência de canal alfa e geometria quadrada no arquivo original `assets/creator_avatar.png` (`512x512`, `pix_fmt: rgb24`, cantos `#0f172b`, gerado por `ensure_default_avatar_image` com 4 retângulos `drawbox`).
  2. **Cenário 2:** Destruição de transparência em `src/viralpanel/studio/avatar.py` (`format=yuv420p[base_avatar]` na linha 96 e `-pix_fmt yuv420p` na linha 120), que converte qualquer canal alfa em preto sólido antes do `overlay` e distorce a cor do `showwaves` (de `#38bdf8` para verde no `avatar.mp4` real).
  3. **Cenário 3:** Moldura branca retangular introduzida por `src/viralpanel/studio/renderer.py` na linha 128 (`pad=352:352:6:6:color=white[pip]`), criando a borda sólida branca (`#FFFFFF`) de 6px visível em `X=680..1032, Y=1448..1800`.
  4. **Cenário 4:** Limitação intrínseca do container/codec intermediário (`avatar.mp4` com `libx264` + `yuv420p`), que não suporta plano Alpha — exigindo a composição direta em memória via Single-Pass (`yuva420p`) para preservar a transparência até o `overlay` final.
- Mapeadas as **Safe Zones 9:16 (`1080x1920`)** para TikTok, Instagram Reels e YouTube Shorts e finalizado o relatório técnico oficial `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` com todas as 6 seções e o Sumário Executivo.

## Task Commits

Each task was committed atomically:

1. **Task 1: Auditar causas de duplicação de legendas e analisar formato e artefatos dos assets de avatar** - `f864b99` (docs)
2. **Task 2: Consolidar e finalizar o relatório técnico oficial 08-AUDIT-REPORT.md** - `4fcbd35` (docs)

## Files Created/Modified
- `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` - Relatório técnico definitivo da Phase 8 contendo Sumário Executivo e Seções 1 a 6 completas.

## Decisions Made
- **Cobertura de Hard-Subs com Caixa Opaca ZUNTO! (`BorderStyle=3`):** Na Phase 10, posicionar as legendas ASS com `BorderStyle=3` (fundo opaco `#0A0A0A`) na faixa `MarginV=640` (`Y ≈ 1080–1280px`), cobrindo diretamente a região onde os vídeos baixados do TikTok trazem hard-subs queimadas e dispensando OCR/blur pesado.
- **Tratamento Conjunto dos 4 Cenários do Avatar (Phases 11 e 12):** Tratar de forma coordenada o asset fonte (`rgba` circular com anel `#FACC15`), o espaço de pixel em memória (`yuva420p` no avatar e `showwaves`), a remoção do `pad=...color=white` em `renderer.py:128` e a eliminação do `avatar.mp4` (`libx264/yuv420p`) intermediário via grafo Single-Pass.
- **Calibração de Safe Zones 9:16 (`1080x1920`):** Separar verticalmente a zona de legendas (`Y = 1060–1280px`, `MarginR = 200`) da zona do avatar circular (`280–300px` em `Y = 1320–1600px`, `H-h-320`), evitando colisão mútua e fugindo das áreas obstruídas pela UI do TikTok/Reels/Shorts (`Y > 1600px` e `X > 880px`).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 8 concluída integralmente com 100% dos requisitos diagnósticos (`COMP-01`, `SUB-01`, `AVTR-01`) comprovados e documentados em `08-AUDIT-REPORT.md` e zero linhas modificadas em `src/viralpanel/` ou `assets/`.
- Pronto para iniciar a **Phase 9 (Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO!)**.

## Self-Check: PASSED
- FOUND: `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md`
- FOUND: `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-02-SUMMARY.md`
- FOUND COMMIT: `f864b99`
- FOUND COMMIT: `4fcbd35`
- VERIFIED: `git status --porcelain src/ assets/` vazio (zero modificações em código de produção e assets)

---
*Phase: 08-auditoria-contratos-e-diagn-stico-de-causa-raiz*
*Completed: 2026-11-06*
