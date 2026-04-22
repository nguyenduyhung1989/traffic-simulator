# 🚀 Traffic Simulator — by Vibe Coder

## 🎯 Mục Đích
Buff view bài báo một cách "có học" — giả lập người thật đọc bài (scroll, hover chuột, dừng đọc), thay vì dùng trò refresh page ngu ngốc bị bot phát hiện ngay.

## 🛠 Cài Đặt

```bash
pip install -r requirements.txt
playwright install chromium
```

## 🚀 Cách Chạy

```bash
# Chạy thật
python main.py

# Dry-run: test config mà không tốn tài nguyên browser
python main.py --dry-run
```

## ⚙️ Cấu Hình (`config.json`)

| Field | Mô tả |
|---|---|
| `urls` | Danh sách URL muốn buff view |
| `user_agents` | Pool UA — mỗi lượt pick ngẫu nhiên 1 cái |
| `viewports` | Pool kích thước màn hình (desktop + mobile) |
| `locales` | Pool ngôn ngữ trình duyệt |
| `timezones` | Pool múi giờ |
| `referers` | Pool nguồn đến (Google, Facebook, direct...) |
| `concurrency.num_workers` | Số browser context chạy song song |
| `concurrency.views_per_worker` | Số lượt mỗi worker chạy |

**Tổng lượt = `num_workers` × `views_per_worker`**

## 🧠 Tại Sao Nó Qua Được Analytics?

1. **Mỗi lượt = 1 browser context mới** → cookie trắng tươn, web chả phân biệt được với user mới
2. **Fingerprint đa dạng** → UA + viewport + locale + timezone + referer đều random → khác nhau hoàn toàn giữa các lượt
3. **Hành vi người thật** → hover chuột, scroll không đều, dừng đọc ~15-30s → vượt ngưỡng bounce rate
4. **Referer giả** → traffic trông như đến từ Google/Facebook, không phải direct (ít bị nghi hơn)

## 📊 Output Mẫu

```
══════════════════════════════════════════════════════
  TRAFFIC SIMULATOR — 🚀 LIVE MODE
══════════════════════════════════════════════════════
  📋 5 workers × 20 views = 100 lượt | 6 URLs trong pool

[W1][1/20] 🖥  Desktop 1920x1080 | vi-VN | gia-nha-lap-dinh-t...
    [W1] 👁️  Đang đọc: gia-nha-lap-dinh-t...
    [W1] ✅  Đọc xong: gia-nha-lap-dinh-t...

══════════════════════════════════════════════════════
  📊 TỔNG KẾT PHIÊN LÀM VIỆC
══════════════════════════════════════════════════════
  ✅ Thành công  : 98 / 100
  ❌ Thất bại    : 2 / 100
  ⏱️  Thời gian   : 12m 34s
══════════════════════════════════════════════════════
```
