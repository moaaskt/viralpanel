# Roadmap: ViralPanel

## Milestones

- 🏁 **v1.0 ViralPanel MVP** — Phases 1–7 (Completed 2026-11-05, archived to [.planning/milestones/v1.0-ROADMAP.md](file:///.planning/milestones/v1.0-ROADMAP.md))
- 🚧 **v1.1 ZUNTO! Visual Engine** — Phases 8–13 (In progress)

## Phases

### Milestone v1.1 — ZUNTO! Visual Engine

- [x] **Phase 8: Auditoria, Contratos e Diagnóstico de Causa Raiz** - Investigação técnica das causas de duplicação de legendas, artefatos do avatar e mapeamento rigoroso dos contratos entre subtitles.py, renderer.py e tasks Celery (completed 2026-11-06)
- [ ] **Phase 9: Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO!** - Refinamento de prompts no Gemini 2.5 Flash para retenção, rastreabilidade de fontes factuais, CTA contextual e identidade visual ZUNTO!
- [ ] **Phase 10: Motor de Legendas ZUNTO! e Desacoplamento** - Desacoplamento de formatação de legendas, eliminação definitiva de duplicação, sincronização milimétrica e estilização visual ZUNTO!
- [ ] **Phase 11: Avatar Reaction e Composição Visual Orgânica** - Recorte orgânico baseado na auditoria dos assets, calibração de proporção, safe zones e posicionamento no layout vertical 9:16
- [ ] **Phase 12: Refatoração do Video Composer FFmpeg e Integração** - Grafo de filtros integrado em single-pass (sem reencodificações intermediárias), 1080x1920 e preservação dos contratos Celery/Publishing
- [ ] **Phase 13: Validação Técnica Automatizada e Inspeção Audiovisual E2E** - Validação técnica automatizada (A/V, specs) combinada obrigatoriamente com inspeção visual humana de vídeos reais renderizados

## Phase Details

### Phase 8: Auditoria, Contratos e Diagnóstico de Causa Raiz

**Goal**: Identificar com precisão técnica a causa raiz de duplicações de legendas, problemas de formato/recorte do avatar reaction e gargalos nos filtros FFmpeg, além de mapear integralmente contratos e interfaces atuais antes de qualquer refatoração de código.
**Depends on**: Nothing (primeira fase do milestone v1.1)
**Requirements**: SUB-01, AVTR-01, COMP-01
**Success Criteria** (what must be TRUE):

  1. Relatório técnico documentando o ponto exato no fluxo (`subtitles.py` vs `renderer.py` vs Celery task) onde ocorre a duplicação ou conflito de renderização de legendas.
  2. Diagnóstico conclusivo do formato real dos assets de avatar (canais alfa/chroma, codecs, dimensões) definindo a técnica nativa de recorte e transparência mais adequada sem assumir máscaras a priori.
  3. Mapeamento exaustivo dos contratos e interfaces atuais entre `subtitles.py`, `renderer.py`, geração de avatar e tasks Celery, documentando entradas, saídas, responsabilidades e dependências para blindar contra regressões.
  4. Mapeamento completo do grafo de filtros FFmpeg atual com identificação de filtros redundantes, reencodificações intermediárias ou passes desnecessários.

**Plans**: 2/2 plans executed
Plans:

- [x] 08-01-PLAN.md — Mapeamento de Contratos & Interfaces e Análise dos Passes e Grafo FFmpeg
- [x] 08-02-PLAN.md — Diagnóstico de Causa Raiz (Legendas Duplicadas e Formato de Avatar) e Consolidação do Relatório Final AUDIT-REPORT.md

### Phase 9: Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO!

**Goal**: Elevar a qualidade editorial dos roteiros gerados pelo Gemini 2.5 Flash para máxima retenção, garantindo rastreabilidade de fatos/fontes, CTAs contextuais sem repetições artificiais e alinhamento à identidade da marca ZUNTO!.
**Depends on**: Phase 8
**Requirements**: BRND-01, BRND-02, SCRP-01, SCRP-02
**Success Criteria** (what must be TRUE):

  1. Prompts do Gemini 2.5 Flash geram roteiros com ganchos magnéticos nos primeiros 3 segundos, ritmo dinâmico e frases fluidas e naturais para sintetização TTS.
  2. Fechamentos e CTAs tornam-se contextuais e opcionais conforme a narrativa do vídeo, orientados pela essência da marca ZUNTO! sem repetição mecânica forçada do slogan em todos os episódios.
  3. Mecanismo de rastreabilidade e preservação de referências/fontes utilizado na elaboração dos roteiros, assegurando precisão factual sem dependência cega exclusiva da LLM.
  4. Diretrizes oficiais de identidade visual ZUNTO! (paleta preto profundo, amarelo de impacto e branco puro) e guia de safe zones (TikTok, Reels, Shorts) especificadas para balizar overlays e legendas.

**Plans**: 2/2 plans executed

Plans:
- [x] 09-01-PLAN.md — Módulo Central de Identidade Visual `branding.py` e Suíte de Testes (BRND-01, BRND-02)
- [x] 09-02-PLAN.md — Roteirista Gemini Editorial, Schemas (closing_thought + cta opcional), Rastreabilidade de Claims e Persistência de Metadados (SCRP-01, SCRP-02)
**UI hint**: yes

### Phase 10: Motor de Legendas ZUNTO! e Desacoplamento

**Goal**: Desacoplar a geração e estilização de legendas do renderer FFmpeg, eliminar qualquer duplicidade e entregar legendas no padrão ZUNTO! com sincronia temporal precisa.
**Depends on**: Phase 9
**Requirements**: SUB-01, SUB-02, SUB-03, BRND-01
**Success Criteria** (what must be TRUE):

  1. `subtitles.py` desacoplado de `renderer.py`, atuando estritamente como formatador e construtor de legendas (ASS/SRT) com tipografia marcante, quebras de linha responsivas para mobile e alto contraste ZUNTO!.
  2. Execução da esteira de composição sem qualquer duplicidade de legenda na tela (burn-in único garantido).
  3. Sincronização temporal milimétrica entre a locução gerada e a cadência de exibição das palavras, com suporte a realce/destaque dinâmico de palavras-chave.

**Plans**: TBD
**UI hint**: yes

### Phase 11: Avatar Reaction e Composição Visual Orgânica

**Goal**: Integrar o avatar virtual de reaction de forma orgânica, sem aspecto de caixa quadrada, utilizando a técnica de recorte identificada na auditoria e respeitando safe zones verticais 9:16.
**Depends on**: Phase 8, Phase 9
**Requirements**: AVTR-01, AVTR-02, AVTR-03, BRND-02
**Success Criteria** (what must be TRUE):

  1. Avatar reaction integrado sem aparência de caixa/imagem quadrada, utilizando a técnica de transparência e recorte nativo validada a partir dos assets reais na Phase 8.
  2. Posicionamento e dimensionamento calibrados estritamente dentro da safe zone vertical 9:16, assegurando que elementos centrais do vídeo e legendas nunca sejam ocluídos.
  3. Proporção, nitidez, sincronização e qualidade visual preservadas, respeitando a taxa de quadros e conformidade técnica esperada pelo pipeline.

**Plans**: TBD
**UI hint**: yes

### Phase 12: Refatoração do Video Composer FFmpeg e Integração

**Goal**: Reestruturar o Video Composer em camadas limpas com grafo de filtros integrado em single-pass (evitando reencodificações intermediárias desnecessárias), saída 1080x1920 e preservação rigorosa dos contratos com Celery e publicação.
**Depends on**: Phase 10, Phase 11
**Requirements**: COMP-01, COMP-02, COMP-03, BRND-01, BRND-02
**Success Criteria** (what must be TRUE):

  1. Composição audiovisual realizada em grafo de filtros integrado em um único passe com codificação final única sempre que tecnicamente viável, eliminando reencodificações intermediárias desnecessárias.
  2. Saída do vídeo rigorosamente padronizada em 1080x1920 (9:16 vertical Full HD) com sincronia perfeita entre áudio e vídeo e ordenação clara de camadas (fundo, avatar, legendas, branding).
  3. Contratos de interface com as tasks Celery preservados, assegurando que as integrações de publicação permaneçam funcionais e desacopladas da refatoração.

**Plans**: TBD

### Phase 13: Validação Técnica Automatizada e Inspeção Audiovisual E2E

**Goal**: Validar rigorosamente o pipeline através de inspeções técnicas automatizadas de integridade de mídia complementadas obrigatoriamente por inspeção visual humana de vídeos reais renderizados.
**Depends on**: Phase 12
**Requirements**: QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):

  1. Validador técnico automatizado inspeciona o vídeo gerado verificando resolução exata (1080x1920), aspect ratio (9:16), duração, taxa de quadros, integridade de streams A/V e integridade do arquivo.
  2. Geração de vídeos de teste completos a partir de dados reais com inspeção visual humana explícita, comprovando ausência de legendas duplicadas, ausência de artefatos no avatar, enquadramento correto em safe zones e sincronia labial (quando o avatar possuir fala/movimento de boca) e harmonia narrativa.
  3. Aprovação formal do milestone condicionada cumulativamente aos testes automatizados verdes e à validação perceptual positiva dos vídeos gerados.

**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| Phase 8: Auditoria, Contratos e Diagnóstico de Causa Raiz | 0/0 | Not started | - |
| Phase 9: Roteirista Editorial Gemini, Rastreabilidade e Branding ZUNTO! | 0/0 | Not started | - |
| Phase 10: Motor de Legendas ZUNTO! e Desacoplamento | 0/0 | Not started | - |
| Phase 11: Avatar Reaction e Composição Visual Orgânica | 0/0 | Not started | - |
| Phase 12: Refatoração do Video Composer FFmpeg e Integração | 0/0 | Not started | - |
| Phase 13: Validação Técnica Automatizada e Inspeção Audiovisual E2E | 0/0 | Not started | - |
