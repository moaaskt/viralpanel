# Phase 11: Avatar Reaction e Composição Visual Orgânica - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-08
**Phase:** 11-avatar-reaction-e-composicao-visual-organica
**Areas discussed:** Técnica de recorte e transparência, Estilo de moldura/contorno, Dimensão e posicionamento no layout vertical, Tratamento da onda sonora reativa

---

## 1. Técnica de recorte e transparência

| Option | Description | Selected |
|--------|-------------|----------|
| Máscara circular programática via FFmpeg (`yuva420p` / canal alfa dinâmico) | Suporta qualquer imagem (RGB opaco ou RGBA nativo) sem intervenção manual | ✓ |
| Exigir PNG pré-cortado com transparência nativa (RGBA) | Frágil perante imagens reais de criadores e fotos comuns | |
| Recorte em formato de cantos arredondados (squircle / rounded-rect) | Menos orgânico e ainda com aspecto de caixa | |

**User's choice:** Máscara circular programática via FFmpeg sobre qualquer imagem de entrada.
**Notes:** Elimina a causa raiz do adesivo quadrado diagnosticada na Phase 8, tratando simultaneamente a ausência de alfa no arquivo fonte e a destruição de alfa no encoding intermediário.

---

## 2. Estilo de moldura ou contorno

| Option | Description | Selected |
|--------|-------------|----------|
| Borda circular sutil de 3px a 4px no Amarelo de Impacto ZUNTO! (`#FACC15`) | Harmonizada com a paleta oficial da marca, destacando o avatar com elegância | ✓ |
| Sem borda externa (corte limpo direto sobre o vídeo) | Pode perder contraste em vídeos de fundo escuros/claros | |
| Borda neutra escura (`#1A1A1A`) | Menor apelo dinâmico | |

**User's choice:** Borda circular sutil de 3px a 4px no Amarelo de Impacto ZUNTO! (`#FACC15`).
**Notes:** Substitui o antigo pad retangular branco rígido de 6px por um acabamento curvo integrado ao branding ZUNTO!.

---

## 3. Dimensão e posicionamento no layout 9:16 (1080x1920)

| Option | Description | Selected |
|--------|-------------|----------|
| Tamanho 300px (diâmetro), no canto inferior direito (`X=W-w-54`, `Y=H-h-320`) | Faixa segura $Y \approx 1320\dots1620\text{px}$, sem colidir com legendas ($Y \approx 1080\dots1280$) nem com botões da rede social | ✓ |
| Tamanho menor (240px) | Menor ocupação da tela | |
| Tamanho maior (360px) | Mais intrusivo sobre o conteúdo de fundo | |

**User's choice:** Tamanho 300px posicionado em `X=W-w-54`, `Y=H-h-320`.
**Notes:** Alinhado com a Safe Zone documentada no `08-AUDIT-REPORT.md` e em `branding.py`.

---

## 4. Tratamento da onda sonora reativa (showwaves)

| Option | Description | Selected |
|--------|-------------|----------|
| Manter onda sonora reativa estilizada na cor ZUNTO! (`#FACC15@0.85`), contida dentro do círculo | Feedback visual dinâmico de fala integrado organicamente à máscara | ✓ |
| Remover a onda de áudio (avatar estático) | Menos dinamismo visual na reação | |

**User's choice:** Manter onda sonora reativa estilizada na cor ZUNTO!, contida dentro da máscara circular.
**Notes:** Correção da distorção de cor detectada na auditoria (onde a onda ficava esverdeada por conversão prematura para yuv420p).

---

## the agent's Discretion

- Expressão exata de máscara circular FFmpeg e método de anti-aliasing / suavização de bordas.
- Escolha da espessura exata da borda amarela (3px ou 4px).

## Deferred Ideas

- Nenhuma ideia adiada nesta fase.
