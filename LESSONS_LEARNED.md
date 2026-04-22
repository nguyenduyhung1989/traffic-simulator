# BÀI HỌC VỠ LÒNG (LESSONS LEARNED)

| Ngày | Sự cố | Nguyên nhân | Bài học |
|---|---|---|---|
| 16/04/2026 | Sếp nhờ cày view web thủ công chậm chạp | Sợ làm cái kịch bản thường chạy synchronous mất nửa ngày xong 1 vòng. Chờ đợi đẻ ra lười. | Viết đồ buff View là PHẢI xài Multi-threading / Async. Ở đây dùng tính năng `asyncio.gather` siêu thoát của Python chạy 5 Playwright Context song song rạch giời rơi xuống buff view tấp nập. Vợ vui, sếp khoẻ. |
| 16/04/2026 | Tool đời đầu bị phát hiện là bot dù đã rotate User-Agent | Chỉ rotate UA nhưng viewport + locale + timezone + referer vẫn giống nhau → analytics xịn (GA4, Cloudflare) đọc fingerprint là biết ngay | Browser fingerprint gồm NHIỀU chiều: UA chỉ là 1/5. Phải randomize đồng thời viewport + locale + timezone_id + color_scheme + referer thì fingerprint mới thực sự đa dạng. 1 browser context = 1 "người" riêng biệt hoàn toàn. |
