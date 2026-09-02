# 灵境导游 RAG 技术报告（竞赛演示冻结版）

> **副标题：面向景区智能导览的可解释、可验证、可降级混合检索增强生成系统**  
> **报告版本：V1.0（冻结版）**  
> **验收证据截止：2026-07-19**  
> **服务端口：后端 `8000`；游客端 `3000`；管理端 `3001`**  
> **系统定位：受控内网的软件杯竞赛演示系统，不作为公网生产级 RAG 平台宣传。**

---

## 摘要

景区智能导览面临四类典型知识问题：开放时间、票务和交通等高频确定性事实；景点历史、建筑和文化等长文本知识；景点与路线等结构化实体知识；天气等具有时效性的实时信息。若仅依赖单一大模型或单一路径向量检索，容易出现景区专名、数字和时间信息匹配不稳定，实时信息过期，以及回答无法追溯来源等问题。

灵境导游围绕“**可靠回答、证据可查、异常可控、体验可展示**”构建混合 RAG 导览系统。系统根据问题类型路由至 FAQ、景点/路线结构化数据、SQLite FTS5/BM25、BGE 向量检索或高德天气工具；再通过 RRF 融合、canonical Chunk 回查、Evidence 过滤和 Citation 校验，使大模型只基于可验证证据生成回答。对于无可靠证据、天气工具异常、检索超时或 LLM 生成失败的情况，系统不使用事实型 mock，而是返回保守拒答并清理不匹配引用。

在交付层，系统将同一份检索与回答结果供文本聊天、Citation 展开、语音播报、3D 数字人和路线卡片共同消费；管理端提供知识库管理、索引健康、检索测试、索引任务和匿名运行摘要。该设计将 RAG 从“模型直接作答”提升为“**可路由、可融合、可回查、可引用、可拒答、可降级**”的景区导览闭环。

**关键词：** 景区智能导览；混合 RAG；FTS5/BM25；BGE；Chroma；RRF；Evidence；Citation；索引生命周期；多模态交互

---

## 1. 报告使用说明与证据口径

### 1.1 冻结范围

本报告描述当前冻结的竞赛演示版本。其目的是为项目文档、答辩讲稿和 PPT 提供统一、可核验的技术事实来源，而不是提出后续研发计划。

报告中的内容按以下口径区分：

| 标签 | 含义 | 使用原则 |
|---|---|---|
| **当前实现** | 已存在于当前主链路代码中的能力 | 可作为系统架构和技术亮点描述 |
| **冻结验收记录** | 2026-07-19 保存的测试、评测、构建和浏览器验证产物 | 必须携带样本、时间或场景边界 |
| **历史工程基线** | 已保存的早期离线检索评测结果 | 如实披露，不替代冻结演示门禁 |
| **未纳入阶段** | 规划、兼容配置或后续方向 | 不作为已实现能力展示 |

### 1.2 核心结论

灵境导游 RAG 的竞赛价值不在于堆叠复杂模型，而在于针对景区业务将不同知识类型放入合适的处理路径，并建立从检索候选到可信 Evidence、从回答内容到 Citation、从在线请求到管理诊断的完整证据链。

> **面向景区专名密集、事实类型混杂、部分信息具有实时性的特点，构建可解释、可验证、可降级的混合 RAG 智能导游系统。**

---

## 2. 项目背景与问题定义

### 2.1 景区导览的知识特点

景区咨询并不是单一的开放域问答，至少包含以下四类信息：

| 知识类型 | 典型问题 | 核心要求 | 单一路径的风险 |
|---|---|---|---|
| 高频确定事实 | “灵山大佛多高？”“几点开园？” | 数字、时间、专名必须稳定 | 语义检索可能混淆相近景点或数字 |
| 景区文化知识 | “梵宫有什么建筑特色？” | 长文本语义理解、可给出处 | 关键词不完整时召回不足 |
| 景点与路线实体 | “带老人半天怎么安排？” | 真实景点约束、结构化输出 | 模型可能虚构景点或路线 |
| 实时信息 | “今天灵山天气怎么样？” | 数据时效、来源和失败语义 | 静态资料可能被误当作实时事实 |

因此，本项目将问题处理拆解为“**先判断应检索什么，再决定如何回答**”，而非让所有问题直接进入同一种向量检索或大模型生成流程。

### 2.2 设计目标

系统目标包括：

1. 对 FAQ、景点文化、路线推荐、天气和无证据问题提供稳定处理；
2. 对回答提供可追溯 Citation，而非只返回自然语言文本；
3. 对无证据、工具失败和模型异常进行保守降级；
4. 让文本、语音和数字人围绕同一份回答语义协同展示；
5. 让管理人员能够查看索引健康、检索证据和匿名运行状态；
6. 用冻结数据、索引版本和评测门禁保障竞赛演示可复现。

### 2.3 系统范围与定位

本项目的当前范围是：**面向受控内网和竞赛答辩的单实例演示系统**。系统已实现混合检索、证据治理和多端展示闭环，但不将以下能力作为当前完成项：

- GraphRAG、复杂 Reranker 或 Cross-Encoder 重排；
- PostgreSQL/pgvector、Redis 跨实例限流、HTTP Chroma 集群化；
- Prometheus/Grafana 全链路监控、生产灰度发布与自动回滚；
- 企业级多租户认证、面向公网的安全与合规体系；
- 大规模真实游客数据分析和高并发 SLA 验证。

这种范围收敛的目的，是优先保证竞赛现场“问得准、说得清、出错不乱、证据可看”的核心体验。

---

## 3. 业务闭环与总体架构

### 3.1 从游客问题到多模态交付的闭环

```text
游客文本 / 语音问题
        │
        ▼
QueryCoordinator：FAQ、天气、结构化与文档检索路由
        │
        ├─ FAQ 高置信快路径
        ├─ 高德天气实时工具
        ├─ Spot / Route 结构化检索
        └─ FTS5/BM25 + BGE/Chroma 文档混合检索
                    │
                    ▼
          RRF 融合、去重、canonical Chunk 回查
                    │
                    ▼
       Evidence 身份、状态、时效、置信度过滤
                    │
                    ▼
       Citation + RetrievalTrace + AnswerOrchestrator
                    │
                    ├─ 基于证据生成回答
                    └─ 无证据 / 异常时保守拒答
                    │
                    ▼
 REST / Voice / WebSocket / 文本聊天 / TTS / 3D 数字人 / 路线卡片
                    │
                    ▼
      管理端：知识管理、索引健康、检索诊断、匿名运行摘要
```

该链路的关键原则是：**LLM 位于 Evidence 过滤之后，而不是直接面对原始知识库或任意检索候选。**

### 3.2 五层技术架构

| 层级 | 组成 | 主要职责 |
|---|---|---|
| 交互展示层 | 游客端、管理端、地图、TTS、3D 数字人 | 展示回答、Citation、路线和管理诊断 |
| 协议服务层 | FastAPI、REST、Voice API、WebSocket | 对外提供统一请求和事件协议 |
| 查询编排层 | `QueryCoordinator`、`AnswerOrchestrator` | 选择路径、聚合证据、生成或拒答 |
| 知识检索层 | FAQ、Spot、Route、FTS5/BM25、Chroma/BGE、RRF | 对不同知识类型实施适配检索 |
| 可信运维层 | Evidence、Citation、RetrievalTrace、manifest、readiness、索引任务 | 确保证据可验证、索引可核验、运行可观察 |

### 3.3 核心模块及职责

| 模块 | 当前实现 | 作用 |
|---|---|---|
| Canonical 知识库 | SQLite `Document`、`Chunk`、FAQ、Spot、Route | 作为可追溯的事实源和统一身份源 |
| FAQ 路由 | 高置信匹配、实体/别名/意图约束 | 稳定回答高频确定问题 |
| 结构化检索 | Spot/Route 检索与真实景点白名单 | 支撑景点、路线与兴趣筛选 |
| 关键词检索 | SQLite FTS5/BM25 | 擅长专名、数字、时间和精确短语 |
| 向量检索 | embedded Chroma + BGE | 覆盖同义表达和语义相近问法 |
| 融合层 | RRF、稳定 ID 去重、排序 | 融合关键词与向量等多路候选 |
| 证据层 | canonical 回查、Evidence 过滤、Citation | 防止孤儿向量、过期或低置信信息进入回答 |
| 生成层 | OpenAI-compatible LLM 编排 | 基于 Evidence 生成、清理未知引用、保守拒答 |
| 工具层 | 高德天气工具 | 处理带时效性的天气信息 |
| 管理诊断 | 索引健康、检索测试、运行摘要 | 支撑答辩可解释和运行排障 |

---

## 4. 技术栈

### 4.1 后端与数据层

| 类别 | 技术选型 | 当前作用 |
|---|---|---|
| Web 框架 | FastAPI、Uvicorn | REST、语音接口和 WebSocket 服务 |
| ORM 与异步访问 | SQLAlchemy asyncio、aiosqlite | 访问 SQLite canonical 数据与运行记录 |
| 主数据存储 | SQLite | 保存 Document、Chunk、FAQ、Spot、Route、Interaction、IndexManifest、IndexJob 等 |
| 关键词索引 | SQLite FTS5/BM25 | 文档 Chunk 的精确关键词召回 |
| 向量数据库 | embedded ChromaDB | 本地持久化向量召回，不依赖远程向量服务 |
| Embedding | `BAAI/bge-large-zh-v1.5` | 中文知识文本和查询向量化 |
| 融合算法 | RRF（Reciprocal Rank Fusion） | 通过排名融合多路检索结果 |
| LLM 接口 | `openai==1.57.4` 的 OpenAI-compatible SDK | 对接本地 Qwen/Qwen3-8B 或 DeepSeek API |
| 实时工具 | 高德 Web 服务 REST | 天气地点解析、实况/预报、缓存和降级 |
| 语音识别 | 科大讯飞 IAT WebSocket | 当前语音识别接入链路；需配置相应凭据才可调用 |
| 语音合成 | Edge-TTS 主链路，可选 CosyVoice | 将回答转为可播放语音 |
| 情感表达 | 规则 + SnowNLP | 映射为数字人 happy/neutral/concerned 等表情状态 |
| 测试工具 | pytest、pytest-asyncio | RAG、索引、天气、WebSocket 和失败契约回归 |

### 4.2 前端与展示层

| 端 | 技术栈 | 当前作用 |
|---|---|---|
| 游客端 | Vue 3、TypeScript、Vite、Pinia、Vue Router、Axios | 文本/语音聊天、Citation、路线和地图展示 |
| 管理端 | Vue 3、TypeScript、Vite、Element Plus、ECharts/vue-echarts | 知识库管理、RAG 诊断、运营展示与配置页 |
| 地图 | 高德地图 JavaScript API | 景点标记、步行路线和天气卡片 |
| 数字人 | 魔珐星云 3D SDK | 语音播报、表情与说话状态展示 |

### 4.3 技术选型说明

1. **SQLite 作为 canonical 事实源**：适合冻结知识库和竞赛单实例部署，便于保存稳定 ID、字符偏移、内容哈希和索引元数据。
2. **FTS5/BM25 与 BGE 互补**：前者保障专名、数字、时间和短语，后者补充自然语言改写与语义表达。
3. **embedded Chroma**：降低演示环境部署复杂度，配合 manifest 与 readiness 管理索引一致性。
4. **OpenAI-compatible LLM 接口**：使本地模型和 DeepSeek API 可切换，避免将回答层锁定在单一模型供应商。
5. **工具化天气而非文档化天气**：把时效问题从静态知识库中剥离，防止历史文本伪装为实时事实。

---

## 5. 知识组织与可验证索引

### 5.1 Canonical 数据模型

系统不把 Chroma 或 FTS5 索引视为唯一事实源，而是将 SQLite 中的 `Document` 与 `Chunk` 作为 canonical 数据。

每个知识 Chunk 具备稳定身份和定位信息，包括：

- `chunk_id` 与 `document_id`；
- 正文内容和检索文本；
- Chunk 序号；
- 字符起止偏移 `char_start` / `char_end`；
- 内容哈希；
- 状态与索引版本；
- 来源文件、章节和页码等定位信息。

这种设计使引用不仅能回答“来自哪份文档”，还可定位到 Chunk 与具体文本范围。

### 5.2 分块与多索引投影

当前 canonical 文档采用如下分块配置：

| 配置 | 当前值 | 目的 |
|---|---:|---|
| `chunk_size` | 600 | 在语义完整性与召回粒度之间平衡 |
| `overlap` | 80 | 保留相邻上下文，降低边界截断风险 |
| 内容哈希 | 每 Chunk 保存 | 检测内容变更和索引漂移 |
| 字符偏移 | 每 Chunk 保存 | 支撑 Citation 的精确定位 |

同一个 canonical Chunk 会投影至两类检索索引：

```text
SQLite canonical Chunk
        ├─ FTS5 行：关键词/BM25 召回
        └─ Chroma 向量：BGE 语义召回
```

检索索引是 canonical 的派生视图，不替代 canonical 数据。任何候选最终都需要回查 canonical Chunk。

### 5.3 索引生命周期：shadow build → validate → activate

为了避免现场更新或索引构建失败破坏当前可演示版本，系统实现独立 shadow 索引生命周期：

```text
创建幂等索引任务
        ↓
构建独立 shadow Chroma collection 与 FTS namespace
        ↓
读取 ready canonical Chunk 并写入双索引
        ↓
validate：数量、ID、指纹、配置和物理索引校验
        ↓
通过后 activate；旧 active 索引转为 retired
        ↓
运行时从 SQLite active manifest 读取 collection 与 namespace
```

该流程的关键机制包括：

- **幂等任务**：通过 idempotency key 避免重复创建同一任务；
- **租约领取与重试上限**：避免多个 worker 同时处理同一索引任务；
- **失败保护**：构建或校验失败时不替换 active 索引；
- **active manifest**：记录当前 collection、FTS namespace、Embedding 模型、分块配置、数量与内容指纹；
- **严格 readiness**：检查 manifest、SQLite、FTS、vector、数量、ID 集合、内容指纹和配置是否一致。

### 5.4 冻结演示索引快照

下表描述冻结演示知识库的**规模快照**，不是系统容量上限：

| 冻结项 | 已验证值 |
|---|---:|
| FAQ 条目 | 15 |
| 文档数 | 2 |
| Canonical Chunk | 36 |
| FTS 索引行 | 36 |
| 向量索引条目 | 36 |
| Embedding 模型 | `BAAI/bge-large-zh-v1.5` |
| Readiness | `ready`，数据库、manifest、FTS、vector、数量、ID、指纹、配置对账通过 |

---

## 6. 场景化路由与混合检索

### 6.1 为什么不是“所有问题都做向量检索”

景区问答包含不同信号类型。大佛高度、开园时间、公交线路等信息中，专名、数字和时间具有关键约束；“它有什么特色”“适合带孩子吗”等问题则更依赖语义理解；天气还要求实时工具。因此系统按场景分流：

| 路由 | 适用问题 | 当前处理方式 | 输出特点 |
|---|---|---|---|
| FAQ | 票务、开放时间、交通、大佛高度等 | 高置信精确问题/别名/意图匹配 | 快路径、稳定 FAQ Citation |
| Weather | “今天/明天/现在天气如何” | 高德天气工具 + 地点约束 | 带查询时间、有效期和工具状态 |
| Structured | 景点、路线、兴趣筛选 | Spot/Route 实体检索 | 结构化 `spot:<id>` / `route:<id>` Citation |
| FTS5/BM25 | 专名、数字、时间、表演名称 | SQLite FTS5/BM25 | 强调字面精确匹配 |
| BGE/Chroma | 同义改写、自然语言描述 | BGE 语义向量检索 | 补充语义相近召回 |
| no_match | 无可靠证据或不支持问题 | 统一拒答 | 无事实型 mock、无误导 Citation |

### 6.2 FAQ 高置信快路径

FAQ 路由适用于高频且事实明确的问题。其设计目标是：

- 精确问题或可靠别名命中后快速返回；
- 路线类问题不会被 FAQ 误短路；
- 多意图冲突时不盲目猜测；
- 生成稳定的 FAQ Citation 和 `route=faq`。

对于 FAQ 命中，系统还会结合结构化景点结果判定是否适合短路，以减少包含特定景点实体时的错误覆盖。

> **当前边界：** 聊天运行时 `match_faq()` 读取 `backend/app/faqs.json`，SQLite FAQ 表由显式同步维护。冻结版本已对 JSON 与 SQLite mirror 执行快照一致性校验；后续若修改 FAQ，必须重新同步与校验，不能把两者视为天然实时一致。

### 6.3 结构化 Spot/Route 检索

景点和路线并非纯文本段落，而具有实体、标签、兴趣和顺序等结构。系统使用 Spot/Route 数据支持：

- 景点名称、标签和简介检索；
- 路线候选与兴趣筛选；
- 真实景点白名单约束；
- `spot:<id>`、`route:<id>` 结构化 Citation；
- LLM 失败时的确定性路线补全。

这使路线能力不完全依赖大模型临时生成，能够降低不存在景点、重复景点或不合理站点的风险。

### 6.4 FTS5/BM25 与 BGE 向量召回

文档检索通道同时执行关键词与向量召回：

```text
用户问题
   ├─ SQLite FTS5 / BM25：专名、数字、时间、精确短语
   └─ BGE + embedded Chroma：改写、描述、语义相近表达
                       ↓
         按稳定 chunk_id 合并候选，RRF 排序
                       ↓
         输出文档候选给统一协调器
```

关键词通道和向量通道不是相互替代，而是互补：

| 通道 | 强项 | 景区示例 |
|---|---|---|
| FTS5/BM25 | 景点专名、数字、时间、表演名称、公交线路 | “灵山大佛 88 米”“九龙灌浴时间” |
| BGE 向量 | 同义改写、自然语言描述、语义接近问题 | “这个建筑有什么看点”“适合慢慢逛吗” |

### 6.5 RRF 融合与稳定去重

系统用 RRF 对多路结果进行融合排序。RRF 的作用是综合不同检索器的排名信息，避免直接比较不同通道的原始分数。

核心策略：

1. 用稳定 `chunk_id` 合并重复候选；
2. 累积不同通道的排名贡献；
3. 按融合分数与稳定 ID 排序，保证同一输入的输出更稳定；
4. 文档候选与结构化 Spot/Route 候选再次融合为最终 Top-K。

需要强调的是：**RRF 解决的是候选排序问题，不负责判断事实是否可用。** 事实可用性由后续 canonical 回查和 Evidence 过滤负责。

---

## 7. Evidence、Citation 与可信回答

### 7.1 Canonical 回查：阻止“孤儿向量”进入回答

向量库或关键词索引中可能存在因历史更新、删除或重建造成的孤立记录。为避免旧向量直接进入回答层，系统对候选实施 canonical 回查：

```text
FTS / Chroma 候选
        ↓
按 chunk_id 查询 SQLite canonical Chunk
        ├─ 找到 ready Chunk：补齐正文、定位、状态和身份
        └─ 未找到：丢弃，并记录 canonical_missing
```

因此，向量检索结果不能绕过 canonical 数据库直接成为回答证据。

### 7.2 Evidence 过滤

最终交给回答编排层的 Evidence 必须通过以下检查：

| 检查维度 | 处理目的 |
|---|---|
| 身份 | 必须具备可追溯的 Chunk 与 Document 身份 |
| 正文 | 过滤空正文或无法提供上下文的候选 |
| 状态 | 仅接收 ready 状态的可用知识 |
| 置信度 | 过滤低置信或相关性不足候选 |
| 有效期 | 工具型数据必须未过期 |
| 索引/工具信息 | 保留索引版本或工具查询时间，支撑诊断 |

若过滤后没有可用 Evidence，系统将路由为 `no_match` 并触发保守拒答。

### 7.3 Citation 的服务端治理

Citation 不是由模型任意生成的文本标记，而是服务端围绕 Evidence 建立的受控引用对象。Citation 可包含：

- 引用 ID；
- `chunk_id`、`document_id`；
- 来源文件或结构化来源；
- 证据片段；
- 章节、页码或字符范围；
- 类型、检索方式、置信度；
- 索引版本，或天气工具的 `as_of` / `expires_at` 等时效信息。

回答生成后，服务端会执行以下操作：

1. 校验模型输出的 Citation ID 是否存在；
2. 删除未知 Citation ID；
3. 若模型未给出引用但存在有效 Evidence，则服务端绑定首条有效 Citation；
4. 若回答只包含未知引用或生成过程失败，则清空不匹配 Evidence 并返回拒答。

这保证游客端看到的引用来自实际检索 Evidence，而不是模型虚构的来源。

### 7.4 无证据拒答是一项主动能力

系统将拒答作为可信问答的一部分，而不是简单的异常提示。以下场景会进入保守拒答：

- 没有召回到可靠 Evidence；
- Evidence 因状态、时效或置信度被过滤；
- 天气工具返回 stale/error；
- 检索超时或关键通道失败；
- LLM 生成失败、空回答或输出未知 Citation。

统一拒答语义为“暂未找到足够可靠的景区资料，建议换个问法或以官方信息为准”，并清空与正文不一致的 Citation，避免“正文拒答但页面仍展示候选来源”的误导体验。

---

## 8. 生成编排、实时工具与故障降级

### 8.1 基于 Evidence 的回答生成

`AnswerOrchestrator` 只向 LLM 传递已过滤的 Evidence 上下文，并在上下文中明确标注证据内容是数据而非指令。生成链路遵循：

```text
有效 Evidence
    ↓
构造带 Citation ID 的上下文
    ↓
LLM 基于证据生成
    ↓
清理未知引用 / 服务端补充有效引用
    ↓
返回答案 + Citation + Trace
```

如果 Evidence 为空，系统不调用带事实型 mock 的回答路径，而是直接拒答。

### 8.2 LLM 稳定策略

当前 LLM 层采用 OpenAI-compatible 接口，支持本地 Qwen/Qwen3-8B 与 DeepSeek API 的配置切换。为控制竞赛现场不确定性，系统实现：

- `settings.llm_timeout_seconds` 总 deadline；
- timeout、连接错误、408、429、5xx 等错误分类；
- 最多两次应用层重试，即最多三次尝试；
- 普通 4xx、认证和权限错误不重试；
- 工具调用与回答生成共享总预算；
- trace 只记录 provider、模型标识、耗时、attempt、retry 和错误类别；
- 不记录完整 prompt、用户问题、回答正文或工具参数。

该策略并不承诺模型永不失败，而是保证失败时能够在有限时间内转入明确、可解释的降级结果。

### 8.3 天气工具的时效治理

天气问题不依赖静态文档，而由高德 Web 服务工具获取。其处理流程如下：

```text
天气问题
   ↓
显式城市/区县识别优先
   ↓
景区别名约束至无锡；未指定时使用默认景区地点
   ↓
高德地点解析与天气请求
   ↓
fresh TTL / stale 窗口 / error 状态判断
   ├─ fresh：可形成 ready Evidence 和 Citation
   └─ stale/error：展示降级原因，不进入 LLM 事实上下文
```

工具通道覆盖请求超时、429、4xx、5xx、无数据等失败语义。系统可以展示天气查询状态，但不会把 stale 或 error 数据包装为可靠实时事实。

---

## 9. 多模态交互与路线展示

### 9.1 统一回答语义的多端消费

RAG 输出不是只服务于一个文本框，而是被多种交互形态共享：

| 终端能力 | 对 RAG 结果的消费方式 |
|---|---|
| 文本聊天 | 展示回答正文、路由状态、Citation 与降级提示 |
| Citation 面板 | 展开来源、证据片段、类型、章节/页码/字符范围、数据时间 |
| 语音问答 | 语音输入转文本后进入同一 RAG 链路；答案交给 TTS 播放 |
| 3D 数字人 | 消费同一回答文本，驱动说话、空闲和情绪表情状态 |
| 路线卡片 | 展示结构化路线、景点、来源、Citation 和 trace |
| 地图 | 展示景点标记、路线和天气卡片 |

这避免了文本、语音和数字人使用不同回答逻辑导致语义不一致。

### 9.2 WebSocket 事件协议

WebSocket 主事件链为：

```text
rag_started → rag_done → llm_stream → llm_done → message_done
```

每条消息配套：

- `request_id`：关联一次请求；
- `message_id`：关联一轮问答；
- `trace_id`：关联检索与生成诊断；
- 单调递增 `seq`：支持前端去重与顺序保护。

游客端根据消息 ID 关联回答，根据 `seq` 去重，并对加载、降级、错误和 Citation 状态进行可视化。

> **准确表述：** 当前 `llm_stream` 通常传递整段回答事件以实现前端渐进展示，不应称为 token 级真实流式生成。

### 9.3 个性化路线与地图

游客可以基于佛教文化、自然风光、历史古迹、亲子游乐、建筑艺术、美食素斋等兴趣标签，以及半天/全天时长生成路线。路线能力具有以下约束：

- 结构化路线快照可保存、删除和再次展示；
- 景点来自真实白名单，降低模型虚构景点风险；
- LLM 失败时可采用确定性补全；
- 地图显示景点标记、信息窗和高德步行路径；
- 步行规划失败时前端以降级样式提示，而不伪装为精确导航。

> **准确表述：** 该能力是“带真实景点约束的个性化游览建议与地图展示”，不是全局最优路径求解或导航级精确规划。

---

## 10. 管理端与运行可观测性

### 10.1 知识库管理

管理端支持：

- `.docx`、`.txt`、`.md` 文档上传；
- 文档状态、分块数、错误信息和删除；
- FAQ 的新增、编辑、删除；
- FAQ 实体、意图、关键词、精确问题及冲突提示；
- 当前 Chunk 与 FAQ 数量查看。

该功能服务于竞赛前的知识库冻结和内容维护。当前不应宣传为 PDF 全格式、生产级文档解析平台。

### 10.2 RAG 检索诊断

管理端 `RagDiagnosticsView` 将“系统如何回答”转化为可展示的工程证据，包含：

| 能力 | 可展示内容 |
|---|---|
| 索引健康 | canonical、FTS、vector 数量，active 版本、manifest、collection、namespace、严格 readiness 检查 |
| 测试检索 | 查询路由、候选证据、Citation 和 trace 摘要 |
| 索引任务 | 任务状态、尝试次数和错误信息 |
| 最近运行 | 最近 100 条有效检索轨迹的匿名聚合统计 |

其中 `GET /api/rag-admin/runtime-summary` 聚合的低敏运行指标包括：

- 请求数与统计时间范围；
- 端到端、检索耗时的 P50/P95；
- 降级率与通道异常率；
- Structured、FTS、BGE、Weather、LLM 五类通道的平均耗时和样本数。

该接口不返回用户问题、回答正文、Citation、trace ID 或模型信息，适合竞赛现场展示系统运行状态，同时避免把检索原文直接放入摘要面板。

### 10.3 可观测性的边界

当前能力是基于 RetrievalTrace、Interaction 记录和管理端摘要的**请求级诊断**，不是 Prometheus/Grafana、OpenTelemetry 或完整告警平台。答辩中应表述为“具备轻量级检索诊断与运行摘要能力”。

---

## 11. 工程创新点与项目亮点

本项目的创新重点是面向景区业务的系统与工程创新，不将已有算法名称包装为未经验证的学术原创算法。

### 创新点 1：面向景区知识类型的分层路由混合 RAG

系统不将所有输入统一送入向量库，而是把问题按知识属性分流：高频确定事实进入 FAQ，景点与路线进入结构化检索，专名/数字/时间进入 FTS5/BM25，语义改写进入 BGE 向量，实时天气进入工具调用，无可靠证据进入拒答。

**价值：** 让“检索什么”先于“怎么生成”，降低单一向量检索在景区专名、数字和时效信息上的失配。

### 创新点 2：从检索候选到可信 Evidence 的 canonical 治理链

所有关键词或向量候选都必须回查 SQLite canonical Chunk；孤儿向量被丢弃；只有通过身份、正文、状态、时效和置信度检查的数据才能进入 LLM 上下文。

**价值：** 模型看到的不是未经约束的检索片段，而是经过治理的 Evidence，降低历史索引残留、过期信息和错误候选导致的幻觉风险。

### 创新点 3：可验证的索引发布机制

索引通过 shadow build → validate → activate 发布，manifest 对 collection、FTS namespace、数量、ID、内容指纹、Embedding 模型和分块配置进行统一约束；校验失败不会替换 active 索引。

**价值：** 将“向量库能否查询”提升为“canonical、关键词索引和向量索引是否一致”的可验证状态，提升现场演示可复现性。

### 创新点 4：将实时工具的时效与失败语义纳入证据模型

天气 Evidence 具有来源、查询时间、有效期和失败原因；fresh 数据才作为事实依据，stale/error 不进入 ready Citation 与 LLM 上下文。

**价值：** 既支持实时服务，又避免把过期工具结果或静态文档误称为实时信息。

### 创新点 5：Evidence 随同多模态体验和管理诊断交付

同一份回答结果被文本、Citation、TTS、数字人、路线卡片和 WebSocket 消费；管理端同时提供索引健康、检索测试和匿名运行摘要。

**价值：** 可解释性不只停留在后端日志，而成为游客可理解、管理人员可观察的产品能力。

---

## 12. 测试、评测与验收证据

### 12.1 验收分层原则

不同测试回答的问题不同，不能用单一“准确率”概括系统质量：

| 验证层级 | 验证重点 | 适合说明的结论 |
|---|---|---|
| 单元/集成测试 | 检索、Evidence、索引、天气、协议与失败契约 | 工程逻辑未偏离预期 |
| 冻结演示评测 | 路由、必需术语、拒答、FAQ、重复稳定、Citation 门禁 | 固定竞赛样例闭环可演示 |
| live smoke | 真实服务关键场景 | 主要演示路径可运行 |
| 前端构建与浏览器 | 页面编译、真实 Citation 渲染 | 交付端能够展示结果 |
| 历史离线基线 | 召回排序与拒答代理 | 泛化检索仍有哪些优化空间 |

### 12.2 冻结验收记录（2026-07-19）

| 验证项 | 已保存结果 | 说明 |
|---|---|---|
| 冻结快照校验 | 通过 | `verify_demo_snapshot --json` 返回 `ready`；FAQ、评测集 SHA-256、canonical/FTS/vector、manifest、指纹与配置匹配 |
| 后端重点回归 | `39 passed in 1.54s` | 面向竞赛主链路的重点测试集 |
| 后端全量测试 | `160 passed in 53.25s` | 冻结验收时保存的回归记录 |
| 40 条演示评测 | gate 通过 | route、grounded、refusal、FAQ、repeat、Citation 指标均为 `1.0` |
| 语义 live smoke | 7 场景通过 | FAQ、文档、连续追问、路线、天气、拒答、trace |
| 游客端构建 | 通过 | `npm run build` 完成 |
| 管理端构建 | 通过 | `npm run build` 完成 |
| 真实浏览器 Citation | 通过 | Chrome/CDP `/chat` 回答包含“88米”，展示 1 条 FAQ Citation，无 loading/降级状态 |
| 运行时摘要测试 | `2 passed in 0.33s` | 覆盖正常聚合、异常/降级、跳过通道、空窗口与损坏 JSON |
| 管理端运行时摘要构建 | 通过 | `vue-tsc` 与 Vite 构建完成，耗时 `4.50s` |

### 12.3 40 条冻结演示评测的正确解读

`backend/demo-eval-result.json` 保存的 40 条演示评测结果如下：

| 指标 | 结果 |
|---|---:|
| Query count | 40 |
| Route accuracy | 1.0 |
| Grounded answer accuracy | 1.0 |
| Refusal accuracy | 1.0 |
| FAQ accuracy | 1.0 |
| Repeat stability | 1.0 |
| Citation canonical rate | 1.0 |
| Citation locator rate | 1.0 |
| Canonical missing | 0 |
| 端到端 P50 | 1757.142 ms |
| 端到端 P95 | 2658.207 ms |
| Gate | passed |

这些数据应表述为：

> 在 40 条人工复核的冻结竞赛演示样例中，系统在路由、必需术语/有证据回答、拒答、FAQ、重复稳定性和 Citation 结构/定位门禁上全部通过。

**不应表述为：** “系统在开放场景的事实准确率为 100%”或“已达到生产质量”。该评测器主要检查预期路由、必需关键词、拒答语义与 Citation 字段，并不等同于面向开放真实游客问题的大规模专家事实评估。

### 12.4 历史离线召回基线：如实披露优化空间

`backend/rag-baseline-result-after-unified.json` 保存了 12 条历史工程基线，其中 10 条带相关片段标注，2 条为无证据拒答代理样例：

| 指标 | 历史保存值 |
|---|---:|
| Query count | 12 |
| Scored query count | 10 |
| Recall@5 | 0.500000 |
| Recall@10 | 0.700000 |
| MRR | 0.404167 |
| nDCG@5 | 0.406161 |
| Citation canonical rate | 1.000000 |
| Citation locator rate | 1.000000 |
| Canonical missing total | 0 |
| Degraded rate | 0.000000 |
| latency P50 / P95 | 64.868 / 526.753 ms |
| no-evidence proxy accuracy | 0.833333 |

该基线样本量较小，且部分相关性标注仍处于待人工复核状态。它的价值是揭示：**当前召回泛化能力仍有优化空间。** 因此，本项目保留该指标，不以 40 条冻结演示集的门禁结果掩盖历史召回基线的不足。

### 12.5 自动化测试覆盖范围

| 测试类别 | 覆盖示例 |
|---|---|
| 混合检索 | RRF 去重与稳定排序、`final_k`、单路检索类型 |
| Evidence/Citation | canonical 身份、置信度、未知 Citation、无证据拒答、天气 Evidence |
| 检索集成 | 关键词/向量 canonical 回查、字符偏移、同名文档删除、孤儿向量丢弃 |
| 索引生命周期 | shadow/validate/activate、幂等、租约、canonical 变更阻止激活、失败不替换 active |
| Readiness | manifest、FTS、vector、数量、ID、指纹和配置不一致检测 |
| WebSocket | 事件顺序、ID、seq、超时清证据、Origin、token、断线取消 |
| 天气降级 | 无锡地点约束、缓存、timeout、provider error、stale 不进入 Evidence |
| 失败契约 | 文本、语音、WebSocket 的 LLM 失败统一拒答并清理 Citation |
| 运行时摘要 | 最近 100 条匿名聚合、空窗口、损坏历史与敏感字段不返回 |

---

## 13. 关键能力边界与风险披露

透明披露边界，是可信答辩材料的一部分。

| 项目 | 当前事实 | 正确答辩表述 |
|---|---|---|
| 系统定位 | 受控内网/竞赛演示 | 不称为公网生产系统 |
| FAQ 数据 | 运行时 JSON + SQLite mirror 显式同步 | 冻结期已校验一致；变更后需重新同步和校验 |
| 存储一致性 | SQLite、FTS5、Chroma 无跨存储事务 | 通过冻结知识库、shadow 发布和 readiness 降低演示风险 |
| 在线观测 | Trace 与匿名运行摘要 | 不等价于完整监控、告警和链路追踪平台 |
| LLM 流式 | 主要为整段回答事件的渐进展示 | 不称 token 级真实流式 |
| 天气 | 高德工具 + 缓存/TTL/降级 | 不承诺每次实时请求必然成功 |
| 路线 | 真实景点约束的建议与地图展示 | 不称全局最优或导航级规划 |
| ASR/TTS/数字人 | 组件与主要链路可用 | 完整端到端验收、断线重连和 30 分钟长稳未纳入 P0 门禁 |
| 运营分析 | 部分为演示数据、派生数据或轻量实现 | 不称全部来自生产实时用户数据 |
| 安全 | 存在认证、debug、Interaction 原文保存等边界 | 不宣称企业级安全或完整隐私合规 |

以下内容不应写入“当前已实现”章节：PostgreSQL/pgvector、Redis、HTTP Chroma、Prometheus/Grafana、GraphRAG、复杂 Reranker、跨实例限流、生产灰度/自动回滚、多租户认证。

---

## 14. 答辩演示建议

### 14.1 推荐现场演示顺序

```text
景点事实问答
→ Citation 展开
→ 连续追问
→ 个性化路线
→ 实时天气
→ TTS / 3D 数字人播报
→ 管理端查看索引与 trace 摘要
→ 知识库外问题拒答
→ 展示 LLM / 天气异常的降级设计
```

建议准备 5～8 个固定高质量问题，至少覆盖：

1. FAQ：灵山大佛高度、开放时间、票务或交通；
2. 景点文化：梵宫、九龙灌浴等；
3. 连续追问：“它有什么特色”“那怎么安排路线”；
4. 个性化路线：半天/全天 + 兴趣标签；
5. 天气：无锡灵山天气；
6. 无证据：与景区知识库无关的问题；
7. 管理诊断：索引健康、引用和通道耗时。

### 14.2 面向答辩 PPT 的 12 页结构

| 页码 | 标题 | 核心内容 | 推荐素材 |
|---:|---|---|---|
| 1 | 项目封面 | 灵境导游与可信 AI 景区讲解主题 | 项目名、场景图、团队信息 |
| 2 | 背景与挑战 | 知识异构、专名/数字、实时性、幻觉与多模态割裂 | 四类痛点图标 |
| 3 | 解决方案总览 | 路由—召回—Evidence—生成—多端交付 | 五段流程图 |
| 4 | 系统总体架构 | 前端、FastAPI、RAG、工具、数据层 | 五层架构图 |
| 5 | 场景化混合检索 | FAQ、结构化、FTS/BM25、BGE、天气的职责 | 路由决策图 |
| 6 | 可信证据链 | RRF、canonical 回查、Evidence、Citation、拒答 | “候选→证据→回答”图 |
| 7 | 可验证索引发布 | shadow build→validate→activate、manifest/readiness | 状态机图 + 36/36/36 数据卡 |
| 8 | 实时与降级 | 天气 TTL/stale/error、LLM deadline/重试、拒答 | 异常分支时序图 |
| 9 | 多模态导览体验 | 文本、语音、Citation、数字人、路线地图 | 游客端截图 |
| 10 | 管理与诊断 | 知识库、索引健康、检索测试、匿名摘要 | 管理端诊断截图 |
| 11 | 验收成果 | 160 测试、40 条门禁、7 场 smoke、构建和浏览器验证 | 分层验收闸门图 |
| 12 | 创新、边界与结论 | 5 项工程创新、冻结边界、项目价值 | 创新卡片 + 已完成/待验证表 |

### 14.3 答辩图表使用原则

1. 架构图只画当前实际使用的 SQLite、FTS5、embedded Chroma、BGE、OpenAI-compatible LLM 和高德天气工具；
2. 不把 PostgreSQL、Redis、GraphRAG、Prometheus 等规划项画入当前架构；
3. 评测页使用“分层验收闸门图”，不要把不同性质的数据压缩为单一综合分；
4. 性能页明确标注“40 条冻结演示评测运行结果”，不将 P95 写成高并发 SLA；
5. Citation 截图优先使用已验证的“灵山大佛 88 米”案例；
6. 管理端截图只展示匿名摘要、索引健康和证据表，避免暴露运行原文、凭据或敏感交互内容；
7. 对历史 Recall@5=0.50、MRR=0.404167 预备说明页，主动说明其样本小、标注有限且代表后续优化方向。

---

## 15. 结论

灵境导游当前 RAG 的核心价值，是将景区导览中不同类型的信息纳入一套可控流程：

- 高频确定事实走 FAQ 高置信路径；
- 景点和路线走真实实体约束的结构化路径；
- 长文档知识通过 FTS5/BM25 与 BGE/Chroma 互补召回并用 RRF 融合；
- 检索候选必须回查 canonical Chunk，并经 Evidence 过滤后才进入回答层；
- 回答绑定服务端校验的 Citation；
- 天气等实时信息具备来源、时效与失败语义；
- 无证据、工具异常或模型失败时统一保守拒答；
- 文本、语音、数字人、路线和管理诊断共同消费同一条可信结果链。

因此，本项目不是简单“接入大模型的景区问答页面”，而是一个以证据治理、索引可验证发布和多模态交付为核心的混合 RAG 竞赛演示系统。

> **当前版本已满足 P0 竞赛演示闭环。后续若进入更广泛应用，应在扩大评测集、提升召回泛化、补齐长稳与断线验收、强化安全和观测后，再讨论生产化能力。**

---

## 附录 A：关键实现与证据索引

| 主题 | 关键文件 |
|---|---|
| 总体验收与冻结口径 | `RAG最新报告汇总.md` |
| 混合检索、FTS/BGE/RRF、canonical 回查 | `backend/app/core/rag.py` |
| FAQ/天气/结构化/文档路由与 Evidence 聚合 | `backend/app/services/query_coordinator.py` |
| 基于 Evidence 的回答、Citation 校验与拒答 | `backend/app/services/answer_orchestrator.py` |
| LLM deadline、重试和工具调用 | `backend/app/core/llm.py` |
| 索引构建、校验和激活 | `backend/app/services/index_lifecycle.py` |
| active 索引严格 readiness | `backend/app/core/index_readiness.py` |
| 高德天气工具 | `backend/app/core/tools/amap_tools.py` |
| RAG 管理端 API 与匿名运行摘要 | `backend/app/api/rag_admin.py` |
| 游客端 Citation/聊天/语音交互 | `frontend-visitor/src/views/ChatView.vue` |
| WebSocket 状态与消息去重 | `frontend-visitor/src/composables/useWebSocket.ts` |
| 3D 数字人 | `frontend-visitor/src/components/XingyunStage.vue` |
| 路线卡片与地图 | `frontend-visitor/src/views/RouteView.vue`、`frontend-visitor/src/components/RoutePlanCard.vue`、`frontend-visitor/src/components/ScenicMap.vue` |
| 管理端 RAG 诊断页 | `frontend-admin/src/views/RagDiagnosticsView.vue` |
| 冻结演示评测 | `backend/demo-eval-result.json`、`backend/evals/demo_eval_v1.jsonl`、`backend/evals/demo_thresholds.json` |
| 历史离线召回基线 | `backend/rag-baseline-result-after-unified.json`、`backend/evals/rag_baseline.jsonl` |
| 冻结快照与清单 | `backend/evals/demo_manifest.json`、`backend/tools/verify_demo_snapshot.py` |

## 附录 B：可复现验证命令

> 以下命令应在竞赛演示前的备份或隔离环境执行；不要在未备份的正式演示数据上执行可能写入索引或数据库的初始化命令。

```bash
# 后端：冻结快照只读校验
cd backend && python -B -m tools.verify_demo_snapshot --json

# 后端：40 条冻结演示评测门禁
cd backend && python -B -m tools.evaluate_demo --gate

# 后端：运行时摘要专项测试
cd backend && python -m pytest tests/test_rag_admin_runtime_summary.py

# 游客端构建
cd frontend-visitor && npm run build

# 管理端构建
cd frontend-admin && npm run build
```
