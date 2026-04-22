import asyncio
import random
import json
import os
import sys
import time
import argparse
from playwright.async_api import async_playwright

# Force UTF-8 output — tránh UnicodeEncodeError trên Windows terminal
sys.stdout.reconfigure(encoding='utf-8')



# ══════════════════════════════════════════════════════
# CONFIG LOADER
# ══════════════════════════════════════════════════════

def load_config():
    """Đọc cấu hình từ config.json."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ══════════════════════════════════════════════════════
# SESSION STATS — thread-safe via asyncio.Lock
# ══════════════════════════════════════════════════════

class SessionStats:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.success = 0
        self.fail = 0

    async def record_success(self):
        async with self._lock:
            self.success += 1

    async def record_fail(self):
        async with self._lock:
            self.fail += 1

    @property
    def total(self):
        return self.success + self.fail


# ══════════════════════════════════════════════════════
# HUMAN BEHAVIOR SIMULATOR
# ══════════════════════════════════════════════════════

async def simulate_reading(page, worker_id, url_short):
    """
    Giả lập hành vi đọc bài theo 4 profile có trọng số xác suất,
    phản ánh phân phối người đọc thật:
      - bounce  (10-17s): vào rồi thoát sớm          → 20%
      - skim    (18-31s): lướt qua không đọc kỹ       → 35%
      - quick   (32-51s): đọc nhanh, đọc giỏi 1 phút  → 30%
      - full    (53-73s): đọc kỹ, nghiền ngẫm          → 15%
    Range boundaries chọn số lẻ (không 5/10/0) — tránh analytics nhận pattern bot.
    """
    profile = random.choices(
        ['bounce', 'skim', 'quick', 'full'],
        weights=[20, 35, 30, 15],
        k=1
    )[0]

    target_secs = {
        'bounce': random.randint(10, 17),
        'skim':   random.randint(18, 31),
        'quick':  random.randint(32, 51),
        'full':   random.randint(53, 73),
    }[profile]
    profile_icons = {'bounce': '💨', 'skim': '⚡', 'quick': '📖', 'full': '🔍'}
    print(f"    [W{worker_id}] {profile_icons[profile]} {target_secs}s — {url_short}")

    # Track thời điểm bắt đầu để pad cuối cùng nếu hành vi nhanh hơn target
    start_ts = time.monotonic()

    # Chờ trang ổn định trước
    await page.wait_for_timeout(random.randint(800, 1800))

    if profile == 'bounce':
        # Vào liếc tiêu đề rồi thoát — 10-12s tổng
        await page.mouse.move(random.randint(200, 800), random.randint(100, 300))
        await page.mouse.wheel(0, random.randint(100, 300))
        await page.wait_for_timeout(random.randint(7000, 9000))

    elif profile == 'skim':
        # Lướt xuống nhanh, không dừng đọc — 12-20s tổng
        for _ in range(random.randint(3, 5)):
            await page.mouse.wheel(0, random.randint(300, 700))
            await page.wait_for_timeout(random.randint(800, 1800))
        # Hover nhẹ 1-2 lần
        await page.mouse.move(random.randint(150, 800), random.randint(300, 600))
        await page.wait_for_timeout(random.randint(1500, 2500))

    elif profile == 'quick':
        # Đọc nhanh, cuộn đều, dừng vài chỗ — 25-45s tổng
        for _ in range(random.randint(5, 8)):
            await page.mouse.wheel(0, random.randint(200, 500))
            await page.wait_for_timeout(random.randint(1500, 3500))
        # Hover qua vài đoạn
        for _ in range(random.randint(2, 3)):
            await page.mouse.move(random.randint(120, 900), random.randint(200, 700))
            await page.wait_for_timeout(random.randint(500, 1000))
        # Cuộn lên 1 lần
        await page.mouse.wheel(0, -random.randint(300, 800))
        await page.wait_for_timeout(random.randint(1000, 2000))

    elif profile == 'full':
        # Đọc kỹ — cuộn chậm, dừng nhiều, hover nhiều — 50-75s tổng
        scroll_steps = random.randint(8, 12)
        for _ in range(scroll_steps):
            await page.mouse.wheel(0, random.randint(150, 400))
            # 40% cơ hội dừng đọc lâu (đoạn hay)
            if random.random() < 0.40:
                await page.wait_for_timeout(random.randint(3000, 6000))
            else:
                await page.wait_for_timeout(random.randint(1500, 2500))
        # Hover qua nhiều vùng như đang highlight đoạn văn
        for _ in range(random.randint(3, 5)):
            await page.mouse.move(random.randint(100, 900), random.randint(300, 900))
            await page.wait_for_timeout(random.randint(600, 1200))
        # Cuộn ngược lên đọc lại
        for _ in range(random.randint(1, 2)):
            await page.mouse.wheel(0, -random.randint(500, 2000))
            await page.wait_for_timeout(random.randint(1500, 3000))
        # Nghỉ cuối
        await page.wait_for_timeout(random.randint(2000, 4000))

    # Padding: nếu behavior nhanh hơn target → chờ bù cho đủ thời lượng đã in ra
    elapsed = time.monotonic() - start_ts
    remaining_ms = int((target_secs - elapsed) * 1000)
    if remaining_ms > 0:
        await page.wait_for_timeout(remaining_ms)

    print(f"    [W{worker_id}] ✅  Xong: {url_short}")


# ══════════════════════════════════════════════════════
# TRAFFIC WORKER
# ══════════════════════════════════════════════════════


async def traffic_worker(worker_id, browser, config, url_list, stats, nav_sem, dry_run=False):
    """
    Worker nhận danh sách URL đã được pre-generate và shuffle.
    Mỗi lượt tạo browser context MỚI với fingerprint hoàn toàn khác.
    """
    viewports  = config.get('viewports',  [{'width': 1366, 'height': 768}])
    locales    = config.get('locales',    ['vi-VN'])
    timezones  = config.get('timezones',  ['Asia/Ho_Chi_Minh'])
    referers   = config.get('referers',   [''])
    color_schemes = ['light', 'dark', 'no-preference']

    # Stagger startup: tránh thundering herd khi tất cả workers bắt đầu cùng lúc
    await asyncio.sleep(random.uniform(0, worker_id * 0.3))

    total = len(url_list)
    for i, url in enumerate(url_list):
        url_short  = url.split('/')[-1][:28] + "..."
        agent      = random.choice(config['user_agents'])
        viewport   = random.choice(viewports)
        locale     = random.choice(locales)
        timezone   = random.choice(timezones)
        referer    = random.choice(referers)
        color      = random.choice(color_schemes)

        device_label = "📱 Mobile" if viewport['width'] < 500 else "🖥  Desktop"
        print(
            f"[W{worker_id}][{i+1}/{total}] "
            f"{device_label} {viewport['width']}x{viewport['height']} | "
            f"{locale} | {url_short}"
        )

        # ── DRY-RUN: bỏ qua, không tốn tài nguyên ──────────────
        if dry_run:
            print(f"    [W{worker_id}] 🧪 DRY-RUN — skip, không open browser")
            await asyncio.sleep(0.05)
            await stats.record_success()
            continue

        # ── LIVE: tạo context với fingerprint riêng ─────────────
        context = await browser.new_context(
            user_agent=agent,
            viewport=viewport,
            locale=locale,
            timezone_id=timezone,
            color_scheme=color,
            extra_http_headers={'Referer': referer} if referer else {},
        )
        context.set_default_navigation_timeout(0)
        page = await context.new_page()

        try:
            # Semaphore giới hạn số trang load đồng thời — tránh overload Docker network
            async with nav_sem:
                await page.goto(url, wait_until='domcontentloaded', timeout=0)
            await simulate_reading(page, worker_id, url_short)
            await stats.record_success()

        except Exception as e:
            print(f"    [W{worker_id}] ❌ Lỗi: {str(e)[:70]}")
            await stats.record_fail()

        finally:
            await context.close()
            # Nghỉ ngẫu nhiên giữa các lượt — phá vỡ pattern đều đặn của bot
            await asyncio.sleep(random.randint(2, 9))



# ══════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════

async def main(dry_run: bool = False):
    mode_label = "🧪 DRY-RUN (không mở browser thật)" if dry_run else "🚀 LIVE MODE"
    print(f"\n{'═'*55}")
    print(f"  TRAFFIC SIMULATOR — {mode_label}")
    print(f"{'═'*55}")

    config      = load_config()
    urls        = config['urls']
    num_workers = config['concurrency']['num_workers']
    view_min, view_max = config.get('url_views_range', [100, 300])
    url_view_counts: dict = config.get('url_view_counts', {})

    # ── Pre-generate số view per URL (fixed hoặc random) ─────
    print("  📋 PHÂN PHỐI VIEW MỖI BÀI:")
    url_pool = []
    for url in urls:
        fixed = url_view_counts.get(url)
        count = int(fixed) if fixed else random.randint(view_min, view_max)
        label = f"{count:4d} views {'(fixed)' if fixed else '(random)'}"
        url_short = url.split('/')[-1][:35]
        print(f"     {label} ← {url_short}...")
        url_pool.extend([url] * count)

    total = len(url_pool)
    random.shuffle(url_pool)  # shuffle để mix URL, không bắn 1 bài liên tục

    # ── Chia đều cho workers ─────────────────────────────────
    chunks = [url_pool[i::num_workers] for i in range(num_workers)]
    print(f"\n  🔢 Tổng: {total} views | {num_workers} workers\n")

    stats      = SessionStats()
    start_time = time.monotonic()

    # Giới hạn số page.goto() đồng thời — Docker/WSL2 network không chịu được 20 luồng cùng lúc
    max_concurrent_nav = config.get('max_concurrent_nav', 8)
    nav_sem = asyncio.Semaphore(max_concurrent_nav)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )

        tasks = [
            traffic_worker(i + 1, browser, config, chunks[i], stats, nav_sem, dry_run)
            for i in range(num_workers)
        ]
        await asyncio.gather(*tasks)

        await browser.close()

    elapsed     = time.monotonic() - start_time
    elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"

    print(f"\n{'═'*55}")
    print("  📊 TỔNG KẾT PHIÊN LÀM VIỆC")
    print(f"{'═'*55}")
    print(f"  ✅ Thành công  : {stats.success} / {total}")
    print(f"  ❌ Thất bại    : {stats.fail} / {total}")
    print(f"  ⏱️  Thời gian   : {elapsed_str}")
    print(f"{'═'*55}")
    print("  🎉 XONG PHIM! MỞ DASHBOARD LÊN CHỤP HÌNH BÁO CÁO VỢ ĐI SẾP!")
    print(f"{'═'*55}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Traffic Simulator — by Vibe Coder',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Chạy thử config mà không mở browser thật (tiện test nhanh)',
    )
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run))
