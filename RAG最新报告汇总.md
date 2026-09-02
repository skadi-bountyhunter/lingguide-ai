# 灵境导游 RAG 软件杯竞赛版目标与验收报告

> **报告日期：2026-07-19**  
> **报告定位：软件杯竞赛项目 P0 验收结果与 P1 交付目标**  
> 后端：`8000`；游客端：`3000`；管理端：`3001`  
> 当前实现：SQLite + FTS5/BM25 + embedded Chroma/BGE + OpenAI-compatible LLM（本地 Qwen/DeepSeek 可切换）  
> 项目状态：**受控内网/竞赛演示环境，不对外开放**

---

## 1. 报告结论

本项目的 RAG 模块以“**功能完整、证据可解释、演示稳定、效果可验证**”为竞赛目标，不以企业级互联网生产系统为目标。

竞赛版不再继续追求 PostgreSQL、Redis、GraphRAG、复杂分布式部署等超出软件杯展示需要的内容，而是集中完成以下闭环：

```text
游客问题
→ 意图识别与场景路由
→ FAQ / 景点 / 路线 / 文档 / 天气
→ 关键词 + 向量混合召回
→ 证据过滤与 Citation
→ 基于证据回答或明确拒答
→ 游客端展示 / 语音播报 / 数字人表达
→ 管理端查看检索结果和轨迹
```

当前代码已经具备较完整的技术底座：

- FAQ 高置信路由；
- Spot/Route 结构化检索；
- SQLite FTS5/BM25 关键词召回；
- BGE + embedded Chroma 向量召回；
- RRF 融合、canonical Chunk 回查和 Evidence 过滤；
- Citation 与 RetrievalTrace；
- 天气实时工具和失效降级；
- WebSocket 基础事件链；
- LLM 总 deadline、错误分类和最多两次有限重试；
- 无证据拒答和禁止事实型 mock；
- 管理端检索诊断接口。

**竞赛版最终目标：稳定完成 P1 验收，而不是宣称达到最终生产上线标准。**

---

## 2. 软件杯 P1 目标

### 2.1 功能目标

竞赛现场必须稳定演示以下场景：

1. 景点介绍：灵山大佛、梵宫、九龙灌浴等；
2. 历史文化问答；
3. 开放时间、门票、交通等 FAQ；
4. 景区路线规划；
5. 根据游客兴趣推荐个性化路线；
6. 实时天气查询；
7. 连续追问，例如“它有什么特色”“那怎么安排路线”；
8. 知识库外问题明确拒答；
9. 文本、语音和数字人播报保持回答语义一致；
10. 游客端展示来源和引用，管理端查看检索诊断。

### 2.2 技术目标

| 目标 | P1 要求 |
|---|---|
| 多路召回 | FAQ、结构化 Spot/Route、FTS5/BM25、BGE 向量均可用 |
| 混合融合 | 通过 RRF 合并候选，按稳定 ID 去重 |
| 证据安全 | 最终回答只使用 canonical 证据；无法核验时不引用 |
| Citation | 展示来源、证据片段、类型和基本定位 |
| 无证据处理 | 没有可靠证据时明确拒答，不输出事实型 mock |
| 天气工具 | 有地点、状态、查询时间/有效期和失败降级 |
| LLM 稳定性 | 总 deadline、错误分类、最多两次有限重试 |
| 会话协议 | WebSocket 事件顺序、消息 ID、trace ID 和 seq 稳定 |
| 索引准备 | 演示环境完成初始化、索引构建和 readiness 检查 |
| 可复现性 | 一键启动、一键初始化、一键运行演示问题 |

### 2.3 展示目标

答辩中重点展示：

- 同一个问题如何根据类型选择 FAQ、结构化、关键词、向量或天气工具；
- RRF 如何融合多路结果；
- 回答如何绑定到 Chunk 级 Citation；
- 无证据问题如何拒答；
- 天气如何显示实时来源和时效；
- 语音和数字人如何消费同一份回答；
- 管理端如何查看路由、证据和失败原因。

项目卖点应表述为：

> **针对景区专名密集、事实类型混杂、部分信息具有实时性的特点，构建可解释、可验证、可降级的混合 RAG 智能导游系统。**

---

## 3. 当前实际架构

```text
游客问题
  → QueryCoordinator
  → FAQ 高置信快路径
  → 天气实时工具路由
  → Structured Spot/Route 检索
  → SQLite FTS5/BM25
  → embedded Chroma + BGE 向量召回
  → RRF 融合、去重、排序
  → canonical Chunk 回查
  → Evidence confidence/status/expiry 过滤
  → Citation / RetrievalTrace
  → AnswerOrchestrator
  → LLM 生成或 no-evidence 拒答
  → REST / Voice / WebSocket / 游客端
```

| 模块 | 当前实现 |
|---|---|
| Canonical 数据 | SQLite `Document`、`Chunk`、FAQ、Spot、Route 和交互记录 |
| 关键词检索 | SQLite FTS5/BM25 |
| 向量检索 | embedded Chroma |
| Embedding | `BAAI/bge-large-zh-v1.5` |
| 统一编排 | `backend/app/services/query_coordinator.py` |
| 回答编排 | `backend/app/services/answer_orchestrator.py` |
| LLM | OpenAI-compatible `openai==1.57.4`；默认本地 `Qwen/Qwen3-8B`，可切换 DeepSeek API |
| 天气 | 高德 Web 服务工具，支持地点解析、缓存、有效期与失败降级 |
| 会话 | FastAPI REST + WebSocket |
| 前端 | 游客端 `3000`，管理端 `3001` |
| 索引运行时 | 从 SQLite active manifest 读取当前 Chroma collection 与 FTS namespace |
| 索引生命周期 | shadow build → validate → activate；支持幂等任务、租约回收与失败保护 |
| 文档分块 | canonical 文档按 `chunk_size=600`、`overlap=80` 构建，带字符偏移和内容哈希 |

PostgreSQL、Redis、HTTP Chroma 虽然出现在部分部署配置中，但没有接入当前 RAG 主链路，竞赛报告不将其作为已实现能力。旧版 `hybrid-v1`/legacy 索引仅作为兼容回退，正式演示必须使用 active manifest 对应的三路索引。

---

## 4. P1 功能闭环

### 4.1 FAQ 路由

适合开放时间、门票、交通、表演时间、大佛高度等高频确定性问题。

规则：

- 精确问题或别名高置信命中时走 FAQ 快路径；
- 路线问题避免误命中 FAQ；
- 多个意图冲突时不直接猜测；
- 返回稳定 FAQ Citation 和 `route=faq`。

当前限制：聊天运行时的 `match_faq()` 仍直接读取 `backend/app/faqs.json`，SQLite FAQ 表由 `tools.init_demo --sync-faqs` 显式同步，并非运行时唯一数据源。竞赛版不把该问题作为 P1 阻塞项，但演示前必须冻结 JSON，并按需执行 FAQ 同步，避免 JSON 与数据库内容不一致。

### 4.2 景点和路线结构化检索

Spot/Route 数据用于：

- 景点名称、标签和简介；
- 路线候选；
- 个性化兴趣筛选；
- 防止 LLM 生成不存在的景点；
- 生成 `spot:<id>` 结构化 Citation。

路线生成即使 LLM 失败，也会使用真实景点白名单和确定性补全，保证竞赛演示不会出现虚构景点。

### 4.3 FTS5/BM25 + BGE 混合召回

关键词召回擅长：

- 景点专名；
- 时间和数字；
- 门票、公交线路；
- 表演名称和精确短语。

向量召回擅长：

- 同义改写；
- 自然语言描述；
- 语义相近但字面不同的问题。

两路结果通过稳定 `chunk_id` 合并，再使用 RRF 排序；文档通道默认并行召回最多 30 个候选，协调器与结构化 Spot/Route 通道再融合为最终 Top-K。向量候选会回查 SQLite canonical Chunk，孤儿向量直接丢弃并记录 `canonical_missing`。最终只把通过状态、身份、有效期和置信度过滤的 canonical Evidence 交给回答编排层。

### 4.4 天气工具

天气问题走白名单工具，不使用静态文档冒充实时天气。

当前具备：

- 显式城市/区县优先；
- 景区别名约束到无锡；
- 默认景区地点；
- 请求 timeout 和总 deadline；
- fresh TTL 和 stale 窗口；
- 429、4xx、5xx、timeout、无数据等降级原因；
- stale/error 不进入 ready Citation 和 LLM 上下文。

### 4.5 Evidence、Citation 和拒答

最终证据必须具备：

- `chunk_id`；
- `document_id`；
- 来源；
- 正文；
- 状态；
- 置信度；
- 索引版本或工具时间信息。

服务端负责：

- 生成 Citation ID；
- 校验引用 ID；
- 删除未知引用；
- 过滤空正文、过期和低置信度证据；
- 在无证据时返回明确拒答。

### 4.6 LLM 稳定性

本轮已实现：

- `settings.llm_timeout_seconds` 总 deadline；
- timeout、连接错误、408、429、5xx 分类；
- 最多两次应用层重试；
- 普通 4xx、认证和权限错误不重试；
- 工具调用共享总预算；
- 失败 trace 记录 provider、model、耗时、attempt、retry 和错误类别；
- 不记录完整 prompt、用户问题、回答或工具参数；
- 生产回答路径禁用事实型 mock。

### 4.7 RAG 运行时聚合诊断

管理端通过 `GET /api/rag-admin/runtime-summary` 查看最近 100 条有效检索轨迹的匿名聚合结果，用于竞赛现场快速判断运行状态。

诊断数据包括：

- 请求数；
- 端到端和检索耗时的 P50/P95；
- 降级率和通道异常率；
- Structured、FTS、BGE、Weather、LLM 五个通道的平均耗时和样本数；
- 当前统计窗口的时间范围，以及无有效轨迹时的空状态。

接口不返回用户问题、回答正文、Citation、trace ID、模型信息等内容。管理端在“索引健康”和“测试检索”之间展示“最近运行”诊断卡片。

### 4.8 WebSocket 和多模态展示

保持事件链：

```text
rag_started → rag_done → llm_stream → llm_done → message_done
```

每条消息使用：

- `request_id`；
- `message_id`；
- `trace_id`；
- 单调递增 `seq`。

游客端负责：

- 按消息 ID 关联回答；
- 按 seq 去重；
- 展示 Citation；
- 正文与 TTS/数字人播报分离。

---

## 5. 当前完成度

| 能力 | P1 状态 | 竞赛说明 |
|---|---|---|
| FAQ 路由 | 已完成基础闭环 | 需冻结演示 FAQ 数据 |
| Spot/Route 结构化数据 | 已完成 | 路线白名单和结构化证据可展示 |
| FTS5/BM25 | 已完成 | 专名、数字和时间问题重点展示 |
| BGE 向量检索 | 已完成 | `BAAI/bge-large-zh-v1.5`，本地模型优先加载 |
| RRF 混合召回 | 已完成 | 向量 + FTS5/BM25，并行候选融合；有自动化测试 |
| canonical 回查 | 已完成 | 向量与关键词结果均回查 ready Chunk；孤儿向量丢弃 |
| Evidence/Citation | 已完成 | 证据身份、来源、定位、版本、置信度可追踪 |
| no-evidence 拒答 | 已完成 | 无证据或 LLM 失败时不走事实型 mock |
| 天气实时工具 | 已完成基础闭环 | ready/stale/error 状态和 TTL/降级原因已接入 |
| LLM deadline/重试 | 已完成 | 总 deadline、最多 2 次重试、低基数错误 trace |
| WebSocket 基础协议 | 已完成 | 事件顺序、消息 ID、trace ID、seq 和并发保护 |
| 游客端引用展示 | 已验收 | 真实 Chrome/CDP 问答已验证 88 米回答和 1 条 FAQ Citation |
| 管理端检索诊断 | 已完成 | 可查看 active 索引、通道、证据和 trace；最近 100 条有效轨迹的匿名运行聚合已接入 |
| 索引生命周期 | 已验收 | shadow build → validate → activate；冻结快照与 active 索引一致 |
| strict readiness | 已验收 | manifest、FTS、向量、数量、ID、指纹和配置全部通过 |
| 当前 active 索引 | 已确认 | `/api/readiness=ready`；canonical/FTS/vector 均为 36 |
| 12 条离线召回基线 | 已存在 | 历史参考，不作为 P0 最终质量结论 |
| 40 条人工复核评测 | 已验收 | 40/40 通过，路由/有证据/拒答/FAQ/稳定性/Citation 指标均为 1.0 |
| Prometheus/Redis/多实例 | 不纳入 P1 | 仅作为后续扩展 |
| Reranker/GraphRAG | 暂缓 | 无评测证据不引入 |

---

## 6. P1 竞赛验收指标

以下是项目内部竞赛目标，不代表软件杯官方统一评分标准，最终应结合赛题评分细则调整。

### 6.1 功能验收

- FAQ、景点、路线、天气四类路由成功率：≥ 90%；
- 文本问答、语音问答、WebSocket 问答主流程均可演示；
- Citation 展示不为空且来源与回答证据一致；
- 无证据问题能够明确拒答；
- 路线不出现白名单之外的景点名称；
- 天气失败时不输出未经验证的实时事实。

### 6.2 质量验收

建议准备 30～50 条人工复核样例，至少覆盖：

- FAQ 和同义改写；
- 景点事实；
- 历史文化；
- 路线和多景点问题；
- 天气；
- 连续追问；
- 多意图；
- 无证据拒答。

建议目标：

| 指标 | P1 目标 |
|---|---:|
| 路由正确率 | ≥ 90% |
| 有证据回答正确率 | ≥ 85% |
| Citation canonical rate | 100% |
| Citation locator rate | ≥ 95% |
| 无证据拒答准确率 | ≥ 90% |
| FAQ 精确命中率 | ≥ 95% |
| 重复问题结果稳定率 | ≥ 90% |

当前保存的 12 条工程基线仅作为起始参考：

| 指标 | 当前值 |
|---|---:|
| Recall@5 | 0.500000 |
| Recall@10 | 0.700000 |
| MRR | 0.404167 |
| nDCG@5 | 0.406161 |
| Citation canonical rate | 1.000000 |
| Citation locator rate | 1.000000 |
| latency P95 | 526.753 ms |
| no-evidence proxy accuracy | 0.833333 |

该基线样本过小，不能直接作为竞赛最终成绩，也不能宣称达到生产质量。

### 6.3 稳定性验收

- 普通问答 P95 目标：≤ 3 秒；
- 天气请求失败能够在总 deadline 内返回；
- LLM 失败能够在有限重试后返回；
- 演示环境连续运行 30 分钟无崩溃；
- 两条并发 WebSocket 消息不串内容；
- 服务重启后知识库和索引仍可用；
- `/api/readiness` 在演示环境返回 `ready`。

### 6.4 演示验收

竞赛演示必须准备：

1. 一键启动命令；
2. 一键初始化数据库和知识索引；
3. 5～8 个固定高质量问题；
4. 一个连续追问案例；
5. 一个路线规划案例；
6. 一个天气工具案例；
7. 一个无证据拒答案例；
8. 一个 Citation 和 trace 展示案例；
9. LLM 或天气不可用时的降级案例；
10. 离线知识库和预构建索引备份。

推荐答辩流程：

```text
景点问答
→ 连续追问
→ Citation 展示
→ 个性化路线
→ 实时天气
→ 语音/数字人播报
→ 管理端查看 trace
→ 提问知识库外问题并展示拒答
```

---

## 7. P1 必须完成的工作清单

### P0：竞赛前必须完成

- [x] 固化演示知识库；
- [x] 完成演示环境 shadow build → validate → activate；
- [x] `/api/readiness` 在演示环境返回 `ready`；
- [x] FAQ、景点、路线、天气四类场景各准备固定样例；
- [x] 游客端 Citation 真实浏览器验收：FAQ 回答包含“88米”，展示 1 条 FAQ Citation；
- [x] 文本、语音、WebSocket 的 LLM 超时拒答字段一致性：拒答时清空 Citation/source，并有自动化回归；
- [x] 无证据拒答演示：`route=no_match`、无 Citation、`citation_validation=no_evidence`；
- [x] LLM/天气失败降级：LLM 失败由失败契约测试覆盖；天气 live smoke 覆盖 fresh/degraded 语义；
- [x] 已提供演示索引初始化 CLI：`python -m tools.init_demo --json`（执行前需备份并确认演示环境）；
- [x] 完成 40 条人工复核评测集；
- [x] 固定测试结果、评测集 SHA-256 和演示数据版本。

### P1：建议完成

- [x] 为 Structured、FTS、BGE、Weather、LLM 记录独立耗时，并聚合最近 100 条有效检索轨迹；
- [x] 管理端增加“最近运行”聚合诊断卡片：请求数、时间范围、P50/P95、降级/异常率及五通道耗时；
- [ ] 补充真实浏览器断线重连；
- [ ] 增加 FAQ JSON 与 SQLite 数据一致性检查；
- [ ] 优化当前 Recall 失败样例；
- [ ] 补充评测集路由和拒答标签；
- [ ] 准备答辩架构图、时序图和异常流程图；
- [ ] 准备 3～5 分钟演示录屏。

### 不纳入本阶段

- [ ] GraphRAG；
- [ ] 复杂 Reranker；
- [ ] Redis 跨实例限流；
- [ ] PostgreSQL/pgvector 迁移；
- [ ] HTTP Chroma 集群化；
- [ ] Prometheus/Grafana 全套监控；
- [ ] 企业级多租户认证；
- [ ] 生产灰度和自动回滚。

---

## 8. 测试与验证记录

### 当前代码核对（2026-07-19）

已核对报告、运行时代码、索引生命周期、离线评测集和 RAG 测试文件，确认以下实现仍在当前代码中：

- `HybridRAGService`：Chroma/BGE + SQLite FTS5/BM25 + RRF；
- `QueryCoordinator`：FAQ、天气、结构化 Spot/Route、文档混合路由；
- `answer_orchestrator`：证据上下文、Citation 校验、未知引用清理和无证据拒答；
- active manifest：同时约束向量 collection、FTS namespace、canonical 数量、ID、内容指纹、embedding 模型和分块配置；
- `tools.init_demo`：只读 dry-run、幂等 job、shadow build、validate、activate 和 readiness 检查；
- `GET /api/rag-admin/runtime-summary`：基于最近 100 条有效检索轨迹输出匿名运行聚合，不暴露问题、回答、Citation、trace ID 或模型信息；
- 管理端 `RagDiagnosticsView`：在索引健康与测试检索之间展示“最近运行”诊断卡，兼容空窗口和损坏历史轨迹 JSON；
- 离线评测集：`backend/evals/rag_baseline.jsonl` 共 12 条，其中 10 条有相关片段标注，2 条为无证据拒答代理样例。

### 已保存的可复现基线

`backend/rag-baseline-result-after-unified.json` 保存的结果为：

| 指标 | 当前保存值 |
|---|---:|
| Query count | 12 |
| Scored query count | 10 |
| Recall@5 | 0.500000 |
| Recall@10 | 0.700000 |
| MRR | 0.404167 |
| nDCG@5 | 0.406161 |
| Citation canonical rate | 1.000000 |
| Citation locator rate | 1.000000 |
| canonical missing total | 0 |
| degraded rate | 0.000000 |
| latency P50 / P95 | 64.868 / 526.753 ms |
| no-evidence proxy accuracy | 0.833333 |

该结果是历史保存基线，不代表本次重新运行；数据集只有 12 条，必须继续扩充和人工复核。

### 本次 P0 验收记录（2026-07-19）

本轮在当前演示运行时完成了实际测试、真实服务 smoke 和 Chrome/CDP 浏览器验证。冻结快照、SQLite、FTS5、embedded Chroma 与 active manifest 均通过一致性检查。

| 验证项 | 结果 | 证据 |
|---|---|---|
| 冻结快照校验 | 通过 | `python -B -m tools.verify_demo_snapshot --json` 返回 `ready`；FAQ、评测集 SHA-256、36 个 canonical/FTS/vector、manifest、指纹和配置全部匹配 |
| 后端重点回归 | 通过 | `39 passed in 1.54s` |
| 后端全量测试 | 通过 | `160 passed in 53.25s` |
| 40 条演示评测 | 通过 | `python -B -m tools.evaluate_demo --gate`：route/grounded/refusal/FAQ/repeat/Citation 指标均为 `1.0`，`gate.passed=true` |
| 语义 live smoke | 通过 | FAQ、文档、连续追问、路线、天气、拒答、trace 共 7 场景通过；LLM 失败由失败契约测试覆盖 |
| 游客端构建 | 通过 | `npm run build` 完成 |
| 管理端构建 | 通过 | `npm run build` 完成 |
| 真实浏览器 Citation | 通过 | Chrome/CDP `:9222` 实测 `/chat`：回答包含“88米”，`citations=1`，无 loading/降级状态 |

本轮持久化产物已更新：

- `backend/demo-eval-result.json`：40 条评测最终通过，P50/P95 为 `1757.142 / 2658.207 ms`；
- `backend/demo-smoke-result.json`：7 个 live 场景全部通过，`passed=true`；
- `backend/evals/demo_manifest.json`：已记录 `demo_eval_v1.jsonl` 的 SHA-256；
- `backend/tools/verify_demo_snapshot.py`：已校验评测集文件、哈希、数量和人工复核状态。

### 本次运行时诊断补充（2026-07-19）

本次新增最近运行聚合诊断能力，覆盖后端接口、后端单元测试和管理端展示：

| 验证项 | 当前结果 | 说明 |
|---|---|---|
| 运行时聚合接口 | 已实现 | `GET /api/rag-admin/runtime-summary` 聚合最近 100 条有效检索轨迹，返回请求数、时间范围、P50/P95、降级/异常率及五通道耗时样本 |
| 隐私边界 | 已实现 | 响应不包含问题、回答、Citation、trace ID、模型信息等内容 |
| 后端自动化测试 | 通过 | `backend/tests/test_rag_admin_runtime_summary.py`：`2 passed in 0.33s`；覆盖正常聚合、降级/异常、跳过通道、空窗口和损坏历史 JSON |
| 管理端运行时卡片 | 已实现 | `RagDiagnosticsView` 已在“索引健康”和“测试检索”之间展示“最近运行”诊断，支持空状态和五通道耗时 |
| IDE 诊断 | 通过 | `rag_admin.py`、`test_rag_admin_runtime_summary.py`、`RagDiagnosticsView.vue` 均无报错 |
| 管理端构建 | 通过 | `npm run build` 成功；`vue-tsc` 与 Vite 生产构建完成，耗时 `4.50s` |

### 已知非阻塞提示

- pytest 仍提示 `pytest-asyncio` 尚未设置默认 fixture loop scope；不影响本轮 160 项测试通过。
- Vite 构建存在依赖库 PURE 注释和 bundle 大小警告；不影响构建结果。
- Chroma 在评测时输出 telemetry 兼容提示，以及请求数大于 36 个索引元素的裁剪提示；不影响 readiness、评测和 Citation 结果。
- 连续运行 30 分钟稳定性、真实浏览器断线重连、完整 ASR/TTS/数字人端到端演示仍属于 P1 后续工作。

---

## 9. 风险与边界

1. 当前 active 索引已通过 readiness 与冻结快照校验；演示前仍应在备份或隔离运行时复核，避免现场写入影响 SQLite interaction 数据。
2. 40 条 P0 演示集已经通过，但 12 条离线召回基线 Recall@5=0.50、MRR=0.404167 仍偏低；它不阻塞当前演示闭环，后续应扩充相关性标注并调优召回。
3. `match_faq()` 仍以 JSON 为运行时来源，SQLite FAQ 同步是显式步骤；当前 JSON 与 SQLite mirror 已通过快照校验，后续改 FAQ 必须重算 manifest 哈希。
4. 当前仍存在正式认证、弱 token、debug 边界和 Interaction 原文保存问题，不能对公网开放。
5. SQLite、FTS5、Chroma 没有跨存储事务，演示环境应使用冻结知识库，避免现场上传造成不确定性。
6. 当前 `llm_stream` 通常是整段回答事件，不是真实 token streaming；答辩中应如实说明。
7. 当前在线观测已补充最近 100 条有效轨迹的匿名聚合诊断，但仍是请求级 trace 基础，不等价于完整监控平台。
8. 本次运行时诊断的 pytest（2 项）与管理端生产构建均已通过；pytest 仍有既有 `pytest-asyncio` loop scope 警告，构建仍有依赖 PURE 注释和包体积警告。
9. 真实浏览器断线重连、连续 30 分钟稳定性和完整 ASR/TTS/数字人链路仍未纳入 P0 门禁。
10. 不应在竞赛前临时引入 GraphRAG、Reranker 或更换向量基础设施，以免破坏稳定演示。

---

## 10. 竞赛版完成定义

当前 P0 已满足竞赛演示闭环；当以下条件全部满足时，可称为：

> **软件杯 P1 竞赛演示版**

- 四类核心场景可稳定演示：FAQ、景点/路线、天气、无证据拒答；
- 多路召回、Evidence、Citation 和 RetrievalTrace 能够现场展示；
- LLM 和天气异常可以有限等待并稳定降级；
- 演示环境 active index readiness 为 `ready`；
- 文本、语音、WebSocket 和数字人链路可完成主要流程；
- 至少 30～50 条人工样例完成复核；
- 自动化测试、前端构建和演示脚本可复现；
- 连续运行 30 分钟、真实浏览器断线重连、ASR/TTS/数字人主流程完成验收；
- 报告、架构图、测试记录和答辩演示材料齐全。

在此之前，项目定位为：**P0 已验收的软件杯竞赛演示版本**。

---

## 11. 一句话结论

**软件杯版本不追求把 RAG 做成企业级生产平台，而要把“景区问题可靠路由、多路召回、证据引用、无证据拒答、天气/LLM 降级、语音数字人展示和可复现评测”做成一个稳定完整的 P1 演示闭环。**
