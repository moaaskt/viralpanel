# Requirements: Milestone v1.1 — ZUNTO! Visual Engine

Refatoração e aprimoramento do pipeline de geração e composição audiovisual, elevando a qualidade dos vídeos produzidos automaticamente pelo sistema com a identidade visual da marca ZUNTO!. Prioridade absoluta para qualidade visual, legibilidade, retenção e consistência editorial sem sacrificar a estabilidade das integrações existentes.

## Requirements

### Motor de Legendas (SUB)

- [x] **SUB-01**: Eliminação definitiva de qualquer duplicação de legendas e unificação clara de responsabilidades entre transcrição, formatação de legenda e renderizador.
- [x] **SUB-02**: Sincronização temporal milimétrica com a locução gerada (XTTS/Voice), garantindo que as palavras acompanhem a cadência do áudio.
- [x] **SUB-03**: Estilização visual no padrão ZUNTO! com tipografia marcante de alta legibilidade para mobile, quebra inteligente de linhas e destaque de palavras-chave.

### Composição do Avatar (AVTR)

- [x] **AVTR-01**: Eliminação da aparência de "imagem quadrada" no avatar reaction, tratando recorte e transparência a partir de diagnóstico dos assets reais de forma orgânica.
- [x] **AVTR-02**: Calibração precisa de posicionamento e dimensionamento no layout vertical 9:16 para evitar que o avatar cubra pontos focais ou legendas essenciais.
- [x] **AVTR-03**: Preservação de proporção, nitidez, sincronização e qualidade visual na sobreposição do avatar, respeitando a taxa de quadros esperada pelo pipeline.

### Refatoração do Renderer (COMP)

- [x] **COMP-01**: Arquitetura modular de renderização FFmpeg em camadas explícitas com composição integrada em grafo de filtros single-pass e codificação final única sempre que tecnicamente viável.
- [ ] **COMP-02**: Padronização estrita de saída vertical 9:16 em 1080x1920 (Full HD vertical) com sincronização A/V consistente.
- [ ] **COMP-03**: Compatibilidade integral com os contratos de interface do Celery, tasks assíncronas e esteira de publicação nas APIs oficiais.

### Identidade Visual ZUNTO! (BRND)

- [x] **BRND-01**: Aplicação da paleta de cores ZUNTO! (preto profundo, amarelo de alto impacto e branco puro) nos elementos de composição e lettering.
- [x] **BRND-02**: Inclusão de elementos de marca e slogan orientando a narrativa sem imposição de repetições forçadas, adaptados para safe zones de TikTok, Reels e Shorts.

### Roteirista Editorial (SCRP)

- [x] **SCRP-01**: Refinamento do prompt e diretrizes do Gemini 2.5 Flash para construção de ganchos irresistíveis (0–3s), narrativa provocativa e CTAs contextuais e opcionais.
- [x] **SCRP-02**: Garantia de precisão factual rigorosa combinada com rastreabilidade/preservação de fontes e cadência natural para síntese de voz (TTS).

### Validação de Qualidade & Integridade (QUAL)

- [ ] **QUAL-01**: Validador técnico automatizado pós-renderização que inspeciona dimensões exatas (1080x1920), aspect ratio (9:16), duração, streams A/V e integridade do arquivo.
- [ ] **QUAL-02**: Testes de regressão audiovisual ponta a ponta com geração de vídeos reais inspecionados visualmente (ausência de legendas duplicadas, artefatos no avatar e safe zones).

## Processo & Restrições de Engenharia

- **Investigação Prévia e Mapeamento de Contratos Obrigatórios**: Identificar a causa raiz exata dos bugs visuais e documentar entradas, saídas, responsabilidades e dependências entre `subtitles.py`, `renderer.py`, avatar e Celery tasks antes de qualquer código.
- **Sem Máscaras Arbitrárias**: Avaliar o formato real dos assets de avatar e escolher a técnica de recorte/transparência ideal baseada em evidências.
- **Divisão Clara de Responsabilidades**: Desacoplar `subtitles.py` (responsável pelo arquivo/estrutura de legenda) e `renderer.py` (responsável pelo pipeline FFmpeg).
- **Zero Regressão**: Manter intactos os pipelines de discovery, scoring, banco PostgreSQL, bot do Telegram e publicação nas APIs oficiais.
- **Validação Dupla Obrigatória**: Aprovação formal do milestone condicionada cumulativamente à aprovação técnica automatizada E inspeção visual humana de vídeos renderizados reais.

## Future Requirements

- Geração procedural de miniaturas/covers dinâmicas com identidade ZUNTO!.
- Suporte a múltiplos apresentadores/vozes no mesmo vídeo.

## Out of Scope

- Alterações nos módulos de coleta (Playwright/TikTok scraper) e publicação oficial (APIs TikTok/Meta/YouTube).
- Modificações na interface web Chakra UI no milestone v1.1.
- Mudança na stack base (Python 3.12, Celery, Redis, FFmpeg, PostgreSQL).

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SUB-01 | Phase 8, Phase 10 | Complete |
| SUB-02 | Phase 10 | Complete |
| SUB-03 | Phase 10 | Complete |
| AVTR-01 | Phase 8, Phase 11 | Complete |
| AVTR-02 | Phase 11 | Complete |
| AVTR-03 | Phase 11 | Complete |
| COMP-01 | Phase 8, Phase 12 | Mapped |
| COMP-02 | Phase 12 | Mapped |
| COMP-03 | Phase 12 | Mapped |
| BRND-01 | Phase 9, Phase 10, Phase 12 | Complete |
| BRND-02 | Phase 9, Phase 11, Phase 12 | Complete |
| SCRP-01 | Phase 9 | Complete |
| SCRP-02 | Phase 9 | Complete |
| QUAL-01 | Phase 13 | Mapped |
| QUAL-02 | Phase 13 | Mapped |
