# 灵境导游改进方案

基于参考视频分析，针对以下四个方面的改进计划。

---

## 一、路线规划页面优化

### 现状
- ✅ 已实现：数字人对话 → AI生成路线 → 跳转路线页
- ✅ 已实现：显示路线地图、景点列表、预计时长
- ✅ 已实现：保存路线功能

### ✅ 本次已完成

#### 1. 路线编辑（拖拽/增删）
**文件**：`frontend-visitor/src/components/RoutePlanCard.vue`、`frontend-visitor/src/views/RouteView.vue`

功能点：
- 拖拽排序景点（`vue-draggable-next`，拖拽手柄 `⋮⋮`）
- 删除景点（至少保留2个，按钮禁用保护）
- 添加景点（从22个景点库中搜索选择）
- 编辑后自动重算时长（0.5小时/景点）
- 保存/取消编辑双按钮，取消可恢复原状

**新增依赖**：`vue-draggable-next`、`nanoid`

#### 2. 路线对比（多方案）
**文件**：`backend/app/api/chat.py`、`frontend-visitor/src/views/RouteView.vue`

功能点：
- 后端 `RouteResponse` 新增 `alternatives` 字段
- 景点数量足够时自动生成最多2个备选方案（不同景点组合）
- 前端"还有 N 个备选方案"入口按钮
- 对话框展示所有方案：标题、时长、景点列表、建议
- "选择此方案"一键切换，自动更新地图

#### 3. 景点点击高亮地图
**文件**：`RoutePlanCard.vue`、`RouteView.vue`、`ScenicMap.vue`

- 路线卡片中景点名称可点击（cursor: pointer + hover 下划线）
- 点击后：地图滚动到可视区域 → 放大到 zoom 18 → 打开信息窗 → 标记弹跳动画
- `ScenicMap` 通过 `defineExpose({ focusSpot })` 对外暴露接口
- 标记 DOM 用 `data-spot` 属性定位，不依赖高德私有字段

#### 4. 分步加载反馈
**文件**：`RouteView.vue`、`i18n.ts`

- 生成路线时按 1.1s/步 轮播：「分析兴趣偏好…→ 匹配景点…→ 优化游览顺序…→ 生成路线建议…」
- 四语言（zh/en/ja/ko）均已配置，组件卸载时清理定时器

#### 5. 时长估算精确化
**文件**：`RouteView.vue`、`types/route.ts`、`backend/app/api/chat.py`

- 后端 `RouteSpot` 新增 `duration_min: int` 字段，解析 `Spot.duration`（如"1.5h"/"0.5h"/"30min"）为分钟
- 前端 `recalculateRoute()` 按实际 `duration_min` 求和，精度从"0.5h/景点"提升为真实时长
- `addSpotToRoute()` 手动添加景点时同步解析 `spot.duration`，客户端解析逻辑与后端一致

#### 6. 实时优化建议
**文件**：`frontend-visitor/src/views/RouteView.vue`

基于当前时段的客户端规则提示（不依赖外部API）：

| 时段 | 建议内容 |
|------|----------|
| 6–9时 | 前往九龙灌浴观看晨间表演，人流较少 |
| 10–12时 | 灵山大佛上午光线充足，优先开阔景区 |
| 12–14时 | 正午阳光强，推荐梵宫/博览馆等室内景点 |
| 14–17时 | 拈花广场/梵天花海拍照黄金时段 |
| 17–19时 | 夕照灵山大佛，全天最美观赏时刻 |

用户可手动关闭提示条（×按钮），关闭后当次会话不再弹出。

---

## 二、双通道情绪识别

### 现状
- ✅ 已实现：文本情绪分析（SnowNLP + 规则融合）
- ✅ 已实现：语音情绪识别（阿里云百炼平台）+ 双通道融合

### ✅ 本次已完成

#### 1. 文本情感分析修复（B方案）
**文件**：`backend/app/core/emotion.py`、`backend/tests/test_emotion.py`

- 修复否定词处理缺失（"不好""不满意"等前缀否定词识别并翻转极性）
- 修复 SnowNLP 对信息查询句（"怎么走""门票多少钱"）的系统性正向偏置，命中查询模式且无情绪词时强制中性
- 修复"好"字歧义：区分褒义词（"好玩""好看"）与语气强化词（"好累""好无聊"）
- 规则/模型融合权重调优为 0.9/0.1（规则命中时以规则为主），正向阈值由 0.62 调整为 0.60
- 新增 `tests/test_emotion.py` 单元测试，30个用例全部通过

#### 2. 语音情感识别接入（A方案）
**文件**：`backend/app/core/emotion.py`、`backend/app/config.py`、`backend/app/api/chat.py`

- 接入阿里云百炼平台 DashScope SDK，`paraformer-realtime-v2` 模型 + `emotion_channel="all"` 实时语音情感识别
- 新增 `analyze_voice_emotion()`：未配置 Key / SDK 未安装 / 调用异常时均优雅降级返回 `None`，由调用方回退纯文本情感
- 新增 `fuse_voice_text_emotion()`：语音与文本情感标签一致时取高置信度分数；不一致时按语音70%/文本30%加权重新分桶
- `chat_voice` 端点已改造为双通道融合逻辑
- 配置项 `dashscope_api_key` 已加入 `.env` 与 `config.py`（未做真实语音文件端到端联调，仅验证参数边界与融合逻辑）

---

## 三、地图导览增强

### 现状问题
```typescript
// frontend-visitor/src/components/ScenicMap.vue
function locateMe() {
  map.setZoomAndCenter(17, CENTER)  // 写死的西湖中心点，非真实GPS
}
```

### 待实现功能

#### 1. 自定义位置标记（开发量：1天）
```typescript
// 监听地图点击，添加可拖拽标记
map.on('click', (e) => {
  const pin = { id: nanoid(), name: '自定义点位', lnglat: [e.lnglat.lng, e.lnglat.lat] }
  showPinNamingDialog(pin)
})
// 标记持久化到 localStorage
```

#### 2. 实时GPS + 地理围栏（开发量：2天）
```typescript
// 替换固定坐标
watchId = navigator.geolocation.watchPosition(
  ({ coords }) => {
    updateUserMarker([coords.longitude, coords.latitude])
    checkGeofencing([coords.longitude, coords.latitude])
  },
  null,
  { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
)

// 地理围栏：50米内自动触发讲解
function checkGeofencing(userPos) {
  geofences.forEach(fence => {
    const dist = AMap.GeometryUtil.distance(userPos, fence.center)
    if (dist <= 50) triggerAutoGuide(fence.spotId)
  })
}
```

**测试要点**：室内信号弱降级处理、电量消耗优化、隐私授权引导

---

## 四、管理端数据大屏重做

### 参考视频中的管理端功能
1. 知识库管理
2. 游客画像分析
3. 运营仪表板
4. AI运营洞察
5. 反馈收集统计

### 缺口分析
后端 `backend/app/api/analytics.py` 中已有以下接口（部分已落地）：
- `GET /api/analytics/sentiment-trend` ✅ 已实现（7天情绪趋势，按天聚合）
- `GET /api/analytics/emotion-3d` ✅ 已实现（景点×时段×情绪分 bar3D，`EmotionBar3D` 组件）
- `GET /api/analytics/satisfaction` ✅ 已实现（情绪分均值转满意度，`SatisfactionBall` 组件）
- `GET /api/analytics/word-freq` ✅ 已实现（jieba 分词词云，`FeedbackWordCloud` 组件）
- `GET /api/visits/heatmap` ✅ 已实现（游客坐标热力图，`PinsHeatmap` 组件，高德 HeatMap）
- `GET /analytics/visitor-profile` ⬜ 待实现
- `GET /analytics/spot-heatmap` ⬜ 待实现（注：`/api/visits/heatmap` 已覆盖位置分布，此为另一维度）
- `GET /analytics/route-analytics` ⬜ 待实现
- `GET /analytics/qa-quality` ⬜ 待实现

### 改进方案

#### 1. 总览看板（2天）
```vue
<!-- 4张关键指标卡：今日游客、问答次数、平均满意度、活跃路线 -->
<!-- 每30秒自动刷新 -->
```

#### 2. 游客画像（1.5天）
- ECharts 年龄分布饼图
- 省份来源地图
- 兴趣词云（echarts-wordcloud）

#### 3. 景点热力图（1天）
```typescript
// 高德地图 AMap.HeatMap 插件
// 数据格式：{ lng, lat, count }，max:100
```

#### 4. 路线分析（1天）
使用次数、平均评分、完成率表格

#### 5. 问答质量分析（1天）
```python
# 高频问题Top10、平均响应时间、满意度分布
```

#### 6. 三维情绪热力图（5天）⭐ 核心升级
景点 × 时段 × 情绪分 bar3D，详见 [dashboard-redesign-plan.md](dashboard-redesign-plan.md)。
现有 `/api/analytics/sentiment-trend` 7天折线图保留为辅助视角。

#### 7. AI运营洞察（1.5天）
```python
# 定期调用 DeepSeek，输出3-5条洞察建议
# 前端 el-timeline 展示
```

**大屏总开发量**：~15天（含三维情绪热力图专项5天，见 [dashboard-redesign-plan.md](dashboard-redesign-plan.md)）

---

## 总进度看板

| 功能模块 | 状态 | 开发量 | 优先级 |
|----------|------|--------|--------|
| 路线编辑（拖拽/增删） | ✅ 已完成 | 1天 | P0 |
| 路线对比（多方案） | ✅ 已完成 | 1天 | P1 |
| 实时优化建议（时段） | ✅ 已完成 | 0.5天 | P1 |
| 景点点击高亮地图 | ✅ 已完成 | 0.5天 | P1 |
| 分步加载反馈 | ✅ 已完成 | 0.5天 | P1 |
| 时长估算精确化 | ✅ 已完成 | 0.5天 | P1 |
| 地图缩略图标记+景点筛选 | ✅ 已完成 | 2天 | P1 |
| 地图自定义标记 | ⬜ 待实现 | 1天 | P0 |
| 实时GPS + 地理围栏 | ⬜ 待实现 | 2天 | P0 |
| 双通道情绪识别 | ✅ 已完成 | 4天 | P1 |
| 管理端数据大屏 | ✅ 已完成 | 15天 | P2 |
| **剩余合计** | | **3天** | |

## 建议排期

- **本周**：地图增强（自定义标记 + 实时GPS，共3天）
- **下周起**：数据大屏（10天）

---

*最后更新：2026-07-30*
