# Agent kiểm chứng

Kiểm tra schema, evidence ID, giới hạn số lượng, thứ tự mảng và cách xử lý `null` trước khi ghi output.

## Contract bàn giao

`VerifierAgent().verify(candidate)` nhận JSON output ứng viên và trả `is_valid` cùng danh sách `errors`. Agent không tự sửa dữ liệu.

Nó kiểm tra: top-level schema, giới hạn/duplicate của các array, confidence, timestamp, phép đối soát tiền, root-cause code, action/status theo primary issue, và evidence ID bắt buộc có tham chiếu entity/policy có mặt trong output.
