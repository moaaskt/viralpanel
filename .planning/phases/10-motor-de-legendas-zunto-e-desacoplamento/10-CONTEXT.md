# Phase 10: Motor de Legendas ZUNTO! e Desacoplamento - Context

**Gathered:** 2026-11-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega o motor de legendas desacoplado e padronizado na identidade visual ZUNTO!. Ela transforma `src/viralpanel/studio/subtitles.py` em uma camada modular e autônoma responsável por:
1. Receber texto, duração total e metadados de formatação através de `SubtitleJobConfig`.
2. Segmentar e quebrar cues temporais com ponderação baseada em pontuação natural (`.`, `,`, `!`, `?`), tamanho fonético/textual dos caracteres e ritmo de retenção (3 a 5 palavras como diretriz editorial flexível).
3. Gerar arquivos `.ass` estritamente estilizados segundo a identidade ZUNTO! (`branding.py`), utilizando caixa opaca (`BorderStyle=3`, fundo `#0A0A0A`, texto branco `#FFFFFF` e realce de palavra-chave em Amarelo de Impacto `#FACC15` via `hex_to_ass_color`).
4. Cobrir fisicamente as hard-subs preexistentes de vídeos baixados do TikTok através da caixa opaca posicionada na Safe Zone vertical calibrada (`MarginV=640` como valor padrão inicial configurável).
5. Desacoplar completamente a lógica de temporalização e estilização do gerador FFmpeg, preservando todos os contratos públicos da v1.0 e garantindo aplicação única de legendas.

Fora de escopo: alteração no grafo do Video Composer FFmpeg (Phase 12), animação de avatar reaction (Phase 11), testes visuais definitivos em telas reais (Phase 13).

</domain>

<decisions>
## Implementation Decisions

### 1. Eliminação Visual de Hard-Subs Preexistentes
- **D-01:** Adotar caixa opaca de identidade visual ZUNTO! no estilo ASS com `BorderStyle=3`, fundo preto profundo `ZuntoPalette.DEEP_BLACK` (`#0A0A0A`) e texto `ZuntoPalette.PURE_WHITE` (`#FFFFFF`).
  - **Reversibility:** costly — define a estética padrão das legendas para todo o ecossistema e mascara legendas nativas do TikTok sem custo adicional de renderização.
  - A caixa deve cobrir visualmente a região onde as legendas preexistentes aparecem (`Y ≈ 1080–1280px`).
  - Consumir as Safe Zones de `src/viralpanel/branding.py` como referência primária.
  - **Posicionamento e dimensões totalmente configuráveis:** A caixa opaca não pode cobrir cegamente uma faixa fixa estática; `SubtitleJobConfig` deve expor parâmetros de ajuste fino (`margin_v`, `box_padding`/`outline`, `font_size`) para permitir calibrar a altura e a posição da faixa sem cobrir elementos visuais importantes da cena original.
  - Caso o vídeo original possua legendas em posição não padrão que exija máscara excessiva que degrade o conteúdo, o sistema deve registrar a limitação nos logs/metadados em vez de aplicar máscaras indiscriminadas.

### 2. Temporização e Quebra dos Cues
- **D-02:** Adotar temporização ponderada por caracteres e quebras sintáticas naturais com base em pontuação e pausas da locução.
  - **Reversibility:** reversible — lógica isolada dentro de `subtitles.py`.
  - Priorizar quebras em sinais de pontuação (`.`, `,`, `!`, `?`) e fronteiras sintáticas naturais.
  - Distribuir a duração de cada cue de forma proporcional ao número de caracteres e peso das palavras em relação à duração total da locução (`voice_duration`).
  - **Reconhecimento formal da limitação de sincronia:** A ponderação por caracteres é estritamente uma estimativa heurística proporcional, não sincronização fonética milimétrica. O sistema e o modelo devem reconhecer essa limitação nos logs/metadados (`timing_mode="proportional_character_estimate"` vs `"word_timestamp_aligned"`), priorizando o alinhamento com timestamps explícitos por palavra (Whisper ou TTS word boundaries) sempre que disponíveis.
  - Tratar a recomendação de 3 a 5 palavras por cue como diretriz editorial de cadência para mobile/retenção, e não como regra rígida que obrigue a cortar termos semanticamente inseparáveis.
  - Evitar que palavras fiquem isoladas em cues órfãos de frações mínimas de segundo.
  - Garantir intervalos sequenciais estritos: `cue[i].end <= cue[i+1].start`, eliminando qualquer sobreposição acidental de texto na tela.

### 3. Destaque Amarelo ZUNTO! e Sanitização ASS
- **D-03:** Aplicar destaque com tags ASS inline (`{\c&H0015CCFA&}`) para a palavra-chave ou primeira palavra relevante de cada bloco, com sanitização e escape blindados.
  - **Reversibility:** reversible — formatador de diálogo ASS interno.
  - Utilizar a cor oficial `ZuntoPalette.IMPACT_YELLOW` (`#FACC15`), obrigatoriamente convertida via `hex_to_ass_color` de `src/viralpanel/branding.py`.
  - Manter as demais palavras em branco puro `&H00FFFFFF&`.
  - Tags inline não devem introduzir espaçamentos extras, desalinhamentos ou deformações no bounding box do estilo ASS.
  - Evitar destacar palavras vazias/artigos/preposições sem peso de retenção.
  - **Blindagem e testes específicos de escape ASS:** Escape rigoroso de caracteres `{`, `}` no texto do usuário para não colidir com o delimitador de tags de controle do ASS (`{...}`); escape ou normalização de quebras de linha para `\N`; e fechamento explícito de qualquer tag de override de cor (`{\c&H00FFFFFF&}`) no final da palavra destacada para impedir terminantemente o vazamento de estilos (`leakage`) entre palavras ou entre cues subsequentes. Implementar suíte de testes unitários dedicada exclusivamente a essa sanitização.

### 4. Calibração da Margem Vertical e Safe Zones
- **D-04:** Adotar `MarginV=640` como valor padrão inicial, consumindo `SafeZones9x16.SUBTITLE_MARGIN_V` de `branding.py` e expondo o campo em `SubtitleJobConfig`.
  - **Reversibility:** reversible — parâmetro de configuração.
  - Centralizar a fonte de verdade das coordenadas em `branding.py`, sem duplicar números mágicos em `subtitles.py`, `renderer.py` ou `service.py`.
  - Permitir parametrização sem alterar o arquivo central de branding.
  - Resolução de referência fixa em `1080x1920` (PlayResX=1080, PlayResY=1920).
  - O ajuste fino visual definitivo será verificado na Phase 13 perante as interfaces do TikTok, Reels e Shorts.

### 5. Arquitetura de Desacoplamento e Contratos
- **D-05:** Desacoplar a geração dos cues e do arquivo `.ass` de qualquer dependência direta do FFmpeg.
  - **Reversibility:** costly — define os limites entre o módulo de legendas e o renderizador.
  - O motor `subtitles.py` é responsável estritamente pela estrutura temporal, divisão de texto, estilização e gravação do `.ass`.
  - O renderer (`renderer.py` / Phase 12) recebe o caminho do `.ass` pronto e aplica o filtro `ass=captions.ass` uma única vez no passe final.
  - Preservar compatibilidade total com os contratos públicos existentes da v1.0 (`SubtitleCue`, `build_cues_from_script`, `write_ass_subtitles`).
  - Introduzir `SubtitleJobConfig` como DTO tipado para novas chamadas estruturadas.

### the agent's Discretion
- Heurística exata para escolha da palavra de destaque quando nenhuma anotação semântica for provida (ex.: priorizar verbos/substantivos com mais de 4 caracteres, ignorando preposições/conjunções).
- Definição do espaçamento vertical (`Outline` / padding da caixa `BorderStyle=3`) para assegurar legibilidade sem bordas cortadas.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Brand & Safe Zones
- `src/viralpanel/branding.py` — Paleta oficial ZUNTO!, tipografia, SafeZones9x16 (`SUBTITLE_MARGIN_V=640`, `SUBTITLE_Y_MIN=1080`, `SUBTITLE_Y_MAX=1280`), `BrandGuidelines` e conversor `hex_to_ass_color`.
- `tests/test_branding.py` — Testes unitários do módulo de branding.

### Auditoria e Diagnósticos
- `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` — Diagnóstico de causas de sobreposição de hard-subs (Seção 2.4), especificação do DTO `SubtitleJobConfig` (Seção 1.5) e safe zones homologadas.

### Subtitles & Renderer
- `src/viralpanel/studio/subtitles.py` — Implementação atual de `SubtitleCue`, `build_cues_from_script` e `write_ass_subtitles`.
- `src/viralpanel/studio/renderer.py` — Ponto de consumo atual do arquivo `.ass` via filtro FFmpeg `ass=captions.ass`.
- `tests/test_studio_renderer.py` — Testes unitários e de integração de legendas ASS e composição.

</canonical_refs>

