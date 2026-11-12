from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from viralpanel.cli import main as cli_main
from viralpanel.database import Base
from viralpanel.models import Asset, Script, SourceVideo
from viralpanel.storage import StorageManager
from viralpanel.studio.avatar import MockAvatarAnimator
from viralpanel.studio.inspection import InspectionRunner
from viralpanel.studio.renderer import StudioRenderRequest
from viralpanel.studio.service import StudioService
from viralpanel.studio.voice import MockVoiceSynthesizer


def _create_test_session_factory():
    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng, expire_on_commit=False)


def test_e2e_normal_scenario_produces_valid_media_and_frame_sampling(tmp_path: Path):
    """Executa o Cenário Normal via InspectionRunner e valida mídia, 3 assets e amostragem de frames."""
    factory = _create_test_session_factory()
    runner = InspectionRunner()
    out_dir = tmp_path / "inspection_normal"

    with factory() as db:
        result = runner.run_scenario_normal(db=db, output_dir=out_dir)

    assert Path(result["video_path"]).exists()
    assert result["file_size_bytes"] > 1000
    assert result["final_asset_type"] == "final_video"
    assert result["assets_count"] == 3
    assert result["assets_created"] == ["audio", "avatar", "final_video"]
    assert result["source_status"] == "produced"

    v_val = result["video_validation"]
    assert v_val.is_valid is True, f"Erros de validação de vídeo: {v_val.errors}"
    assert v_val.metrics["width"] == 1080
    assert v_val.metrics["height"] == 1920
    assert v_val.metrics["video_codec"] == "h264"
    assert v_val.metrics["pix_fmt"] == "yuv420p"
    assert v_val.metrics["audio_codec"] == "aac"
    assert v_val.metrics["sample_rate"] >= 44100

    a_val = result["avatar_validation"]
    assert a_val.is_valid is True, f"Erros de validação do avatar: {a_val.errors}"
    assert a_val.metrics["video_codec"] == "png"
    assert a_val.metrics["pix_fmt"] == "rgba"

    p_val = result["pixel_inspection"]
    assert p_val.passed is True, f"Erros de amostragem de pixels: {p_val.errors}"
    assert p_val.details["distributed_points_checked"] >= 90
    assert p_val.details["distributed_points_failed"] == 0
    assert p_val.details["yellow_border_rays_confirmed"] == "5/5"

    assert all(result["ass_checks"].values())


def test_e2e_fallback_audio_only_scenario(tmp_path: Path):
    """Executa o Cenário Fallback (áudio puro -> lavfi #0f172a single-pass) e valida composição."""
    factory = _create_test_session_factory()
    runner = InspectionRunner()
    out_dir = tmp_path / "inspection_fallback"

    with factory() as db:
        result = runner.run_scenario_fallback(db=db, output_dir=out_dir)

    assert Path(result["video_path"]).exists()
    assert result["no_temp_bg_file"] is True
    assert result["assets_count"] == 3
    assert result["assets_created"] == ["audio", "avatar", "final_video"]
    assert result["source_status"] == "produced"

    v_val = result["video_validation"]
    assert v_val.is_valid is True, f"Erros de validação no fallback: {v_val.errors}"

    a_val = result["avatar_validation"]
    assert a_val.is_valid is True, f"Erros de avatar no fallback: {a_val.errors}"

    p_val = result["pixel_inspection"]
    assert p_val.passed is True, f"Erros de pixels no fallback: {p_val.errors}"
    assert p_val.details["expected_bg_rgb"] == (15, 23, 42)
    assert p_val.details["distributed_points_failed"] == 0


def test_studio_produce_atomic_rollback_on_failure(tmp_path: Path):
    """Comprova que falha no render final reverte os assets intermediários (audio e avatar) na sessão e no banco."""
    factory = _create_test_session_factory()
    flushed_before_crash: list[str] = []

    with factory() as db:
        src = SourceVideo(
            url="https://www.tiktok.com/@zunto/video/atomic-fail-test",
            author="zunto",
            score=95.0,
        )
        db.add(src)
        db.flush()

        script = Script(
            source_video_id=src.id,
            hook="Hook de teste atômico",
            script_text="Texto para testar rollback atômico dos três assets no StudioService.",
            version=1,
        )
        db.add(script)
        db.commit()
        script_id = script.id
        src_id = src.id

        class FailingRenderer:
            def render_from_request(self, request: StudioRenderRequest) -> tuple[Path, float]:
                # Verifica que os 2 assets intermediários (audio e avatar) já foram flushados na transação
                in_tx_assets = list(db.scalars(select(Asset).where(Asset.script_id == script_id)).all())
                flushed_before_crash.extend(sorted(a.asset_type for a in in_tx_assets))
                raise RuntimeError("Falha simulada na codificação de vídeo")

        service = StudioService(
            voice_synthesizer=MockVoiceSynthesizer(min_duration=1.5, max_duration=1.5),
            avatar_animator=MockAvatarAnimator(),
            renderer=FailingRenderer(),  # type: ignore[arg-type]
            storage=StorageManager(tmp_path / "atomic_storage"),
        )

        with pytest.raises(RuntimeError, match="Falha simulada na codificação de vídeo"):
            service.produce(db=db, run_id="run-atomic-fail", script=script)

        # 1. Confirma que os registros intermediários haviam sido inseridos na transação antes da falha
        assert flushed_before_crash == ["audio", "avatar"]

        # 2. Verifica o estado interno da sessão SQLAlchemy imediatamente após o rollback
        assert len(db.new) == 0, "Não deve haver objetos pendentes em db.new após rollback"
        assert len(db.dirty) == 0, "Não deve haver objetos sujos em db.dirty após rollback"
        residual_identity_assets = [obj for obj in db.identity_map.values() if isinstance(obj, Asset)]
        assert len(residual_identity_assets) == 0, (
            f"Identity map da sessão não deve reter objetos Asset revertidos: {residual_identity_assets}"
        )

        # 3. Força expiração da sessão atual e consulta novamente
        db.expire_all()
        remaining_in_same_session = list(db.scalars(select(Asset).where(Asset.script_id == script_id)).all())
        assert remaining_in_same_session == []

    # 4. Consulta em uma nova sessão totalmente independente para confirmar persistência zero
    with factory() as fresh_db:
        remaining_in_fresh_session = list(fresh_db.scalars(select(Asset).where(Asset.script_id == script_id)).all())
        assert remaining_in_fresh_session == []
        fresh_src = fresh_db.get(SourceVideo, src_id)
        assert fresh_src is not None
        assert fresh_src.status == "pending"


def test_inspection_directory_isolation_and_cli_execution(tmp_path: Path):
    """Garante que clean_inspection_dir elimina resíduos anteriores e que o CLI compartilha InspectionRunner."""
    insp_dir = tmp_path / "isolated_inspection"
    insp_dir.mkdir(parents=True, exist_ok=True)

    # Cria arquivos e subpastas residuais fantasma
    ghost_file = insp_dir / "old_residual_video.mp4"
    ghost_file.write_bytes(b"GHOST_DATA")
    ghost_subdir = insp_dir / "stale_subfolder"
    ghost_subdir.mkdir()
    (ghost_subdir / "stale.raw").write_bytes(b"STALE")

    report_file = tmp_path / "INSPECTION-REPORT.md"

    exit_code = cli_main(
        [
            "validate-e2e",
            "--output-dir",
            str(insp_dir),
            "--report-path",
            str(report_file),
        ]
    )
    assert exit_code == 0

    # Resíduos antigos devem ter sido completamente expurgados
    assert not ghost_file.exists()
    assert not ghost_subdir.exists()

    # Novos artefatos determinísticos devem existir
    assert (insp_dir / "scenario_normal_final.mp4").exists()
    assert (insp_dir / "scenario_fallback_final.mp4").exists()
    assert (insp_dir / "README.md").exists()
    assert report_file.exists()

    report_text = report_file.read_text(encoding="utf-8")
    assert "[PENDENTE DE INSPEÇÃO HUMANA]" in report_text
    assert "- [x]" not in report_text, "Nenhum critério visual deve ser auto-aprovado no relatório"
