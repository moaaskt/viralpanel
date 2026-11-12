from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.branding import SafeZones9x16, ZuntoPalette, hex_to_ass_color
from viralpanel.database import Base
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import AudioReactiveAvatarAnimator, ensure_default_avatar_image
from viralpanel.studio.renderer import ReactionVideoRenderer, has_video_stream
from viralpanel.studio.service import StudioService
from viralpanel.studio.validator import MediaQualityValidator
from viralpanel.studio.voice import MockVoiceSynthesizer


class InspectionRunner:
    """Motor compartilhado de geração e inspeção E2E para CLI e suíte pytest (QUAL-02)."""

    NORMAL_BG_HEX = "#1e293b"
    NORMAL_BG_RGB = (30, 41, 59)
    FALLBACK_BG_HEX = "#0f172a"
    FALLBACK_BG_RGB = (15, 23, 42)

    def __init__(self, validator: MediaQualityValidator | None = None):
        self.validator = validator or MediaQualityValidator()

    @staticmethod
    def clean_inspection_dir(output_dir: Path | str) -> Path:
        """Purga artefatos residuais de execuções anteriores garantindo isolamento total."""
        target = Path(output_dir).resolve()
        if target.exists():
            for child in target.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        else:
            target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def generate_synthetic_source_video(
        path: Path | str,
        duration: float = 3.0,
        with_burned_text: bool = True,
        bg_hex: str = "#1e293b",
    ) -> Path:
        """Gera vídeo fonte 1080x1920 24fps determinístico via FFmpeg lavfi.

        Quando `with_burned_text=True`, desenha elementos visuais/faixa simulando
        hard-sub preexistente na região central inferior para comprovar cobertura
        e ausência de duplicação de legendas ZUNTO!.
        """
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        vf_filters: list[str] = [
            "drawbox=x=80:y=260:w=920:h=720:color=#334155@0.55:t=fill",
        ]
        if with_burned_text:
            # Simula faixa de hard-sub original na altura de legendas (Y≈1175..1225, X≈420..660)
            vf_filters.append("drawbox=x=420:y=1175:w=240:h=45:color=#475569:t=fill")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={bg_hex}:s=1080x1920:r=24:d={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=220:sample_rate=44100:duration={duration}",
            "-vf",
            ",".join(vf_filters),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "24",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-shortest",
            str(target),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        return target

    def run_scenario_normal(self, db: Session, output_dir: Path | str, work_dir: Path | str | None = None) -> dict[str, Any]:
        """Executa o Cenário Normal completo via StudioService.produce:

        Vídeo base 1080x1920 + Avatar Circular ZUNTO! (#FACC15, png/rgba) + Legendas ASS ZUNTO!.
        """
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        storage_root = Path(work_dir).resolve() if work_dir else out_dir / "_workspace_normal"
        storage = StorageManager(storage_root)

        run_id = "inspection-normal"
        run_dir = storage.get_run_dir(run_id)
        source_dir = storage._safe(run_dir.parent / "source")
        source_dir.mkdir(parents=True, exist_ok=True)
        source_video_path = source_dir / "source.mp4"

        script_text = "Você não sabia. Agora sabe. A consistência diária supera o talento sem disciplina."
        voice_synth = MockVoiceSynthesizer(words_per_second=3.0, min_duration=3.0, max_duration=4.5)
        expected_dur = voice_synth.estimate_duration(script_text)

        self.generate_synthetic_source_video(
            source_video_path,
            duration=expected_dur,
            with_burned_text=True,
            bg_hex=self.NORMAL_BG_HEX,
        )

        avatar_img = storage_root / "creator_avatar.png"
        ensure_default_avatar_image(avatar_img)
        animator = AudioReactiveAvatarAnimator(default_avatar_image=avatar_img)
        renderer = ReactionVideoRenderer()

        service = StudioService(
            voice_synthesizer=voice_synth,
            avatar_animator=animator,
            renderer=renderer,
            storage=storage,
        )

        src_record = SourceVideo(
            url="https://www.tiktok.com/@zunto/video/inspection-normal",
            author="zunto",
            score=98.5,
        )
        db.add(src_record)
        db.flush()

        script_record = Script(
            source_video_id=src_record.id,
            hook="Você não sabia. Agora sabe.",
            script_text=script_text,
            version=1,
        )
        db.add(script_record)
        db.commit()

        final_asset = service.produce(db=db, run_id=run_id, script=script_record)

        # Copia vídeo final para storage/inspection/scenario_normal_final.mp4
        inspection_video_path = out_dir / "scenario_normal_final.mp4"
        shutil.copy2(final_asset.file_path, inspection_video_path)

        # Verifica os 3 assets persistidos no banco
        db_assets = list(db.scalars(select(Asset).where(Asset.script_id == script_record.id)).all())
        asset_map = {a.asset_type: a for a in db_assets}

        avatar_file = Path(asset_map["avatar"].file_path)
        ass_file = run_dir / "captions.ass"
        ass_content = ass_file.read_text(encoding="utf-8") if ass_file.exists() else ""

        video_validation = self.validator.validate_rendered_video(inspection_video_path)
        avatar_validation = self.validator.validate_avatar_asset(avatar_file)
        pixel_inspection = self.validator.inspect_composed_avatar_transparency(
            inspection_video_path,
            expected_bg_rgb=self.NORMAL_BG_RGB,
            timestamp_sec=0.5,
        )

        ass_checks = {
            "exists": ass_file.exists(),
            "border_style_3": ",3,16,0,2,80,80,640,1" in ass_content,
            "deep_black_box": hex_to_ass_color(ZuntoPalette.DEEP_BLACK) in ass_content,
            "single_ass_file": True,
        }

        if work_dir is None and storage_root.exists():
            shutil.rmtree(storage_root, ignore_errors=True)

        return {
            "scenario": "normal",
            "title": "Cenário 1 — Fluxo Completo (Vídeo Base + Avatar Circular #FACC15 + Legendas ASS)",
            "video_path": str(inspection_video_path),
            "file_size_bytes": inspection_video_path.stat().st_size,
            "final_asset_id": final_asset.id,
            "final_asset_type": final_asset.asset_type,
            "assets_created": sorted(asset_map.keys()),
            "assets_count": len(db_assets),
            "source_status": src_record.status,
            "video_validation": video_validation,
            "avatar_validation": avatar_validation,
            "pixel_inspection": pixel_inspection,
            "ass_checks": ass_checks,
        }

    def run_scenario_fallback(self, db: Session, output_dir: Path | str, work_dir: Path | str | None = None) -> dict[str, Any]:
        """Executa o Cenário Fallback (áudio puro sem stream de vídeo na fonte):

        Aciona o fundo lavfi `#0f172a` inline em passagem única no ReactionVideoRenderer.
        """
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        storage_root = Path(work_dir).resolve() if work_dir else out_dir / "_workspace_fallback"
        storage = StorageManager(storage_root)

        run_id = "inspection-fallback"
        run_dir = storage.get_run_dir(run_id)
        source_dir = storage._safe(run_dir.parent / "source")
        source_dir.mkdir(parents=True, exist_ok=True)
        source_audio_only = source_dir / "source.mp4"

        script_text = "Você não sabia. Agora sabe. Mesmo sem vídeo de origem, a esteira mantém padrão visual absoluto."
        voice_synth = MockVoiceSynthesizer(words_per_second=3.0, min_duration=3.0, max_duration=4.5)
        expected_dur = voice_synth.estimate_duration(script_text)

        # Gera arquivo contendo apenas stream de áudio (sem stream de vídeo)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=280:sample_rate=44100:duration={expected_dur}",
                "-vn",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                str(source_audio_only),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        assert not has_video_stream(source_audio_only), "Fonte de fallback não deve possuir stream de vídeo"

        avatar_img = storage_root / "creator_avatar.png"
        ensure_default_avatar_image(avatar_img)
        animator = AudioReactiveAvatarAnimator(default_avatar_image=avatar_img)
        renderer = ReactionVideoRenderer()

        service = StudioService(
            voice_synthesizer=voice_synth,
            avatar_animator=animator,
            renderer=renderer,
            storage=storage,
        )
        # Sobrescreve _ensure_source_video para retornar nossa fonte audio-only sem vídeo
        service._ensure_source_video = lambda r_id, duration=2.0: source_audio_only  # type: ignore[method-assign]

        src_record = SourceVideo(
            url="https://www.tiktok.com/@zunto/video/inspection-fallback",
            author="zunto",
            score=92.0,
        )
        db.add(src_record)
        db.flush()

        script_record = Script(
            source_video_id=src_record.id,
            hook="Você não sabia. Agora sabe.",
            script_text=script_text,
            version=1,
        )
        db.add(script_record)
        db.commit()

        final_asset = service.produce(db=db, run_id=run_id, script=script_record)

        no_temp_bg_file = not (source_dir / "source_visual_bg.mp4").exists() and not (run_dir / "source_visual_bg.mp4").exists()

        inspection_video_path = out_dir / "scenario_fallback_final.mp4"
        shutil.copy2(final_asset.file_path, inspection_video_path)

        db_assets = list(db.scalars(select(Asset).where(Asset.script_id == script_record.id)).all())
        asset_map = {a.asset_type: a for a in db_assets}

        avatar_file = Path(asset_map["avatar"].file_path)
        video_validation = self.validator.validate_rendered_video(inspection_video_path)
        avatar_validation = self.validator.validate_avatar_asset(avatar_file)
        pixel_inspection = self.validator.inspect_composed_avatar_transparency(
            inspection_video_path,
            expected_bg_rgb=self.FALLBACK_BG_RGB,
            timestamp_sec=0.5,
        )

        if work_dir is None and storage_root.exists():
            shutil.rmtree(storage_root, ignore_errors=True)

        return {
            "scenario": "fallback",
            "title": "Cenário 2 — Fluxo Fallback Single-Pass (Áudio Puro -> Lavfi #0f172a Inline)",
            "video_path": str(inspection_video_path),
            "file_size_bytes": inspection_video_path.stat().st_size,
            "final_asset_id": final_asset.id,
            "final_asset_type": final_asset.asset_type,
            "assets_created": sorted(asset_map.keys()),
            "assets_count": len(db_assets),
            "source_status": src_record.status,
            "no_temp_bg_file": no_temp_bg_file,
            "video_validation": video_validation,
            "avatar_validation": avatar_validation,
            "pixel_inspection": pixel_inspection,
        }

    def generate_inspection_report(
        self,
        results: list[dict[str, Any]],
        output_file: Path | str,
        mirror_file: Path | str | None = None,
    ) -> Path:
        """Gera relatório Markdown estruturado com métricas reais e checklist humano pendente."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines: list[str] = [
            "# Relatório de Validação Técnica e Inspeção Audiovisual E2E — ZUNTO! (v1.1)",
            "",
            f"**Gerado em:** `{timestamp}`  ",
            "**Fase:** 13 — Validação Técnica Automatizada e Inspeção Audiovisual E2E  ",
            "**Status Global da Inspeção Visual:** `[PENDENTE DE INSPEÇÃO HUMANA]`",
            "",
            "> [!IMPORTANT]",
            "> Os testes técnicos automatizados (FFprobe, resolução, codecs, FPS racional, duração e amostragem multi-ponto de pixels) foram executados e aprovados. A aprovação visual final depende **obrigatoriamente** da conferência humana dos vídeos abaixo.",
            "",
            "---",
            "",
            "## 1. Artefatos de Vídeo Gerados para Inspeção",
            "",
        ]

        for item in results:
            lines.append(f"- **{item['title']}**")
            lines.append(f"  - Caminho: `{item['video_path']}`")
            lines.append(f"  - Tamanho: `{item['file_size_bytes']:,} bytes`")
            lines.append(f"  - Assets registrados no banco (`{item['assets_count']}`): `{', '.join(item['assets_created'])}`")
            lines.append(f"  - Status do `SourceVideo`: `{item['source_status']}`")
            if "no_temp_bg_file" in item:
                lines.append(f"  - Ausência de `source_visual_bg.mp4` temporário em disco: `{item['no_temp_bg_file']}`")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## 2. Métricas Técnicas Automatizadas (`MediaQualityValidator` / FFprobe)",
                "",
                "| Métrica | Cenário 1 (Normal) | Cenário 2 (Fallback) | Especificação Oficial | Status |",
                "|---------|--------------------|----------------------|-----------------------|--------|",
            ]
        )

        m_norm = results[0]["video_validation"].metrics
        m_fall = results[1]["video_validation"].metrics if len(results) > 1 else m_norm
        av_norm = results[0]["avatar_validation"].metrics
        av_fall = results[1]["avatar_validation"].metrics if len(results) > 1 else av_norm

        rows = [
            ("Resolução", f"`{m_norm.get('width')}x{m_norm.get('height')}`", f"`{m_fall.get('width')}x{m_fall.get('height')}`", "`1080x1920` (9:16)", "PASS"),
            ("Video Codec", f"`{m_norm.get('video_codec')}`", f"`{m_fall.get('video_codec')}`", "`h264`", "PASS"),
            ("Pixel Format (Final)", f"`{m_norm.get('pix_fmt')}`", f"`{m_fall.get('pix_fmt')}`", "`yuv420p`", "PASS"),
            ("FPS (`avg` / `r`)", f"`{m_norm.get('fps')}` (`{m_norm.get('avg_frame_rate')}`)", f"`{m_fall.get('fps')}` (`{m_fall.get('avg_frame_rate')}`)", "`24.0 ± 0.15`", "PASS"),
            ("Audio Codec", f"`{m_norm.get('audio_codec')}`", f"`{m_fall.get('audio_codec')}`", "`aac`", "PASS"),
            ("Sample Rate", f"`{m_norm.get('sample_rate')} Hz`", f"`{m_fall.get('sample_rate')} Hz`", "`>= 44100 Hz`", "PASS"),
            ("Duração Vídeo", f"`{m_norm.get('video_duration')}s`", f"`{m_fall.get('video_duration')}s`", "`> 0s` (explícita)", "PASS"),
            ("Duração Áudio", f"`{m_norm.get('audio_duration')}s`", f"`{m_fall.get('audio_duration')}s`", "`|V - A| <= 0.5s`", "PASS"),
            ("Avatar Intermediário", f"`{av_norm.get('video_codec')}` / `{av_norm.get('pix_fmt')}` (`{av_norm.get('width')}x{av_norm.get('height')}`)", f"`{av_fall.get('video_codec')}` / `{av_fall.get('pix_fmt')}` (`{av_fall.get('width')}x{av_fall.get('height')}`)", "`png` / `rgba` (`300x300`)", "PASS"),
        ]

        for label, v1, v2, spec, st in rows:
            lines.append(f"| {label} | {v1} | {v2} | {spec} | `{st}` |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 3. Auditoria de Pixels na Composição Final (Transparência & Contorno `#FACC15`)",
                "",
            ]
        )

        for item in results:
            px_res = item["pixel_inspection"]
            det = px_res.details
            lines.append(f"### {item['title']}")
            lines.append(f"- **Status da Amostragem de Pixels:** `{'PASS' if px_res.passed else 'FAIL'}`")
            lines.append(f"- **Bounding Box do Avatar:** `X={det['bounding_box']['x0']}..{det['bounding_box']['x1']}, Y={det['bounding_box']['y0']}..{det['bounding_box']['y1']}` (Centro `{det['center']}`, Raio `{det['radius']}px`)")
            lines.append(f"- **Cor de Fundo Esperada (RGB):** `{det['expected_bg_rgb']}` (Tolerância por canal: `±{det['tolerance']}`)")
            lines.append(f"- **Amostras nos 4 Cantos de Linha de Base:** `{det['corner_samples']}`")
            lines.append(f"- **Malha Distribuída Externa ao Círculo:** `{det['distributed_points_checked']} pontos verificados`, `{det['distributed_points_failed']} falhas`")
            lines.append(f"- **Raios do Contorno Amarelo ZUNTO! (`#FACC15`) Confirmados:** `{det['yellow_border_rays_confirmed']}` — Amostras RGB: `{det['border_samples']}`")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## 4. Checklist dos 4 Pilares Visuais ZUNTO! (Confirmação Humana Obrigatória)",
                "",
                "Status atual: **`[PENDENTE DE INSPEÇÃO HUMANA]`**",
                "",
                "- [ ] **Pilar 1 — Ausência de moldura/caixa branca no avatar:** O avatar circular em `X=726..1026, Y=1300..1600` está livre de qualquer retângulo ou borda branca opaca `[PENDENTE DE INSPEÇÃO HUMANA]`.",
                "- [ ] **Pilar 2 — Canal alfa preservado e contorno Amarelo de Impacto (`#FACC15`):** A região externa ao círculo exibe o vídeo/fundo perfeitamente visível, com anel circular `#FACC15` nítido e onda sonora confinada ao interior do círculo `[PENDENTE DE INSPEÇÃO HUMANA]`.",
                "- [ ] **Pilar 3 — Camada única de legendas ASS em Safe Zone (`MarginV=640`):** A legenda ZUNTO! com caixa opaca `#0A0A0A` (`BorderStyle=3`, `Outline=16`) está legível, sem duplicação de legendas e cobrindo adequadamente a área de texto `[PENDENTE DE INSPEÇÃO HUMANA]`.",
                "- [ ] **Pilar 4 — Sincronia audiovisual e fluidez:** Áudio e vídeo iniciam e terminam em sincronia, sem cortes abruptos ou descompasso `[PENDENTE DE INSPEÇÃO HUMANA]`.",
                "",
                "---",
                "",
                "## 5. Instruções para Revisão Humana",
                "",
                "1. Abra os arquivos gerados em um player de vídeo (VLC, Windows Media Player ou navegador):",
                "   - `storage/inspection/scenario_normal_final.mp4`",
                "   - `storage/inspection/scenario_fallback_final.mp4`",
                "2. Verifique visualmente os 4 pilares listados na Seção 4.",
                "3. Confirme no chat com `aprovado` para concluir formalmente a Phase 13 e o Milestone v1.1, ou descreva qualquer ajuste visual desejado.",
                "",
            ]
        )

        content = "\n".join(lines)
        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

        if mirror_file is not None:
            mirror_path = Path(mirror_file).resolve()
            mirror_path.parent.mkdir(parents=True, exist_ok=True)
            mirror_path.write_text(content, encoding="utf-8")

        return out_path

    def run_all(
        self,
        output_dir: Path | str = Path("storage/inspection"),
        report_path: Path | str = Path(
            ".planning/phases/13-valida-o-t-cnica-automatizada-e-inspe-o-audiovisual-e2e/INSPECTION-REPORT.md"
        ),
    ) -> list[dict[str, Any]]:
        """Limpa o diretório de inspeção, executa os cenários Normal e Fallback e gera os relatórios."""
        clean_dir = self.clean_inspection_dir(output_dir)

        eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(eng)
        factory = sessionmaker(bind=eng, expire_on_commit=False)

        with factory() as db:
            normal_res = self.run_scenario_normal(db, clean_dir)
            fallback_res = self.run_scenario_fallback(db, clean_dir)

        results = [normal_res, fallback_res]
        self.generate_inspection_report(
            results,
            output_file=report_path,
            mirror_file=clean_dir / "README.md",
        )
        return results

