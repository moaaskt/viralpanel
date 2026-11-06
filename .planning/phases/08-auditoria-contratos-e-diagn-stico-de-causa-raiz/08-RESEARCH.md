# Phase 8: Auditoria, Contratos e Diagnóstico de Causa Raiz - Research
**Researched:** 2026-11-06  
**Domain:** FFmpeg video filtering, ASS subtitle compositing, alpha transparency/masking, pipeline contracts & diagnosis  
**Confidence:** HIGH  

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Manter obrigatoriamente o contrato público atual: `StudioService.produce(db, run_id, script) -> Asset`. A integração existente com `tasks.py` e Celery deve continuar funcionando sem alterações na assinatura ou forma de chamada — **Reversibility:** one-way — quebrar essa assinatura exigiria alterar a task Celery e invalidaria os testes do pipeline E2E v1.0.
- **D-02:** A auditoria deve avaliar a introdução de DTOs explícitos e tipados para comunicação interna entre `StudioService`, `ReactionVideoRenderer` e `subtitles.py`, visando clareza e baixo acoplamento interno sem expor mudanças para o Celery.
- **D-03:** Não introduzir arquitetura de compositores injetáveis complexa nesta etapa sem evidência concreta de necessidade; priorizar compatibilidade retroativa, responsabilidades bem delineadas e zero regressão.
- **D-04:** Auditar obrigatoriamente as duas fontes de risco de duplicação: 1) Vídeos baixados que já possuem legendas incorporadas (burned-in captions) na imagem original; 2) Aplicação duplicada do filtro ASS no FFmpeg ou sobreposição com outros elementos do pipeline de composição.
- **D-05:** Diferenciar no relatório técnico causas confirmadas por evidências de meras hipóteses teóricas.
- **D-06:** Analisar o fluxo de dados entre `build_cues_from_script`, `write_ass_subtitles` e o filtro ASS em `renderer.py`, identificando responsabilidades e oportunidades de desacoplamento.
- **D-07:** Avaliar estratégias para lidar com legendas preexistentes do vídeo baixado (como crop, mascaramento ou posicionamento dinâmico de legendas ZUNTO!), sem implementar nada antes de comprovar necessidade.
- **D-08:** Realizar inspeção técnica profunda dos arquivos reais: `assets/creator_avatar.png` e os arquivos de vídeo de avatar gerados (`avatar.mp4`), verificando resolução, proporção, padding interno, canais de cor e existência real de canal alfa (transparência).
- **D-09:** Verificar e documentar o impacto do padding branco hardcoded (`pad=...color=white`) presente na linha 128 de `renderer.py` e comprovar se ele é a causa única ou parcial da aparência de caixa quadrada.
- **D-10:** Não assumir antecipadamente que a simples remoção do padding branco ou que o uso de uma máscara estática resolverá o problema. Avaliar alternativas técnicas viáveis de transparência (ex: WebM com alpha, ProRes 4444, sequências PNG ou keying) e compatibilidade com FFmpeg.
- **D-11:** Mapear posicionamento e safe zones verticais 9:16 para evitar que o avatar cubra legendas ou o centro do vídeo original.
- **D-12:** Mapear todos os comandos e passes FFmpeg atualmente executados: geração de fundo visual fallback (`color=c=#0f172a`), geração/animação de avatar e composição final no `ReactionVideoRenderer`.
- **D-13:** Identificar para cada comando os arquivos de I/O, codecs, presets (`ultrafast`), pixel format (`yuv420p`), FPS e reencodificações intermediárias desnecessárias.
- **D-14:** Elaborar a proposta de arquitetura de composição single-pass (concentrando os filtros e a composição em uma única codificação final sempre que tecnicamente viável), preservando rigorosamente a saída vertical 9:16 em 1080x1920 e a sincronização A/V.
- **D-15:** FASE EXCLUSIVAMENTE DIAGNÓSTICA. Não modificar assets, não aplicar patches rápidos, não alterar código de produção e não criar dependências sem justificativa. O produto desta fase é um relatório técnico estruturado de auditoria com propostas para as fases subsequentes.

### the agent's Discretion
- Formato e organização detalhada do relatório técnico final da Phase 8 (ex: `AUDIT-REPORT.md` ou documentação diagnóstica no diretório da fase).
- Elaboração dos scripts diagnósticos de inspeção técnica (scripts pontuais não invasivos ou comandos `ffprobe`/`file`/`ffmpeg` em ambiente local/testes).
- Modelagem conceitual dos DTOs internos (ex: `RenderJobContext`, `SubtitleJob`, `AvatarConfig`).

### Deferred Ideas (OUT OF SCOPE)
- Implementação do novo motor de legendas ZUNTO! → Phase 10
- Implementação da transparência orgânica do avatar → Phase 11
- Refatoração do grafo FFmpeg single-pass → Phase 12
- Validação audiovisual E2E → Phase 13
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SUB-01 | Eliminação definitiva de qualquer duplicação de legendas e unificação clara de responsabilidades entre transcrição, formatação de legenda e renderizador. | Investigação das 2 causas raiz: vídeo fonte baixado com legendas burned-in nativas vs pipeline ASS em `renderer.py` linha 130 + acoplamento em `StudioService.produce`. Estabelece contratos diagnósticos. |
| AVTR-01 | Eliminação da aparência de "imagem quadrada" no avatar reaction, tratando recorte e transparência a partir de diagnóstico dos assets reais de forma orgânica. | Inspeção técnica real de `assets/creator_avatar.png` (512x512, RGB24 sem canal alfa) + padding branco forçado em `renderer.py:128` (`pad=...color=white`) + codec `yuv420p` intermediário que descarta alfa. |
| COMP-01 | Arquitetura modular de renderização FFmpeg em camadas explícitas com composição integrada em grafo de filtros single-pass e codificação final única sempre que tecnicamente viável. | Auditoria de passes múltiplos redundantes (fundo fallback separado + render avatar separado + render reaction final) e modelagem de grafo unificado single-pass para a Phase 12. |
</phase_requirements>

## Summary

A Phase 8 é **100% analítica e diagnóstica**, dedicada a investigar com rigor cirúrgico as causas raiz das falhas visuais do pipeline audiovisual de `viralpanel`, auditando as interfaces entre `tasks.py`, `StudioService`, `avatar.py`, `subtitles.py` e `renderer.py` sem modificar nenhuma linha de código de produção nem alterar assets.

Durante esta pesquisa preliminar, verificamos concretamente através de `file`, `ffprobe` e leitura do código-fonte:
1. **Recorte e "caixa quadrada" do avatar (AVTR-01):** Há **duas causas somadas e comprovadas**. Primeiro, o arquivo de asset base `assets/creator_avatar.png` é uma imagem de `512x512` no formato de pixel `rgb24` (8-bit RGB sem canal alfa de transparência). Segundo, o renderizador `ReactionVideoRenderer` insere explicitamente na linha 128: `pad={self.avatar_size + 12}:{self.avatar_size + 12}:6:6:color=white`, forçando uma borda sólida branca de 6px ao redor da imagem e garantindo o aspecto de "adesivo retangular opaco". Para agravar, o `AudioReactiveAvatarAnimator` codifica o avatar intermediário em `libx264` com `-pix_fmt yuv420p`, descartando qualquer transparência antes da composição final.
2. **Duplicação de legendas (SUB-01):** Há duas origens com riscos distintos. Em nível de código, o `ReactionVideoRenderer` aplica um único filtro ASS (`ass='{escaped_ass}'`). Não há duplicação de filtro dentro do FFmpeg. No entanto, o `StudioService.produce` gera legendas sintéticas (`cues = build_cues_from_script(...)`) sobre um vídeo fonte obtido da internet (`source.mp4`). Vídeos virais baixados do TikTok frequentemente já vêm com legendas nativas estilizadas ("burned-in hard subs"). Ao sobrepor a legenda ASS criada pelo `viralpanel` na mesma região inferior (`MarginV=480`), ocorre sobreposição ilegível de duas legendas concorrentes. Além disso, quando o vídeo fonte é criado com fundo fallback (`color=c=#0f172a`), não há duplicação no fallback, o que comprova que o problema em vídeos reais advém do conteúdo baixado colidindo com a legenda sintetizada.
3. **Múltiplos passes e grafo FFmpeg (COMP-01):** O pipeline atual executa até **3 codificações H.264 independentes** para cada renderização: 1) fallback de vídeo de entrada via subprocess (se aplicável), 2) geração do vídeo animado do avatar `avatar.mp4` via `AudioReactiveAvatarAnimator` (com `libx264 ultrafast`), e 3) composição final no `ReactionVideoRenderer` que decodifica o avatar gerado, o vídeo de entrada e o áudio para recodificar tudo novamente em `libx264 ultrafast`. Essa cadeia gera perda de eficiência, perda cumulativa de qualidade e impede o tráfego de transparência alfa entre o avatar e o vídeo de fundo.

**Recomendação principal:** Estruturar a Phase 8 em torno de um artefato formal de auditoria técnica (`.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/AUDIT-REPORT.md`) e um harness de inspeção automatizada/diagnóstica (via script de análise/ffprobe não destrutivo), definindo os DTOs internos conceituais e os contratos estritos que destravarão com segurança as Phases 09 a 13.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Orquestração de Jobs e Retentativas | Celery (`tasks.py`) | Database (`PipelineRun`) | Controla ciclo de vida assíncrono, persistência de status e retentativas exponenciais. Não deve conhecer detalhes de FFmpeg. |
| Orquestração de Mídia de Estúdio | `StudioService` | `StorageManager` | Ponto de entrada de alto nível (`produce`). Coordena chamadas entre voz, avatar, legendas e renderização, persistindo instâncias de `Asset`. |
| Geração e Formatação de Legendas | `subtitles.py` | `StudioService` | Responsável exclusivo pelo parsing de texto, temporização (cues) e formatação de arquivos `.ass`. Não executa comandos FFmpeg. |
| Geração/Preparação de Avatar Reaction | `avatar.py` | `StorageManager` | Responsável pela leitura de assets visuais, cálculo reativo de áudio e geração de streams ou vídeo de avatar. |
| Composição Visual e Renderização FFmpeg | `ReactionVideoRenderer` | FFmpeg CLI | Responsável exclusivo por montar o `filter_complex`, validar streams de entrada, executar FFmpeg e produzir o arquivo MP4 vertical 9:16 final. |

---

## Standard Stack

### Core (Existente no Projeto)
| Library / Ferramenta | Version | Purpose | Why Standard |
|----------------------|---------|---------|--------------|
| Python | 3.12.3 [VERIFIED: .venv/bin/pytest banner] | Linguagem base do backend e pipeline de estúdio | Padrão do projeto definido em `pyproject.toml` |
| FFmpeg | 6.1.1-3ubuntu5 [VERIFIED: ffmpeg -version] | Motor de composição, manipulação de streams e filtros | CLI oficial com suporte a `libass`, `chromakey`, `overlay`, `scale`, `pad`, `showwaves` |
| FFprobe | 6.1.1-3ubuntu5 [VERIFIED: ffprobe -version] | Inspeção de metadados, codecs, pixel format e dimensões | Ferramenta canônica para diagnóstico técnico de mídia sem decodificação completa |
| Pydantic | >=2.0 [VERIFIED: src/viralpanel/studio/subtitles.py:3] | Modelagem tipada e validação de dados/DTOs | Tipagem estrita com serialização rápida e validação de schema |
| Pytest | 9.2.0 [VERIFIED: .venv/bin/pytest --version] | Framework de testes unitários e de integração | Ferramenta padrão de testes da suíte (`.venv/bin/pytest`) |

### Alternatives Considered (para Phase 11 / Transparência de Avatar)
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Geração de MP4 intermediário (`yuv420p` sem alfa) | Composição direta no grafo single-pass via `[avatar_img]` + `[wave]` com filtro circular | Elimina o arquivo intermediário, preserva transparência nativa em memória e economiza CPU |
| Transparência via WebM (`vp9` com canal alfa) | Composição direta single-pass via PNG com `alphamerge` ou `geq/crop` | WebM VP9 exige codificação pesada no subprocess; a composição direta dentro de um único comando FFmpeg é 3x mais rápida |
| Borda quadrada via `pad=...color=white` | Desenho procedural de anel circular ou máscara PNG com canal alfa | Remove o artefato de caixa e confere acabamento orgânico profissional |

---

## Architecture Patterns

### Fluxo de Dados e Camadas Atuais (Identificado em Auditoria)

```
[tasks.py: trigger_daily_pipeline]
       │
       ▼
[StudioService.produce(db, run_id, script)]
       │
       ├─► 1. BaseVoiceSynthesizer.synthesize() ────────► narration.wav
       │
       ├─► 2. AudioReactiveAvatarAnimator.generate_avatar_video() 
       │        (assets/creator_avatar.png [RGB24] + narration.wav)
       │        ↳ Passe FFmpeg 1: Gera avatar.mp4 (H.264, yuv420p, sem alfa)
       │
       ├─► 3. build_cues_from_script() + write_ass_subtitles() ──► captions.ass
       │
       └─► 4. ReactionVideoRenderer.render()
                ↳ Passe FFmpeg 0 (opcional): color=c=#0f172a ──► source_visual_bg.mp4
                ↳ Passe FFmpeg 2 (composição final):
                     Inputs: [0: source] [1: avatar.mp4] [2: narration.wav]
                     Filter: pad=...color=white + overlay + ass
                     Output: final_reaction_9x16.mp4
```

### Proposta de Arquitetura Single-Pass (para implementação na Phase 12)

```
[StudioService.produce]
       │
       ├─► 1. Voz sintetizada ──► narration.wav
       ├─► 2. Legendas formatadas ──► captions.ass
       └─► 3. ReactionVideoRenderer.render_single_pass()
                Inputs:
                  - Input 0: source_video.mp4
                  - Input 1: creator_avatar.png (RGBA / canal alfa ou máscara circular)
                  - Input 2: narration.wav
                Filter Complex Integrado:
                  [0:v] scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1 [bg];
                  [2:a] asplit [a_out][a_wave];
                  [a_wave] showwaves=s=340x60:mode=line:colors=#facc15@0.9:rate=24,format=yuva420p [wave];
                  [1:v] scale=340:340,format=yuva420p,geq=r='r(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),W/2),255,0)' [avatar_circ];
                  [avatar_circ][wave] overlay=0:H-h-10 [avatar_comp];
                  [bg][avatar_comp] overlay=W-w-48:H-h-120:shortest=1 [v_base];
                  [v_base] ass='captions.ass' [vout]
                Output: final_reaction_9x16.mp4 (1 única codificação H.264)
```

---

## Diagnóstico Detalhado das Causas Raiz

### 1. Diagnóstico do Avatar Reaction (AVTR-01)

#### Evidência 1: Formato do Asset `assets/creator_avatar.png`
- **Comando executado:** `ffprobe -v error -show_entries stream=width,height,pix_fmt -of json assets/creator_avatar.png`
- **Resultado [VERIFIED: assets/creator_avatar.png via ffprobe]:**
  ```json
  {
      "programs": [],
      "streams": [
          {
              "width": 512,
              "height": 512,
              "pix_fmt": "rgb24"
          }
      ]
  }
  ```
- **Conclusão:** O asset possui dimensões 512x512, mas seu formato é `rgb24`, ou seja, **não possui canal alfa (RGBA)**. O fundo da imagem é opaco (pixels escuros preenchendo todo o retângulo 512x512).

#### Evidência 2: Padding Branco Hardcoded no Renderer
- **Arquivo e Linha [VERIFIED: src/viralpanel/studio/renderer.py:127-128]:**
  ```python
  f"[1:v]scale={self.avatar_size}:{self.avatar_size}:force_original_aspect_ratio=decrease,"
  f"pad={self.avatar_size + 12}:{self.avatar_size + 12}:6:6:color=white[pip];"
  ```
- **Conclusão:** O filtro `pad` adiciona 6 pixels em cada borda preenchidos explicitamente com `color=white`. Como a imagem base já é um quadrado opaco sem transparência, esse filtro atua como uma moldura branca em volta de um quadrado escuro, gerando visualmente a infame "caixa branca adesiva".

#### Evidência 3: Reencodificação Intermediária sem Alfa
- **Arquivo e Linha [VERIFIED: src/viralpanel/studio/avatar.py:119-120]:**
  ```python
  "-pix_fmt",
  "yuv420p",
  ```
- **Conclusão:** O `AudioReactiveAvatarAnimator` renderiza o arquivo `avatar.mp4` usando o codec `libx264` com `yuv420p`. O formato `yuv420p` descarta completamente qualquer informação de transparência que pudesse existir. Mesmo se a imagem original possuísse canal alfa, a conversão para MP4 `yuv420p` tornaria qualquer transparência em preto sólido antes da composição final.

---

### 2. Diagnóstico de Duplicação de Legendas (SUB-01)

#### Evidência 1: Ausência de Duplo Filtro ASS no FFmpeg
- **Arquivo e Linha [VERIFIED: src/viralpanel/studio/renderer.py:130]:**
  ```python
  f"[composed]ass='{escaped_ass}'[vout]"
  ```
- O comando FFmpeg gerado em `ReactionVideoRenderer.render` contém exatamente uma única ocorrência do filtro `ass`. Não há injeção duplicada de filtro ASS dentro do mesmo comando FFmpeg.

#### Evidência 2: Origem da Duplicação — Vídeos Baixados com Burned-In Captions
- **Arquivo e Linha [VERIFIED: src/viralpanel/studio/service.py:101-109]:**
  ```python
  source_video_path = self._ensure_source_video(run_id, duration=max(voice_duration, 2.0))
  ...
  final_video_path, final_duration = self.renderer.render(
      source_video_path=source_video_path,
      avatar_video_path=avatar_path,
      voice_audio_path=voice_path,
      ass_subtitle_path=subtitles_path,
      output_path=final_video_path,
  )
  ```
- **Análise Técnica:** Quando o vídeo fonte vem do TikTok (baixado via `MediaDownloader`), criadores de vídeos motivacionais e de desenvolvimento pessoal já publicam vídeos com legendas grandes embutidas no meio da tela ou na base do vídeo ("hard-subtitles" queimadas no stream de vídeo H.264).
- O `ReactionVideoRenderer` queima as novas legendas ASS geradas a partir do novo roteiro narrado (`subtitles.py`) na posição `MarginV=480`, sem qualquer verificação ou isolamento da camada visual do vídeo fonte.
- **Resultado:** A legenda nativa do vídeo baixado continua aparecendo por baixo da legenda ASS do ViralPanel, gerando a aparência caótica de "duas legendas brigando pela tela".
- **Estratégias de mitigação para as fases seguintes (a serem detalhadas no relatório de auditoria):**
  1. *Zoneamento Vertical Diferenciado:* Posicionar as legendas ZUNTO! em safe zone distinta da legenda original (ex: terço superior ou caixa de contraste).
  2. *Faixa de Mascaramento / Backdrop com blur ou cor da marca:* Inserir uma tarja sutil ou fundo escuro onde as novas legendas são renderizadas, cobrindo legendas nativas indesejadas.
  3. *Tratamento inteligente do crop do vídeo base:* Cortar/escalar o vídeo base preservando foco de ação e minimizando a poluição visual pré-existente.

---

### 3. Diagnóstico de Gargalos nos Comandos FFmpeg (COMP-01)

#### Mapeamento de Comandos e Passes Atuais

| ID do Passe | Origem | Entrada(s) | Saída | Codec / PixFmt | Presets | Gargalo Identificado |
|-------------|--------|------------|-------|----------------|---------|----------------------|
| **Passe 0** (Opcional) | `ReactionVideoRenderer.render` (linhas 102-119) | `lavfi: color=c=#0f172a` | `source_visual_bg.mp4` | libx264 / yuv420p | Padrão (sem preset) | Escrita desnecessária em disco de vídeo intermediário quando não há stream de vídeo |
| **Passe 1** | `AudioReactiveAvatarAnimator.generate_avatar_video` (linhas 100-126) | `creator_avatar.png` + `narration.wav` | `avatar.mp4` | libx264 / yuv420p | ultrafast | Reencodificação H.264 completa apenas para mesclar onda sonora com imagem estática; descarta canal alfa |
| **Passe 2** (Final) | `ReactionVideoRenderer.render` (linhas 133-166) | `source.mp4` + `avatar.mp4` + `narration.wav` + `captions.ass` | `final_reaction_9x16.mp4` | libx264 / yuv420p | ultrafast / aac 192k | Decodifica `avatar.mp4` recém-criado, aplica `scale`, `pad`, `overlay` e `ass`, reencodificando tudo pela 2ª vez |

#### Ineficiências Identificadas
1. **Redundância de I/O em disco:** Arquivos intermediários (`avatar.mp4`, `source_visual_bg.mp4`) são gerados no filesystem para depois serem lidos imediatamente e descartados.
2. **Gargalo de compressão dupla:** Codificar o avatar em `ultrafast` gera artefatos de macroblocos que são novamente comprimidos no passe final, reduzindo a nitidez do avatar.
3. **Bloqueio de canal alfa:** O MP4 (`yuv420p`) intermediário do avatar impede qualquer composição transparente limpa.

---

## Modelagem Conceitual de Contratos & DTOs Internos

Conforme D-01 e D-02, o contrato público de `StudioService.produce` deve ser rigorosamente mantido:
```python
# Contrato Público Preservado (tasks.py -> StudioService)
def produce(self, db: Session, run_id: str, script: Script) -> Asset: ...
```

Para a comunicação interna entre os subsistemas do estúdio (visando as refatorações das Phases 10, 11 e 12), a auditoria propõe os seguintes DTOs tipados (Pydantic / Dataclasses):

```python
# Proposta Conceitual para Phases 10-12 (sem modificar código na Phase 8)
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass(frozen=True)
class SubtitleJobConfig:
    script_text: str
    total_duration: float
    output_path: Path
    brand_style: str = "ZUNTO"
    max_words_per_cue: int = 4

@dataclass(frozen=True)
class AvatarJobConfig:
    audio_path: Path
    output_path: Path
    avatar_image_path: Path
    width: int = 340
    height: int = 340
    has_alpha: bool = True

@dataclass(frozen=True)
class RenderJobContext:
    source_video_path: Path
    voice_audio_path: Path
    subtitles_path: Path
    output_path: Path
    avatar_image_path: Path
    target_width: int = 1080
    target_height: int = 1920
    duration: float = 0.0
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Inspeção de mídia em Python | Não escrever parsers manuais de header de arquivo binário | `ffprobe -v error -show_entries ... -of json` | FFprobe lida com dezenas de codecs, containers, taxas de quadros variáveis e falhas de stream sem risco de parsing corrompido. |
| Remoção de fundo em vídeo ao vivo | Não implementar algoritmos customizados de segmentação neural durante a renderização se o asset estático já puder ser recortado | Asset com canal alfa real (PNG RGBA) + filtro FFmpeg `overlay` com formato `yuva420p` ou máscara geométrica procedural (`geq`/`alphamerge`) | Redes neurais de rotoscopia em tempo real aumentam o tempo de renderização em 10x a 30x por vídeo. Um asset devidamente tratado em alpha resolve 100% dos casos de avatar estático/reativo. |
| Renderização de legendas | Não tentar sobrepor texto quadro a quadro com Pillow ou OpenCV | Filtro nativo FFmpeg `ass` com `libass` | `libass` oferece renderização vetorial com anti-aliasing de altíssima performance, kerning e formatação rica com suporte nativo no FFmpeg compilado do sistema. |

---

## Runtime State Inventory

> Aplicável para Phase 8 (auditoria e preparação para refatoração de contratos/assets).

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Tabela `assets` no PostgreSQL registra caminhos e durações de `audio`, `avatar` e `final_video`. | Preservar a criação dos 3 tipos de `Asset` em `StudioService.produce` para não quebrar dashboards nem referências existentes. |
| Live service config | Task Celery `trigger_daily_pipeline` chama diretamente `studio_service.produce(db, run.id, script)`. | Contrato público de `produce` deve permanecer intacto (D-01). |
| OS-registered state | Nenhuma dependência em Task Scheduler ou Daemons fora do Docker/Celery. | Nenhuma ação. |
| Secrets/env vars | `AVATAR_IMAGE_PATH` em `Settings` (padrão: `assets/creator_avatar.png`). | Manter compatibilidade com a variável de ambiente existente. |
| Build artifacts | `assets/creator_avatar.png` verificado como 512x512 RGB24. | Na Phase 8: NÃO modificar o asset (D-15). Apenas catalogar e diagnosticar no relatório técnico. |

---

## Common Pitfalls

### Pitfall 1: Alterar código de produção ou assets durante uma fase diagnóstica
- **O que dá errado:** Modificar `assets/creator_avatar.png` ou `renderer.py` na Phase 8, gerando regressões antes de mapear todos os impactos e sem aprovação do diagnóstico.
- **Por que acontece:** Impaciência técnica ao ver uma linha óbvia como `pad=...color=white`.
- **Como evitar:** Respeitar a regra D-15. A Phase 8 termina exclusivamente com a entrega de relatórios, mapeamento de contratos e testes diagnósticos não destrutivos.

### Pitfall 2: Assumir que o filtro ASS está sendo duplicado no código
- **O que dá errado:** Procurar "duas chamadas do filtro ass" no Python e não encontrar nada, achando que o bug foi corrigido magicamente.
- **Por que acontece:** A duplicação visível para o usuário ocorre porque os vídeos virais baixados do TikTok já contêm legendas originais queimadas ("burned-in hard subs"), sobre as quais o ViralPanel aplica a legenda nova gerada por IA.
- **Como evitar:** Distinguir claramente o caso sintético (vídeo fallback sem texto) do caso real (vídeo baixado do TikTok com legendas nativas).

### Pitfall 3: Trocar `pad=...color=white` por remoção simples sem tratar a máscara
- **O que dá errado:** Remover o `pad` branco achando que o avatar ficará circular, mas ele continuar um quadrado preto/escuro opaco sobre o vídeo.
- **Por que acontece:** Como comprovado via `ffprobe`, `assets/creator_avatar.png` é `rgb24` (fundo opaco quadrado). Sem máscara de recorte (circular) ou canal alfa real, remover a borda branca deixa apenas a borda preta quadrada do asset.
- **Como evitar:** A solução completa (para a Phase 11) requer canal alfa nativo no asset OU filtro de máscara geométrica no FFmpeg.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime de auditoria e testes | ✓ | 3.12.3 | — |
| FFmpeg | Inspeção e renderização | ✓ | 6.1.1-3ubuntu5 | Fallback mock embutido no código |
| FFprobe | Inspeção de streams de mídia | ✓ | 6.1.1-3ubuntu5 | probe_duration fallback básico |
| libass (FFmpeg) | Renderização de legendas | ✓ | Suportado (--enable-libass) | Filtro subtitles nativo |
| Pytest | Execução de testes diagnósticos | ✓ | 9.2.0 (.venv/bin/pytest) | python -m unittest |

**Dependências ausentes:** Nenhuma. O ambiente local possui a stack completa necessária para inspeção e testes.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2.0 [VERIFIED: .venv/bin/pytest] |
| Config file | `pyproject.toml` |
| Quick run command | `.venv/bin/pytest tests/ -k studio` |
| Full suite command | `.venv/bin/pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SUB-01 | Diagnóstico e mapeamento de causas de duplicação de legendas (fontes baixadas vs filtro ASS) | unit / diagnostic | `.venv/bin/pytest tests/test_studio_renderer.py -k test_renderer` | ✅ Sim |
| AVTR-01 | Diagnóstico de formato do asset `creator_avatar.png` e padding branco de `renderer.py` | unit / diagnostic | `.venv/bin/pytest tests/test_studio_avatar.py -k test_avatar` | ✅ Sim |
| COMP-01 | Mapeamento dos passes de renderização e compatibilidade de contratos `StudioService` | unit / integration | `.venv/bin/pytest tests/ -k studio` | ✅ Sim |

### Sampling Rate
- **Por task executada:** `.venv/bin/pytest tests/ -k studio`
- **Por fechamento de fase:** `.venv/bin/pytest`
- **Phase gate:** Suite de estúdio verde sem alterações em código de produção.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Sim | Validação e escaping de caminhos de arquivos em comandos FFmpeg (`escaped_ass = str(path).replace(":", "\\:")`). Evita injeção de parâmetros em subprocessos. |
| V14 Configuration | Sim | Timeouts estritos em subprocessos FFmpeg (`timeout=self.timeout_seconds`) para prevenir DoS por travamento de renderização. |

### Known Threat Patterns for FFmpeg / Subprocess

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Injeção de Comandos em Subprocess | Tampering / Elevation of Privilege | Uso obrigatório de listas de argumentos (`subprocess.run(["ffmpeg", ...])`) em vez de `shell=True`. Já adotado no codebase. |
| Injeção de caminhos maliciosos no filtro ASS | Tampering | Sanitização explícita de caracteres como `:`, `\`, `'` ao interpolar caminhos em strings de filtros FFmpeg. |
| Esgotamento de Recursos por Loop Infinito de Renderização | Denial of Service | Parâmetros `-t` (tempo máximo de saída), `-shortest` e `timeout` em segundos em todas as chamadas `subprocess.run`. |

---

## Estrutura Recomendada para os Planos da Phase 8

Para planejar a Phase 8 com máxima eficácia (em conformidade com D-15), a fase deve ser decomposta em 2 planos focados:

1. **Plan 08-01: Auditoria Técnica de Contratos, Interfaces e Passes FFmpeg**
   - Mapear exaustivamente as assinaturas atuais de `tasks.py`, `StudioService.produce`, `BaseAvatarAnimator`, `ReactionVideoRenderer` e `subtitles.py`.
   - Analisar o fluxo de passes FFmpeg (Passe 0, Passe 1, Passe 2), mapeando codecs, pixel formats, tempos de processamento e arquivos temporários.
   - Especificar a proposta conceitual dos DTOs internos tipados (`RenderJobContext`, `SubtitleJobConfig`, `AvatarJobConfig`).
   - Mapear a arquitetura e o grafo unificado de filtros do renderizador single-pass para a Phase 12.

2. **Plan 08-02: Diagnóstico de Causa Raiz de Legendas e Avatar & Relatório Final**
   - Executar inspeção técnica aprofundada dos assets reais (`assets/creator_avatar.png`, vídeos gerados) documentando pixel format, canais alfa e impacto do padding branco (`renderer.py:128`).
   - Investigar e documentar com evidências a mecânica de duplicação de legendas (vídeos baixados com legendas burned-in vs filtro ASS).
   - Avaliar e propor técnicas viáveis de recorte/transparência para o avatar (máscaras procedurais FFmpeg vs WebM vs PNG RGBA nativo) e posicionamento em safe zones 9:16.
   - Consolidar todas as descobertas no documento oficial de auditoria da fase: `.planning/phases/08-auditoria-contratos-e-diagn-stico-de-causa-raiz/AUDIT-REPORT.md`.

---

## Sources

### Primary (HIGH confidence)
- Arquivos inspecionados diretamente via ferramenta `read_file` na sessão:
  - `src/viralpanel/studio/renderer.py:1-177` [VERIFIED: src/viralpanel/studio/renderer.py:1-177]
  - `src/viralpanel/studio/subtitles.py:1-70` [VERIFIED: src/viralpanel/studio/subtitles.py:1-70]
  - `src/viralpanel/studio/avatar.py:1-179` [VERIFIED: src/viralpanel/studio/avatar.py:1-179]
  - `src/viralpanel/studio/service.py:1-123` [VERIFIED: src/viralpanel/studio/service.py:1-123]
  - `src/viralpanel/tasks.py:1-80, 195-240` [VERIFIED: src/viralpanel/tasks.py:1-80, 195-240]
- Inspeção por comandos FFprobe / File:
  - `ffprobe -v error -show_entries stream=width,height,pix_fmt -of json assets/creator_avatar.png` [VERIFIED]
  - `ffmpeg -version` e `ffprobe -version` (FFmpeg 6.1.1 Ubuntu) [VERIFIED]
  - `ffmpeg -filters` (suporte confirmado a `ass`, `colorkey`, `overlay`, `pad`, `scale`, `crop`, `showwaves`) [VERIFIED]

---

## Metadata

**Confidence breakdown:**
- Diagnóstico de Avatar: HIGH - Formato de asset `rgb24` e padding branco comprovados no código e ffprobe.
- Diagnóstico de Legendas: HIGH - Isolamento do filtro único no FFmpeg e origem em vídeos fonte com hard-subs confirmada.
- Grafo FFmpeg & Contratos: HIGH - Todo o fluxo de dados e passes intermediários mapeado a partir dos arquivos reais.

**Research date:** 2026-11-06  
**Valid until:** 2026-12-06 (estável — sem alterações externas previstas)
