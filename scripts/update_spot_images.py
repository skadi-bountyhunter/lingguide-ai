# -*- coding: utf-8 -*-
"""
用高德 Place Search API 为每个景点获取真实图片，
下载到 frontend-visitor/public/images/ 并更新 SQLite。
"""
import os
import sys
import sqlite3

# 强制 UTF-8 输出，避免 Windows GBK 乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import re
import time
import urllib.request
import urllib.parse
import json
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / "backend" / ".env"
DB_PATH = ROOT / "backend" / "app" / "data" / "lingguide.db"
IMG_DIR = ROOT / "frontend-visitor" / "public" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

# ── 读 .env ───────────────────────────────────────────────────────────────────
def _load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env

_env = _load_env(ENV_FILE)
AMAP_KEY = _env.get("AMAP_WEB_KEY", "")
if not AMAP_KEY:
    sys.exit("AMAP_WEB_KEY not found in backend/.env")

# ── 高德搜索词（更精确的 query 提高匹配率）──────────────────────────────────
SPOT_QUERIES: list[tuple[str, str]] = [
    ("灵山大佛",       "灵山大佛"),
    ("梵宫",           "灵山梵宫"),
    ("九龙灌浴",       "九龙灌浴"),
    ("五印坛城",       "五印坛城"),
    ("降魔浮雕",       "降魔浮雕 灵山"),
    ("菩提大道",       "菩提大道 灵山胜境"),
    ("灵山大照壁",     "灵山大照壁"),
    ("五明桥",         "五明桥 灵山"),
    ("佛足坛",         "佛足坛 灵山"),
    ("五智门",         "五智门 灵山"),
    ("阿育王柱",       "阿育王柱 灵山"),
    ("百子戏弥勒",     "百子戏弥勒"),
    ("祥符禅寺",       "祥符禅寺"),
    ("佛教文化博览馆", "灵山 佛教文化博览馆"),
    ("曼飞龙塔",       "曼飞龙塔 灵山"),
    ("无尽意斋",       "无尽意斋 灵山"),
    ("拈花广场",       "拈花广场 拈花湾"),
    ("梵天花海",       "梵天花海 拈花湾"),
    ("香月花街",       "香月花街 拈花湾"),
    ("拈花堂",         "拈花堂 拈花湾"),
    ("五灯湖",         "五灯湖 拈花湾"),
    ("鹿鸣谷",         "鹿鸣谷 拈花湾"),
]

# ── 高德 POI 搜索 ─────────────────────────────────────────────────────────────
def amap_search(keywords: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "keywords": keywords,
        "city": "无锡",
        "citylimit": "true",
        "extensions": "all",
        "key": AMAP_KEY,
    })
    url = f"https://restapi.amap.com/v3/place/text?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("pois", [])

def pick_photo_url(pois: list[dict]) -> str | None:
    for poi in pois:
        photos = poi.get("photos", [])
        for p in photos:
            url = p.get("url", "")
            if url and url.startswith("http"):
                return url
    return None

# ── 下载图片 ──────────────────────────────────────────────────────────────────
def download_image(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://ditu.amap.com/",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
        if len(content) < 2000:          # 疑似错误页
            return False
        dest.write_bytes(content)
        return True
    except Exception as e:
        print(f"  下载失败 {url}: {e}")
        return False

# ── 文件名安全化 ──────────────────────────────────────────────────────────────
def safe_name(name: str) -> str:
    return re.sub(r"[^\w一-鿿]", "_", name)

# ── 主流程 ────────────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)

results: list[tuple[str, str]] = []   # (spot_name, new_image_path)
failures: list[str] = []

for spot_name, query in SPOT_QUERIES:
    print(f"[{spot_name}] 搜索: {query}")
    try:
        pois = amap_search(query)
        photo_url = pick_photo_url(pois)
    except Exception as e:
        print(f"  API 失败: {e}")
        failures.append(spot_name)
        continue

    if not photo_url:
        print(f"  未找到图片")
        failures.append(spot_name)
        continue

    # 推断扩展名
    ext = ".jpg"
    if ".png" in photo_url.lower():
        ext = ".png"
    elif ".webp" in photo_url.lower():
        ext = ".webp"

    dest_name = f"spot_{safe_name(spot_name)}{ext}"
    dest_path = IMG_DIR / dest_name

    print(f"  下载 → {dest_name}")
    ok = download_image(photo_url, dest_path)
    if not ok:
        print(f"  下载失败，跳过")
        failures.append(spot_name)
        continue

    web_path = f"/images/{dest_name}"
    conn.execute(
        "UPDATE spots SET image = ? WHERE name = ?",
        (web_path, spot_name),
    )
    results.append((spot_name, web_path))
    print(f"  OK {web_path}")
    time.sleep(0.3)   # 礼貌延迟

conn.commit()
conn.close()

print("\n=== 完成 ===")
print(f"成功: {len(results)}/{len(SPOT_QUERIES)}")
if failures:
    print(f"失败: {failures}")
