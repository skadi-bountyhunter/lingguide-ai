# 灵境导游 (LingGuide) — 游客端前端重构文档

> 撰写日期：2026-06-18 | 供前端设计 Agent 使用

---

## 一、项目身份

**灵境导游**是一个 AI 数字人智慧导览系统的游客端。游客通过文字/语音与"小灵"AI 导游对话，获取灵山胜境景区的实时讲解、路线推荐。

**品牌调性**：东方美学 × 现代科技感，佛教文化庄严但不沉重，亲切而不轻浮。

---

## 二、技术栈（不可变）

```
Vue 3.5        Composition API + <script setup lang="ts">
Vite 6         开发服务器，代理 /api → localhost:8000
Pinia 2        状态管理
Vue Router 4   客户端路由 (createWebHistory)
Element Plus 2.14   UI 组件库（全局注册 + auto-import）
@element-plus/icons-vue  图标（全局注册所有图标）
TypeScript 5.7
```

**Element Plus 自动导入已配置**：`ElMessage` 等无需手动 import（但 `env.d.ts` 需保留包的原始类型声明）。

---

## 三、路由结构

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | `HomeView.vue` | 首页：品牌展示 + 兴趣标签选择 → 跳转对话 |
| `/chat` | `ChatView.vue` | 核心对话页：WebSocket 聊天 + 语音 + TTS |
| `/route` | `RouteView.vue` | 路线推荐：AI 智能规划 + 5 条预设路线卡片 |

---

## 四、页面详细说明

### 4.1 首页 `HomeView.vue`

**用户任务**：了解产品 → 选择兴趣 → 进入对话

**UI 结构**：
```
┌────────────────────────────┐
│  🏯 灵山胜境                │  ← hero-title
│  AI 数字人导游 · 智慧导览   │  ← hero-subtitle
│  我是您的专属导游"小灵"...  │  ← hero-desc
│                            │
│  选择您感兴趣的主题         │
│  [佛教文化] [自然风光]     │  ← interest-tag (多选 toggle, 6 个)
│  [历史古迹] [亲子游乐]     │
│  [建筑艺术] [美食素斋]     │
│                            │
│  [ 开始对话 ]              │  ← 主按钮，跳 /chat，携带兴趣
│                            │
│  语音问答 | 路线推荐        │  ← 快捷入口
└────────────────────────────┘
```

**交互**：
- 兴趣标签点击 toggle（多选），蓝色高亮 `#e8d5b5`
- "开始对话"把选中的兴趣写入 `chatStore.interests`，`router.push('/chat')`
- 快捷入口可直跳 `/chat` 或 `/route`

**状态**：仅本地 `selected: string[]`，无网络请求

---

### 4.2 对话页 `ChatView.vue` — 核心页面

**用户任务**：与 AI 导游实时对话，获取景区知识

**UI 结构**：
```
┌────────────────────────────┐
│  ← 返回  小灵·AI导游 ●在线  ↻新对话 │  ← chat-header (sticky)
├────────────────────────────┤
│                            │
│  [空态]                    │
│  🧑‍💼 大图标                │
│  您好，我是小灵 👋         │
│  您的灵山胜境 AI 导游...   │
│  [灵山大佛有多高？]        │  ← quick-questions (5 个快捷按钮)
│  [梵宫有什么特色？]        │
│  ...                       │
│                            │
│  [对话中]                  │
│  ┌──────────────┐         │
│  │ user bubble   │ 右对齐   │  ← message-row.user
│  └──────────────┘         │
│  ┌──────────────────────┐ │
│  │ assistant bubble     │ │  ← message-row.assistant
│  │ 回复文本内容         │ │
│  │ [😊 正面]            │ │  ← message-emotion (可选)
│  │ ─────────            │ │
│  │ 🎧 播放 / 停止       │ │  ← TTS 按钮 (播放中高亮蓝色)
│  └──────────────────────┘ │
│  ● ● ●  (loading dots)    │  ← 思考中动画
│                            │
├────────────────────────────┤
│  💬 [输入您的问题...]     │  ← el-input + 发送按钮
│  [ 发送 ] [🎤]            │
│  按 Enter 发送 · 支持语音  │  ← 提示文字
└────────────────────────────┘
```

**状态机**：
```
初始 → 用户输入 → isLoading=true(三点动画) → 流式收到chunk(追加文本) → llm_done(完成)
                                                                     → error(异常)
```

**WebSocket 消息协议**：

客户端 → 服务端：
```json
{ "query": "灵山大佛有多高？", "mode": "text", "interests": ["佛教文化"] }
```

服务端 → 客户端（流式）：
```json
{"type": "asr_done", "asr_text": "..."}          // 仅语音模式
{"type": "rag_done", "sources": ["doc1.docx"]}    // 检索完成
{"type": "llm_stream", "chunk": "灵山大佛高达"}   // 流式文本块
{"type": "llm_done", "reply_text": "...", "emotion": "neutral", "expression": "neutral", "sources": [...]}
{"type": "error", "message": "..."}
```

**TTS 播放**：
- 每条 assistant 消息有独立播放/停止按钮
- 点击 → `GET /api/chat/audio/{session_id}?reply={文本}` → 后端合成 Edge-TTS 音频
- `playingState` (reactive Record) 追踪各消息播放状态
- `audioMap` (Map<id, Audio>) 管理 Audio 实例
- 组件卸载时 `onUnmounted` 全部停止

**语音输入**：
- 点击麦克风 → `navigator.mediaDevices.getUserMedia({audio: true})` → MediaRecorder 录 webm
- 停止 → `POST /api/chat/voice` (FormData: audio + session_id + interests)
- 后端返回 `{query_text, reply, emotion, audio_url}` → 追加消息 + 自动播 TTS

**快捷问题** (5 个)：
```
灵山大佛有多高？| 梵宫有什么特色？| 九龙灌浴表演时间是？| 推荐一条游览路线 | 灵山的历史文化
```

---

### 4.3 路线推荐 `RouteView.vue`

**UI 结构**：
```
┌────────────────────────────┐
│  ← 返回   🗺️ 个性化路线推荐 │
├────────────────────────────┤
│  🤖 AI 智能规划        [AI]│  ← 卡片
│  兴趣偏好: [佛教文化][自然风光]... │  ← checkbox-button 6 个
│  游览时长: ○半天 ○全天   │  ← radio-group
│  [ ✨ AI 智能规划 ]       │  ← 触发 POST /api/chat/route
│  ─────────────────────── │
│  (AI 返回的路线文本)      │  ← v-html 渲染 Markdown→HTML
│                            │
├────────────────────────────┤
│  📋 预设经典路线            │  ← 静态备选
│  按兴趣筛选: [全部][佛教文化]...│
│                            │
│  ┌─ 路线卡片 ────────────┐ │
│  │ 🛕 佛韵深度游  3.5h   │ │  ← 5 张卡片 grid
│  │ 描述...               │ │
│  │ 📍 景点1  📍 景点2   │ │
│  │ ℹ️ 温馨提示           │ │
│  └──────────────────────┘ │
└────────────────────────────┘
```

**API 调用**：`POST /api/chat/route` → `{route_text, spots, sources}`

---

## 五、Pinia Store（`chat.ts`）

```typescript
// 单 store，全局共享
useChatStore: {
  sessionId: string        // crypto.randomUUID()，标识一次会话
  interests: string[]      // 兴趣标签，首页选择后携带
  messages: ChatMessage[]  // 所有对话消息
  isLoading: boolean       // 当前是否等待 AI 回复（控制 loading 动画和输入禁用）
  wsConnected: boolean     // WebSocket 连接状态（头部在线/离线标签）

  // computed
  lastAssistantMessage: ChatMessage | null

  // actions
  addMessage(msg: ChatMessage)
  clearMessages()
  newSession()             // 重置 sessionId + 清空消息
}

ChatMessage: {
  id: string
  role: 'user' | 'assistant'
  content: string
  emotion?: string         // positive/neutral/negative
  expression?: string      // happy/neutral/concerned
  timestamp: number
}
```

---

## 六、WebSocket Composable（`useWebSocket.ts`）

```typescript
useWebSocket() → {
  isConnected: Ref<boolean>    // 连接状态
  connect()                     // 建立 WebSocket，自动重连
  sendMessage(query, mode)     // 发送消息，断连时先重连再发(1次重试)
  disconnect()                  // 主动断开
}

// 内部处理消息分发：
// llm_stream → store.addMessage(assistant) 或追加 content
// llm_done   → 用 reply_text 替换 content + 设置 emotion/expression
// error      → console.error
```

---

## 七、API 接口总览（前端消费）

| 方法 | 路径 | 用途 | 调用位置 |
|------|------|------|----------|
| `POST` | `/api/chat/text` | 文本对话（非流式） | 备用 |
| `WS` | `/api/chat/ws/{sessionId}` | WebSocket 流式对话 | ChatView |
| `POST` | `/api/chat/voice` | 语音上传+识别+回复 | ChatView 语音 |
| `GET` | `/api/chat/audio/{id}?reply=...` | 获取 TTS 音频 | ChatView 播放按钮 |
| `POST` | `/api/chat/route` | AI 路线规划 | RouteView |
| `GET` | `/api/knowledge/stats` | 知识库统计 | 可选 |

---

## 八、样式系统

**全局** (`global.css`)：CSS reset + 滚动条美化 + 基础字体（PingFang SC / Microsoft YaHei）

**页面级**：`<style scoped>` 内联，无 CSS 变量/设计令牌体系

**色板（当前硬编码）**：
```
背景深色: #0f1729 → #1a2a3a → #0d1b2a  (渐变)
品牌金色: #e8d5b5  (标题/高亮/选中边框)
品牌金色半透: rgba(201, 169, 110, 0.15~0.3)
文字主色: #cbd5e1 / #e2e8f0
文字辅助: #94a3b8 / #64748b / #475569
表面背景: rgba(255,255,255, 0.03~0.06)
表面边框: rgba(255,255,255, 0.06~0.08)
```

---

## 九、目录结构

```
frontend-visitor/
├── index.html
├── package.json
├── vite.config.ts          # 代理 /api→:8000, ws:true
├── tsconfig.json
├── env.d.ts               # 类型声明（不应覆盖 element-plus 原始类型）
└── src/
    ├── main.ts             # createApp + Pinia + Router + ElementPlus + Icons
    ├── App.vue             # <router-view /> + 全局深色背景渐变
    ├── router.ts           # 3 条路由 (/, /chat, /route)
    ├── stores/
    │   └── chat.ts         # Pinia store（会话/消息/加载状态）
    ├── composables/
    │   └── useWebSocket.ts # WebSocket 封装
    ├── views/
    │   ├── HomeView.vue    # 首页
    │   ├── ChatView.vue    # 对话页 (440 行, 最复杂)
    │   └── RouteView.vue   # 路线推荐 (350 行)
    └── assets/
        └── styles/
            └── global.css  # 全局样式
```

**当前无 `components/` 目录** — 所有 UI 均内联在 views 中。

---

## 十、已知问题 / 重构建议

### 当前痛点
1. **无组件拆分** — ChatView 440 行单文件，消息列表/输入区/语音/TTS 全部耦合
2. **硬编码色板** — 颜色散落各处，无设计令牌，换主题需全局搜索替换
3. **语音功能脆弱** — MediaRecorder API 兼容性差，无状态反馈
4. **TTS 通过 URL 传全文** — 长文本会超 URL 长度限制，应用 POST 替代
5. **空态/加载/错误** — 样式中规中矩但缺乏情感化设计
6. **无过渡动画** — 消息出现、页面切换无过渡
7. **移动端适配未独立测试** — 依赖 Element Plus 响应式，未专调

### 后端接口（不变）
后端 API 路径、WebSocket 协议、TTS 接口均为稳定接口，重构时不应修改。

### 建议保留
- Pinia Store 结构（`chat.ts`）— 接口稳定
- WebSocket 消息类型协议 — 后端依赖
- 路由结构（3 页面）— 用户流程已验证
- Element Plus 技术选型 — 但可考虑封装业务组件

---

*文档版本: v1.0 | 基于 commit: 未纳入版本控制*
