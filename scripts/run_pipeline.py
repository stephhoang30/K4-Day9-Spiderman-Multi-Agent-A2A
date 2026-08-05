"""Chạy pipeline LangGraph trên toàn bộ input/EC_*.json, ghi output/EC_*.json +
logging/trace.jsonl (ghi đè mỗi lần chạy, không append tích lũy — README mục 8).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from agents.coordinator import run_case  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
TRACE_PATH = ROOT / "logging" / "trace.jsonl"


def clear_output_dir() -> None:
    """Xoá sạch output cũ trước khi chạy để tránh lẫn file stale từ lần chạy trước
    (VD: 1 case lỗi giữa chừng ở lần chạy này nhưng vẫn còn file JSON cũ từ lần
    chạy trước, dễ gây tưởng nhầm là case vừa chạy xong)."""
    removed = 0
    for f in OUTPUT_DIR.glob("EC_*.json"):
        f.unlink()
        removed += 1
    if removed:
        print(f"Đã xoá {removed} file output cũ trong {OUTPUT_DIR}/")


def main() -> None:
    input_files = sorted(INPUT_DIR.glob("EC_*.json"))
    if not input_files:
        print("Không tìm thấy file input/EC_*.json", file=sys.stderr)
        sys.exit(1)

    clear_output_dir()

    all_trace_lines = []
    failed_cases = []

    for input_path in input_files:
        case_input = json.loads(input_path.read_text(encoding="utf-8"))
        case_id = case_input["case_id"]
        print(f"[{case_id}] đang xử lý order_id={case_input['customer_request']['claimed_order_id']}...")

        try:
            final_state = run_case(case_input)
        except Exception as exc:
            print(f"[{case_id}] LỖI khi chạy graph: {exc}", file=sys.stderr)
            failed_cases.append(case_id)
            continue

        verifier_result = final_state["verifier_result"]
        if not verifier_result["valid"]:
            print(f"[{case_id}] CẢNH BÁO: verifier phát hiện lỗi schema: {verifier_result['errors']}")

        output_path = OUTPUT_DIR / input_path.name
        output_path.write_text(
            json.dumps(verifier_result["case_output"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        for entry in final_state.get("trace", []):
            all_trace_lines.append(json.dumps(entry, ensure_ascii=False, default=str))

    TRACE_PATH.write_text("\n".join(all_trace_lines) + ("\n" if all_trace_lines else ""), encoding="utf-8")

    print(f"\nHoàn tất: {len(input_files) - len(failed_cases)}/{len(input_files)} case ghi thành công.")
    if failed_cases:
        print(f"Case lỗi (không ghi được output): {failed_cases}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
