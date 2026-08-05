# Phân công công việc — Day 9 Multi-Agent A2A

Nguyên tắc: 1 role = 1 file sở hữu. Chỉ Role 4 được sửa entrypoint. Cần đổi file của người khác thì nói với owner, đừng tự sửa cho nhanh — đó là nguồn conflict duy nhất trong repo kiểu này.

Nhóm tự điền cột cuối. Không điền sẵn tên.

## Bảng phân vai

| Role | File sở hữu | Nhiệm vụ chính | Người đảm nhận |
|:---|:---|:---|:---|
| Role 1 — Data / Tool Engineer | `src/datastore.py`, `src/tools.py`, `tests/test_tools.py` | Index 9 CSV, 4 tool tính toán xác định | `________________` |
| Role 2 — Policy Engineer | `src/policy.py`, `tests/test_policy.py` | EC_POLICY_V2, evidence ID, refund, actions | `________________` |
| Role 3 — Agent / Prompt Engineer | `src/agents.py`, `src/llm.py`, `.env.example` | 7 agent, prompt ép JSON, gọi model ≤10B | `________________` |
| Role 4 — Core Integrator | `src/bus.py`, `src/run_case.py`, `src/run_all.py` | Envelope, trace, ghép end-to-end, chạy 50 case | `________________` |
| Role 5 — Verifier / Observability | `src/verifier.py`, `scripts/validate_output.py`, `architecture.md`, `logging/metadata.json` | 12 luật kiểm, sơ đồ kiến trúc, khai model | `________________` |

Nhóm 4 người: Role 2 kiêm Role 5 — người viết luật cũng là người viết luật kiểm. Nhóm 3 người: thêm Role 1 kiêm Role 2. Không bao giờ gộp Role 4.

Ai yếu lập trình thì nhận Role 5: 12 luật kiểm và `architecture.md` là hai deliverable được chấm trực tiếp ở `README.md` §8, và viết được chúng thì không cần viết agent.

## Handoff giữa các role

| Từ | Đến | Bàn giao | Điều kiện nhận |
|:---|:---|:---|:---|
| Role 1 | Role 2 | `src/tools.py` | `python tests/test_tools.py` in ra `OK 11/11` |
| Role 1 | Role 3 | `src/datastore.py` | `get_case_bundle` trả về list rỗng chứ không crash ở order không có item |
| Role 2 | Role 4 | `src/policy.py` | `python tests/test_policy.py` in ra `OK 8/8` |
| Role 3 | Role 4 | `src/agents.py`, `src/llm.py` | `python -m src.llm --ping` trả về tên model đang chạy |
| Role 4 | Role 5 | `src/run_case.py` | in ra JSON có đủ 11 khoá cấp một |
| Role 5 | Role 4 | `src/verifier.py` | bắt được lỗi trên một file bị sửa tay cho sai |

## Bốn mốc và chế độ làm việc

| Mốc | Giờ | Chế độ | Ai làm gì |
|:---|:---|:---|:---|
| 1 | 13h30–14h15 | Tuần tự rồi song song | Role 1 dựng `datastore` trước; Role 2–5 chốt contract khoá dữ liệu cùng lúc |
| 2 | 14h15–15h35 | Song song | Role 1 làm tool, Role 2 làm policy, Role 3 làm agent, Role 5 làm verifier — khác file, không ăn output của nhau |
| 3 | 15h35–16h35 | Gate | Role 4 pull hết, ghép `run_case`, cả nhóm xem output của một case cùng nhau |
| 4 | 16h35–17h30 | Tuần tự | Role 4 chạy 50 case; Role 5 chạy validate; cả nhóm viết báo cáo cá nhân |

Điều kiện vào mốc 2: contract khoá dữ liệu đã chốt và push. Vào mốc 3: cả 4 file module đã push. Vào mốc 4: một case chạy end-to-end ra `0 lỗi`.

## Integration gate cuối mỗi mốc

```
1. Role 1, 2, 3, 5 push file của mình
2. Role 4 git pull
3. Role 4 (và chỉ Role 4) ghép vào src/run_case.py
4. Chạy: python -m src.run_case tests/fixtures/EC_SAMPLE.json
5. Cả nhóm xem output cùng nhau
6. Pass thì sang mốc sau. Fail thì sửa ngay, không dồn sang mốc kế
```

## Commit đề xuất

| Cuối mốc | Message | Người push | File |
|:---|:---|:---|:---|
| 1 | `feat: datastore index 9 csv` | Role 1 | `src/datastore.py`, `.gitignore` |
| 2 | `feat: tools + policy + agents` | Role 4 sau khi pull | `src/tools.py`, `src/policy.py`, `src/agents.py`, `src/llm.py`, `tests/` |
| 3 | `feat: a2a bus + trace + run_case` | Role 4 | `src/bus.py`, `src/run_case.py`, `logging/trace.jsonl` |
| 4 | `feat: 50 case output + architecture + metadata` | Role 4 | `src/run_all.py`, `output/`, `architecture.md`, `logging/metadata.json` |

Không đưa `.env` vào bất kỳ commit nào. Vòng làm việc: `git pull` trước khi sửa, `git push` ngay sau khi xong một file. Push bị chặn thì `git pull` rồi push lại.
