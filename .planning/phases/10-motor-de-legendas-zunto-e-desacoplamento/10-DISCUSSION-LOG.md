# Phase 10: Motor de Legendas ZUNTO! e Desacoplamento - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-06
**Phase:** 10-motor-de-legendas-zunto-e-desacoplamento
**Areas discussed:** Eliminação visual de hard-subs, Temporização e quebra dos cues, Destaque amarelo ZUNTO!, Calibração da margem vertical

---

## 1. Eliminação visual de hard-subs preexistentes

| Option | Description | Selected |
|--------|-------------|----------|
| Tarja / caixa opaca ZUNTO! (`BorderStyle=3`, fundo `#0A0A0A`, texto branco) | Mascara legendas embutidas nativas do TikTok sem custo extra de renderização ou OCR | ✓ |
| Mascaramento dinâmico / crop sem caixa | Menor cobertura, risco de expor texto preexistente | |

**User's choice:** Caixa opaca ZUNTO! com `BorderStyle=3`, fundo `#0A0A0A` e texto branco.
**Notes:** 
- Cobrir visualmente a região onde aparecem as legendas incorporadas ao vídeo de origem.
- Utilizar as Safe Zones centralizadas em `branding.py` como referência inicial.
- Evitar tarja excessivamente alta que prejudique a composição ou esconda elementos importantes.
- Não presumir posição idêntica em todos os vídeos: permitir ajustes de posicionamento e dimensão por configuração (`SubtitleJobConfig`).
- Registrar limitações quando a posição não puder ser coberta sem prejudicar conteúdo relevante, sem mascarar indiscriminadamente.

---

## 2. Temporização e quebra dos cues

| Option | Description | Selected |
|--------|-------------|----------|
| Ponderação por peso de caracteres, quebras em pontuação (`.`, `,`, `!`, `?`) e 3-5 palavras por cue | Ritmo dinâmico para retenção e sincronia com fala natural | ✓ |
| Divisão estritamente uniforme por número de palavras | Cues artificiais sem respeito à prosódia | |

**User's choice:** Ponderação por peso de caracteres com quebras naturais por pontuação e limite preferencial de 3 a 5 palavras.
**Notes:**
- Priorizar quebras em finais de frases e pausas naturais (vírgulas, pontos, exclamações, interrogações).
- Distribuir a duração proporcionalmente ao tamanho textual, respeitando a duração real da locução.
- Evitar palavras isoladas ou cortes semânticos artificiais (3-5 palavras é referência editorial, não regra rígida).
- Sequencialidade estrita sem sobreposições acidentais de cues.
- Preservar alinhamento com timestamps da locução sempre que disponíveis.

---

## 3. Destaque amarelo ZUNTO!

| Option | Description | Selected |
|--------|-------------|----------|
| Tags ASS inline (`{\c&H0015CCFA&}`) com cor oficial `#FACC15` via `hex_to_ass_color` | Destaque na palavra-chave ou primeira palavra do bloco sem quebrar layout | ✓ |
| Legenda homogênea em branco puro | Menor apelo dinâmico | |

**User's choice:** Tags ASS inline com cor oficial `#FACC15` convertida pelo helper centralizado `hex_to_ass_color`.
**Notes:**
- Destacar palavra-chave ou primeira palavra relevante; manter o restante em branco `#FFFFFF`.
- Tags não podem alterar espaçamento, alinhamento ou dimensões.
- Não destacar palavras vazias/sem relevância apenas por animação.
- Escape correto de caracteres especiais (`{`, `}`, `\N`) e fechamento estrito das tags.

---

## 4. Calibração da margem vertical (Safe Zones)

| Option | Description | Selected |
|--------|-------------|----------|
| `MarginV=640` como valor padrão inicial, configurável via `SubtitleJobConfig` | Não hardcodar margem; consumir de `branding.py`; flexível para Phase 13 | ✓ |
| Valor fixo hardcoded em 640 | Inflexível para testes de UI e validação visual | |

**User's choice:** `MarginV=640` padrão inicial configurável via `SubtitleJobConfig`.
**Notes:**
- Consumir de `branding.py` (`SafeZones9x16.SUBTITLE_MARGIN_V`) sem hardcode espalhado.
- Permitir ajustes sem alterar o arquivo central de branding.
- Resolução 1080x1920 mantida.
- Validação visual na Phase 13 perante TikTok, Reels e Shorts.

---

## the agent's Discretion

- Heurística de pontuação de relevância para palavras a destacar (ignorar preposições, conjunções e stopwords curtas).
- Espessura de Outline e padding interno da caixa `BorderStyle=3` para legibilidade ideal.

## Deferred Ideas

- Nenhuma ideia adiada nesta fase.
