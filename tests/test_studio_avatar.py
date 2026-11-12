import json
import shutil
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from viralpanel.branding import SafeZones9x16, ZuntoPalette
from viralpanel.studio.avatar import (
    AudioReactiveAvatarAnimator,
    AvatarConfig,
    MockAvatarAnimator,
    ensure_default_avatar_image,
)
from viralpanel.studio.voice import MockVoiceSynthesizer


def test_avatar_config_defaults_and_immutability():
    """Valida DTO AvatarConfig tipado, imutável e com defaults calibrados per D-05."""
    config = AvatarConfig()
    assert config.avatar_image_path is None
    assert config.size == SafeZones9x16.AVATAR_SIZE == 300
    assert config.crop_mode == "circle_alpha"
    assert config.border_color == ZuntoPalette.IMPACT_YELLOW == "#FACC15"
    assert config.border_width == 4
    assert config.overlay_x_expr == "W-w-54"
    assert config.overlay_y_expr == "H-h-320"
    assert config.enable_waveform is True
    assert config.waveform_color == "#FACC15@0.85"

    with pytest.raises(FrozenInstanceError):
        config.size = 360

    custom = AvatarConfig(
        avatar_image_path=Path("assets/custom.png"),
        size=280,
        crop_mode="native_rgba",
        border_color="#FFFFFF",
        border_width=2,
        overlay_x_expr="W-w-60",
        overlay_y_expr="H-h-300",
        enable_waveform=False,
        waveform_color="#FFFFFF@0.5",
    )
    assert custom.size == 280
    assert custom.border_width == 2
    assert custom.enable_waveform is False


def test_mock_avatar_animator_matches_voice_duration(tmp_path):
    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "avatar.mp4"

    _, voice_dur = MockVoiceSynthesizer().synthesize("Disciplina constrói liberdade todos os dias.", voice_path)
    out_path, avatar_dur = MockAvatarAnimator().generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert abs(avatar_dur - voice_dur) < 0.5


def test_ensure_default_avatar_image_creates_file(tmp_path):
    target = tmp_path / "avatar.png"
    result = ensure_default_avatar_image(target)
    assert result.exists()
    assert result.stat().st_size > 0


def test_audio_reactive_avatar_animator(tmp_path):
    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "reactive_avatar.mp4"
    img_path = tmp_path / "img.png"
    ensure_default_avatar_image(img_path)

    _, voice_dur = MockVoiceSynthesizer().synthesize("Foco diário.", voice_path)
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    out_path, dur = animator.generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert dur > 0


def test_avatar_video_codec_and_pixel_format(tmp_path):
    """Valida metadados de codec 'png' e pix_fmt 'rgba' em avatar.mp4 per AVTR-03."""
    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg/ffprobe não disponíveis no ambiente")

    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "avatar.mp4"
    img_path = tmp_path / "img.png"
    ensure_default_avatar_image(img_path)

    MockVoiceSynthesizer().synthesize("Teste codec e formato.", voice_path)
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    out_path, dur = animator.generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert dur > 0

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,pix_fmt",
        "-of",
        "json",
        str(out_path),
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    probe_data = json.loads(proc.stdout)
    assert "streams" in probe_data and len(probe_data["streams"]) > 0
    stream = probe_data["streams"][0]

    assert stream["codec_name"] == "png"
    assert stream["pix_fmt"] == "rgba"


def test_avatar_circular_alpha_and_yellow_border_pixels(tmp_path):
    """Renderiza 1 frame de avatar.mp4 em rawvideo rgba e inspeciona pixels numéricos per D-01, AVTR-01 e BRND-01."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg não disponível no ambiente")

    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "avatar.mp4"
    img_path = tmp_path / "img.png"
    ensure_default_avatar_image(img_path)

    MockVoiceSynthesizer().synthesize("Análise empírica de pixels do avatar.", voice_path)
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    animator.generate_avatar_video(voice_path, avatar_path)

    raw_path = tmp_path / "frame.raw"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(avatar_path),
            "-vframes",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            str(raw_path),
        ],
        check=True,
        capture_output=True,
    )

    raw_bytes = raw_path.read_bytes()
    assert len(raw_bytes) == 300 * 300 * 4

    def get_rgba(x: int, y: int) -> tuple[int, int, int, int]:
        offset = (y * 300 + x) * 4
        return tuple(raw_bytes[offset : offset + 4])

    # 1. Quatro cantos externos do bounding box 300x300 possuem Alpha == 0 (transparência total)
    corners = [(10, 10), (290, 10), (10, 290), (290, 290)]
    for pt in corners:
        rgba = get_rgba(*pt)
        assert rgba[3] == 0, f"Canto {pt} deveria ter alfa 0, obteve: {rgba}"

    # 2. Pontos na borda anelar circular (raio entre 146px e 150px) possuem Alpha > 200 e cor amarela ZUNTO! (#FACC15: R > 220, G > 180, B < 60)
    border_points = [(150, 2), (150, 297), (2, 150), (297, 150)]
    for pt in border_points:
        r, g, b, a = get_rgba(*pt)
        assert a > 200, f"Borda {pt} deveria ter alfa > 200, obteve: {a}"
        assert r > 220 and g > 180 and b < 60, f"Borda {pt} deveria ser amarela #FACC15, obteve R={r}, G={g}, B={b}"

    # 3. Centro do avatar (150, 150) é opaco (alpha == 255)
    center_rgba = get_rgba(150, 150)
    assert center_rgba[3] == 255, f"Centro deveria ter alfa 255, obteve: {center_rgba[3]}"

    # 4. Confinamento do showwaves: cantos inferiores externos mantêm Alpha == 0
    lower_outside = [(15, 250), (285, 250)]
    for pt in lower_outside:
        rgba = get_rgba(*pt)
        assert rgba[3] == 0, f"Canto inferior externo {pt} deveria ter alfa 0, obteve: {rgba}"


def test_showwaves_background_transparency(tmp_path):
    """Comprova empiricamente que o showwaves não produz fundo opaco ou retângulo preto per D-04."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg não disponível no ambiente")

    blue_img = tmp_path / "solid_blue.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=300x300:d=0.1",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(blue_img),
        ],
        check=True,
        capture_output=True,
    )

    audio_path = tmp_path / "voice.wav"
    MockVoiceSynthesizer().synthesize("Confinamento e transparência do showwaves.", audio_path)

    animator = AudioReactiveAvatarAnimator()
    avatar_out = tmp_path / "blue_avatar.mp4"
    animator.generate_avatar_video(audio_path, avatar_out, avatar_image_path=blue_img)

    raw_path = tmp_path / "blue_frame.raw"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(avatar_out),
            "-vframes",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            str(raw_path),
        ],
        check=True,
        capture_output=True,
    )

    raw_bytes = raw_path.read_bytes()
    assert len(raw_bytes) == 300 * 300 * 4

    def get_rgba(x: int, y: int) -> tuple[int, int, int, int]:
        offset = (y * 300 + x) * 4
        return tuple(raw_bytes[offset : offset + 4])

    # Amostrar linha vertical central na região da onda (Y=200..280)
    # Pixels onde não há traço sonoro preservam o azul e alfa intactos (sem caixa preta opaca)
    wave_sample_ys = [205, 210, 220, 230, 240, 250, 260, 270]
    for y in wave_sample_ys:
        r, g, b, a = get_rgba(150, y)
        assert a == 255, f"Pixel em (150, {y}) teve alfa degradado: {a}"
        assert not (r == 0 and g == 0 and b == 0), f"Pixel em (150, {y}) tornou-se preto indesejado"
        is_blue = (b > 200 and r < 50 and g < 50)
        is_yellow = (r > 150 and g > 120)
        assert is_blue or is_yellow, f"Pixel em (150, {y}) tem cor inesperada: R={r}, G={g}, B={b}"


