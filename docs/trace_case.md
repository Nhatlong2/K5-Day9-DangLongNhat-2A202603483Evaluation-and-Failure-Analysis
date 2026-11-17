# Trace case: từ trace tới quyết định sai đầu tiên

Chạy từ `src/`.

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= tests/test_lab9_trace_case_regression.py
```

| Trường | Kết quả |
|---|---|
| Trial | `seeded_regression C-002@11`, item `E-002`, run `E-seeded_regression-20261117-67a2`. |
| Triệu chứng | `TrialPass` sai trạng thái `resolved` thay vì `denied`. Ledger ghi 20.000 VND, nhãn là 0 VND. Reply báo đúng số đã ghi, nên nguyên nhân nằm trước khâu soạn câu trả lời. |
| Bước sai đầu tiên | Event 3 `model_override` có payload `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Event 1 chuyển đúng claim. Event 2 trả order nhìn thấy được và số ngày trễ trong DB là 2. Event 3 ghi đè dữ kiện đó, làm event 4 tính quote 20.000 VND. |
| Failure mode | FM-03 `ticket_trust`. |
| Đối chứng | `fixed C-002@11`, run `E-fixed-20261117-67a2`. Event 3 là `quote` với `no_entitlement` và số tiền 0. Ledger 0, kết quả `denied` khớp nhãn. |
| Regression test | `test_c002_keeps_database_delay_before_quoting` xác nhận thứ tự event, giá trị DB và ledger trên cả hai replay. Test quan sát `TrialPass` trượt ở variant lỗi và đạt ở `fixed`. |
| Giới hạn | Bằng chứng bao phủ một cặp claim–seed trên MockLLM. Các quyết định cho ticket khác cần được đo bằng eval set tương ứng. |

[Report variant lỗi](../src/reports/eval_seeded_regression.json) · [Report đối chứng](../src/reports/eval_fixed.json)
