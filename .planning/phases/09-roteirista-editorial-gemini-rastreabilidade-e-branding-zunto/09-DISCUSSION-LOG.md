# Phase 9: Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO! - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-06
**Phase:** 09-Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO!
**Areas discussed:** Ganchos e Retenção Editorial, CTA Contextual e Slogan, Rastreabilidade Factual de Fontes, Centralização de Branding ZUNTO!

---

## Ganchos, Retenção & Estrutura Editorial

**Diretriz do Usuário:** Trabalhar gancho forte nos primeiros 0-3 segundos, desenvolvimento com suspense e revelação, evitando introduções genéricas e promessas exageradas.
**Decisão:** Refinar o prompt do Gemini 2.5 Flash com persona madura, direta e sem clichês.

---

## CTA Contextual & Flexibilidade do Slogan

| Option | Description | Selected |
|--------|-------------|----------|
| Estender GeneratedScriptSchema com cta opcional | cta: str \| None = None | |
| Manter cta obrigatório permitindo string vazia | Sem alteração de campos | |
| Separar closing_thought (obrigatório) e cta (estritamente opcional) | Conclusão narrativa separada de engajamento | ✓ |

**User's choice:** Separar closing_thought (fechamento narrativo obrigatório) de cta (chamada para ação estritamente opcional). Slogan "Você não sabia. Agora sabe." como filosofia editorial orientadora, sem repetição mecânica obrigatória em todos os vídeos.

---

## Rastreabilidade Factual & Preservação de Fontes

| Option | Description | Selected |
|--------|-------------|----------|
| Estruturar factual_claims no GeneratedScriptSchema e persistir em campo JSON no Script | Estrutura tipada sem quebrar banco | ✓ |
| Adicionar colunas explícitas no Script | Migração relacional pesada | |
| Manter rastreabilidade apenas em log | Sem persistência | |

**User's choice:** Estruturar `factual_claims` tipados no schema do Gemini e persistir no modelo `Script` via campo JSON de metadados (`metadata_json`). Não inventar fontes nem tratar a transcrição como verdade absoluta independente.

---

## Centralização de Branding ZUNTO!

| Option | Description | Selected |
|--------|-------------|----------|
| Criar src/viralpanel/branding.py com classes tipadas e conversão Hex -> ASS BGR | Módulo centralizado compartilhado | ✓ |
| Criar src/viralpanel/studio/branding.py | Acoplado apenas ao estúdio | |
| Adicionar ao config.py ou YAML | Mistura configuração e identidade | |

**User's choice:** Criar `src/viralpanel/branding.py` como fonte única da verdade para cores (#0A0A0A, #FACC15, #FFFFFF), tipografia, safe zones 9:16 e conversão de cores Hex para ASS BGR.

