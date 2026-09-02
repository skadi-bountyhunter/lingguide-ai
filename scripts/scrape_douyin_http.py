"""
用 HTTP 请求爬取抖音视频（无需安装浏览器）

使用方法：
python scripts/scrape_douyin_http.py

输出：scripts/douyin_videos.json
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import httpx

# ===== 配置 =====
USER_URL = "https://www.douyin.com/user/MS4wLjABAAAAaGti2Gp2XFW8zmr6zUIJ_4SOs7H0gbySNlIhBdnQDgOGzPE0Hae82h2MGu5O1Nn_?from_tab_name=main"
OUTPUT_FILE = Path(__file__).parent / "douyin_videos.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
}


def extract_videos_from_html(html: str) -> list[dict]:
    """从抖音用户主页 HTML 提取视频数据"""
    videos = []

    # 抖音 SSR 数据在 RENDER_DATA 中
    pattern = r'<script id="RENDER_DATA" type="application/json">(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)

    if not match:
        print("未找到 RENDER_DATA，可能需要登录 Cookie")
        return videos

    raw = match.group(1)
    decoded = unquote(raw)

    try:
        data = json.loads(decoded)
        print(f"✓ RENDER_DATA 解析成功 ({len(decoded)} 字符)")
    except json.JSONDecodeError as e:
        print(f"✗ JSON 解析失败：{e}")
        return videos

    # 抖音视频数据结构
    # 通常在 data.user.postList 或 data.user.videoList
    user_data = data.get("user", {})

    # 尝试不同路径
    post_list = (
        user_data.get("postList") or
        user_data.get("videoList") or
        user_data.get("awemeList") or
        []
    )

    if not post_list:
        # 可能在其他嵌套结构中
        for key, val in user_data.items():
            if isinstance(val, list) and len(val) > 0:
                post_list = val
                break

    print(f"✓ 找到 {len(post_list)} 个视频")

    for item in post_list:
        video_id = item.get("awemeId") or item.get("videoId") or item.get("id", "")
        desc = item.get("desc") or item.get("title", "")
        cover = ""
        duration = "0:00"

        # 提取封面图
        video = item.get("video", {})
        if video:
            duration_ms = video.get("duration", 0)
            if duration_ms:
                mins = int(duration_ms) // 60000
                secs = (int(duration_ms) % 60000) // 1000
                duration = f"{mins}:{secs:02d}"

            cover_obj = video.get("cover", {}) or video.get("dynamicCover", {}) or video.get("originCover", {})
            if cover_obj:
                cover = cover_obj.get("urlList", [""])[0] or cover_obj.get("uri", "")

        # 提取统计
        stats = item.get("statistics", {})
        views = stats.get("playCount") or stats.get("diggCount") or 0

        # 格式化播放量
        if isinstance(views, (int, float)):
            if views >= 10000:
                views_str = f"{views / 10000:.1f}万"
            else:
                views_str = str(int(views))
        else:
            views_str = str(views)

        if video_id:
            videos.append({
                "id": str(video_id),
                "title": desc[:100] if desc else f"视频 {video_id}",
                "desc": desc[:200] if desc else "",
                "cover": cover,
                "duration": duration,
                "views": views_str,
                "source": "抖音",
                "category": "景区风光",
                "shareUrl": f"https://www.douyin.com/video/{video_id}",
            })

    return videos


def scrape_videos() -> list[dict]:
    """爬取抖音视频列表"""
    print(f"目标：{USER_URL}")
    print("发送请求...")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        resp = client.get(USER_URL)

        print(f"状态码：{resp.status_code}")
        print(f"响应大小：{len(resp.text)} 字符")

        if resp.status_code != 200:
            print("✗ 请求失败，可能需要登录 Cookie")
            return []

        videos = extract_videos_from_html(resp.text)
        return videos


def save_videos(videos: list[dict]):
    """保存视频数据"""
    if not videos:
        print("没有视频数据")
        return

    output = {
        "account": "无锡灵山胜境",
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(videos),
        "videos": videos,
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 已保存到：{OUTPUT_FILE}")
    print(f"  共 {len(videos)} 个视频")

    if videos:
        print("\n前 3 个视频预览：")
        for v in videos[:3]:
            print(f"  - {v['title']}")
            print(f"    时长：{v['duration']}  播放：{v['views']}")
            print(f"    链接：{v['shareUrl']}")


def main():
    videos = scrape_videos()
    save_videos(videos)


if __name__ == "__main__":
    main()
