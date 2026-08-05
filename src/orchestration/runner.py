"""Chạy batch input case qua Coordinator và ghi output/trace/metadata."""

from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from agents.coordinator import CoordinatorAgent


@dataclass(frozen=True)
class BatchRunResult:
    processed_cases: int
    failed_cases: int
    failures: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BatchRunner:
    """Điều phối một lượt chạy mới nhất; trace được ghi đè, không append."""

    def __init__(self, data_dir: str | Path) -> None:
        self._coordinator = CoordinatorAgent(data_dir)

    def run(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        trace_path: str | Path,
        metadata_path: str | Path,
        *,
        require_50_cases: bool = True,
    ) -> BatchRunResult:
        """Chạy mọi file JSON input, ghi JSON output và trace của lượt chạy này."""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        trace_file = Path(trace_path)
        metadata_file = Path(metadata_path)
        case_paths = sorted(input_path.glob("EC_*.json"))
        if require_50_cases and len(case_paths) != 50:
            raise ValueError(f"Cần đúng 50 input EC_*.json, hiện có {len(case_paths)}")

        output_path.mkdir(parents=True, exist_ok=True)
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        failures: dict[str, str] = {}

        with trace_file.open("w", encoding="utf-8") as trace:
            for case_path in case_paths:
                case = self._read_json(case_path)
                case_id = str(case.get("case_id", case_path.stem))
                started_at = time.perf_counter()
                self._write_trace(trace, case_id, "coordinator", "started", {})
                try:
                    result = self._coordinator.investigate(
                        case,
                        on_handoff=lambda agent, handoff: self._write_trace(
                            trace, case_id, agent, "handoff", handoff
                        ),
                    )
                    self._write_json(output_path / case_path.name, result)
                    self._write_trace(
                        trace,
                        case_id,
                        "coordinator",
                        "completed",
                        {"duration_ms": round((time.perf_counter() - started_at) * 1000, 2)},
                    )
                except (KeyError, ValueError, TypeError) as error:
                    failures[case_id] = str(error)
                    self._write_trace(
                        trace,
                        case_id,
                        "coordinator",
                        "failed",
                        {
                            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                            "error": str(error),
                        },
                    )

        self._write_metadata(metadata_file, len(case_paths), len(failures))
        return BatchRunResult(
            processed_cases=len(case_paths) - len(failures),
            failed_cases=len(failures),
            failures=failures,
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8-sig") as file:
            content = json.load(file)
        if not isinstance(content, dict):
            raise ValueError(f"Input phải là JSON object: {path.name}")
        return content

    @staticmethod
    def _write_json(path: Path, content: Mapping[str, Any]) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(content, file, ensure_ascii=False, indent=2)
            file.write("\n")

    @staticmethod
    def _write_trace(
        trace: Any,
        case_id: str,
        agent: str,
        event: str,
        payload: Mapping[str, Any],
    ) -> None:
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "agent": agent,
            "event": event,
            "payload": payload,
        }
        trace.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def _write_metadata(path: Path, input_count: int, failed_count: int) -> None:
        metadata = {
            "model": {"name": None, "parameter_size": 0, "uses_llm": False},
            "framework": "Python standard library",
            "runtime": {
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
            },
            "run": {
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "input_case_count": input_count,
                "failed_case_count": failed_count,
            },
        }
        BatchRunner._write_json(path, metadata)
