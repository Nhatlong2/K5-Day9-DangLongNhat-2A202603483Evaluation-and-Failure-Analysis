# Eval card — LogiX-VN refund agent

## v1 · Core

- **Snapshot baseline và grader** `8e09ed008ff3f518146ea33a31f0daed33d409e5`. Runtime Day 08 từ `034c6c421c198dae67a9211d15e2587d5a378972`.
- **Eval set** `67a2f18ba456`, 14 item từ matrix Day 08, 5 seed `11,22,33,44,55`, 70 trial mỗi shape. Nhãn ở `src/data/eval/labels_v1.json`. Metric spec `1.0`, MockLLM, Python `3.12.14`.
- **Cổng chặn** Approval bypass và secret leak tối đa 0. Pass rate ≥0,85, refund đúng ≥0,95 và CI 95% của Δ phải chạm hoặc nằm trên 0. Reply khớp ledger ở mọi lần có số tiền được ghi trong reply.

| Shape | Run ID | Pass rate | Ledger đúng | Reply khớp ledger | `pass_5` | Chi phí/ca pass | Δ pass rate và CI 95% | Gate |
|---|---|---:|---:|---:|---:|---:|---|---|
| `swarm` | `E-swarm-20261117-67a2` | 0,9857 | 0,9857 | 1,0000 | 0,9286 | 49,5670 | 0,000 [0,000, 0,000] | Exit 0 |
| `fixed` | `E-fixed-20261117-67a2` | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 48,7157 | +0,014 [0,000, +0,043] | Exit 0 |
| `seeded_regression` | `E-seeded_regression-20261117-67a2` | 0,7143 | 0,8571 | 0,7857 | 0,7143 | 81,2020 | −0,271 [−0,500, −0,057] | Exit 1 |

Cả ba report ghi 0 approval bypass và 0 secret leak. `seeded_regression` trượt `refund_amount_correct`, `pass_rate` và `reply_matches_ledger`. Chẩn đoán M3 phủ 20/20 trial lỗi, báo nhầm 0/70 trial đối chứng. `proposal_matches_quote` ghi nhận proposal sai ở C-013 dù ledger vẫn bằng 0.

- **Judge** `tone_ok` đạt với κ 0,757, precision 0,857 và recall 0,800. `helpful` trượt do κ 0,375 và recall 0,300. [Judge audit](judge_audit.md)
- **Trace và regression test** `C-002@11`, event 3 ghi đè số ngày trễ từ DB. [Trace case](trace_case.md)
- **Gate owner** Đặng Long Nhật đối chiếu report, trace và ledger khi gate chặn. [PRD v1.1](PRD_v1.1.md)
- **Phạm vi pilot** Replay nội bộ yêu cầu hoàn phí cho một đơn, với fixture giả lập và policy Day 08.
- **Giới hạn** 14 item làm CI rộng khi lỗi hiếm. Judge replay dùng CSV công khai. Swarm Day 08 thiếu event reply, nên giá trị FM-08 của baseline mô tả các sự kiện quan sát được. Metric này đã được kiểm tra trực tiếp trên variant có reply.
- **Tăng version eval set** Tăng version và sinh baseline mới khi thêm item, sửa nhãn hoặc đổi nguồn fixture.

[Baseline v1](../src/reports/baseline_v1.json) · [Fixed](../src/reports/eval_fixed.json) · [Seeded regression](../src/reports/eval_seeded_regression.json) · [Spec v1](../src/config/metric_spec.yaml)

## v2 · Advanced và Expert

- **Snapshot baseline và gate** `71569db8da3761e2d1122d24538b3b487489fea3`. Run `E-swarm-20261117-fecc`, eval-set SHA `fecc094a9301`, metric spec `2.0`.
- **Tập đánh giá** 28 item × 5 seed, gồm 14 ca v1 và 14 ca phân nhóm giả lập trong pack công khai. Từng FM được pack kiểm tra có 3–6 item sau khi ghép tập.
- **A/A** Swarm trên seed `11,22,33,44,55` và `66,77,88,99,110` cho Δ 0,0000 ở mọi metric. Hai lượt đều có pass rate 0,9786, `pass_at_5` 1,0000 và `pass_hat_5` 0,8929.
- **Sàn lặp lại** `pass_hat_5` ≥0,80 và chặn merge. Mốc này thấp hơn baseline ở cả hai lượt A/A. `flaky_regression` đạt `pass_at_5` 1,0000 nhưng chỉ đạt `pass_hat_5` 0,5714.

| Slice | Pass rate baseline | Bằng chứng gate |
|---|---:|---|
| `money_movement` | 1,0000 | `slice_regression` đạt 0,8500 dưới sàn 0,90. Pass rate toàn tập là 0,9357 với CI của Δ [−0,121, +0,029]. Gate chặn riêng slice này. |
| `adversarial` | 0,9714 | `seeded_regression` đạt 0,5714, CI của Δ [−0,657, −0,143]. Slice chặn cùng các metric toàn tập. |
| `denial` | 0,9455 | `seeded_regression` đạt 0,3636, CI của Δ [−0,836, −0,309]. |

Scorecard chặn 3/3 regression, báo nhầm 0. `fixed`, `honest_refactor` và baseline tự so đều qua. Bốn trap công khai đều trả exit 1 với verdict `integrity`. Kiểm tra bổ sung xác nhận gate chặn dòng lặp giữ nguyên tổng số dòng, lỗi evaluator trên report còn lại hợp lệ, đổi nhãn slice và bỏ điều kiện blocking cho cùng eval-set version.

Với xác suất lỗi 1/3 trên một item và giả thiết các lần độc lập, 5 lần vẫn có khoảng 13% xác suất chưa quan sát lỗi. Hai bộ seed MockLLM có Δ 0 nên phép A/A này chỉ mô tả độ lặp lại của lab. Dùng dữ liệu và seed mới để ước lượng nhiễu trước khi áp sàn cho hệ thống dùng model thật.

[Baseline v2](../src/reports/baseline_v2.json) · [Spec v2](../src/config/metric_spec_v2.yaml)
