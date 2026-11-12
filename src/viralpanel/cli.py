from __future__ import annotations

import argparse
from pathlib import Path
import sys

from viralpanel.studio.inspection import InspectionRunner


def _cmd_validate_e2e(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    report_path = Path(args.report_path)

    runner = InspectionRunner()
    results = runner.run_all(output_dir=output_dir, report_path=report_path)

    all_passed = True
    print("=== ZUNTO! E2E Inspection & Technical Validation ===")
    for item in results:
        v_val = item["video_validation"]
        a_val = item["avatar_validation"]
        p_val = item["pixel_inspection"]
        scenario_ok = v_val.is_valid and a_val.is_valid and p_val.passed
        if not scenario_ok:
            all_passed = False

        status_label = "PASS" if scenario_ok else "FAIL"
        print(f"[{status_label}] {item['title']}")
        print(f"       Video: {item['video_path']} ({item['file_size_bytes']} bytes)")
        print(
            f"       Specs: {v_val.metrics.get('width')}x{v_val.metrics.get('height')} | "
            f"fps={v_val.metrics.get('fps')} | codec={v_val.metrics.get('video_codec')}/{v_val.metrics.get('pix_fmt')} | "
            f"audio={v_val.metrics.get('audio_codec')}@{v_val.metrics.get('sample_rate')}Hz"
        )
        print(
            f"       Avatar: {a_val.metrics.get('video_codec')}/{a_val.metrics.get('pix_fmt')} | "
            f"Pixels checked={p_val.details.get('distributed_points_checked')} "
            f"(failed={p_val.details.get('distributed_points_failed')}) | "
            f"Border #FACC15={p_val.details.get('yellow_border_rays_confirmed')}"
        )
        if not scenario_ok:
            for err in v_val.errors + a_val.errors + p_val.errors:
                print(f"       ERROR: {err}", file=sys.stderr)

    print(f"Report written to: {report_path.resolve()}")
    print("Visual status: [PENDENTE DE INSPEÇÃO HUMANA]")
    return 0 if all_passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="viralpanel", description="ViralPanel CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    val_parser = subparsers.add_parser(
        "validate-e2e",
        help="Executa os cenários E2E (Normal e Fallback) e gera os vídeos e relatório de inspeção.",
    )
    val_parser.add_argument(
        "--output-dir",
        default="storage/inspection",
        help="Diretório de saída isolado para os vídeos de inspeção.",
    )
    val_parser.add_argument(
        "--report-path",
        default=".planning/phases/13-valida-o-t-cnica-automatizada-e-inspe-o-audiovisual-e2e/INSPECTION-REPORT.md",
        help="Caminho do relatório Markdown de inspeção.",
    )
    val_parser.set_defaults(func=_cmd_validate_e2e)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

