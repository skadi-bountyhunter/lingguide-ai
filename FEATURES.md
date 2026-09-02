# 灵境导游 - 功能实现记录

> 更新日期：2026-07-18

---

## 一、景区详情页（SpotDetailView）

### 功能
- 景点详情页，展示完整景区信息
- 路由：`/spot/:name`

### 内容模块
| 模块 | 说明 |
|---|---|
| Hero 大图 | 顶部封面图，含返回按钮、标题、标签 |
| 快捷信息栏 | 游览时长 / 距入口 / 最佳季节 |
| 景点介绍 | 多段落完整介绍 |
| 核心亮点 | 2 列网格编号卡片 |
| 实用信息 | 开放时间 / 门票信息 / 最佳季节 |
| 游览贴士 | 带勾选图标的建议列表 |
| 周边景点 | 横向滚动卡片，可点击跳转 |
| 底部操作栏 | AI讲解（跳转聊天页）/ 导航前往 |

### 数据源
`src/data/spots.ts` — 6 个景点完整数据（灵山大佛、梵宫、九龙灌浴、五印坛城、降魔浮雕、菩提大道）

### 涉及文件
| 文件 | 操作 |
|---|---|
| `src/data/spots.ts` | 新建 — 共享景点数据 |
| `src/views/SpotDetailView.vue` | 新建 — 详情页组件 |
| `src/views/HomeView.vue` | 修改 — 导入共享数据，添加点击跳转 |
| `src/router.ts` | 修改 — 新增 spot 路由 |
| `src/App.vue` | 修改 — 详情页隐藏 TabBar |

---

## 二、滚动修复

### 问题
`index.html` 中 `html, body, #app { overflow: hidden }` 导致所有页面无法垂直滚动。

### 修复
移除 `overflow: hidden`，仅保留 `margin: 0; padding: 0; width: 100%; height: 100%`。

### 影响
- 导览页、路线页滚动恢复正常

---

## 三、一键启停脚本

### 启停说明
当前未提供已提交的 `启动.bat`/`停止.bat` 脚本，请按《启动与停止说明.md》分别启动和停止后端、游客端与管理端。

### 服务端口
| 服务 | 端口 |
|---|---|
| 后端 API | 8000 |
| 游客前端 | 3000 |
| 管理后台 | 3001 |

---

## 四、景区视频专栏

### 功能
- 视频列表页，展示抖音账号"无锡灵山胜境"的发布视频
- 路由：`/videos`
- 点击视频卡片直接跳转抖音播放（新标签页）

### 数据爬取
| 文件 | 说明 |
|---|---|
| `scripts/scrape_douyin_playwright.py` | 浏览器自动化爬取脚本（推荐） |
| `scripts/scrape_douyin_http.py` | HTTP 请求爬取脚本（需 Cookie） |
| `scripts/DOUYIN_SCRAPER_README.md` | 爬取使用文档 |
| `frontend-visitor/public/data/douyin_videos.json` | 爬取输出的视频数据（19 条真实数据） |

### 爬取流程
```bash
# 1. 修改脚本中的 USER_URL 为目标抖音账号主页
# 2. 运行爬取
python scripts/scrape_douyin_playwright.py

# 3. 复制到前端目录
cp scripts/douyin_videos.json frontend-visitor/public/data/
```

### 页面特性
- 从 JSON 文件动态加载视频数据
- 视频卡片包含：封面图、标题、描述、跳转提示、来源标识
- 移动端响应式适配（缩略图 120×90px）
- 点击卡片新标签页打开抖音播放

### 涉及文件
| 文件 | 操作 |
|---|---|
| `src/views/VideoView.vue` | 新建 — 视频页面组件 |
| `public/data/douyin_videos.json` | 新建 — 视频数据（19 条） |
| `src/router.ts` | 修改 — 新增 videos 路由 |
| `src/App.vue` | 修改 — 视频页隐藏 TabBar |
| `src/views/HomeView.vue` | 修改 — 快捷入口添加"景区视频"按钮 |

---

## 五、数字人遮罩修复

### 问题
魔珐星云 SDK 在 TTS 播报时自动注入 `avatar-sdk-widget-container` div，带 `rgba(0,0,0,0.8)` 黑色遮罩。

### 修复
在 `XingyunStage.vue` 添加 CSS 覆盖：
```css
.xy-render :deep(.avatar-sdk-widget-container) {
  background: transparent !important;
}
```

---

## 六、技术栈

| 层面 | 技术 |
|---|---|
| 前端框架 | Vue 3 + TypeScript + Vite |
| UI 组件 | Element Plus |
| 状态管理 | Pinia |
| 路由 | Vue Router |
| 后端 | FastAPI + Uvicorn |
| 数据库 | SQLite |
| 数字人 | 魔珐星云 3D |
| 浏览器自动化 | Playwright（抖音视频爬取） |

---

## 七、已知限制

| 项目 | 说明 |
|---|---|
| 抖音视频播放 | 不支持外链嵌入，只能跳转抖音播放 |
| 抖音视频时长 | 爬取数据中时长字段为 0:00，已移除显示 |
| RAG 生产候选限制 | 天气可靠性阶段4A已具备地点优先、总 deadline、fresh/stale 降级；WebSocket 会话边界、在线观测、LLM deadline/有限重试、认证安全和灰度回滚仍在后续计划中，未完成前仅适合受控内网/测试环境 |
| 视频数据更新 | 需手动运行爬取脚本更新 |
