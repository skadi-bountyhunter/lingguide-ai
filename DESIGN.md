# AI 数字人导游 — 系统架构设计文档

---

## 一、项目概述

**项目名称**：灵境导游（LingGuide）— AI 数字人智慧导览系统

**赛题目标**：构建具备多模态交互能力的 AI 数字人导游，为游客提供 7×24 小时智能问答、个性化讲解、情感互动，同时为管理方提供游客洞察数据看板。

**示范景区**：灵山胜境（佛教文化主题景区）

---

## 二、系统架构总览

```
┌─────────────────────────────────────────────────────────┐
│                     游客交互端 (Web/移动端)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ 语音输入  │  │ 文本输入  │  │ 数字人渲染 (口型+表情) │  │
│  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘  │
│       │             │                   │               │
│       ▼             ▼                   ▲               │
│  ┌──────────────────────────────────────────────────┐   │
│  │              WebSocket 实时通信层                  │   │
│  └──────────────────────┬───────────────────────────┘   │
└─────────────────────────┼────────────────────────────────┘
                          │
┌─────────────────────────┼────────────────────────────────┐
│                  FastAPI 后端服务层                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ ASR 模块  │  │ LLM 模块  │  │ TTS 模块  │  │ 表情模块 │ │
│  │ (Whisper) │  │(Qwen3/DS)│  │(CosyVoice)│  │(MiniMates)│ │
│  └─────┬─────┘  └────┬─────┘  └─────┬─────┘  └────┬────┘ │
│        │             │              │              │      │
│        │     ┌───────┴───────┐      │              │      │
│        │     │   RAG 检索    │      │              │      │
│        │     │ (ChromaDB)   │      │              │      │
│        │     └───────┬───────┘      │              │      │
│        │             │              │              │      │
│  ┌─────┴─────────────┴──────────────┴──────────────┴───┐ │
│  │              交互日志 & 情感分析模块                   │ │
│  └──────────────────────────┬──────────────────────────┘ │
└─────────────────────────────┼────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────┐
│                      管理后台 (Web)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │ 知识库管理 │  │ 形象管理  │  │ 感受度报告 │  │ 数据大屏 │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## 三、技术选型与版本

| 层级 | 技术 | 版本/型号 | 选型理由 |
|------|------|-----------|----------|
| **数字人引擎** | MiniMates / DH_live | latest | 极轻量（CPU可跑）、MIT开源、零训练、完整ASR→TTS链路 |
| **语音识别 ASR** | faster-whisper | Large-v3 | 开源、多语言高精度、支持流式识别 |
| **语音合成 TTS** | Edge-TTS（主）/ CosyVoice（增） | - | Edge-TTS免费稳定；CosyVoice支持情感/音色克隆 |
| **大模型 LLM** | Qwen3-8B（本地）/ DeepSeek-V3（API备） | 8B+ | Qwen3国产开源可本地部署；DeepSeek API性价比高 |
| **RAG 检索** | SQLite canonical + FTS5/BM25 + embedded Chroma/BGE + RRF | 当前实现 | 多路召回、canonical 回查、证据过滤和可审计引用 |
| **情感分析** | Qwen2.5-7B / snownlp | - | 对交互文本做情感分类和趋势分析 |
| **前端框架** | Vue3 + Vite + Element Plus | 3.x | 双端统一技术栈、生态成熟 |
| **后端框架** | FastAPI + WebSocket | 0.115+ | 异步高性能、原生WebSocket、Python生态兼容 |
| **数据库** | SQLite | 当前实现 | canonical 文档、分块、FAQ、交互和索引生命周期元数据 |
| **对象存储** | MinIO（本地）/ 本地文件系统 | - | 知识文档、数字人形象素材存储 |
| **部署** | 本地脚本/受控服务进程 | 当前实现 | 后端 8000、游客端 3000、管理端 3001；Docker/灰度仍待补齐 |

---

## 四、模块详细设计

### 4.1 游客交互端

#### 4.1.1 多模态交互模块

```
┌──────────────────────────────────────────┐
│              交互流程                      │
│                                           │
│  语音输入 ──→ VAD 检测 ──→ Whisper ASR    │
│                       ──→ 转文本          │
│                                           │
│  文本输入 ──→ 直接进入 LLM 推理           │
│                                           │
│  LLM 回复 ──→ 文本 → TTS 合成语音         │
│            ──→ 情感标签 → 数字人表情驱动    │
│            ──→ 音素序列 → 数字人口型同步    │
└──────────────────────────────────────────┘
```

**关键流程**：
1. 语音输入 → VAD（Voice Activity Detection）静音切除 → Whisper 流式识别 → 文本
2. 文本 → RAG 检索相关景区知识 → 拼入 Prompt → LLM 生成回复
3. 回复文本 → TTS 合成语音 + 表情参数 → 数字人 WebGL 渲染
4. 全流程目标延迟 < 5 秒

#### 4.1.2 智能问答模块

**RAG Pipeline**：
```
知识文档 (docx/txt/md)
    │
    ▼
文档切片 (chunk_size=600, overlap=80)
    │
    ├──→ SQLite canonical + FTS5/BM25
    │
    └──→ BGE embedding → embedded Chroma
                    │
用户问题 → Structured/FAQ/FTS/Chroma 多路召回 → RRF 融合
                    │
        canonical 回查 → Evidence/Citation/RetrievalTrace → LLM 或拒答
```

**Prompt 模板**：
```
你是灵山胜境景区的AI导游"小灵"。请基于以下景区知识回答游客问题：

【景区知识】
{检索到的知识片段}

【游客问题】
{用户输入}

【回答要求】
1. 准确引用知识片段中的信息
2. 语气亲切自然，像真人导游
3. 如果知识片段不足以回答，请诚实说明
4. 回答控制在200字以内
```

#### 4.1.3 个性化推荐模块

**推荐策略**：

| 兴趣标签 | 推荐路线 | 讲解侧重 |
|----------|----------|----------|
| 佛教文化 | 灵山大佛 → 梵宫 → 五印坛城 | 佛教典故、建筑寓意 |
| 自然风光 | 九龙灌浴 → 曼飞龙塔 → 古银杏广场 | 自然景观、拍照点 |
| 历史古迹 | 祥符禅寺 → 天下第一掌 → 百子戏弥勒 | 历史沿革、人物故事 |
| 亲子游乐 | 梵宫文化体验 → 九龙灌浴 → 素斋体验 | 互动体验、趣味故事 |

**实现方式**：
- 游客首次进入时选择兴趣标签（或对话中自然引导）
- 存储在 Redis 会话中，每次问答携带偏好上下文
- LLM 根据偏好调整讲解风格和推荐内容

---

### 4.2 管理后台端

#### 4.2.1 知识库管理

```
┌──────────────────────────────────────────┐
│            知识库管理界面                  │
│                                           │
│  ┌─ 文档上传 ──────────────────────────┐ │
│  │ 支持格式: .docx / .txt / .md（PDF 待实现） │ │
│  │ 上传后自动切片 + 向量化              │ │
│  │ 显示处理状态和文档列表               │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ┌─ FAQ 管理 ──────────────────────────┐ │
│  │ 手动添加/编辑常见问答对              │ │
│  │ 直接匹配优先于 RAG 检索              │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ┌─ 知识测试 ──────────────────────────┐ │
│  │ 输入测试问题,查看检索结果和回答      │ │
│  │ 调试 chunk 大小和检索参数            │ │
│  └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

**数据结构**：
```sql
-- 知识文档表
documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(255),
    file_type VARCHAR(20),      -- docx/pdf/txt/md
    status VARCHAR(20),          -- processing/done/failed
    chunk_count INT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 知识分块表
chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    content TEXT,
    chunk_index INT,
    embedding VECTOR(1024),      -- bge-large-zh 维度
    created_at TIMESTAMP
);

-- FAQ 表
faqs (
    id UUID PRIMARY KEY,
    question TEXT,
    answer TEXT,
    tags VARCHAR(255)[],
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### 4.2.2 数字人形象管理

```
┌──────────────────────────────────────────┐
│            形象配置界面                    │
│                                           │
│  ┌─ 外观选择 ──────────────────────────┐ │
│  │ ○ 预设形象1 (知性女导游)             │ │
│  │ ○ 预设形象2 (儒雅男导游)             │ │
│  │ ○ 自定义上传                         │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ┌─ 服装配置 ──────────────────────────┐ │
│  │ ○ 景区工服  ○ 汉服  ○ 现代休闲      │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ┌─ 声音配置 ──────────────────────────┐ │
│  │ 音色选择: [温柔女声] [稳重男声]      │ │
│  │ 语速: [===|=====] 1.0x              │ │
│  │ 音量: [=======|==] 0.8x             │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ┌─ 预览 ──────────────────────────────┐ │
│  │     [实时数字人预览播放器]            │ │
│  └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

#### 4.2.3 游客感受度报告

**分析维度**：

| 维度 | 分析方法 | 输出内容 |
|------|----------|----------|
| **关注点分析** | 问答主题聚类 (TF-IDF + K-Means) | 游客最关心的景点/话题 Top10 |
| **情感趋势** | snownlp / Qwen 情感分类 | 每日/每周正向/中性/负向比例曲线 |
| **高频问题** | 问答日志统计 | 未命中FAQ的问题汇总 → 建议补充 |
| **服务质量** | 回答评价收集 | 游客点赞/点踩率、问题解决率 |

**实现流程**：
```
交互日志 (已脱敏)
    │
    ├─→ 文本清洗 ──→ 情感分类 ──→ 情感趋势图表
    │
    ├─→ 词频统计 ──→ 主题提取 ──→ 关注点云图
    │
    └─→ 问答匹配率统计 ──→ 知识缺口分析 ──→ 优化建议
```

#### 4.2.4 数据大屏

```
┌──────────────────────────────────────────────────────┐
│  灵境导游 · 运营数据中心         2026-06-17 14:30    │
├────────────┬────────────┬────────────┬────────────────┤
│  今日服务  │  本周服务  │  当前在线  │  满意度        │
│  1,283人次 │  8,562人次 │      42人  │  94.7% ↑2.1%  │
├────────────┴────────────┴────────────┴────────────────┤
│                                                        │
│  ┌─ 热门问题 Top5 ─────────┐  ┌─ 情感趋势 (7天) ───┐ │
│  │ 1. 灵山大佛有多高？      │  │ ▁▂▃▄▅▆▇           │ │
│  │ 2. 梵宫开放时间？        │  │ 正向 82%           │ │
│  │ 3. 门票多少钱？          │  │ 中性 15%           │ │
│  │ 4. 九龙灌浴几点表演？    │  │ 负向  3%           │ │
│  │ 5. 有什么素斋推荐？      │  │                    │ │
│  └──────────────────────────┘  └────────────────────┘ │
│                                                        │
│  ┌─ 景点关注度排行 ────────┐  ┌─ 服务时段分布 ─────┐ │
│  │ 灵山大佛   ████████ 38% │  │ 08-10  ████ 22%    │ │
│  │ 梵宫       ██████   28% │  │ 10-12  ██████ 35%  │ │
│  │ 九龙灌浴   ████     18% │  │ 12-14  ███   16%   │ │
│  │ 五印坛城   ███      10% │  │ 14-16  ████  20%   │ │
│  │ 曼飞龙塔   █         6% │  │ 16-18  █      7%   │ │
│  └──────────────────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 五、数据流设计

### 5.1 核心交互流程（时序图）

```
游客                前端             后端              LLM         TTS      数字人
 │                  │                │                 │           │         │
 │──语音输入────────→│                │                 │           │         │
 │                  │──音频流────────→│                 │           │         │
 │                  │                │─Whisper ASR────→│           │         │
 │                  │                │←──文本─────────│           │         │
 │                  │                │─RAG检索────────→│           │         │
 │                  │                │←──知识块───────│           │         │
 │                  │                │─Prompt拼合─────→│           │         │
 │                  │                │←──回复文本─────│           │         │
 │                  │                │──回复文本──────────→│       │         │
 │                  │                │←──音频+音素─────│           │         │
 │                  │←──文本+音频+表情数据────────────│           │         │
 │←──数字人播报─────│                │                 │           │         │
 │                  │                │─存储交互日志──→DB│           │         │
```

### 5.2 WebSocket 消息协议

```json
// 客户端 → 服务端
{
  "type": "input",
  "mode": "voice",           // voice | text
  "content": "灵山大佛有多高？",
  "session_id": "uuid",
  "preferences": {            // 游客偏好（首次交互后携带）
    "interests": ["佛教文化"],
    "language": "zh"
  }
}

// 服务端 → 客户端（流式推送）
{
  "type": "response",
  "stage": "asr_done",       // asr_done | rag_done | llm_streaming | llm_done | tts_done
  "asr_text": "灵山大佛有多高？",
  "reply_text": "灵山大佛高达88米...",
  "audio_url": "/api/audio/xxx.wav",     // TTS 完成后返回
  "expression": "smile",                  // 表情标签
  "phonemes": [                           // 口型音素序列
    {"phoneme": "l", "start": 0.0, "end": 0.15},
    {"phoneme": "ing", "start": 0.15, "end": 0.35},
    ...
  ],
  "thinking_time_ms": 3200               // 总耗时
}
```

---

## 六、数据库设计

### 6.1 核心表结构

```sql
-- 游客会话
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id VARCHAR(64),          -- 匿名游客标识
    session_start TIMESTAMPTZ DEFAULT NOW(),
    session_end TIMESTAMPTZ,
    platform VARCHAR(20),            -- web / ios / android
    interests VARCHAR(50)[]          -- 兴趣标签数组
);

-- 交互记录
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    query_text TEXT,                 -- 用户问题文本
    query_mode VARCHAR(10),          -- voice / text
    response_text TEXT,              -- AI 回复文本
    rag_sources JSONB,               -- RAG 检索到的源文档
    emotion_label VARCHAR(10),       -- 情感标签: positive/neutral/negative
    satisfaction INT,                -- 用户满意度评分 1-5 (如有反馈)
    thinking_time_ms INT,            -- 响应延迟(ms)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 知识文档
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255),
    file_type VARCHAR(20),
    file_size BIGINT,
    status VARCHAR(20) DEFAULT 'uploaded', -- uploaded/processing/done/failed
    chunk_count INT DEFAULT 0,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 知识分块 (pgvector)
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,
    embedding VECTOR(1024) NOT NULL   -- bge-large-zh-v1.5 维度
);

-- FAQ 问答对
CREATE TABLE faqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    match_text TEXT,                 -- 用于模糊匹配的关键词
    tags VARCHAR(50)[],
    priority INT DEFAULT 0,          -- 优先级，越高越靠前
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 数字人配置
CREATE TABLE avatar_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100),               -- 配置名称
    appearance VARCHAR(50),          -- 外观类型
    costume VARCHAR(50),             -- 服装
    voice_type VARCHAR(50),          -- 音色
    speech_rate FLOAT DEFAULT 1.0,   -- 语速
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 运营统计（物化视图/定时计算）
CREATE TABLE daily_stats (
    date DATE PRIMARY KEY,
    total_sessions INT DEFAULT 0,
    total_interactions INT DEFAULT 0,
    avg_thinking_time_ms FLOAT DEFAULT 0,
    positive_ratio FLOAT DEFAULT 0,
    top_questions JSONB,             -- Top10 问题
    top_attractions JSONB            -- Top10 景点
);
```

---

## 七、项目目录结构

```
lingguide/
├── docker-compose.yml               # 一键部署
├── .env.example                     # 环境变量模板
├── README.md
├── DESIGN.md                        # 本设计文档
│
├── backend/                         # FastAPI 后端
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                     # 数据库迁移
│   ├── app/
│   │   ├── main.py                  # 应用入口
│   │   ├── config.py                # 配置管理
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py              # 游客问答接口 (WS + REST)
│   │   │   ├── knowledge.py         # 知识库管理 CRUD
│   │   │   ├── avatar.py            # 数字人形象管理
│   │   │   ├── analytics.py         # 数据分析与报告
│   │   │   └── dashboard.py         # 数据大屏接口
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── asr.py               # Whisper 语音识别封装
│   │   │   ├── llm.py               # LLM 调用 (Qwen3/DeepSeek)
│   │   │   ├── tts.py               # TTS 语音合成
│   │   │   ├── rag.py               # RAG 检索逻辑
│   │   │   ├── emotion.py           # 情感分析
│   │   │   └── avatar_driver.py     # 数字人表情/口型驱动
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── session.py
│   │   │   ├── interaction.py
│   │   │   ├── document.py
│   │   │   └── faq.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── chat_service.py      # 对话业务编排
│   │   │   ├── knowledge_service.py # 知识库服务
│   │   │   ├── analytics_service.py # 分析服务
│   │   │   └── dashboard_service.py # 大屏数据服务
│   │   └── utils/
│   │       ├── text_process.py      # 文本处理
│   │       └── embeddings.py        # Embedding 封装
│   └── tests/
│       ├── test_chat.py
│       ├── test_rag.py
│       └── test_knowledge.py
│
├── frontend-visitor/                # Vue3 游客端
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── views/
│   │   │   ├── HomeView.vue         # 首页/兴趣选择
│   │   │   ├── ChatView.vue         # 数字人对话页
│   │   │   └── RouteView.vue        # 路线推荐页
│   │   ├── components/
│   │   │   ├── DigitalHuman.vue     # 数字人渲染组件
│   │   │   ├── VoiceInput.vue       # 语音输入按钮
│   │   │   ├── TextInput.vue        # 文本输入框
│   │   │   ├── ChatBubble.vue       # 对话气泡
│   │   │   ├── InterestPicker.vue   # 兴趣选择器
│   │   │   └── RouteCard.vue        # 路线卡片
│   │   ├── composables/
│   │   │   ├── useWebSocket.ts      # WebSocket 封装
│   │   │   ├── useAudio.ts          # 音频播放控制
│   │   │   └── useDigitalHuman.ts   # 数字人状态管理
│   │   └── assets/
│   │       └── styles/
│   └── public/
│       └── favicon.ico
│
├── frontend-admin/                  # Vue3 管理后台
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── views/
│   │   │   ├── DashboardView.vue    # 数据大屏
│   │   │   ├── KnowledgeView.vue    # 知识库管理
│   │   │   ├── AvatarView.vue       # 形象管理
│   │   │   └── ReportView.vue       # 游客感受度报告
│   │   ├── components/
│   │   │   ├── StatCard.vue         # 统计卡片
│   │   │   ├── TrendChart.vue       # 趋势图表 (ECharts)
│   │   │   ├── HotWordCloud.vue     # 热门词云
│   │   │   ├── DocUploader.vue      # 文档上传组件
│   │   │   ├── FaqEditor.vue        # FAQ 编辑器
│   │   │   └── AvatarPreview.vue    # 形象预览
│   │   └── composables/
│   │       └── useApi.ts            # API 请求封装
│   └── public/
│
├── knowledge-base/                  # 知识库初始化
│   ├── import_docs.py               # 文档导入脚本
│   └── sample_data/                 # 示例景区资料
│       ├── 灵山胜境_历史.docx
│       ├── 灵山胜境_景点.docx
│       └── 灵山胜境_FAQ.json
│
└── scripts/
    ├── setup.sh                     # 环境初始化
    ├── seed_db.py                   # 数据库初始化
    └── eval_accuracy.py             # 问答准确率评测
```

---

## 八、开发步骤规划（6 阶段）

### 阶段一：基础环境搭建（预计 2 天）

| 任务 | 产出 | 关键点 |
|------|------|--------|
| 1.1 初始化前后端项目 | 三个项目骨架可运行 | FastAPI + Vue3 分别启动成功 |
| 1.2 Docker Compose 编排 | 一键启动全部服务 | PostgreSQL + Redis + ChromaDB + 后端 |
| 1.3 数据库建表 | Seeding 脚本就绪 | Alembic 迁移 + 初始数据 |
| 1.4 知识库导入脚本 | 景区资料向量化入库 | 处理 .docx 文档切片 → ChromaDB |

### 阶段二：核心 AI 链路（预计 3 天）

| 任务 | 产出 | 关键点 |
|------|------|--------|
| 2.1 ASR 模块 | Whisper 语音转文本 API | faster-whisper 流式识别 |
| 2.2 RAG 检索 | 知识检索 → Prompt 拼合 | bge-large-zh Embedding + ChromaDB top_k |
| 2.3 LLM 对话 | Qwen3 中文问答 | 可选本地部署或 API，Prompt 模板调优 |
| 2.4 TTS 合成 | 文本 → 自然语音 | Edge-TTS 免费方案 / CosyVoice 情感合成 |
| 2.5 链路串联 | 文本问答端到端跑通 | ASR → RAG → LLM → TTS 全流程 |

### 阶段三：数字人集成（预计 2 天）

| 任务 | 产出 | 关键点 |
|------|------|--------|
| 3.1 MiniMates/DH_live 集成 | 数字人在前端渲染 | WebGL 加载、音频+口型同步 |
| 3.2 表情驱动 | TTS 文本 → 情感标签 → 表情 | 规则映射或模型推理 |
| 3.3 音素同步 | LLM 文本 → 音素序列 → 口型 | 中文音素到 viseme 映射 |

### 阶段四：前后端联调（预计 3 天）

| 任务 | 产出 | 关键点 |
|------|------|--------|
| 4.1 游客端聊天界面 | 数字人对话页完整可用 | WebSocket 流式通信、语音/文本双模式 |
| 4.2 个性化推荐 | 兴趣选择 + 路线推荐 | 偏好存储 + LLM 定制回复 |
| 4.3 管理后台 | 知识库管理 + 形象管理 | 文档 CRUD、配置界面 |
| 4.4 数据大屏 | 运营数据可视化 | ECharts 图表、定时刷新 |

### 阶段五：测试优化（预计 2 天）

| 任务 | 产出 | 关键点 |
|------|------|--------|
| 5.1 问答准确率评测 | 准确率 ≥ 90% 验证 | 构建测试问题集，逐条评测 |
| 5.2 延迟优化 | 端到端响应 < 5s | 流式输出、缓存热点问答、模型量化 |
| 5.3 稳定性测试 | 压力测试报告 | 并发 50+ 用户无崩溃 |

### 阶段六：文档与演示（预计 1 天）

| 任务 | 产出 |
|------|------|
| 6.1 设计文档 | 本文档终版 |
| 6.2 演示视频 | 5-8 分钟功能演示 |
| 6.3 提交打包 | 源码 + Docker 镜像 |

---

## 九、评分对照自查

| 评分项 | 满分 | 对应我们的实现 |
|--------|------|----------------|
| **功能完整度** | 40 | T1-T3 游客端 + M1-M4 管理后台 = 7 个核心功能全覆盖 |
| **数字人表现力** | 15 | MiniMates 口型同步 + 表情驱动 + Edge-TTS 自然语音 |
| **大模型与知识库** | 15 | Qwen3 RAG + ChromaDB + 事实准确率 ≥ 90% |
| **行业实用性** | 20 | 解决导游短缺、个性化讲解、情感互动 3 大痛点 |
| **文档质量** | 10 | 本设计文档 + 演示视频 |

**预期总分：85-92 分**

---

## 十、风险与应对

| 风险 | 概率 | 应对方案 |
|------|------|----------|
| Qwen3-8B 本地部署显存不足 | 中 | 使用 DeepSeek API 降级方案，或 Qwen3-1.8B 轻量版 |
| DH_live 与自定义知识库集成困难 | 中 | 解耦数字人渲染与对话逻辑，通过标准 API 对接 |
| 语音问答延迟 > 5s | 中 | 使用流式 TTS + 缓存热点问题 + 模型量化加速 |
| 知识库检索准确率不达标 | 低 | 调整 chunk 大小、尝试多种 Embedding 模型、加入 FAQ 精确匹配 |
| 时间不足 | 中 | 优先完成核心链路（阶段一~三），管理后台部分功能降低优先级 |

---

*文档版本: v1.0 | 日期: 2026-06-17*
