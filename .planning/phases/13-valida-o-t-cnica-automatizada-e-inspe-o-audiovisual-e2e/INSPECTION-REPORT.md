# Relatório de Validação Técnica e Inspeção Audiovisual E2E — ZUNTO! (v1.1)

**Gerado em:** `2026-11-12 03:19:14 UTC`  
**Fase:** 13 — Validação Técnica Automatizada e Inspeção Audiovisual E2E  
**Status Global da Inspeção Visual:** `[PENDENTE DE INSPEÇÃO HUMANA]`

> [!IMPORTANT]
> Os testes técnicos automatizados (FFprobe, resolução, codecs, FPS racional, duração e amostragem multi-ponto de pixels) foram executados e aprovados. A aprovação visual final depende **obrigatoriamente** da conferência humana dos vídeos abaixo.

---

## 1. Artefatos de Vídeo Gerados para Inspeção

- **Cenário 1 — Fluxo Completo (Vídeo Base + Avatar Circular #FACC15 + Legendas ASS)**
  - Caminho: `C:\Users\Windows Lite BR\Documents\GitHub\viralpanel\storage\inspection\scenario_normal_final.mp4`
  - Tamanho: `153,887 bytes`
  - Assets registrados no banco (`3`): `audio, avatar, final_video`
  - Status do `SourceVideo`: `produced`

- **Cenário 2 — Fluxo Fallback Single-Pass (Áudio Puro -> Lavfi #0f172a Inline)**
  - Caminho: `C:\Users\Windows Lite BR\Documents\GitHub\viralpanel\storage\inspection\scenario_fallback_final.mp4`
  - Tamanho: `163,929 bytes`
  - Assets registrados no banco (`3`): `audio, avatar, final_video`
  - Status do `SourceVideo`: `produced`
  - Ausência de `source_visual_bg.mp4` temporário em disco: `True`

---

## 2. Métricas Técnicas Automatizadas (`MediaQualityValidator` / FFprobe)

| Métrica | Cenário 1 (Normal) | Cenário 2 (Fallback) | Especificação Oficial | Status |
|---------|--------------------|----------------------|-----------------------|--------|
| Resolução | `1080x1920` | `1080x1920` | `1080x1920` (9:16) | `PASS` |
| Video Codec | `h264` | `h264` | `h264` | `PASS` |
| Pixel Format (Final) | `yuv420p` | `yuv420p` | `yuv420p` | `PASS` |
| FPS (`avg` / `r`) | `24.0` (`24/1`) | `24.0` (`24/1`) | `24.0 ± 0.15` | `PASS` |
| Audio Codec | `aac` | `aac` | `aac` | `PASS` |
| Sample Rate | `44100 Hz` | `44100 Hz` | `>= 44100 Hz` | `PASS` |
| Duração Vídeo | `4.292s` | `4.5s` | `> 0s` (explícita) | `PASS` |
| Duração Áudio | `4.33s` | `4.5s` | `|V - A| <= 0.5s` | `PASS` |
| Avatar Intermediário | `png` / `rgba` (`300x300`) | `png` / `rgba` (`300x300`) | `png` / `rgba` (`300x300`) | `PASS` |

---

## 3. Auditoria de Pixels na Composição Final (Transparência & Contorno `#FACC15`)

### Cenário 1 — Fluxo Completo (Vídeo Base + Avatar Circular #FACC15 + Legendas ASS)
- **Status da Amostragem de Pixels:** `PASS`
- **Bounding Box do Avatar:** `X=726..1026, Y=1300..1600` (Centro `(876, 1450)`, Raio `150.0px`)
- **Cor de Fundo Esperada (RGB):** `(30, 41, 59)` (Tolerância por canal: `±18`)
- **Amostras nos 4 Cantos de Linha de Base:** `{'top_left': (29, 39, 59), 'top_right': (29, 39, 59), 'bottom_left': (29, 39, 59), 'bottom_right': (29, 39, 59)}`
- **Malha Distribuída Externa ao Círculo:** `107 pontos verificados`, `0 falhas`
- **Raios do Contorno Amarelo ZUNTO! (`#FACC15`) Confirmados:** `5/5` — Amostras RGB: `{'angle_-90': (245, 206, 10), 'angle_-45': (242, 206, 7), 'angle_0': (254, 205, 26), 'angle_-135': (248, 204, 53), 'angle_180': (247, 203, 16)}`

### Cenário 2 — Fluxo Fallback Single-Pass (Áudio Puro -> Lavfi #0f172a Inline)
- **Status da Amostragem de Pixels:** `PASS`
- **Bounding Box do Avatar:** `X=726..1026, Y=1300..1600` (Centro `(876, 1450)`, Raio `150.0px`)
- **Cor de Fundo Esperada (RGB):** `(15, 23, 42)` (Tolerância por canal: `±18`)
- **Amostras nos 4 Cantos de Linha de Base:** `{'top_left': (15, 23, 43), 'top_right': (15, 23, 43), 'bottom_left': (15, 23, 43), 'bottom_right': (15, 23, 43)}`
- **Malha Distribuída Externa ao Círculo:** `107 pontos verificados`, `0 falhas`
- **Raios do Contorno Amarelo ZUNTO! (`#FACC15`) Confirmados:** `5/5` — Amostras RGB: `{'angle_-90': (245, 206, 10), 'angle_-45': (245, 203, 4), 'angle_0': (248, 206, 25), 'angle_-135': (244, 200, 49), 'angle_180': (253, 200, 16)}`

---

## 4. Checklist dos 4 Pilares Visuais ZUNTO! (Confirmação Humana Obrigatória)

Status atual: **`[PENDENTE DE INSPEÇÃO HUMANA]`**

- [ ] **Pilar 1 — Ausência de moldura/caixa branca no avatar:** O avatar circular em `X=726..1026, Y=1300..1600` está livre de qualquer retângulo ou borda branca opaca `[PENDENTE DE INSPEÇÃO HUMANA]`.
- [ ] **Pilar 2 — Canal alfa preservado e contorno Amarelo de Impacto (`#FACC15`):** A região externa ao círculo exibe o vídeo/fundo perfeitamente visível, com anel circular `#FACC15` nítido e onda sonora confinada ao interior do círculo `[PENDENTE DE INSPEÇÃO HUMANA]`.
- [ ] **Pilar 3 — Camada única de legendas ASS em Safe Zone (`MarginV=640`):** A legenda ZUNTO! com caixa opaca `#0A0A0A` (`BorderStyle=3`, `Outline=16`) está legível, sem duplicação de legendas e cobrindo adequadamente a área de texto `[PENDENTE DE INSPEÇÃO HUMANA]`.
- [ ] **Pilar 4 — Sincronia audiovisual e fluidez:** Áudio e vídeo iniciam e terminam em sincronia, sem cortes abruptos ou descompasso `[PENDENTE DE INSPEÇÃO HUMANA]`.

---

## 5. Instruções para Revisão Humana

1. Abra os arquivos gerados em um player de vídeo (VLC, Windows Media Player ou navegador):
   - `storage/inspection/scenario_normal_final.mp4`
   - `storage/inspection/scenario_fallback_final.mp4`
2. Verifique visualmente os 4 pilares listados na Seção 4.
3. Confirme no chat com `aprovado` para concluir formalmente a Phase 13 e o Milestone v1.1, ou descreva qualquer ajuste visual desejado.
