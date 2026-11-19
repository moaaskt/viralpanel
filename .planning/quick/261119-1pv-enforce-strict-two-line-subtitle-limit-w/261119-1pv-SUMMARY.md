---
quick_id: "261119-1pv"
slug: "enforce-strict-two-line-subtitle-limit-w"
status: "complete"
date: "2026-11-19"
human_visual_approval: "approved"
commit: "none (per user governance constraint)"
---

# Quick Task Summary: 261119-1pv — Limite Global Estrito de 2 Linhas por Bloco de Legenda

## 1. Visão Geral
Identificado durante a inspeção visual da primeira versão do Short do tubarão-branco (`run_google_flow_shark_001/final_output.mp4`), o trecho `"seus dentes são constantemente substituídos"` havia renderizado em 3 linhas devido ao `WrapStyle: 0` do libass. Esta tarefa estabeleceu e comprovou a garantia de no máximo 2 linhas para qualquer bloco de legenda no sistema ZUNTO!.

## 2. Implementação Concluída
1. **Medidor Horizontal em Python Puro (`FontWidthMeasurer`):**
   - Implementado em `src/viralpanel/studio/subtitles.py` utilizando exclusivamente `hmtx.advanceWidth`, `cmap` formato 4 e `head.unitsPerEm`.
   - **Proibição estrita cumprida:** Nenhuma métrica vertical da tabela `OS/2` (`usWinAscent`/`usWinDescent`) é lida ou empregada.
   - Fator de escala horizontal calibrado em $k_{\text{ass}} = 0.72$ e fator de segurança de largura útil $0.94$.
2. **Reflow Inteligente Prioritário:**
   - Atualizado `_segment_words_into_chunks` para avaliar a largura horizontal antes de fechar o chunk, distribuindo palavras de forma equilibrada sem quebrar frases abruptamente e preservando 100% dos tokens originais.
3. **Quebra Balanceada Explícita com `\N`:**
   - Implementado `find_balanced_two_line_split` para encontrar o ponto ideal de divisão visual.
   - Observação técnica 1 cumprida: `format_ass_dialogue_line` trata `\N` como separador de palavras antes de `select_highlight_word`, aplicando a cor amarela por segmento sem corromper palavras iniciadas por `N` após `\N`.
4. **Fallback Controlado de Fonte:**
   - Adicionada constante `ZuntoTypography.SUBTITLE_MIN_FONT_SIZE = 48` em `src/viralpanel/branding.py`.
   - `fit_chunk_to_two_lines` aplica redução local via `{\fsN}` (piso 48px e piso emergencial 42px com warning) estritamente ao bloco indivisível que demandar, mantendo os demais blocos na fonte padrão 64px.
5. **Calibração de Diacríticos no Teste libass (Observação Técnica 2):**
   - Configurado `max_diacritic_gap_px = 6` e `min_band_height_px = 8` no extrator de linhas RGB24, unindo acentos aos glifos de base sem fundir linhas distintas mesmo com fonte reduzida.

## 3. Resultados de Testes e Validação
- **Testes Unitários e E2E:** 178 testes executados e aprovados (`178 passed in 61.93s`, zero falhas, zero skips).
- **Inspeção Real libass:** 100% dos 61 eventos do tubarão renderizados em 1 ou 2 linhas (52 em 2L, 9 em 1L, 0 em 3+L), com folga mínima de 87 px em relação ao mascote.
- **Validação Perceptual:** O Short v2 (`final_output_v2.mp4`) gerado com esta implementação recebeu **aprovação visual humana explícita do Project Owner**.
