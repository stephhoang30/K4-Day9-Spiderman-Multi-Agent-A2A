# Điều phối luồng chạy

Đặt tại đây logic định tuyến case, thứ tự bàn giao agent, ghi trace và chạy theo lô.

## Chạy batch

Từ root dự án:

```powershell
$env:PYTHONPATH = "src"
python src/main.py
```

Mặc định lệnh yêu cầu đúng 50 file `EC_*.json` trong `input/`, ghi output tương ứng, ghi đè `logging/trace.jsonl` bằng trace lượt chạy mới nhất và cập nhật `logging/metadata.json`.

Khi phát triển với ít case hơn, thêm `--allow-partial`.
