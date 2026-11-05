from pathlib import Path

from sqlalchemy.orm import Session

from viralpanel.config import get_settings
from viralpanel.models import Asset, PipelineRun
from viralpanel.telegram.approval import parse_approval_callback_data, send_approval_request
from viralpanel.telegram.client import BaseTelegramClient, MockTelegramClient
from viralpanel.telegram.notifier import TelegramNotifier


class SupervisionService:
    """Gerencia notificações e o fluxo de aprovação humana via Telegram."""

    def __init__(
        self,
        client: BaseTelegramClient | None = None,
        notifier: TelegramNotifier | None = None,
        supervised_mode: bool | None = None,
    ):
        self.client = client or MockTelegramClient()
        self.notifier = notifier or TelegramNotifier(client=self.client)
        self.supervised_mode = (
            get_settings().telegram_supervised_mode if supervised_mode is None else supervised_mode
        )

    def handle_post_production(
        self,
        db: Session,
        run: PipelineRun,
        final_asset: Asset,
        hook: str = "",
        score: float | None = None,
    ) -> str:
        """Retorna o status de aprovação ('awaiting_approval' ou 'approved')."""
        meta = dict(run.run_metadata or {})
        if not self.supervised_mode:
            meta["approval_status"] = "approved"
            run.run_metadata = meta
            if final_asset.script and final_asset.script.source_video:
                final_asset.script.source_video.status = "approved"
            db.commit()
            self.notifier.notify_stage_completed(
                run.id, "supervision", {"mode": "auto", "approval_status": "approved"}
            )
            return "approved"

        send_approval_request(
            client=self.client,
            run_id=run.id,
            video_path=Path(final_asset.file_path),
            hook=hook,
            score=score,
        )
        meta["approval_status"] = "awaiting_approval"
        run.run_metadata = meta
        if final_asset.script and final_asset.script.source_video:
            final_asset.script.source_video.status = "awaiting_approval"
        db.commit()
        return "awaiting_approval"

    def process_callback(
        self,
        db: Session,
        callback_data: str,
        callback_query_id: str | None = None,
    ) -> str:
        """Processa clique humano nos botões 'Aprovar' ou 'Rejeitar' e atualiza o banco."""
        action, run_id = parse_approval_callback_data(callback_data)
        run = db.get(PipelineRun, run_id)
        if run is None:
            raise ValueError(f"PipelineRun não encontrado: {run_id}")

        new_status = "approved" if action == "approve" else "rejected"
        meta = dict(run.run_metadata or {})
        meta["approval_status"] = new_status
        run.run_metadata = meta

        final_asset_id = meta.get("final_asset_id")
        if final_asset_id:
            asset = db.get(Asset, final_asset_id)
            if asset and asset.script and asset.script.source_video:
                asset.script.source_video.status = new_status

        db.commit()

        if callback_query_id:
            label = "Vídeo aprovado para publicação! ✅" if new_status == "approved" else "Vídeo rejeitado. ❌"
            self.client.answer_callback_query(callback_query_id, text=label)

        self.notifier.notify_stage_completed(run_id, "supervision_decision", {"decision": new_status})
        return new_status
