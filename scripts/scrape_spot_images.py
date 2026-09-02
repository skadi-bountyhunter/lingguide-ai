"""
用 Playwright 浏览器从必应图片搜索 22 个景点图片并下载
"""
import asyncio
import json
import re
import httpx
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "frontend-tourist" / "public" / "images" / "spots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SPOTS = [
    (1,  "灵山大佛 无锡"),
    (2,  "灵山梵宫 内部"),
    (3,  "九龙灌浴 灵山"),
    (4,  "五印坛城 灵山"),
    (5,  "降魔浮雕 灵山"),
    (6,  "菩提大道 灵山胜境"),
    (7,  "灵山大照壁"),
    (8,  "五明桥 灵山胜境"),
    (9,  "佛足坛 灵山"),
    (10, "五智门 灵山 牌坊"),
    (11, "阿育王柱 灵山"),
    (12, "百子戏弥勒 灵山"),
    (13, "祥符禅寺 无锡"),
    (14, "佛教文化博览馆 灵山"),
    (15, "曼飞龙塔 灵山"),
    (16, "无尽意斋 灵山"),
    (17, "拈花广场 拈花湾"),
    (18, "梵天花海 拈花湾"),
    (19, "香月花街 拈花湾 夜景"),
    (20, "拈花堂 拈花湾"),
    (21, "五灯湖 拈花湾 夜景"),
    (22, "鹿鸣谷 拈花湾"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Referer": "https://cn.bing.com/",
}


async def get_image_urls(page, query: str) -> list[str]:
    url = f"https://cn.bing.com/images/search?q={query}&first=1&count=10"
    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    await page.wait_for_timeout(2000)
    urls = await page.evaluate("""() => {
        const imgs = [];
        document.querySelectorAll('a.iusc').forEach(a => {
            try {
                const m = JSON.parse(a.getAttribute('m'));
                if (m && m.murl) imgs.push(m.murl);
            } catch(e) {}
        });
        return imgs.slice(0, 5);
    }""")
    return urls


async def download_image(client: httpx.AsyncClient, url: str, filepath: Path) -> bool:
    try:
        r = await client.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        r.raise_for_status()
        if "image" not in r.headers.get("content-type", "") or len(r.content) < 5000:
            return False
        filepath.write_bytes(r.content)
        print(f"  OK {filepath.name} ({len(r.content)//1024} KB)")
        return True
    except Exception as e:
        print(f"  FAIL {url[:60]}... {e}")
        return False


async def main():
    print("=" * 55)
    print("灵山景点图片批量下载（Playwright + 必应）")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 55)

    mapping = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        async with httpx.AsyncClient() as client:
            for spot_id, query in SPOTS:
                print(f"\n[{spot_id:2d}/22] {query}")
                try:
                    urls = await get_image_urls(page, query)
                except Exception as e:
                    print(f"  搜索失败: {e}")
                    urls = []

                if not urls:
                    print(f"  未找到图片")
                    mapping[spot_id] = None
                    continue

                saved = False
                for url in urls:
                    ext = re.search(r'\.(jpe?g|png|webp)', url, re.I)
                    ext = ext.group(1).lower() if ext else "jpg"
                    ext = "jpg" if ext == "jpeg" else ext
                    filepath = OUTPUT_DIR / f"spot_{spot_id:02d}.{ext}"
                    if await download_image(client, url, filepath):
                        mapping[spot_id] = f"/images/spots/spot_{spot_id:02d}.{ext}"
                        saved = True
                        break

                if not saved:
                    print(f"  所有候选URL均下载失败")
                    mapping[spot_id] = None

        await browser.close()

    # 保存映射
    mapping_file = Path(__file__).parent / "spot_image_mapping.json"
    mapping_file.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    success = sum(1 for v in mapping.values() if v)
    print(f"\n{'='*55}")
    print(f"完成！成功 {success}/22，映射保存至 {mapping_file}")
    print("="*55)


if __name__ == "__main__":
    asyncio.run(main())
