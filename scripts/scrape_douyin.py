"""
一次性爬取"无锡灵山胜境"抖音账号视频列表

使用方法：
1. 先获取抖音用户主页 URL（见下方说明）
2. 运行脚本：python scripts/scrape_douyin.py
3. 输出：scripts/douyin_videos.json

获取用户主页 URL 的方法：
- 打开抖音 App → 搜索"无锡灵山胜境" → 进入主页
- 点击分享 → 复制链接 → 得到类似 https://www.douyin.com/user/MS4wLjABAAAA...
- 将 URL 粘贴到下方 USER_URL 变量中

注意：
- 抖音有反爬机制，可能需要登录 Cookie
- 如果脚本失败，可用浏览器开发者工具手动提取数据
"""

import json
import re
import time
from pathlib import Path

import httpx

# ===== 配置 =====
USER_URL = "https://www.douyin.com/user/MS4wLjABAAAA..."  # 替换为实际 URL
OUTPUT_FILE = Path(__file__).parent / "douyin_videos.json"

# 抖音请求头（模拟浏览器）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
}

# 可选：登录 Cookie（从浏览器复制）
# 获取方法：F12 → Application → Cookies → 复制 douyin.com 的 Cookie
COOKIE = ""  # 如果有 Cookie，粘贴到这里


def extract_video_data(html: str) -> list[dict]:
    """从抖音用户主页 HTML 中提取视频数据"""
    videos = []

    # 方法 1: 从 __RENDER_DATA__ 提取（SSR 数据）
    pattern = r'<script id="RENDER_DATA" type="application/json">(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        import urllib.parse
        raw = match.group(1)
        decoded = urllib.parse.unquote(raw)
        try:
            data = json.loads(decoded)
            # 抖音数据结构可能变化，需要根据实际调整
            # 通常在 data.user.videoList 或类似路径
            print(f"✓ 找到 RENDER_DATA，大小：{len(decoded)} 字符")
            # TODO: 根据实际数据结构提取视频列表
            # 这里需要根据实际返回的 JSON 结构调整
        except json.JSONDecodeError as e:
            print(f"✗ RENDER_DATA 解析失败：{e}")

    # 方法 2: 从页面中的 JSON 数据提取（备用）
    # 抖音可能在其他 script 标签中嵌入数据
    pattern2 = r'window\.__videoData__\s*=\s*({.*?});'
    match2 = re.search(pattern2, html, re.DOTALL)
    if match2:
        try:
            data = json.loads(match2.group(1))
            print(f"✓ 找到 __videoData__")
        except json.JSONDecodeError:
            pass

    # 方法 3: 从 HTML 中提取视频卡片（最笨但最稳）
    # 每个视频卡片通常包含封面图、标题、播放量等
    card_pattern = r'<a[^>]*href="/video/(\d+)"[^>]*>.*?<img[^>]*src="([^"]*)".*?<p[^>]*>(.*?)</p>'
    for match in re.finditer(card_pattern, html, re.DOTALL):
        video_id, cover, title = match.groups()
        videos.append({
            "id": video_id,
            "title": title.strip()[:100],
            "cover": cover,
            "duration": "0:00",  # 需要额外请求获取
            "views": "0",
            "source": "抖音",
            "category": "景区风光",
            "shareUrl": f"https://www.douyin.com/video/{video_id}",
        })

    return videos


def scrape_videos() -> list[dict]:
    """爬取抖音视频列表"""
    print(f"开始爬取：{USER_URL}")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        if COOKIE:
            client.headers["Cookie"] = COOKIE

        resp = client.get(USER_URL)
        print(f"状态码：{resp.status_code}")
        print(f"响应大小：{len(resp.text)} 字符")

        if resp.status_code != 200:
            print("✗ 请求失败，可能需要登录 Cookie")
            return []

        videos = extract_video_data(resp.text)
        print(f"✓ 提取到 {len(videos)} 个视频")

        return videos


def save_videos(videos: list[dict]):
    """保存视频数据到 JSON"""
    if not videos:
        print("没有视频数据可保存")
        return

    # 转换为前端格式
    output = {
        "account": "无锡灵山胜境",
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(videos),
        "videos": videos,
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 已保存到：{OUTPUT_FILE}")
    print(f"  共 {len(videos)} 个视频")


def main():
    if USER_URL.endswith("..."):
        print(" 请先设置 USER_URL 为实际的抖音用户主页链接")
        print("  获取方法：抖音 App → 搜索'无锡灵山胜境' → 分享 → 复制链接")
        return

    videos = scrape_videos()
    save_videos(videos)

    if videos:
        print("\n前 3 个视频预览：")
        for v in videos[:3]:
            print(f"  - {v['title']}")
            print(f"    封面：{v['cover'][:50]}...")
            print(f"    链接：{v['shareUrl']}")


if __name__ == "__main__":
    main()
