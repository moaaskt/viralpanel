# Requirements: Milestone v1.1 — ZUNTO! Visual Engine

Refatoração e aprimoramento do pipeline de geração e composição audiovisual, elevando a qualidade dos vídeos produzidos automaticamente pelo sistema com a identidade visual da marca ZUNTO!. Prioridade absoluta para qualidade visual, legibilidade, retenção e consistência editorial sem sacrificar a estabilidade das integrações existentes.

## Requirements

### Motor de Legendas (SUB)
- [ ] **SUB-01**: Eliminação definitiva de qualquer duplicação de legendas e unificação clara de responsabilidades entre transcrição, formatação de legenda e renderizador.
- [ ] **SUB-02**: Sincronização temporal milimétrica com a locução gerada (XTTS/Voice), garantindo que as palavras acompanhem a cadência do áudio.
- [ ] **SUB-03**: Estilização visual no padrão ZUNTO! com tipografia marcante de alta legibilidade para mobile, quebra inteligente de linhas e destaque de palavras-chave.

### Composição do Avatar (AVTR)
- [ ] **AVTR-01**: Eliminação da aparência de "imagem quadrada" no avatar reaction, tratando recorte, canal alfa/transparência ou formato de integração de forma nativa e orgânica.
- [ ] **AVTR-02**: Calibração precisa de posicionamento e dimensionamento no layout vertical 9:16 para evitar que o avatar cubra pontos focais ou legendas essenciais.
- [ ] **AVTR-03**: Preservação estrita de resolução, proporção e nitidez na sobreposição do avatar durante a transcodificação FFmpeg.

### Refatoração do Renderer (COMP)
- [ ] **COMP-01**: Arquitetura modular de renderização FFmpeg em camadas explícitas (vídeo de fundo, avatar, legendas, branding) com grafo de filtros otimizado (single-pass, sem sobreposição duplicada).
- [ ] **COMP-02**: Padronização estrita de saída vertical 9:16 em 1080x1920 (Full HD vertical) com sincronização labial e A/V perfeita.
- [ ] **COMP-03**: Compatibilidade integral com os contratos de interface do Celery, tasks assíncronas e esteira E2E do ViralPanel.

### Identidade Visual ZUNTO! (BRND)
- [ ] **BRND-01**: Aplicação da paleta de cores ZUNTO! (preto profundo, amarelo de alto impacto e branco puro) nos elementos de composição e lettering.
- [ ] **BRND-02**: Inclusão de elementos de marca e slogan ("Você não sabia. Agora sabe.") adaptados para as zonas seguras (safe zones) de TikTok, Instagram Reels e YouTube Shorts.

### Roteirista Editorial (SCRP)
- [ ] **SCRP-01**: Refinamento do prompt e diretrizes do Gemini 2.5 Flash para construção de ganchos irresistíveis (0–3s), narrativa provocativa e ritmo dinâmico que estimule retenção.
- [ ] **SCRP-02**: Garantia de precisão factual rigorosa (sem alucinações), frases naturais para síntese de voz (TTS) e fechamento/CTA memorável.

### Validação de Qualidade & Integridade (QUAL)
- [ ] **QUAL-01**: Validador automatizado pós-renderização que inspeciona dimensões exatas (1080x1920), aspect ratio (9:16), integridade dos streams de áudio e vídeo e taxa de quadros.
- [ ] **QUAL-02**: Testes de regressão audiovisual ponta a ponta que garantem ausência de legendas sobrepostas/duplicadas e geram vídeos reais inspecionáveis antes do encerramento.

## Processo & Restrições de Engenharia
- **Investigação Prévia Obrigatória**: Identificar a causa raiz exata dos bugs visuais antes de qualquer implementação (não aplicar patches cosméticos).
- **Sem Máscaras Arbitrárias**: Avaliar o formato real dos assets de avatar e escolher a técnica de recorte/transparência ideal baseada em evidências.
- **Divisão Clara de Responsabilidades**: Desacoplar `subtitles.py` (responsável pelo arquivo/estrutura de legenda) e `renderer.py` (responsável pelo pipeline FFmpeg).
- **Zero Regressão**: Manter intactos os pipelines de discovery, scoring, banco PostgreSQL, bot do Telegram e publicação nas APIs oficiais.
- **Validação com Mídia Real**: Testar com vídeos e áudios gerados em ambiente de teste para validação perceptual completa.

## Future Requirements
- Geração procedural de miniaturas/covers dinâmicas com identidade ZUNTO!.
- Suporte a múltiplos apresentadores/vozes no mesmo vídeo.

## Out of Scope
- Alterações nos módulos de coleta (Playwright/TikTok scraper) e publicação oficial (APIs TikTok/Meta/YouTube).
- Modificações na interface web Chakra UI no milestone v1.1.
- Mudança na stack base (Python 3.12, Celery, Redis, FFmpeg, PostgreSQL).

## Traceability
*(To be populated by ROADMAP.md)*
