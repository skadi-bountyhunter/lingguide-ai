"""
用本地 Playwright 从百度图片搜索下载22个景点图片。
运行：python scripts/fetch_spot_images.py
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "frontend-visitor" / "public" / "images" / "spots"

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

def get_image_urls_from_page(page, query: str) -> list[str]:
    url = f"https://image.baidu.com/search/index?tn=baiduimage&word={query}&rn=20"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)  # 等JS渲染
    urls = page.evaluate("""() => {
        const imgs = [];
        document.querySelectorAll('img').forEach(i => {
            const src = i.src || i.getAttribute('src');
            if (src && src.startsWith('http') && src.includes('baidu.com/it') && src.length > 30) {
                imgs.push(src);
            }
        });
        return [...new Set(imgs)];
    }""")
    return urls


def download_image(page, img_url: str, dest: Path) -> bool:
    try:
        resp = page.request.get(img_url, headers={
            "Referer": "https://image.baidu.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, timeout=20000)
        if resp.status == 200 and "image" in resp.headers.get("content-type", ""):
            data = resp.body()
            if len(data) > 5000:
                dest.write_bytes(data)
                return True
    except Exception as e:
        print(f"  下载失败: {e}")
    return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--lang=zh-CN"])
        ctx = browser.new_context(locale="zh-CN", extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"})
        page = ctx.new_page()

        for spot_id, query in SPOTS:
            dest_jpg = OUTPUT_DIR / f"spot_{spot_id:02d}.jpg"
            dest_png = OUTPUT_DIR / f"spot_{spot_id:02d}.png"
            print(f"[{spot_id:02d}] 搜索: {query}")

            urls = get_image_urls_from_page(page, query)
            print(f"  找到 {len(urls)} 张候选图")

            success = False
            for img_url in urls[:5]:
                ext = ".png" if ".png" in img_url.lower() else ".jpg"
                dest = OUTPUT_DIR / f"spot_{spot_id:02d}{ext}"
                # 清理旧文件（另一个扩展名）
                other = dest_jpg if ext == ".png" else dest_png
                if other.exists():
                    other.unlink()
                if download_image(page, img_url, dest):
                    print(f"  已保存 → {dest.name}")
                    results[spot_id] = {"query": query, "url": img_url, "file": dest.name}
                    success = True
                    break
                time.sleep(0.5)

            if not success:
                print(f"  [警告] spot_{spot_id:02d} 下载失败")
                results[spot_id] = {"query": query, "url": None, "file": None}

            time.sleep(1)

        browser.close()

    # 保存映射记录
    mapping_file = Path(__file__).parent / "spot_image_mapping_v2.json"
    mapping_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n完成！映射已保存至 {mapping_file}")
    failed = [k for k, v in results.items() if not v["file"]]
    if failed:
        print(f"失败的 spot ID: {failed}")


if __name__ == "__main__":
    main()
