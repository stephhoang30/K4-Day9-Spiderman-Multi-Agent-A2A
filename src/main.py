"""CLI chạy toàn bộ pipeline Day 9."""

from __future__ import annotations

import argparse
from pathlib import Path

from orchestration import BatchRunner


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Chạy batch Olist multi-agent")
    parser.add_argument("--input-dir", type=Path, default=project_root / "input")
    parser.add_argument("--output-dir", type=Path, default=project_root / "output")
    parser.add_argument("--trace-path", type=Path, default=project_root / "logging" / "trace.jsonl")
    parser.add_argument("--metadata-path", type=Path, default=project_root / "logging" / "metadata.json")
    parser.add_argument("--allow-partial", action="store_true", help="Cho phép chạy ít hơn 50 case khi phát triển")
    args = parser.parse_args()

    result = BatchRunner(project_root / "data").run(
        args.input_dir,
        args.output_dir,
        args.trace_path,
        args.metadata_path,
        require_50_cases=not args.allow_partial,
    )
    print(f"Hoàn tất {result.processed_cases} case; lỗi: {result.failed_cases}")
    if result.failures:
        for case_id, error in result.failures.items():
            print(f"- {case_id}: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
