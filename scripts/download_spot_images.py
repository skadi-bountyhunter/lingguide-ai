"""
景点图片批量下载脚本
从多个来源（Pixabay、Unsplash、Pexels）搜索并下载灵山景区 22 个景点的高质量图片
"""
import requests
import json
import time
from pathlib import Path
from urllib.parse import quote

# 配置
OUTPUT_DIR = Path(__file__).parent.parent / "frontend-tourist" / "public" / "images" / "spots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 景点列表（按 sort_order 排序）
SPOTS = [
    {"id": 1, "name": "灵山大佛", "keywords": "Lingshan Grand Buddha Wuxi statue bronze"},
    {"id": 2, "name": "梵宫", "keywords": "Lingshan Palace Buddhist architecture China"},
    {"id": 3, "name": "九龙灌浴", "keywords": "Nine Dragons Bathing Buddha fountain Lingshan"},
    {"id": 4, "name": "五印坛城", "keywords": "Wuyin Mandala Palace Tibetan Buddhist Lingshan"},
    {"id": 5, "name": "降魔浮雕", "keywords": "Buddhist relief sculpture demon Buddha"},
    {"id": 6, "name": "菩提大道", "keywords": "Bodhi path tree avenue Buddhist temple"},
    {"id": 7, "name": "灵山大照壁", "keywords": "Lingshan screen wall stone calligraphy"},
    {"id": 8, "name": "五明桥", "keywords": "Five Wisdom Bridges white marble Buddhist"},
    {"id": 9, "name": "佛足坛", "keywords": "Buddha footprint bronze Buddhist"},
    {"id": 10, "name": "五智门", "keywords": "Five Wisdom Gate arch Buddhist white marble"},
    {"id": 11, "name": "阿育王柱", "keywords": "Ashoka Pillar lion Buddhist India"},
    {"id": 12, "name": "百子戏弥勒", "keywords": "Maitreya Buddha children sculpture laughing"},
    {"id": 13, "name": "祥符禅寺", "keywords": "Xiangfu Buddhist temple ancient China pagoda"},
    {"id": 14, "name": "佛教文化博览馆", "keywords": "Buddhist culture museum hall interior China"},
    {"id": 15, "name": "曼飞龙塔", "keywords": "Manfeilong Pagoda white towers Buddhist Yunnan"},
    {"id": 16, "name": "无尽意斋", "keywords": "Chinese courtyard traditional architecture garden"},
    {"id": 17, "name": "拈花广场", "keywords": "Nianhua Bay square bronze Buddha flower statue"},
    {"id": 18, "name": "梵天花海", "keywords": "flower field garden colorful scenic China"},
    {"id": 19, "name": "香月花街", "keywords": "traditional Chinese street lanterns night architecture"},
    {"id": 20, "name": "拈花堂", "keywords": "Buddhist meditation hall tea ceremony traditional"},
    {"id": 21, "name": "五灯湖", "keywords": "lake reflection lights night scenic China"},
    {"id": 22, "name": "鹿鸣谷", "keywords": "bamboo forest mountain path nature trail China"},
]

# Pixabay API（免费，需注册获取 key：https://pixabay.com/api/docs/）
# 替换为你的 API key，或留空跳过 Pixabay
PIXABAY_API_KEY = ""  # 从环境变量或配置文件读取更安全

# Unsplash API（免费，需注册：https://unsplash.com/developers）
UNSPLASH_ACCESS_KEY = ""

# Pexels API（免费，需注册：https://www.pexels.com/api/）
PEXELS_API_KEY = ""


def download_image(url: str, filepath: Path) -> bool:
    """下载图片到本地"""
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        filepath.write_bytes(resp.content)
        print(f"✓ 下载成功: {filepath.name}")
        return True
    except Exception as e:
        print(f"✗ 下载失败 {url}: {e}")
        return False


def search_pixabay(query: str, spot_id: int) -> bool:
    """从 Pixabay 搜索并下载图片"""
    if not PIXABAY_API_KEY:
        return False
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={quote(query)}&image_type=photo&per_page=3&safesearch=true"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data["hits"]:
            img_url = data["hits"][0]["largeImageURL"]  # 或 webformatURL
            return download_image(img_url, OUTPUT_DIR / f"spot_{spot_id:02d}_pixabay.jpg")
    except Exception as e:
        print(f"Pixabay 搜索失败: {e}")
    return False


def search_unsplash(query: str, spot_id: int) -> bool:
    """从 Unsplash 搜索并下载图片"""
    if not UNSPLASH_ACCESS_KEY:
        return False
    url = f"https://api.unsplash.com/search/photos?query={quote(query)}&per_page=1&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data["results"]:
            img_url = data["results"][0]["urls"]["regular"]  # 或 full
            return download_image(img_url, OUTPUT_DIR / f"spot_{spot_id:02d}_unsplash.jpg")
    except Exception as e:
        print(f"Unsplash 搜索失败: {e}")
    return False


def search_pexels(query: str, spot_id: int) -> bool:
    """从 Pexels 搜索并下载图片"""
    if not PEXELS_API_KEY:
        return False
    url = f"https://api.pexels.com/v1/search?query={quote(query)}&per_page=1"
    try:
        resp = requests.get(url, timeout=10, headers={"Authorization": PEXELS_API_KEY})
        resp.raise_for_status()
        data = resp.json()
        if data["photos"]:
            img_url = data["photos"][0]["src"]["large"]  # 或 original
            return download_image(img_url, OUTPUT_DIR / f"spot_{spot_id:02d}_pexels.jpg")
    except Exception as e:
        print(f"Pexels 搜索失败: {e}")
    return False


def main():
    print("=" * 60)
    print("灵山景点图片批量下载")
    print("=" * 60)
    print(f"输出目录: {OUTPUT_DIR.absolute()}\n")

    if not any([PIXABAY_API_KEY, UNSPLASH_ACCESS_KEY, PEXELS_API_KEY]):
        print("⚠️  未配置任何 API Key，请在脚本中填写至少一个图片源的 API Key：")
        print("  - Pixabay: https://pixabay.com/api/docs/")
        print("  - Unsplash: https://unsplash.com/developers")
        print("  - Pexels: https://www.pexels.com/api/")
        print("\n或者手动从以下网站搜索下载：")
        for spot in SPOTS:
            print(f"  {spot['id']:2d}. {spot['name']:12s} → {spot['keywords']}")
        return

    success_count = 0
    for spot in SPOTS:
        print(f"\n[{spot['id']}/22] {spot['name']} ({spot['keywords']})")

        # 优先级：Pixabay > Unsplash > Pexels
        if search_pixabay(spot["keywords"], spot["id"]):
            success_count += 1
        elif search_unsplash(spot["keywords"], spot["id"]):
            success_count += 1
        elif search_pexels(spot["keywords"], spot["id"]):
            success_count += 1
        else:
            print(f"✗ 未找到合适图片")

        time.sleep(1)  # 避免 API 限流

    print("\n" + "=" * 60)
    print(f"完成！成功下载 {success_count}/22 张图片")
    print(f"输出目录: {OUTPUT_DIR.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
