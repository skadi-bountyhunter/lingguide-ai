"""
用浏览器自动化爬取抖音视频（更可靠）

依赖：pip install playwright
安装浏览器：playwright install chromium

使用方法：
1. 先手动登录抖音网页版（保存登录态）
2. 运行：python scripts/scrape_douyin_playwright.py
3. 输出：scripts/douyin_videos.json

优势：
- 模拟真实浏览器，绕过反爬
- 可以复用浏览器登录态
- 滚动加载所有视频
"""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# ===== 配置 =====
USER_URL = "https://www.douyin.com/user/MS4wLjABAAAAaGti2Gp2XFW8zmr6zUIJ_4SOs7H0gbySNlIhBdnQDgOGzPE0Hae82h2MGu5O1Nn_?from_tab_name=main"
OUTPUT_FILE = Path(__file__).parent / "douyin_videos.json"

# 浏览器登录态保存路径
STORAGE_STATE = Path(__file__).parent / "douyin_auth.json"


def scrape_with_playwright():
    """用 Playwright 爬取抖音视频"""
    print("启动浏览器...")

    with sync_playwright() as p:
        # 启动浏览器（有头模式，方便调试）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        # 加载登录态（如果存在）
        if STORAGE_STATE.exists():
            print("加载登录态...")
            context.storage_state(path=str(STORAGE_STATE))

        page = context.new_page()

        # 访问用户主页
        print(f"访问：{USER_URL}")
        page.goto(USER_URL, wait_until="domcontentloaded", timeout=60000)
        print("页面加载完成，等待渲染...")
        time.sleep(5)  # 等待 SSR 渲染

        # 检查是否需要登录
        if "login" in page.url.lower():
            print("需要登录！请在浏览器中手动登录抖音")
            print("登录完成后按回车继续...")
            input()
            # 保存登录态
            context.storage_state(path=str(STORAGE_STATE))
            print("登录态已保存")

        # 滚动加载所有视频
        print("滚动加载视频...")
        last_height = 0
        scroll_count = 0
        max_scrolls = 50  # 最多滚动 50 次

        while scroll_count < max_scrolls:
            # 获取当前页面高度
            current_height = page.evaluate("document.documentElement.scrollHeight")

            if current_height == last_height:
                # 高度没变化，可能已经到底部
                time.sleep(2)
                current_height = page.evaluate("document.documentElement.scrollHeight")
                if current_height == last_height:
                    print("已加载所有视频")
                    break

            # 滚动到底部
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            time.sleep(1.5)  # 等待加载

            last_height = current_height
            scroll_count += 1
            print(f"  滚动 {scroll_count} 次，当前高度：{current_height}")

        # 提取视频数据
        print("提取视频数据...")
        videos = page.evaluate("""
            () => {
                const videos = [];
                // 查找所有视频卡片
                const cards = document.querySelectorAll('[data-e2e="user-post-list"] a, .ECMzMy a');
                cards.forEach(card => {
                    const link = card.href || '';
                    const videoId = link.match(/\\/video\\/(\\d+)/)?.[1];
                    if (!videoId) return;

                    const img = card.querySelector('img');
                    const title = card.querySelector('p')?.textContent || '';

                    videos.push({
                        id: videoId,
                        title: title.trim().substring(0, 100),
                        cover: img?.src || '',
                        duration: '0:00',
                        views: '0',
                        source: '抖音',
                        category: '景区风光',
                        shareUrl: `https://www.douyin.com/video/${videoId}`,
                    });
                });
                return videos;
            }
        """)

        print(f"提取到 {len(videos)} 个视频")

        browser.close()

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
    print(f"已保存到：{OUTPUT_FILE}")

    # 显示前 3 个
    print("\n前 3 个视频预览：")
    for v in videos[:3]:
        print(f"  - {v['title']}")
        print(f"    链接：{v['shareUrl']}")


def main():
    if USER_URL.endswith("..."):
        print("请先设置 USER_URL")
        print("获取方法：")
        print("1. 打开抖音网页版：https://www.douyin.com/")
        print("2. 搜索'无锡灵山胜境'")
        print("3. 进入主页，复制浏览器地址栏的 URL")
        print("4. 粘贴到脚本的 USER_URL 变量中")
        return

    videos = scrape_with_playwright()
    save_videos(videos)


if __name__ == "__main__":
    main()
