# 管理端数据大屏改造专项计划

> 灵境导游 · 管理端（:3001）数据大屏，核心产出：景点×时段情绪热力图（三维 bar3D）。
> 最后更新：2026-07-30

---

## 一、核心三维图设计

### 1.1 维度映射

| 轴 | 含义 | 数据来源 | 范围 |
|----|------|----------|------|
| X轴 | 一天内小时 | `created_at` 取小时 | 0–23 |
| Y轴 | 景点名称 | `spot_id → Spot.name` | 22个景点 |
| Z轴 | 情绪分均值 | `AVG(emotion_score)` | 0–1 |
| 颜色 | 双重编码分值 | visualMap 分级渲染 | 红→黄→绿 |

### 1.2 可视化行为

- **默认视图**：近7天数据按小时聚合（降低单日稀疏问题）
- **时间切换**：今日 / 近7天 / 近30天（复用 DashboardView 现有 period 切换器）
- **Tooltip**：悬停显示景点名、时段、情绪分均值、样本量
- **空值处理**：无数据的（小时,景点）单元格不渲染柱体

### 1.3 技术选型（参考 iDataV/case02 bar3D 模式）

```javascript
option = {
  grid3D: { boxWidth: 200, boxDepth: 80, viewControl: { distance: 200 } },
  xAxis3D: { type: 'category', data: hours },      // ['00','01',...,'23']
  yAxis3D: { type: 'category', data: spotNames },  // ['灵山大佛','九龙灌浴',...]
  zAxis3D: { type: 'value', max: 1 },
  visualMap: { max: 1, inRange: { color: ['#e84040', '#f5c518', '#52c41a'] } },
  series: [{ type: 'bar3D', data: [[hour, spotIdx, score]], shading: 'lambert' }]
}
```

---

## 二、数据层改造

### 2.1 Interaction 表新增 spot_id

```python
# backend/app/models/__init__.py  Interaction 类末尾追加
spot_id = Column(String(64), ForeignKey("spots.id"), nullable=True, index=True)
```

SQLite 迁移（直接执行，无需 Alembic）：
```sql
ALTER TABLE interactions ADD COLUMN spot_id VARCHAR(64) REFERENCES spots(id);
CREATE INDEX ix_interactions_spot_id ON interactions(spot_id);
```

历史数据 nullable，不影响旧记录。

### 2.2 聊天接口透传景点上下文

游客端聊天请求体新增可选字段 `spot_id`，后端写入 `Interaction.spot_id`。

**取值来源（优先级）：**
1. GPS 地理围栏自动检测（待实现，见 improvement-plan.md §三）
2. 游客手动选择当前景点（过渡方案：ChatView 顶部加轻量景点选择器）

### 2.3 新后端接口 GET /api/analytics/emotion-3d

```python
# 查询逻辑（SQLite 兼容）
GROUP BY STRFTIME('%H', interactions.created_at), interactions.spot_id
# 返回格式
[{"hour": 10, "spot_name": "灵山大佛", "avg_score": 0.72, "count": 15}, ...]
```

日期范围参数：`?days=7`（默认7天）。

---

## 三、辅助组件（case04 参考）

| 组件 | 参考来源 | 数据源 | 用途 |
|------|----------|--------|------|
| 满意度水球图 | case04 ballChart (liquidFill) | 今日 AVG(emotion_score) | 整体满意度百分比 |
| 反馈词云 | case04 wordChart (wordCloud) | query_text 中文分词 | 高频词 Top50 |

词云后端新增 `GET /api/analytics/word-freq`，使用 `jieba` 分词（新增依赖）。

---

## 四、前端工程

### 4.1 新增依赖（frontend-admin/package.json）

```json
"echarts-gl": "^2.0.9",
"echarts-liquidfill": "^3.1.0",
"echarts-wordcloud": "^2.1.0"
```

后端新增：`jieba`（Python，用于中文分词）

### 4.2 新增组件

| 文件 | 职责 |
|------|------|
| `src/components/charts/EmotionBar3D.vue` | 三维情绪热力图（核心） |
| `src/components/charts/SatisfactionBall.vue` | 满意度水球图 |
| `src/components/charts/FeedbackWordCloud.vue` | 反馈词云 |

### 4.3 DashboardView 新布局（在现有指标卡+折线图下方追加）

```
┌──────────────────────────────────────────────────┐
│       现有：指标卡 4格 + 交互趋势折线图           │
├───────────┬──────────────────────┬───────────────┤
│ 满意度    │  景点×时段情绪热力图  │   反馈词云    │
│ 水球图    │     bar3D（主视觉）   │               │
│  (1/4)   │       (1/2)          │    (1/4)      │
└───────────┴──────────────────────┴───────────────┘
```

---

## 五、实施计划

| 阶段 | 任务 | 工时 |
|------|------|------|
| 阶段一 | Interaction 加 spot_id + 数据库迁移 + `/api/analytics/emotion-3d` 接口 | 1天 |
| 阶段二 | `EmotionBar3D.vue`（bar3D 渲染 + tooltip + 时间切换） | 1.5天 |
| 阶段三 | `SatisfactionBall.vue` + `FeedbackWordCloud.vue` + 后端 word-freq 接口 | 1天 |
| 阶段四 | `DashboardView.vue` 布局集成 + 样式调优 + 测试 | 1.5天 |
| **合计** | | **5天** |

---

## 六、验收标准

- [ ] 三维图正常渲染，22景点 × 24小时矩阵数据可呈现
- [ ] 悬停 tooltip 显示景点名、时段、情绪分均值、样本量
- [ ] 时间范围切换（今日 / 近7天 / 近30天）
- [ ] 满意度水球图实时刷新今日数据
- [ ] 词云展示近7天 Top50 高频词
- [ ] 游客端聊天请求可携带 `spot_id`（手动选择或 GPS 联动）

*最后更新：2026-07-30*
