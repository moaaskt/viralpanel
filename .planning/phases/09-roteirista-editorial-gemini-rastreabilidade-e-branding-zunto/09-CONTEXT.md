# Phase 9: Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO! - Context

**Gathered:** 2026-11-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase entrega a elevação da qualidade editorial e da retenção dos roteiros gerados pelo Gemini 2.5 Flash, a estruturação de rastreabilidade factual entre claims do roteiro e a transcrição original, e a centralização da identidade visual e Safe Zones da marca ZUNTO!.

Abrange:
- Refinamento do prompt e persona do roteirista no Gemini 2.5 Flash (`src/viralpanel/scripting/gemini.py`).
- Evolução de `GeneratedScriptSchema` com separação explícita entre `closing_thought: str` e `cta: str | None = None`.
- Estruturação de `factual_claims` tipados e sua persistência sem quebra no campo JSON de metadados do `Script` (`src/viralpanel/models.py` / `src/viralpanel/scripting/service.py`).
- Criação do módulo central de identidade da marca: `src/viralpanel/branding.py` (`ZuntoPalette`, `ZuntoTypography`, `SafeZones9x16`, `BrandGuidelines` e helpers de cor Hex -> ASS BGR).

Não abrange:
- Modificação na renderização FFmpeg de legendas (Phase 10) ou composição de avatar (Phase 11/12).
- Modificação no scraper de discovery ou APIs de publicação oficial.

</domain>

<decisions>
## Implementation Decisions

### Estrutura Editorial, Ganchos & Retenção
- **D-01:** Prompts do Gemini 2.5 Flash devem focar em ganchos provocativos e intrigantes nos primeiros 0–3s (`hook`, máx. ~10 palavras), desenvolvimento com suspense/revelação (`body`, ritmo dinâmico para narração TTS fluida) e encerramento sem enrolação ou promessas exageradas — **Reversibility:** reversible — ajustes em prompts e templates de roteiro.
- **D-02:** O slogan *"Você não sabia. Agora sabe."* deve orientar a filosofia editorial e a postura do roteirista, mas **não deve ser forçado como frase de encerramento mecânica em todos os vídeos**. Deve surgir apenas quando fizer sentido editorial genuíno.

### CTA Contextual & Schema de Roteiro
- **D-03:** Separar formalmente conclusão narrativa de chamada para ação em `GeneratedScriptSchema`:
  - `closing_thought: str` — fechamento narrativo obrigatório, natural e intrinsecamente ligado ao tema.
  - `cta: str | None = None` — chamada para ação estritamente opcional, inserida apenas quando houver oportunidade contextual legítima.
- **D-04:** A propriedade `GeneratedScriptSchema.full_text` deve compor `hook`, `body` e `closing_thought`. O bloco de `cta` só é anexado ao final quando `cta` estiver preenchida e não vazia. Nenhum placeholder artificial ou quebra de linha órfã deve ser gerada quando `cta` for `None`.
- **D-05:** Preservar compatibilidade com testes e serialização existentes de `GeneratedScriptSchema` (garantindo que chamadas que consomem `full_text` ou `hook` continuem funcionando sem quebra).

### Rastreabilidade Factual & Preservação de Fontes
- **D-06:** Modelar `FactualClaim` tipado contendo:
  - `claim: str` (afirmação factual feita no roteiro)
  - `source_reference: str | None` (referência/origem da informação)
  - `source_excerpt: str | None` (trecho correspondente da transcrição original)
  - `timestamp: str | None` (localização temporal na transcrição, se houver)
  - `verification_status: str` (ex: "unverified_source_claim", "extracted_from_transcript" — sem presumir veracidade confirmada)
- **D-07:** Não tratar a transcrição do vídeo original como comprovação independente de veracidade. Não inventar fontes, URLs ou evidências ausentes.
- **D-08:** Persistir os claims e referências no modelo `Script`: adicionar coluna `metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)` em `Script` (em `src/viralpanel/models.py`), preservando a compatibilidade total com os registros existentes e sem exigir refatoração em outras tabelas.

### Módulo Central de Branding ZUNTO!
- **D-09:** Criar `src/viralpanel/branding.py` como a **fonte única de verdade** para as constantes visuais, cores e safe zones do ZUNTO!, acessível por todos os módulos (`subtitles.py`, `avatar.py`, `renderer.py`).
- **D-10:** Estrutura tipada do `branding.py`:
  - `ZuntoPalette`: Cores oficiais — Preto Profundo (`#0A0A0A`), Amarelo de Impacto (`#FACC15`), Branco Puro (`#FFFFFF`), Cinza Escuro Neutro (`#1A1A1A`).
  - `ZuntoTypography`: Famílias tipográficas sugeridas (ex: Montserrat/DejaVu Sans Bold), tamanhos proporcionais para 1080x1920.
  - `SafeZones9x16`: Coordenadas e limites verticais/horizontais em 1080x1920 (TikTok, Reels, Shorts), baseadas nos dados homologados na Seção 3.5 do `08-AUDIT-REPORT.md` (`MarginV=640` para legendas em Y=1080–1280px, Avatar PIP em Y=1320–1600px).
  - `BrandGuidelines`: Objeto agregador com slogan, tom de voz e regras de aplicação.
- **D-11:** Utilitário de conversão de cores: função testada `hex_to_ass_color(hex_color: str, alpha_hex: str = "00") -> str` que converte cores Hex `#RRGGBB` para o formato ASS BGR `&HAABBGGRR&` (ex: `#FACC15` -> `&H0015CCFA&`), prevenindo bugs de inversão de canais no `libass`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos e Roadmap
- `.planning/REQUIREMENTS.md` — Requisitos BRND-01, BRND-02, SCRP-01, SCRP-02
- `.planning/ROADMAP.md` — Escopo e critérios de sucesso da Phase 9
- `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` — Seções 2 (estilo ASS ZUNTO!), 3.5 (Safe Zones 9:16) e 5.1 (Roteiro técnico para Phase 9)

### Código-Fonte Existente
- `src/viralpanel/scripting/gemini.py` — Prompt, persona e schemas do roteirista
- `src/viralpanel/scripting/service.py` — Orquestração de transcrição e geração de roteiro
- `src/viralpanel/models.py` — Definição das entidades `Script` e `SourceVideo`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets & Padrões
- `gemini.py`: Já possui integração robusta com API Gemini via REST (`urllib.request`) com retry exponencial e suporte a `RESPONSE_SCHEMA` estruturado.
- `models.py`: `Script` possui campos `transcription`, `script_text`, `hook`, `version`. A inclusão de `metadata_json` permite salvar `factual_claims` e metadados de branding sem quebrar consultas existentes.

### Integration Points
- `ScriptWriter.generate(transcription, fallback_context)` é consumido por `ScriptingService.process(db, run_id, source)`.
- O novo `src/viralpanel/branding.py` será importado futuramente por `src/viralpanel/studio/subtitles.py` (Phase 10) e `src/viralpanel/studio/renderer.py` (Phase 12).

</code_context>

<specifics>
## Specific Ideas

- O teste unitário deve validar a conversão `hex_to_ass_color("#FACC15") == "&H0015CCFA&"` para garantir que o amarelo ZUNTO! não fique azul no FFmpeg.
- O prompt do Gemini deve conter exemplos contrastantes (ex: o que é um gancho provocativo ZUNTO! vs o que é um gancho genérico fraco).

</specifics>

<deferred>
## Deferred Ideas

- Integração de verificação factual contra APIs de busca externas (Google Search / Perplexity) → Marco futuro v1.2+
- Aplicação das constantes de branding no motor de legendas ASS → Phase 10
- Aplicação das Safe Zones no recorte orgânico do avatar → Phase 11
- Aplicação da paleta no grafo FFmpeg single-pass → Phase 12

</deferred>

---

*Phase: 9-Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO!*
*Context gathered: 2026-11-06*
