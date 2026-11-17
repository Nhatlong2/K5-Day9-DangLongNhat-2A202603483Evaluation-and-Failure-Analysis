# Judge audit

Chạy `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` và lặp lại với `judge_helpful_public.csv` từ `src/`. Lớp dương là `FAIL`.

| Tiêu chí | n | κ | Precision | Recall | FLOORS | Quyết định |
|---|---:|---:|---:|---:|---|---|
| `tone_ok` | 100 | 0,757 | 0,857 | 0,800 | Đạt | Dùng replay judge cho tone trong phạm vi eval công khai. |
| `helpful` | 100 | 0,375 | 1,000 | 0,300 | Trượt κ và recall | Loại khỏi gate. Dùng grader code cho ledger và approval. |

| Tiêu chí | TP | FP | FN | TN | Fail quan sát | Rogan–Gladen |
|---|---:|---:|---:|---:|---:|---:|---:|
| `tone_ok` | 24 | 4 | 6 | 66 | 28% | 30% |
| `helpful` | 9 | 0 | 21 | 70 | 9% | 30% |

## Audit bất đồng

| Case | Judge | Người | Kết luận audit | Điều chỉnh rubric |
|---|---|---|---|---|
| H-008 | PASS | FAIL | Đồng ý nhãn người. Xưng “em” và dùng “nha” quá thân mật trong kịch bản chăm sóc khách hàng. | Thêm ví dụ phân biệt lịch sự với thân mật quá mức. |
| H-017 | PASS | FAIL | Đồng ý nhãn người. Cách gọi “bạn ơi” lệch cách xưng hô với khách trong ca. | Yêu cầu xưng hô theo ngữ cảnh, mặc định “anh/chị” khi thiếu thông tin. |
| H-029 | PASS | FAIL | Đồng ý nhãn người. Câu “không cần nhắn thêm” tạo giọng ra lệnh. | Chấm toàn bộ câu trả lời và yêu cầu nêu bước tiếp theo một cách trung tính. |
| H-042 | FAIL | PASS | Đồng ý nhãn người. Câu trả lời ngắn, lịch sự và nêu thời gian xử lý. | Chấp nhận thông báo hoàn tiền trực tiếp khi đã đủ dữ kiện, lời xin lỗi tùy ngữ cảnh. |
| H-051 | FAIL | PASS | Đồng ý nhãn người. Từ “refund” nằm trong ngôn ngữ nghiệp vụ cho phép của ca. | Cho phép thuật ngữ nghiệp vụ hiểu được khi cách xưng hô vẫn lịch sự. |
| HL-015 | PASS | FAIL | Đồng ý nhãn người. Reply báo 55.000 VND, ledger ghi 40.000 VND. | Bắt buộc đối chiếu khoản hoàn với ledger trước khi xét cách diễn đạt. |
| HL-016 | PASS | FAIL | Đồng ý nhãn người. Reply dài vẫn báo 55.000 VND trong khi ledger ghi 35.000 VND. | Chấm dữ kiện trước độ dài hoặc lời xin lỗi. |
| HL-020 | PASS | FAIL | Đồng ý nhãn người. Reply báo 90.000 VND, ledger ghi 120.000 VND. | Thêm ví dụ báo thiếu tiền và dùng grader cho số tiền thực ghi. |

## Kết luận

`helpful` bỏ sót 21 trong 30 lỗi dù precision bằng 1. Các audit có ledger cho thấy lời văn lịch sự dễ che sai lệch số tiền. Tỷ lệ hiệu chỉnh là mô tả trên CSV replay đã công khai. Để dùng với dữ liệu mới, cần nhãn người trên một tập giữ riêng và chạy calibration lại.
