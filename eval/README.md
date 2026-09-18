# Kiểm tra tích hợp

Chạy từ `codebase/`:

```powershell
python -m unittest discover -q
node scripts/test_ui.cjs
python scripts/verify_agent.py
python scripts/evaluate.py
```

Hai lệnh đầu dùng dữ liệu PDF tự sinh và provider fixture. Lệnh cuối cần server chạy và gọi provider thật; yêu cầu thẩm định hoàn tất nên sẽ báo không đạt nếu LLM hết credit. Báo cáo chứa trích dẫn được lưu vào thư mục `data/verification/` được Git bỏ qua.

`results.json` và `http_results.json` chỉ ghi kiểm tra kỹ thuật đã chạy. `golden_set.json` là 20 ca tích hợp bổ sung sau merge, không phải dữ liệu gốc của lượt 5/20 đã ghi trong SPEC (các nhánh không chứa bộ gốc đó). Kết quả contract không thay thế đánh giá ngữ nghĩa hoặc validation người dùng thật. Quality bar đã chốt trong `../spec.md` giữ nguyên. Không suy ra đạt 80% từ số unit test. Các ca có `semantic_review: pending/blocked` chưa được công nhận đạt chuẩn ngữ nghĩa.
