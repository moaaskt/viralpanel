# Relatório de Validação Técnica e Inspeção Audiovisual E2E — ZUNTO! (v1.1)

**Gerado em:** `2026-11-14 20:26:29 UTC`  
**Run ID:** `run_20261114_202604_13880` (`sequence_number = 11`)  
**Fase:** 13 — Validação Técnica Automatizada e Inspeção Audiovisual E2E  
**Status da Validação Automatizada:** `APPROVED_FOR_HUMAN_INSPECTION`  
**Status da Inspeção Humana Oficial:** `[PENDENTE DE INSPEÇÃO HUMANA]`

> [!IMPORTANT]
> Os testes técnicos automatizados (FFprobe, resolução, codecs, FPS racional, duração, amostragem multi-ponto de pixels e congruência acústica PCM) foram executados e aprovados. A aprovação final da Phase 13 depende **obrigatoriamente** da conferência humana dos vídeos abaixo.

---

## 1. Identidade Editorial & Ficha da Narração

- **Classificação da Voz:** `Voz Neural Sintética (TTS Neural pt-BR)`
- **Sintetizador:** `EdgeTTSVoiceSynthesizer (pt-BR-AntonioNeural)`
- **Roteiro Canônico (52 palavras):**
  > *"Você não sabia. Agora sabe. Evidências fósseis de escamas atribuídas a ancestrais dos tubarões apontam para mais de quatrocentos milhões de anos de história. Isso indica que linhagens precursoras já nadavam nos oceanos antes do surgimento das primeiras árvores na Terra. A história dos vertebrados marinhos começou muito antes das primeiras florestas."*
- **Duração do Áudio Mestre:** `22.1760s`
- **Hash SHA-256 do Áudio Mestre WAV:** `8a84a51312ba4d8aa3b4e2f5b6276b09b2a0e606a5a63612d0c00baf98c6f55e`
- **Referência Científica:** Fósseis basais de escamas atribuídas a linhagens precursoras de condríctes (*Mongolepis*, *Elegestolepis*, Siluriano ~420–440 Ma, Turner 2004; espécime articulado *Doliodus problematicus*, ~409 Ma, Miller et al. 2003, *Nature* 425) precedendo as primeiras florestas fósseis (*Wattieza*, ~385 Ma, Stein et al. 2007, *Nature* 446).

---

## 2. Artefatos de Vídeo Gerados

- **Cenário 1 — Fluxo Completo (Vídeo Base + Avatar Circular #FACC15 + Legendas ASS)**
  - Caminho: `C:\Users\Windows Lite BR\Documents\GitHub\viralpanel\storage\inspection\runs\.staging_run_20261114_202604_13880\scenario_normal_final.mp4`
  - Tamanho: `1,171,982 bytes`
  - Assets registrados no banco (`3`): `audio, avatar, final_video`
  - Status do `SourceVideo`: `produced`

- **Cenário 2 — Fluxo Fallback Single-Pass (Áudio Puro -> Lavfi #0f172a Inline)**
  - Caminho: `C:\Users\Windows Lite BR\Documents\GitHub\viralpanel\storage\inspection\runs\.staging_run_20261114_202604_13880\scenario_fallback_final.mp4`
  - Tamanho: `1,169,306 bytes`
  - Assets registrados no banco (`3`): `audio, avatar, final_video`
  - Status do `SourceVideo`: `produced`

---

## 3. Três Verificações de Integridade de Áudio

### A. Integridade Criptográfica (Arquivos WAV)
- Hash SHA-256 do Áudio Mestre: `8a84a51312ba4d8aa3b4e2f5b6276b09b2a0e606a5a63612d0c00baf98c6f55e` (`PASS`)
- Entrega garantida e verificada por hash idêntico em memória no `PreSynthesizedVoice.synthesize`.

### B. Congruência Acústica (Streams PCM Decodificados via FFmpeg 44.1kHz s16le)
| Comparação | Pearson (r) | NMAE | Lag (amostras) | Diferença Amostras | Status |
|:----------:|:-----------:|:----:|:--------------:|:------------------:|:------:|
| Cenário Normal vs Mestre | `0.999994` | `0.000191` | `0` | `0` | `PASS` |
| Cenário Fallback vs Mestre | `0.999994` | `0.000191` | `0` | `1066` | `PASS` |
| Normal vs Fallback | `1.000000` | `0.000000` | `0` | `1066` | `PASS` |

### C. Verificação Temporal e Ausência de Truncamento
- Duração Mestre WAV: `22.1760s`
- Duração Áudio no Container Normal: `22.1760s` (desvio: `0.0000s`)
- Duração Áudio no Container Fallback: `22.1667s` (desvio: `0.0093s`)
- RMS Seccionado Normal (Início / Meio / Fim): `0.1427` / `0.1631` / `0.1471`
- RMS Seccionado Fallback (Início / Meio / Fim): `0.1423` / `0.1633` / `0.1473`

---

## 4. Métricas Técnicas Automatizadas (`MediaQualityValidator` / FFprobe)

| Métrica | Cenário 1 (Normal) | Cenário 2 (Fallback) | Especificação Oficial | Status |
|---------|--------------------|----------------------|-----------------------|--------|
| Resolução | `1080x1920` | `1080x1920` | `1080x1920` (9:16) | `PASS` |
| Video Codec | `h264` | `h264` | `h264` | `PASS` |
| Pixel Format (Final) | `yuv420p` | `yuv420p` | `yuv420p` | `PASS` |
| FPS (`avg` / `r`) | `24.0` (`24/1`) | `24.0` (`24/1`) | `24.0 ± 0.15` | `PASS` |
| Audio Codec | `aac` | `aac` | `aac` | `PASS` |
| Sample Rate | `44100 Hz` | `44100 Hz` | `>= 44100 Hz` | `PASS` |
| Avatar Intermediário | `png` / `rgba` | `png` / `rgba` | `png` / `rgba` (`300x300`) | `PASS` |

---

## 5. Auditoria de Pixels na Composição Final (Transparência & Contorno `#FACC15`)

### Cenário 1 — Fluxo Completo (Vídeo Base + Avatar Circular #FACC15 + Legendas ASS)
- **Status da Amostragem de Pixels:** `PASS`
- **Bounding Box do Avatar:** `X=726..1026, Y=1300..1600`
- **Cor de Fundo Esperada (RGB):** `(30, 41, 59)` (Tolerância: `±18`)
- **Malha Distribuída Externa ao Círculo:** `107 pontos verificados`, `0 falhas`
- **Raios do Contorno Amarelo ZUNTO! (`#FACC15`) Confirmados:** `5/5`

### Cenário 2 — Fluxo Fallback Single-Pass (Áudio Puro -> Lavfi #0f172a Inline)
- **Status da Amostragem de Pixels:** `PASS`
- **Bounding Box do Avatar:** `X=726..1026, Y=1300..1600`
- **Cor de Fundo Esperada (RGB):** `(15, 23, 42)` (Tolerância: `±18`)
- **Malha Distribuída Externa ao Círculo:** `107 pontos verificados`, `0 falhas`
- **Raios do Contorno Amarelo ZUNTO! (`#FACC15`) Confirmados:** `5/5`

---

## 6. Checklist dos 4 Pilares Visuais ZUNTO! (Confirmação Humana Obrigatória)

Status atual: **`[PENDENTE DE INSPEÇÃO HUMANA]`**

- [ ] **Pilar 1 — Ausência de moldura/caixa branca no avatar:** O avatar circular em `X=726..1026, Y=1300..1600` está livre de qualquer retângulo ou borda branca opaca `[PENDENTE DE INSPEÇÃO HUMANA]`.
- [ ] **Pilar 2 — Canal alfa preservado e contorno Amarelo de Impacto (`#FACC15`):** A região externa ao círculo exibe o vídeo/fundo perfeitamente visível, com anel circular `#FACC15` nítido e onda sonora confinada ao interior do círculo `[PENDENTE DE INSPEÇÃO HUMANA]`.
- [ ] **Pilar 3 — Camada única de legendas ASS em Safe Zone (`MarginV=640`):** A legenda ZUNTO! com caixa opaca `#0A0A0A` (`BorderStyle=3`, `Outline=16`) está legível, sem duplicação de legendas e cobrindo adequadamente a área de texto `[PENDENTE DE INSPEÇÃO HUMANA]`.
- [ ] **Pilar 4 — Sincronia audiovisual e fluidez:** Áudio neural inteligível (sem zunido/microfonia) e vídeo iniciam e terminam em sincronia, sem cortes abruptos ou descompasso `[PENDENTE DE INSPEÇÃO HUMANA]`.

---

## 7. Instruções para Revisão Humana

1. Abra os arquivos de vídeo em um player de sua escolha:
   - `C:\Users\Windows Lite BR\Documents\GitHub\viralpanel\storage\inspection\runs\.staging_run_20261114_202604_13880\scenario_normal_final.mp4`
   - `C:\Users\Windows Lite BR\Documents\GitHub\viralpanel\storage\inspection\runs\.staging_run_20261114_202604_13880\scenario_fallback_final.mp4`
2. Ouça a narração neural com atenção (certifique-se de que a fala é nítida, em português do Brasil e sem ruídos).
3. Verifique os 4 pilares listados na Seção 6.
4. Confirme no chat com `aprovado` para concluir formalmente a Phase 13 e o Milestone v1.1.
