# Phase 9: Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO! - Research
**Researched:** 2026-11-06  
**Domain:** Prompt Engineering Gemini 2.5 Flash, Structured Outputs (Pydantic v2 / REST v1beta OpenAPI), Factual Claim Traceability & Model Persistence, ZUNTO! Brand Design System & Color/SafeZone Math  
**Confidence:** HIGH

---

## Summary

A Phase 9 foca na excelência editorial, no rigor de rastreabilidade factual e na padronização da identidade de marca **ZUNTO!** no ViralPanel. O objetivo é transformar roteiros gerados por IA de mensagens genéricas em peças de altíssima retenção para vídeos curtos verticais (9:16), respeitando a filosofia editorial orientada pelo slogan *"Você não sabia. Agora sabe."*, sem impor frases artificiais mecânicas e sem inventar fontes ou evidências externas inexistentes.

Além do refinamento editorial, esta fase estabelece a **fonte única de verdade** da identidade visual da marca no novo módulo `src/viralpanel/branding.py`, fornecendo a paleta oficial (Preto Profundo `#0A0A0A`, Amarelo de Impacto `#FACC15`, Branco Puro `#FFFFFF`, Cinza Escuro `#1A1A1A`), a tipografia proporcional calibrada para 1080x1920, as Safe Zones verticais e horizontais homologadas no relatório da Phase 8 (`08-AUDIT-REPORT.md`), e o algoritmo de conversão de cores Hex para o formato ASS BGR (`libass` do FFmpeg).

Por fim, os modelos de dados e serviços são evoluídos de forma retrocompatível: `GeneratedScriptSchema` ganha campos explícitos `closing_thought` e `cta` opcional (`str | None = None`), além de uma lista de `factual_claims` (`FactualClaim`). Na camada de persistência, `Script` recebe a coluna `metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)` em `src/viralpanel/models.py`, preservando compatibilidade com SQLite e PostgreSQL sem quebrar migrations ou registros legados.

**Primary recommendation:** Centralizar as constantes de estilo e matemática de cores/safe zones em `src/viralpanel/branding.py`, evoluir `GeneratedScriptSchema` e o prompt do Gemini 2.5 Flash com separação formal de `closing_thought` e `cta` opcional + claims factuais tipados, e persistir esses metadados via `metadata_json` em `Script` no `ScriptingService`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Prompts do Gemini 2.5 Flash devem focar em ganchos provocativos e intrigantes nos primeiros 0–3s (`hook`, máx. ~10 palavras), desenvolvimento com suspense/revelação (`body`, ritmo dinâmico para narração TTS fluida) e encerramento sem enrolação ou promessas exageradas — **Reversibility:** reversible — ajustes em prompts e templates de roteiro.
- **D-02:** O slogan *"Você não sabia. Agora sabe."* deve orientar a filosofia editorial e a postura do roteirista, mas **não deve ser forçado como frase de encerramento mecânica em todos os vídeos**. Deve surgir apenas quando fizer sentido editorial genuíno.
- **D-03:** Separar formalmente conclusão narrativa de chamada para ação em `GeneratedScriptSchema`:
  - `closing_thought: str` — fechamento narrativo obrigatório, natural e intrinsecamente ligado ao tema.
  - `cta: str | None = None` — chamada para ação estritamente opcional, inserida apenas quando houver oportunidade contextual legítima.
- **D-04:** A propriedade `GeneratedScriptSchema.full_text` deve compor `hook`, `body` e `closing_thought`. O bloco de `cta` só é anexado ao final quando `cta` estiver preenchida e não vazia. Nenhum placeholder artificial ou quebra de linha órfã deve ser gerada quando `cta` for `None`.
- **D-05:** Preservar compatibilidade com testes e serialização existentes de `GeneratedScriptSchema` (garantindo que chamadas que consomem `full_text` ou `hook` continuem funcionando sem quebra).
- **D-06:** Modelar `FactualClaim` tipado contendo:
  - `claim: str` (afirmação factual feita no roteiro)
  - `source_reference: str | None` (referência/origem da informação)
  - `source_excerpt: str | None` (trecho correspondente da transcrição original)
  - `timestamp: str | None` (localização temporal na transcrição, se houver)
  - `verification_status: str` (ex: "unverified_source_claim", "extracted_from_transcript" — sem presumir veracidade confirmada)
- **D-07:** Não tratar a transcrição do vídeo original como comprovação independente de veracidade. Não inventar fontes, URLs ou evidências ausentes.
- **D-08:** Persistir os claims e referências no modelo `Script`: adicionar coluna `metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)` em `Script` (em `src/viralpanel/models.py`), preservando a compatibilidade total com os registros existentes e sem exigir refatoração em outras tabelas.
- **D-09:** Criar `src/viralpanel/branding.py` como a **fonte única de verdade** para as constantes visuais, cores e safe zones do ZUNTO!, acessível por todos os módulos (`subtitles.py`, `avatar.py`, `renderer.py`).
- **D-10:** Estrutura tipada do `branding.py`:
  - `ZuntoPalette`: Cores oficiais — Preto Profundo (`#0A0A0A`), Amarelo de Impacto (`#FACC15`), Branco Puro (`#FFFFFF`), Cinza Escuro Neutro (`#1A1A1A`).
  - `ZuntoTypography`: Famílias tipográficas sugeridas (ex: Montserrat/DejaVu Sans Bold), tamanhos proporcionais para 1080x1920.
  - `SafeZones9x16`: Coordenadas e limites verticais/horizontais em 1080x1920 (TikTok, Reels, Shorts), baseadas nos dados homologados na Seção 3.5 do `08-AUDIT-REPORT.md` (`MarginV=640` para legendas em Y=1080–1280px, Avatar PIP em Y=1320–1600px).
  - `BrandGuidelines`: Objeto agregador com slogan, tom de voz e regras de aplicação.
- **D-11:** Utilitário de conversão de cores: função testada `hex_to_ass_color(hex_color: str, alpha_hex: str = "00") -> str` que converte cores Hex `#RRGGBB` para o formato ASS BGR `&HAABBGGRR&` (ex: `#FACC15` -> `&H0015CCFA&`), prevenindo bugs de inversão de canais no `libass`.

### the agent's Discretion
- Definição exata dos contrastes de prompt (exemplos positivos vs negativos de hooks ZUNTO!).
- Estrutura detalhada do OpenAPI responseSchema enviado na chamada REST da API Gemini para suportar campos `nullable: true` e arrays de objetos sem rejeição pelo endpoint `v1beta`.
- Valores padrão das margens e tamanhos de fonte em `ZuntoTypography` e `SafeZones9x16`.

### Deferred Ideas (OUT OF SCOPE)
- Integração de verificação factual contra APIs de busca externas (Google Search / Perplexity) → Marco futuro v1.2+
- Aplicação das constantes de branding no motor de legendas ASS → Phase 10
- Aplicação das Safe Zones no recorte orgânico do avatar → Phase 11
- Aplicação da paleta no grafo FFmpeg single-pass → Phase 12
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Descrição | Apoio da Pesquisa / Implementação |
|----|-----------|-----------------------------------|
| **BRND-01** | Aplicação da paleta de cores ZUNTO! (preto profundo, amarelo de alto impacto e branco puro) nos elementos de composição e lettering. | Implementação de `ZuntoPalette` e conversão matemática testada `hex_to_ass_color` em `src/viralpanel/branding.py`. [VERIFIED: in-repo test] |
| **BRND-02** | Inclusão de elementos de marca e slogan orientando a narrativa sem imposição de repetições forçadas, adaptados para safe zones de TikTok, Reels e Shorts. | Especificação de `BrandGuidelines` e `SafeZones9x16` em `branding.py` alinhadas à Seção 3.5 do `08-AUDIT-REPORT.md`. [VERIFIED: 08-AUDIT-REPORT.md] |
| **SCRP-01** | Refinamento do prompt e diretrizes do Gemini 2.5 Flash para construção de ganchos irresistíveis (0–3s), narrativa provocativa e CTAs contextuais e opcionais. | Atualização do `PERSONA`, `PROMPT_TEMPLATE` e `RESPONSE_SCHEMA` com `hook`, `body`, `closing_thought`, `cta` opcional em `gemini.py`. [VERIFIED: src/viralpanel/scripting/gemini.py] |
| **SCRP-02** | Garantia de precisão factual rigorosa combinada com rastreabilidade/preservação de fontes e cadência natural para síntese de voz (TTS). | Modelagem de `FactualClaim`, extração de fontes originais da transcrição, persistência em `Script.metadata_json` e formatação limpa de `full_text` para TTS. [VERIFIED: models.py / service.py] |
</phase_requirements>

---

## Architectural Responsibility Map

| Capacidade | Camada Primária | Camada Secundária | Racional |
|------------|-----------------|-------------------|----------|
| **Diretrizes e Constantes de Marca** | `src/viralpanel/branding.py` | — | Fonte única de verdade de cores, tipografia e safe zones acessível por todos os módulos. |
| **Geração de Roteiro e Persona IA** | `src/viralpanel/scripting/gemini.py` | `src/viralpanel/scripting/service.py` | ScriptWriter é responsável por prompts, structured outputs e parsing de IA. |
| **Rastreabilidade Factual** | `src/viralpanel/scripting/gemini.py` | `src/viralpanel/models.py` | Gemini extrai os claims e o ORM persiste no JSON de metadados do `Script`. |
| **Persistência de Metadados** | `src/viralpanel/models.py` | `src/viralpanel/scripting/service.py` | SQLAlchemy mapeia a coluna `metadata_json` e `ScriptingService` armazena o payload. |
| **Conversão de Cores ASS/BGR** | `src/viralpanel/branding.py` | `src/viralpanel/studio/subtitles.py` | Matemática de conversão de cores fica centralizada em branding para reuso. |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | `2.14.3` [VERIFIED: .venv] | Modelagem de DTOs, validação e schemas estruturados | Padrão do projeto, serialização JSON ultrarrápida e validação estrita. |
| `sqlalchemy` | `2.1.8` [VERIFIED: .venv] | Mapeamento ORM e persistência de dados | Camada de dados padrão do projeto com suporte a colunas `JSON` universais. |
| `python` | `3.12.3` [VERIFIED: .venv] | Runtime principal | Tipagem moderna (`str \| None`, `dataclass(frozen=True)`). |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `urllib.request` / `json` | Built-in | Chamadas REST para API Gemini (`v1beta`) | Cliente leve sem dependências pesadas de SDKs externos. |
| `pytest` | `9.2.0` [VERIFIED: .venv] | Testes automatizados | Validação de schemas, prompts e conversão de cores. |

---

## Package Legitimacy Audit

Nenhum novo pacote externo é necessário nesta fase. Toda a funcionalidade utiliza as dependências já instaladas no ambiente virtual (`pydantic 2.14.3`, `sqlalchemy 2.1.8`, Python 3.12 standard library).

---

## Architecture Patterns

### Pattern 1: Gemini REST Structured Output com Pydantic v2 e Campos Opcionais

A API Gemini REST `v1beta` (`generateContent`) suporta `generationConfig.responseSchema` seguindo um subconjunto do OpenAPI 3.0. Quando um campo é opcional (`cta: str | None = None`), o schema OpenAPI aceito pelo Gemini deve especificar `nullable: True` e o campo **não** deve estar na lista `required`.

```python
# Estrutura do RESPONSE_SCHEMA para Gemini 2.5 Flash
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "theme": {"type": "STRING"},
        "hook": {"type": "STRING"},
        "body": {"type": "STRING"},
        "closing_thought": {"type": "STRING"},
        "cta": {"type": "STRING", "nullable": True},
        "estimated_duration_seconds": {"type": "NUMBER"},
        "factual_claims": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "claim": {"type": "STRING"},
                    "source_reference": {"type": "STRING", "nullable": True},
                    "source_excerpt": {"type": "STRING", "nullable": True},
                    "timestamp": {"type": "STRING", "nullable": True},
                    "verification_status": {"type": "STRING"},
                },
                "required": ["claim", "verification_status"],
            },
        },
    },
    "required": ["hook", "body", "closing_thought", "estimated_duration_seconds"],
}
```

### Pattern 2: Matemática de Cores Hex -> ASS BGR (`libass`)

O padrão ASS (`Advanced SubStation Alpha`) utilizado pelo `libass` e FFmpeg codifica cores na ordem **Alpha-Blue-Green-Red** no formato `&HAABBGGRR&` (ou `&H00BBGGRR&` para totalmente opaco), enquanto cores web são `#RRGGBB` (Red-Green-Blue).

A conversão matemática exata:
1. Extrai canais hexadecimais: $R = \text{hex}[0:2]$, $G = \text{hex}[2:4]$, $B = \text{hex}[4:6]$.
2. Inverte para BGR e anexa o canal Alpha $A$ (padrão `00` = opaco no ASS): `&H` + $A$ + $B$ + $G$ + $R$ + `&`.
- Exemplo 1: `#FACC15` (Amarelo ZUNTO!) -> $R=\text{FA}$, $G=\text{CC}$, $B=15$ -> `&H0015CCFA&` [VERIFIED: run_command assertion].
- Exemplo 2: `#0A0A0A` (Preto Profundo ZUNTO!) -> $R=0\text{A}$, $G=0\text{A}$, $B=0\text{A}$ -> `&H000A0A0A&`.
- Exemplo 3: `#FFFFFF` (Branco Puro) -> `&H00FFFFFF&`.
- Exemplo 4: `#1A1A1A` (Cinza Escuro) -> `&H001A1A1A&`.

### Pattern 3: Estrutura do Módulo Central `src/viralpanel/branding.py`

```python
"""Módulo Central de Identidade Visual e Safe Zones da marca ZUNTO!.

Fonte única de verdade para constantes visuais, cores oficiais, safe zones 9:16
e conversão de cores para legendas e composição FFmpeg.
"""
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ZuntoPalette:
    """Paleta de cores oficial da marca ZUNTO!."""
    DEEP_BLACK: Final[str] = "#0A0A0A"     # Preto profundo (fundo, caixas opacas)
    IMPACT_YELLOW: Final[str] = "#FACC15"  # Amarelo de alto impacto (destaques, bordas, ênfases)
    PURE_WHITE: Final[str] = "#FFFFFF"     # Branco puro (texto primário, legendas)
    DARK_NEUTRAL: Final[str] = "#1A1A1A"   # Cinza escuro neutro (cards, detalhes secundários)


@dataclass(frozen=True)
class ZuntoTypography:
    """Especificações tipográficas para resolução base 1080x1920."""
    PRIMARY_FONT: Final[str] = "Montserrat"
    FALLBACK_FONT: Final[str] = "DejaVu Sans"
    SUBTITLE_FONT_SIZE: Final[int] = 64
    TITLE_FONT_SIZE: Final[int] = 84
    SUBTITLE_MAX_CHARS_PER_LINE: Final[int] = 28
    SUBTITLE_MAX_LINES: Final[int] = 2


@dataclass(frozen=True)
class SafeZones9x16:
    """Limites e coordenadas de safe zone em 1080x1920 para TikTok, Reels e Shorts."""
    WIDTH: Final[int] = 1080
    HEIGHT: Final[int] = 1920

    # Margens de segurança da UI mobile (cabeçalho, barra inferior e botões laterais)
    TOP_MARGIN: Final[int] = 220       # Evitar ícones de busca, abas 'Seguindo/Para Você'
    BOTTOM_MARGIN: Final[int] = 340    # Evitar descrição, áudio giratório e barra de navegação
    RIGHT_MARGIN: Final[int] = 140     # Evitar botões de like, comentários, salvar e compartilhar
    LEFT_MARGIN: Final[int] = 48       # Margem lateral esquerda segura

    # Zonas verticais calibradas (homologadas na Seção 3.5 do 08-AUDIT-REPORT.md)
    # Legenda ZUNTO!: Y ≈ 1080px a 1280px (MarginV ≈ 640 a partir da base)
    SUBTITLE_Y_MIN: Final[int] = 1080
    SUBTITLE_Y_MAX: Final[int] = 1280
    SUBTITLE_MARGIN_V: Final[int] = 640

    # Avatar Reaction: Canto inferior direito acima da barra do TikTok
    # Posicionado em Y ≈ 1320px a 1660px, X ≈ 692px a 1032px (size=340px)
    AVATAR_SIZE: Final[int] = 340
    AVATAR_MARGIN_RIGHT: Final[int] = 48
    AVATAR_MARGIN_BOTTOM: Final[int] = 260


@dataclass(frozen=True)
class BrandGuidelines:
    """Diretrizes editoriais e slogan da marca ZUNTO!."""
    BRAND_NAME: Final[str] = "ZUNTO!"
    SLOGAN: Final[str] = "Você não sabia. Agora sabe."
    TONE_OF_VOICE: Final[str] = "Direto, maduro, confiante, provocativo e livre de clichês motivacionais rasos."


def hex_to_ass_color(hex_color: str, alpha_hex: str = "00") -> str:
    """Converte cor Hex (#RRGGBB ou #RRGGBBAA) para formato ASS BGR (&HAABBGGRR&)."""
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) == 6:
        r, g, b = cleaned[0:2], cleaned[2:4], cleaned[4:6]
        a = alpha_hex.strip().lstrip("&Hh")
        if len(a) != 2:
            a = "00"
    elif len(cleaned) == 8:
        r, g, b, a = cleaned[0:2], cleaned[2:4], cleaned[4:6], cleaned[6:8]
    else:
        raise ValueError(f"Formato de cor Hex inválido: {hex_color}. Esperado #RRGGBB ou #RRGGBBAA.")
    return f"&H{a.upper()}{b.upper()}{g.upper()}{r.upper()}&"
```

---

## Don't Hand-Roll

| Problema | Não Inventar | Usar em Vez Disso | Racional |
|----------|--------------|-------------------|----------|
| **Conversão de cores para ASS** | Inversão manual de strings no código de legenda | `hex_to_ass_color` centralizado em `branding.py` | Garante que o amarelo ZUNTO! `#FACC15` não vire azul ciano no `libass`. |
| **Parsing e validação do Gemini** | Regex ou `json.loads` manual solto | `GeneratedScriptSchema.model_validate_json` do Pydantic v2 | Pydantic valida tipos, comprimentos mínimos e valores opcionais de forma robusta. |
| **Definição de Safe Zones** | Coordenadas mágicas espalhadas em strings FFmpeg | Constantes tipadas em `SafeZones9x16` | Permite que `subtitles.py` e `renderer.py` compartilhem os mesmos limites espaciais. |
| **Persistência de Metadados** | Criar novas tabelas relacionais para cada claim | Coluna `metadata_json` em `Script` | Preserva retrocompatibilidade total com SQLite/Postgres sem quebras de foreign keys. |

---

## Common Pitfalls

### Pitfall 1: Erro de Canal no ASS SubStation Alpha (Amarelo vira Azul)
- **O que acontece:** O desenvolvedor passa `&H00FACC15&` achando que o formato é RGBA.
- **Resultado:** No FFmpeg/libass, `&HAABBGGRR&` interpreta `RR=15` e `BB=FA`, renderizando a legenda ou contorno em azul ciano em vez de amarelo ZUNTO!.
- **Prevenção:** Sempre usar `hex_to_ass_color("#FACC15")`, que produz o valor BGR correto `&H0015CCFA&`.

### Pitfall 2: Rejeição de Schema da API Gemini REST para Campos Nulos
- **O que acontece:** Enviar `{"type": "STRING"}` para `cta` e tentar retornar `None`/`null`. A API Gemini rejeita a requisição com erro HTTP 400 (`Invalid JSON payload: field cta must be string`).
- **Prevenção:** Definir explicitamente `"nullable": True` no schema OpenAPI e omitir `cta` da lista `"required"`.

### Pitfall 3: Inserção de Frase de Efeito Forçada no Fechamento
- **O que acontece:** O prompt instruir o Gemini a sempre colocar *"Você não sabia. Agora sabe."* no final de todo vídeo.
- **Resultado:** Vídeos monótonos, robóticos e artificiais que irritam o usuário e diminuem a retenção após assistir 2 ou 3 vídeos seguidos.
- **Prevenção:** Conforme D-02, o slogan deve orientar o tom investigativo/revelador da persona, surgindo como frase falada apenas quando houver encaixe contextual genuíno.

### Pitfall 4: Quebras de Linha Órfãs em `full_text` quando `cta` é `None`
- **O que acontece:** Fazer `f"{hook}\n\n{body}\n\n{closing_thought}\n\n{cta}"`, resultando em `...\n\nNone` ou espaços duplos que confundem o sintetizador de voz (TTS).
- **Prevenção:** A propriedade `full_text` deve montar uma lista dinâmica `parts = [self.hook, self.body, self.closing_thought]` e anexar `self.cta.strip()` apenas se `self.cta` for preenchida e não vazia.

---

## Code Examples

### Exemplo 1: Schema de Roteiro Evoluído (`GeneratedScriptSchema` e `FactualClaim`)
```python
from pydantic import BaseModel, Field


class FactualClaim(BaseModel):
    """Afirmação factual identificada no roteiro com rastreabilidade."""
    claim: str = Field(..., description="Afirmação factual feita no roteiro")
    source_reference: str | None = Field(default=None, description="Referência ou contexto de origem")
    source_excerpt: str | None = Field(default=None, description="Trecho extraído da transcrição original")
    timestamp: str | None = Field(default=None, description="Timestamp de referência na transcrição")
    verification_status: str = Field(
        default="unverified_source_claim",
        description="Status de verificação (ex: unverified_source_claim, extracted_from_transcript)",
    )


class GeneratedScriptSchema(BaseModel):
    """Schema estruturado do roteiro gerado com separação editorial e rastreabilidade."""
    theme: str = ""
    hook: str = Field(min_length=3, description="Gancho nos primeiros 0-3s")
    body: str = Field(min_length=20, description="Desenvolvimento narrativo fluido")
    closing_thought: str = Field(default="", description="Fechamento narrativo natural")
    cta: str | None = Field(default=None, description="Chamada para ação opcional")
    estimated_duration_seconds: float = Field(ge=10, le=75)
    factual_claims: list[FactualClaim] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        parts = [self.hook, self.body]
        if self.closing_thought:
            parts.append(self.closing_thought)
        if self.cta and self.cta.strip():
            parts.append(self.cta.strip())
        return "\n\n".join(parts)
```

---

## Environment Availability

| Dependência | Necessário Por | Disponível | Versão | Fallback |
|-------------|----------------|------------|--------|----------|
| Python | Runtime | ✓ | 3.12.3 | — |
| Pydantic | Modelos e DTOs | ✓ | 2.14.3 | — |
| SQLAlchemy | Persistência ORM | ✓ | 2.1.8 | — |
| Pytest | Testes automatizados | ✓ | 9.2.0 | — |
| FFmpeg / libass | Renderização audiovisual | ✓ | 6.1.1 | — |

**Dependências ausentes:** Nenhuma.

---

## Validation Architecture

### Test Framework
| Propriedade | Valor |
|-------------|-------|
| Framework | pytest 9.2.0 |
| Configuração | `pyproject.toml` |
| Comando Rápido | `./.venv/bin/pytest tests/test_gemini_scripting.py -v` |
| Suite Completa | `./.venv/bin/pytest` |

### Phase Requirements → Test Map
| Req ID | Comportamento Esperado | Tipo de Teste | Comando de Teste Automatizado | Arquivo Existe? |
|--------|------------------------|---------------|-------------------------------|-----------------|
| **BRND-01** | Paleta ZUNTO! definida e conversão `hex_to_ass_color` BGR precisa | unit | `./.venv/bin/pytest tests/test_branding.py -k test_hex_to_ass_color` | ❌ Wave 0 (a criar) |
| **BRND-02** | Safe Zones 9:16 e guidelines de marca sem repetição forçada | unit | `./.venv/bin/pytest tests/test_branding.py -k test_safe_zones_and_guidelines` | ❌ Wave 0 (a criar) |
| **SCRP-01** | Prompt do Gemini com ganchos 0-3s e `closing_thought`/`cta` opcional | unit | `./.venv/bin/pytest tests/test_gemini_scripting.py -k test_gemini_writer_parses_structured_json` | ✅ Existente (estender) |
| **SCRP-02** | Extração de `factual_claims` e persistência em `Script.metadata_json` | integration | `./.venv/bin/pytest tests/test_gemini_scripting.py -k test_scripting_service_persists_metadata` | ✅ Existente (estender) |

### Wave 0 Gaps
- [ ] `tests/test_branding.py` — Testes de paleta, tipografia, safe zones e conversão de cores ASS BGR.
- [ ] Atualização em `tests/test_gemini_scripting.py` — Cobrir `closing_thought`, `cta: None`, `factual_claims` e persistência de `metadata_json`.

---

## Security Domain

### ASVS / Checklist de Segurança

| Categoria | Aplica-se | Controle Padrão |
|-----------|-----------|-----------------|
| **V5 Input Validation** | Sim | Validação estrita via Pydantic v2 em todas as respostas de IA (`model_validate_json`). Sanitização de strings em campos opcionais. |
| **V4 Access Control / Injection** | Sim | Escape de tags de formatação ASS em textos do usuário/IA para evitar injeções maliciosas no `libass`. |
| **V8 Data Protection** | Sim | Chaves de API (`GEMINI_API_KEY`, `GROQ_API_KEY`) nunca logadas em texto plano nem gravadas no banco de dados. |

---

## Sources

### Primárias (HIGH confidence)
- `src/viralpanel/scripting/gemini.py` [VERIFIED: read_file]
- `src/viralpanel/scripting/service.py` [VERIFIED: read_file]
- `src/viralpanel/models.py` [VERIFIED: read_file]
- `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/08-AUDIT-REPORT.md` [VERIFIED: read_file]
- `.planning/phases/09-roteirista-editorial-gemini-rastreabilidade-e-branding-zunto/09-CONTEXT.md` [VERIFIED: read_file]
- Teste empírico de conversão Hex -> ASS BGR e Pydantic v2 [VERIFIED: run_command]

---

## Metadata

**Research date:** 2026-11-06  
**Valid until:** Indefinido (estável no escopo do milestone v1.1)
