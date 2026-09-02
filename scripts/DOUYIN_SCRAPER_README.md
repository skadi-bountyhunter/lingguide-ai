# 抖音视频爬取指南

## 目标
批量获取抖音账号"无锡灵山胜境"的发布视频，用于灵境导游应用的视频专栏页。

---

## 方法一：浏览器自动化（推荐）

### 1. 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 2. 获取用户主页 URL

1. 打开抖音网页版：https://www.douyin.com/
2. 搜索"无锡灵山胜境"
3. 进入官方账号主页
4. 复制浏览器地址栏的 URL，格式类似：
   ```
   https://www.douyin.com/user/MS4wLjABAAAA...
   ```

### 3. 修改脚本配置

编辑 `scripts/scrape_douyin_playwright.py`，将 `USER_URL` 替换为实际 URL：

```python
USER_URL = "https://www.douyin.com/user/MS4wLjABAAAA..."  # 你的实际 URL
```

### 4. 运行脚本

```bash
python scripts/scrape_douyin_playwright.py
```

**首次运行**：
- 会打开浏览器窗口
- 如果需要登录，手动扫码登录
- 登录态会自动保存，下次无需重新登录

**脚本行为**：
- 自动滚动页面加载所有视频
- 提取视频标题、封面、链接
- 保存到 `scripts/douyin_videos.json`

### 5. 输出结果

```json
{
  "account": "无锡灵山胜境",
  "scraped_at": "2026-06-21 18:00:00",
  "total": 50,
  "videos": [
    {
      "id": "7380123456789",
      "title": "灵山大佛全景航拍",
      "cover": "https://...",
      "duration": "2:30",
      "views": "12.5 万",
      "source": "抖音",
      "category": "景区风光",
      "shareUrl": "https://www.douyin.com/video/7380123456789"
    }
  ]
}
```

---

## 方法二：HTTP 请求（轻量，可能失败）

如果不想安装 Playwright，可以用 `scrape_douyin.py`：

```bash
pip install httpx beautifulsoup4
python scripts/scrape_douyin.py
```

**注意**：抖音反爬严格，此方法可能需要登录 Cookie。

---

## 集成到应用

### 方案 A：静态 JSON（简单）

1. 爬取后得到 `douyin_videos.json`
2. 将文件复制到 `frontend-visitor/public/data/douyin_videos.json`
3. 修改 `VideoView.vue`，从 `/data/douyin_videos.json` 读取数据

### 方案 B：后端 API（推荐）

1. 将 `douyin_videos.json` 放到后端
2. 新增 API 接口 `/api/videos` 返回视频列表
3. 前端从 API 获取数据

### 方案 C：数据库存储（长期）

1. 创建 `videos` 表
2. 导入爬取的数据
3. 后台管理界面可增删改

---

## 注意事项

### 法律合规
- 仅用于学习和个人项目
- 商用需获得抖音官方授权
- 不要高频爬取，避免被封禁

### 技术限制
- 只能获取公开视频
- 私密视频无法获取
- 抖音改版后脚本可能失效

### 数据更新
- 建议每月重新爬取一次
- 或手动检查新视频并添加

---

## 常见问题

**Q: 脚本运行失败怎么办？**
A: 检查 URL 是否正确，尝试用方法二（Playwright）

**Q: 提取到的视频数量为 0？**
A: 可能需要登录，或抖音页面结构已变化

**Q: 视频封面图无法显示？**
A: 抖音图片有防盗链，需要后端代理或下载图片到本地

**Q: 如何获取视频时长和播放量？**
A: 需要额外请求每个视频的详情页，脚本中已预留字段

---

## 下一步

1. 运行脚本爬取视频
2. 检查输出的 JSON 数据
3. 决定集成方案（静态 JSON / API / 数据库）
4. 修改 `VideoView.vue` 读取真实数据
