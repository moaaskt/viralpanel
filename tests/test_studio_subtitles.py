from pathlib import Path
import pytest

from viralpanel.branding import (
    SafeZones9x16,
    ZuntoPalette,
    ZuntoTypography,
    hex_to_ass_color,
)
from viralpanel.studio.subtitles import (
    SubtitleCue,
    SubtitleJobConfig,
    align_words_with_timestamps,
    build_ass_header,
    build_cues_from_script,
    format_ass_dialogue_line,
    generate_subtitles,
    generate_word_karaoke_dialogue_events,
    sanitize_ass_text,
    select_highlight_word,
    split_script_into_cues,
    write_ass_subtitles,
)


def test_subtitle_job_config_defaults(tmp_path: Path):
    """Testa instanciação de SubtitleJobConfig com valores padrão ZUNTO!."""
    out = tmp_path / "captions.ass"
    config = SubtitleJobConfig(
        script_text="Texto do roteiro de alta retenção.",
        total_duration=5.0,
        output_path=out,
    )
    assert config.brand_style == "ZUNTO"
    assert config.max_words_per_cue == 5
    assert config.min_words_per_cue == 3
    assert config.margin_v == SafeZones9x16.SUBTITLE_MARGIN_V  # 690
    assert config.margin_v == 690
    assert config.box_padding == 16
    assert config.font_size == ZuntoTypography.SUBTITLE_FONT_SIZE  # 64
    assert config.font_name == ZuntoTypography.PRIMARY_FONT  # Montserrat
    assert config.play_res_x == 1080
    assert config.play_res_y == 1920
    assert config.timing_mode == "proportional_character_estimate"


def test_ass_header_zunto_style():
    """Valida que o cabeçalho ASS possui BorderStyle=3, MarginV=690 e cores ZUNTO!."""
    header = build_ass_header()

    assert "PlayResX: 1080" in header
    assert "PlayResY: 1920" in header
    assert "[V4+ Styles]" in header

    # Cores esperadas convertidas de branding.py
    expected_primary = hex_to_ass_color(ZuntoPalette.PURE_WHITE)       # &H00FFFFFF&
    expected_secondary = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)  # &H0015CCFA&
    expected_box = hex_to_ass_color(ZuntoPalette.DEEP_BLACK)           # &H000A0A0A&

    assert expected_primary == "&H00FFFFFF&"
    assert expected_secondary == "&H0015CCFA&"
    assert expected_box == "&H000A0A0A&"

    # Verificar linha Style
    style_lines = [line for line in header.splitlines() if line.startswith("Style: Default")]
    assert len(style_lines) == 1
    style = style_lines[0]

    # Style: Default,Montserrat,64,&H00FFFFFF,&H0015CCFA,&H000A0A0A,&H000A0A0A,-1,0,0,0,100,100,0,0,3,16,0,2,80,80,640,1
    tokens = style.replace("Style: ", "").split(",")
    # Formato dos campos:
    # 0: Name (Default)
    # 1: Fontname (Montserrat)
    # 2: Fontsize (64)
    # 3: PrimaryColour (&H00FFFFFF&)
    # 4: SecondaryColour (&H0015CCFA&)
    # 5: OutlineColour (&H000A0A0A&)
    # 6: BackColour (&H000A0A0A&)
    # 15: BorderStyle (3)
    # 16: Outline (16)
    # 17: Shadow (0)
    # 18: Alignment (2)
    # 21: MarginV (690)
    assert tokens[0] == "Default"
    assert tokens[2] == "64"
    assert tokens[3] == expected_primary
    assert tokens[4] == expected_secondary
    assert tokens[5] == expected_box
    assert tokens[6] == expected_box
    assert tokens[15] == "3"  # BorderStyle=3 (caixa opaca)
    assert tokens[16] == "16"  # Outline=16 (padding)
    assert tokens[17] == "0"  # Shadow=0
    assert tokens[18] == "2"  # Alignment=2 (Bottom-center)
    assert tokens[21] == "690"  # MarginV=690


def test_generate_subtitles_tracer_end_to_end(tmp_path: Path):
    """Teste tracer ponta a ponta gerando arquivo ASS válido em disco com estilo ZUNTO!."""
    out_file = tmp_path / "subtitles_zunto.ass"
    config = SubtitleJobConfig(
        script_text="Pare de procrastinar agora mesmo.",
        total_duration=3.0,
        output_path=out_file,
    )

    result_path = generate_subtitles(config)
    assert result_path == out_file
    assert out_file.exists()

    content = out_file.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "[V4+ Styles]" in content
    assert "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV" in content
    assert f",3,16,0,2,80,80,{SafeZones9x16.SUBTITLE_MARGIN_V},1" in content
    assert "Dialogue: 0," in content


def test_cue_chunking_punctuation_aware():
    """Valida segmentação sensível a pontuação e limites de retenção mobile (3-5 palavras)."""
    script = "Pare de esperar o momento ideal. Comece agora, mesmo sem motivação, e veja o resultado!"
    cues = split_script_into_cues(script, total_duration=8.0, min_words=3, max_words=5)

    assert len(cues) >= 3
    for cue in cues:
        word_count = len(cue.text.split())
        # Cada cue deve respeitar a cadência entre 2 e 6 palavras (meta de 3 a 5 palavras sem quebras artificiais)
        assert 2 <= word_count <= 6, f"Cue fora do intervalo rítmico: {cue.text!r}"

    # O texto concatenado deve conter todo o roteiro original
    reconstructed = " ".join(c.text for c in cues)
    for word in ["esperar", "ideal.", "Comece", "motivação,", "resultado!"]:
        assert word in reconstructed


def test_proportional_timing_allocation():
    """Valida alocação de tempo proporcional ao peso de caracteres e pausas."""
    # Frase 1: curta (10 chars, 1 ponto)
    # Frase 2: longa (58 chars, 1 vírgula, 1 ponto)
    script = "Comece já. A disciplina diária supera a motivação temporária de qualquer pessoa."
    cues = split_script_into_cues(script, total_duration=7.0, min_words=2, max_words=6)

    assert len(cues) >= 2
    # O primeiro cue é curto ("Comece já.")
    # Os cues subsequentes são mais longos
    cue_first = cues[0]
    cue_last = cues[-1]

    dur_first = cue_first.end - cue_first.start
    dur_last = cue_last.end - cue_last.start

    assert dur_first >= 0.8  # Piso mínimo
    assert dur_last > dur_first, f"Cue mais longo deve ter mais tempo: {dur_last} vs {dur_first}"


def test_temporal_contiguity_and_no_overlaps():
    """Valida contiguidade temporal estrita sem sobreposições e sem gaps."""
    script = (
        "Você não precisa de mais tempo. Precisa de foco implacável. "
        "A cada minuto perdido, sua concorrência dá mais um passo à frente."
    )
    total_duration = 9.4
    cues = split_script_into_cues(script, total_duration=total_duration, min_words=3, max_words=5)

    assert len(cues) > 1
    assert cues[0].start == 0.0

    for i in range(len(cues)):
        assert cues[i].start < cues[i].end, f"Cue {i} inválido: start >= end"
        if i > 0:
            # Contiguidade estrita sem gaps nem overlaps
            assert cues[i].start == pytest.approx(cues[i - 1].end, abs=1e-2)
            assert cues[i - 1].end <= cues[i].start

    assert cues[-1].end == pytest.approx(total_duration, abs=1e-2)


def test_timing_mode_metadata_and_word_timestamps():
    """Valida metadados de timing_mode com fallback heurístico e word timestamps."""
    script = "Aja agora mesmo."

    # Cenário 1: Fallback heurístico proporcional
    cues_heur = split_script_into_cues(script, total_duration=3.0)
    assert all(c.timing_mode == "proportional_character_estimate" for c in cues_heur)

    # Cenário 2: Word timestamps fornecidos explicitamente
    w_timestamps = [
        {"word": "Aja", "start": 0.2, "end": 0.8},
        {"word": "agora", "start": 0.85, "end": 1.6},
        {"word": "mesmo.", "start": 1.65, "end": 2.8},
    ]
    cues_aligned = split_script_into_cues(
        script,
        total_duration=3.0,
        word_timestamps=w_timestamps,
    )
    assert all(c.timing_mode == "word_timestamp_aligned" for c in cues_aligned)
    assert cues_aligned[0].start == pytest.approx(0.2, abs=0.05)
    assert cues_aligned[-1].end == pytest.approx(3.0, abs=0.05)


def test_build_cues_from_script_backwards_compatibility():
    """Valida que build_cues_from_script preserva compatibilidade delegando com sucesso."""
    cues = build_cues_from_script(
        "Foco diário constrói resultados duradouros.",
        total_duration=4.5,
        max_words_per_cue=5,
    )
    assert isinstance(cues, list)
    assert len(cues) >= 1
    assert all(isinstance(c, SubtitleCue) for c in cues)
    assert cues[0].start == 0.0
    assert cues[-1].end == pytest.approx(4.5, abs=0.05)


def test_ass_sanitization_brackets_and_newlines():
    """Valida substituição estrita de {} por () e normalização de quebras para \\N."""
    raw = "Atenção {chave_perigosa} e mais {outra}\nNova linha aqui\r\nTerceira linha"
    sanitized = sanitize_ass_text(raw)

    assert "{" not in sanitized
    assert "}" not in sanitized
    assert "(chave_perigosa)" in sanitized
    assert "(outra)" in sanitized
    assert "\r" not in sanitized
    assert "\n" not in sanitized
    assert "\\N" in sanitized


def test_select_highlight_word_heuristics():
    """Valida que stopwords em português e palavras curtas não são selecionadas para destaque."""
    words = ["e", "para", "o", "com", "disciplina", "diária"]
    chosen = select_highlight_word(words)
    assert chosen == "disciplina"

    # Caso com apenas stopwords/palavras curtas: escolhe a mais longa disponível
    fallback_words = ["o", "de", "que"]
    chosen_fallback = select_highlight_word(fallback_words)
    assert chosen_fallback == "que"


def test_format_ass_dialogue_line_highlight_and_explicit_closure():
    """Valida destaque amarelo ZUNTO! com fechamento compulsório em branco puro."""
    cue = SubtitleCue(
        start=1.25,
        end=3.50,
        text="Pare de procrastinar agora.",
        highlight_word="Pare",
    )
    line = format_ass_dialogue_line(cue)

    assert line.startswith("Dialogue: 0,0:00:01.25,0:00:03.50,Default,,0,0,0,,")
    # Tag amarela ZUNTO!
    assert r"{\c&H0015CCFA&}Pare{\c&H00FFFFFF&}" in line
    # Sem vazamento para as palavras seguintes
    assert line.endswith(r"{\c&H0015CCFA&}Pare{\c&H00FFFFFF&} de procrastinar agora.")


def test_no_style_leakage_between_cues_and_words(tmp_path: Path):
    """Valida que toda abertura de cor tem fechamento imediato para evitar style leakage."""
    cues = [
        SubtitleCue(start=0.0, end=2.0, text="FOCO absoluto no objetivo."),
        SubtitleCue(start=2.0, end=4.0, text="Execute sem desculpas hoje."),
    ]
    ass_path = tmp_path / "leakage_test.ass"
    write_ass_subtitles(cues, ass_path)

    content = ass_path.read_text(encoding="utf-8")
    dialogue_lines = [l for l in content.splitlines() if l.startswith("Dialogue:")]
    assert len(dialogue_lines) == 2

    for line in dialogue_lines:
        text_part = line.split(",,", 1)[1]
        # Quantidade de aberturas de amarelo deve ser igual a fechamentos em branco
        yellow_opens = text_part.count(r"{\c&H0015CCFA&}")
        white_closes = text_part.count(r"{\c&H00FFFFFF&}")
        assert yellow_opens == white_closes, f"Style leakage detectado na linha: {line}"
        if yellow_opens > 0:
            # Fechamento deve ocorrer antes de qualquer palavra subsequente
            pos_yellow = text_part.find(r"{\c&H0015CCFA&}")
            pos_white = text_part.find(r"{\c&H00FFFFFF&}")
            assert pos_white > pos_yellow


def test_align_words_with_timestamps_handles_punctuation_and_numbers():
    """Alinhador trata pontuações periféricas e numerais falados por extenso sem perder o fluxo."""
    script_words = "Você, não sabia... Mas 400 pessoas viram!".split()
    wb = [
        {"word": "você", "start": 0.1, "end": 0.4},
        {"word": "não", "start": 0.45, "end": 0.7},
        {"word": "sabia", "start": 0.75, "end": 1.2},
        {"word": "mas", "start": 1.3, "end": 1.5},
        {"word": "quatrocentos", "start": 1.55, "end": 2.1},
        {"word": "pessoas", "start": 2.15, "end": 2.6},
        {"word": "viram", "start": 2.65, "end": 3.1},
    ]

    aligned = align_words_with_timestamps(script_words, wb, total_duration=3.5)
    assert [w["word"] for w in aligned] == script_words
    assert aligned[0]["start"] == pytest.approx(0.1, abs=1e-3)
    assert aligned[4]["start"] == pytest.approx(1.55, abs=1e-3)
    assert aligned[4]["end"] == pytest.approx(2.1, abs=1e-3)
    assert aligned[5]["start"] == pytest.approx(2.15, abs=1e-3)
    assert aligned[6]["end"] == pytest.approx(3.1, abs=1e-3)


def test_align_words_with_timestamps_handles_compound_and_hyphenated_words():
    """Alinhador absorve múltiplos eventos WordBoundary em palavras com hífen e contrações."""
    script_words = ["O", "guarda-chuva", "d'água", "abriu."]
    wb = [
        {"word": "o", "start": 0.0, "end": 0.15},
        {"word": "guarda", "start": 0.2, "end": 0.5},
        {"word": "chuva", "start": 0.5, "end": 0.85},
        {"word": "d'", "start": 0.9, "end": 1.0},
        {"word": "água", "start": 1.0, "end": 1.35},
        {"word": "abriu", "start": 1.4, "end": 1.9},
    ]

    aligned = align_words_with_timestamps(script_words, wb, total_duration=2.0)
    assert [w["word"] for w in aligned] == script_words
    assert aligned[1]["start"] == pytest.approx(0.2, abs=1e-3)
    assert aligned[1]["end"] == pytest.approx(0.85, abs=1e-3)
    assert aligned[2]["start"] == pytest.approx(0.9, abs=1e-3)
    assert aligned[2]["end"] == pytest.approx(1.35, abs=1e-3)
    assert aligned[3]["start"] == pytest.approx(1.4, abs=1e-3)


def test_align_words_with_timestamps_handles_ambiguous_lookahead_and_repeated_words():
    """Lookahead filtra stopwords curtas e preserva ordem correta em palavras repetidas."""
    # Cenário A: omissão antes de palavra repetida ("não, não")
    script_rep = ["Ele", "disse", "que", "não,", "não", "sabia", "que", "viria."]
    wb_rep = [
        {"word": "ele", "start": 0.0, "end": 0.3},
        {"word": "disse", "start": 0.3, "end": 0.6},
        # "que" omitido pelo TTS; espaço de 0.1s antes do primeiro "não"
        {"word": "não", "start": 0.7, "end": 1.0},
        {"word": "não", "start": 1.05, "end": 1.35},
        {"word": "sabia", "start": 1.4, "end": 1.8},
        {"word": "que", "start": 1.8, "end": 1.95},
        {"word": "viria", "start": 1.95, "end": 2.4},
    ]
    res_a = align_words_with_timestamps(script_rep, wb_rep, total_duration=2.5)
    assert len(res_a) == len(script_rep)
    # Primeiro "não," deve alinhar no primeiro evento (0.7..1.0), não saltar para o segundo (1.05..1.35)
    assert res_a[3]["start"] == pytest.approx(0.7, abs=1e-3)
    assert res_a[4]["start"] == pytest.approx(1.05, abs=1e-3)
    assert res_a[5]["start"] == pytest.approx(1.4, abs=1e-3)

    # Cenário B: descompasso antes de "que" ambíguo não deve pular "não" nem alinhar com "que viria"
    script_amb = ["Ele", "disse", "que", "não", "sabia", "que", "viria"]
    wb_amb = [
        {"word": "ele", "start": 0.0, "end": 0.3},
        {"word": "ruido", "start": 0.35, "end": 0.45},
        {"word": "sabia", "start": 0.8, "end": 1.2},
        {"word": "que", "start": 1.2, "end": 1.4},
        {"word": "viria", "start": 1.4, "end": 1.9},
    ]
    res_b = align_words_with_timestamps(script_amb, wb_amb, total_duration=2.0)
    assert res_b[4]["start"] == pytest.approx(0.8, abs=1e-3)  # "sabia"
    assert res_b[5]["start"] == pytest.approx(1.2, abs=1e-3)  # "que"
    assert res_b[6]["start"] == pytest.approx(1.4, abs=1e-3)  # "viria"
    # Monotonicidade absoluta preservada
    for i in range(len(res_b)):
        assert res_b[i]["start"] <= res_b[i]["end"]
        if i > 0:
            assert res_b[i - 1]["end"] <= res_b[i]["start"]


def test_align_words_with_timestamps_recovers_after_token_desync():
    """Recupera alinhamento exato após evento espúrio seguido de palavra omitida."""
    script_words = ["Foco", "total", "agora", "mesmo", "sempre."]
    wb = [
        {"word": "foco", "start": 0.1, "end": 0.5},
        {"word": "uhm", "start": 0.55, "end": 0.65},  # evento espúrio antes de "agora" ("total" omitido)
        {"word": "agora", "start": 0.8, "end": 1.2},
        {"word": "mesmo", "start": 1.25, "end": 1.65},
        {"word": "sempre", "start": 1.7, "end": 2.2},
    ]

    aligned = align_words_with_timestamps(script_words, wb, total_duration=2.4)
    assert [w["word"] for w in aligned] == script_words
    assert aligned[2]["start"] == pytest.approx(0.8, abs=1e-3)
    assert aligned[3]["start"] == pytest.approx(1.25, abs=1e-3)
    assert aligned[4]["start"] == pytest.approx(1.7, abs=1e-3)


def test_align_words_with_timestamps_fallback_when_empty_or_none():
    """Aciona estimativa proporcional contígua quando word_timestamps for None ou vazio."""
    script_words = ["Ação", "gera", "resultado."]
    for empty_arg in (None, []):
        aligned = align_words_with_timestamps(script_words, empty_arg, total_duration=3.0)
        assert len(aligned) == 3
        assert aligned[0]["start"] == 0.0
        assert aligned[-1]["end"] == pytest.approx(3.0, abs=1e-3)
        for i in range(len(aligned) - 1):
            assert aligned[i]["end"] == pytest.approx(aligned[i + 1]["start"], abs=1e-3)


def test_align_words_with_timestamps_clamps_to_total_duration():
    """Aplica clamp estrito em [0.0, total_duration] mesmo com timestamps extrapolando o áudio."""
    script_words = ["Comece", "agora."]
    wb = [
        {"word": "comece", "start": -0.2, "end": 1.2},
        {"word": "agora", "start": 1.5, "end": 25.0},
    ]

    aligned = align_words_with_timestamps(script_words, wb, total_duration=2.5)
    assert aligned[0]["start"] == 0.0
    assert aligned[-1]["end"] == 2.5
    assert all(0.0 <= w["start"] <= w["end"] <= 2.5 for w in aligned)


def _parse_ass_time_to_cs(ts: str) -> int:
    hours_s, mins_s, sec_cs = ts.split(":")
    secs_s, cs_s = sec_cs.split(".")
    return ((int(hours_s) * 3600 + int(mins_s) * 60 + int(secs_s)) * 100) + int(cs_s)


def test_word_karaoke_dialogue_events_minimum_50ms_floor_without_overlap():
    """Piso de 50ms estende palavra curta quando há folga, mas respeita start_{i+1} quando < 50ms."""
    yellow = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)
    white = hex_to_ass_color(ZuntoPalette.PURE_WHITE)

    # Palavra 1: 20ms falados, mas próxima palavra começa só 30ms depois -> real sync prevalece (end=0.13)
    # Palavra 2: 20ms falados, com folga de 200ms antes da próxima -> piso de 50ms aplicado (end=0.18)
    # Palavra 3: estendida até no máximo total_audio_duration
    cue_words = [
        {"word": "E", "start": 0.10, "end": 0.12},
        {"word": "o", "start": 0.13, "end": 0.15},
        {"word": "foco", "start": 0.35, "end": 0.70},
    ]
    events = generate_word_karaoke_dialogue_events(cue_words, yellow, white, total_audio_duration=1.0)
    # Ev1: E [0.10..0.13] (sem invadir 0.13), Ev2: o [0.13..0.18] (50ms floor), Ev3: neutro [0.18..0.35], Ev4: foco [0.35..0.70]
    bounds = [
        (_parse_ass_time_to_cs(line.split(",")[1]), _parse_ass_time_to_cs(line.split(",")[2]))
        for line in events
    ]
    assert bounds[0] == (10, 13)
    assert bounds[1] == (13, 18)  # piso de 5 centésimos = 50ms
    assert bounds[2] == (18, 35)  # evento neutro mantendo a caixa sem empurrar "foco"
    assert bounds[3] == (35, 70)  # início de "foco" permanece ancorado em 0.35s


def test_word_karaoke_dialogue_events_strict_centisecond_contiguity():
    """Garante contiguidade inteira event[k].end_cs == event[k+1].start_cs (zero gaps/overlaps)."""
    yellow = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)
    white = hex_to_ass_color(ZuntoPalette.PURE_WHITE)

    cue_words = [
        {"word": "Você", "start": 0.124, "end": 0.416},
        {"word": "não", "start": 0.489, "end": 0.712},
        {"word": "sabia.", "start": 1.154, "end": 1.886},
    ]
    events = generate_word_karaoke_dialogue_events(cue_words, yellow, white, total_audio_duration=2.0)
    assert len(events) >= 3
    for k in range(len(events) - 1):
        end_k = _parse_ass_time_to_cs(events[k].split(",")[2])
        start_next = _parse_ass_time_to_cs(events[k + 1].split(",")[1])
        assert end_k == start_next, f"Gap/overlap entre evento {k} e {k+1}: {events[k]} vs {events[k+1]}"


def test_pause_handling_short_gap_absorption_vs_long_gap_neutral_event():
    """Pausas <= 120ms são absorvidas na palavra ativa; pausas > 120ms geram evento neutro branco."""
    yellow = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)
    white = hex_to_ass_color(ZuntoPalette.PURE_WHITE)

    cue_words = [
        {"word": "Primeiro", "start": 0.00, "end": 0.30},
        # gap = 80ms -> absorvido (Primeiro vai de 0.00 até 0.38)
        {"word": "segundo", "start": 0.38, "end": 0.60},
        # gap = 300ms -> pausa longa -> evento neutro de 0.60 até 0.90 todo branco
        {"word": "terceiro", "start": 0.90, "end": 1.40},
    ]
    events = generate_word_karaoke_dialogue_events(cue_words, yellow, white, total_audio_duration=1.5)
    assert len(events) == 4  # Primeiro + segundo + neutro + terceiro

    assert events[0].startswith("Dialogue: 0,0:00:00.00,0:00:00.38,")
    assert events[1].startswith("Dialogue: 0,0:00:00.38,0:00:00.60,")
    assert events[2].startswith("Dialogue: 0,0:00:00.60,0:00:00.90,")
    assert yellow not in events[2]
    assert events[2].endswith(",,Primeiro segundo terceiro")
    assert events[3].startswith("Dialogue: 0,0:00:00.90,0:00:01.40,")


def test_dialogue_events_contain_single_yellow_word_per_event():
    """Cada evento ativo destaca exclusivamente uma palavra em amarelo e fecha em branco puro."""
    yellow = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)
    white = hex_to_ass_color(ZuntoPalette.PURE_WHITE)

    cue_words = [
        {"word": "Ação", "start": 0.0, "end": 0.4},
        {"word": "gera", "start": 0.45, "end": 0.8},
        {"word": "poder.", "start": 0.85, "end": 1.3},
    ]
    events = generate_word_karaoke_dialogue_events(cue_words, yellow, white, total_audio_duration=1.5)
    assert len(events) == 3

    for idx, (line, active) in enumerate(zip(events, ["Ação", "gera", "poder."])):
        text_part = line.split(",,", 1)[1]
        assert text_part.count(f"\\c{yellow}") == 1, f"Evento {idx} deve conter exatamente 1 amarelo: {line}"
        assert f"{{\\c{yellow}}}{active}{{\\c{white}}}" in text_part
        assert r"\k" not in text_part and r"\kf" not in text_part


def test_generate_subtitles_with_word_timestamps_produces_karaoke_events(tmp_path: Path):
    """generate_subtitles com word_timestamps gera eventos sequenciais sem tags \\k/\\kf."""
    out_file = tmp_path / "karaoke.ass"
    timestamps = [
        {"word": "Você", "start": 0.1, "end": 0.5, "duration": 0.4},
        {"word": "não", "start": 0.55, "end": 0.9, "duration": 0.35},
        {"word": "sabia.", "start": 0.95, "end": 1.6, "duration": 0.65},
    ]
    config = SubtitleJobConfig(
        script_text="Você não sabia.",
        total_duration=2.0,
        output_path=out_file,
        word_timestamps=timestamps,
    )

    result = generate_subtitles(config)
    assert result == out_file and out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    dialogues = [l for l in content.splitlines() if l.startswith("Dialogue:")]
    assert len(dialogues) == 3
    yellow = hex_to_ass_color(ZuntoPalette.IMPACT_YELLOW)
    for line in dialogues:
        assert line.count(f"\\c{yellow}") == 1
        assert r"\k" not in line and r"\kf" not in line


def test_generate_subtitles_fallback_when_word_timestamps_none(tmp_path: Path):
    """generate_subtitles com word_timestamps=None aciona fallback proporcional válido."""
    out_file = tmp_path / "fallback.ass"
    config = SubtitleJobConfig(
        script_text="Foco constante gera transformação diária real.",
        total_duration=4.0,
        output_path=out_file,
        word_timestamps=None,
    )

    generate_subtitles(config)
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    dialogues = [l for l in content.splitlines() if l.startswith("Dialogue:")]
    assert len(dialogues) >= 1
    assert r"\k" not in content and r"\kf" not in content


def test_subtitle_service_wiring_and_sidecar_validation(tmp_path: Path):
    """StudioService repassa word_timestamps ao SubtitleJobConfig e rejeita sidecar obsoleto."""
    import hashlib
    import json
    import wave
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from viralpanel.database import Base
    from viralpanel.models import Script, SourceVideo
    from viralpanel.storage import StorageManager
    from viralpanel.studio.avatar import MockAvatarAnimator
    from viralpanel.studio.renderer import StudioRenderRequest
    from viralpanel.studio.service import StudioService
    from viralpanel.studio.voice import BaseVoiceSynthesizer, compute_file_sha256

    def _write_valid_wav(path: Path, seconds: float = 2.0) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(b"\x00\x00" * int(8000 * seconds))

    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)

    class WordBoundarySpyVoice(BaseVoiceSynthesizer):
        def __init__(self, emit_timestamps: bool):
            self.emit_timestamps = emit_timestamps
            self.last_word_timestamps = None

        def synthesize(self, text, output_path, speaker_wav=None):
            _write_valid_wav(output_path, seconds=2.0)
            if self.emit_timestamps:
                self.last_word_timestamps = [
                    {"word": "Foco", "start": 0.1, "end": 0.5, "duration": 0.4},
                    {"word": "total", "start": 0.6, "end": 1.1, "duration": 0.5},
                    {"word": "agora.", "start": 1.2, "end": 1.8, "duration": 0.6},
                ]
            else:
                self.last_word_timestamps = None
            return output_path, 2.0

    class DummyRenderer:
        def render_from_request(self, request: StudioRenderRequest):
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            request.output_path.write_bytes(b"MP4")
            return request.output_path, 2.0

    with factory() as db:
        src = SourceVideo(url="https://tiktok.com/@z/1", author="z", score=99.0)
        db.add(src)
        db.flush()
        script = Script(source_video_id=src.id, hook="Foco", script_text="Foco total agora.", version=1)
        db.add(script)
        db.commit()

        # Cenário 1: voz com WordBoundary -> 3 eventos karaoke
        storage = StorageManager(tmp_path / "s1")
        svc1 = StudioService(
            voice_synthesizer=WordBoundarySpyVoice(emit_timestamps=True),
            avatar_animator=MockAvatarAnimator(),
            renderer=DummyRenderer(),  # type: ignore[arg-type]
            storage=storage,
        )
        svc1.produce(db=db, run_id="run-ts", script=script)
        ass1 = (tmp_path / "s1" / "runs" / "run-ts" / "assets" / "captions.ass").read_text(encoding="utf-8")
        assert len([l for l in ass1.splitlines() if l.startswith("Dialogue:")]) == 3

        # Cenário 2: sidecar com text_hash de outro roteiro -> rejeitado -> fallback proporcional (1 cue)
        storage2 = StorageManager(tmp_path / "s2")
        bad_run_dir = storage2.get_run_dir("run-bad-sidecar")
        bad_sidecar = bad_run_dir / "narration.words.json"

        class SidecarOnlyVoice(BaseVoiceSynthesizer):
            def synthesize(self, text, output_path, speaker_wav=None):
                _write_valid_wav(output_path, seconds=2.0)
                bad_sidecar.write_text(
                    json.dumps({
                        "schema_version": "1.0",
                        "audio_duration_sec": 2.0,
                        "audio_hash": compute_file_sha256(output_path),
                        "text_hash": hashlib.sha256(b"Outro texto completamente diferente").hexdigest(),
                        "timestamps": [
                            {"word": "Outro", "start": 0.0, "end": 0.5},
                            {"word": "texto", "start": 0.5, "end": 1.0},
                        ],
                    }),
                    encoding="utf-8",
                )
                return output_path, 2.0

        svc2 = StudioService(
            voice_synthesizer=SidecarOnlyVoice(),
            avatar_animator=MockAvatarAnimator(),
            renderer=DummyRenderer(),  # type: ignore[arg-type]
            storage=storage2,
        )
        svc2.produce(db=db, run_id="run-bad-sidecar", script=script)
        ass2 = (bad_run_dir / "captions.ass").read_text(encoding="utf-8")
        # Fallback proporcional de 3 palavras gera 1 bloco estático com destaque heurístico ("agora")
        assert len([l for l in ass2.splitlines() if l.startswith("Dialogue:")]) == 1





