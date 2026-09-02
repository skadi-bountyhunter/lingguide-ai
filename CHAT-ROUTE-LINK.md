# AI 对话页与路线规划页联动说明

> 项目：灵境导游（LingGuide）  
> 最后更新：2026-07-19

## 当前联动契约

数字人只负责连接、渲染和播报；路线意图识别及结构化路线生成由后端聊天服务负责。

### 文本对话

```text
ChatView.sendText
  → WebSocket /api/chat/ws/{session_id}
  → 后端 _is_route_request 判断路线意图
  → generate_route 生成结构化路线
  → llm_done / message_done 返回 route_plan
  → useWebSocket 写入 assistantMessage.routePlan
  → 用户点击“路线推荐”
  → ChatView 将响应式路线深拷贝为普通对象
  → router.push({ query: { from: 'chat' }, state: { route_plan } })
  → RouteView 校验并消费快照
  → RoutePlanCard 展示，ScenicMap 按景点顺序绘制路线
```

### 语音对话

```text
ChatView 录音
  → POST /api/chat/voice
  → ASR 得到 query_text
  → 路线意图命中时复用 generate_route / _route_plan_payload
  → 响应返回 reply + route_plan
  → assistantMessage.routePlan
  → 后续跳转与文本对话完全一致
```

普通语音问答不返回 `route_plan`，不会显示“路线推荐”。

## 跳转数据契约

当前可靠入口是同一 SPA 内部导航：

```ts
router.push({
  name: 'route',
  query: { from: 'chat' },
  state: {
    route_plan: plainRouteSnapshot,
  },
})
```

路线快照最低结构：

```json
{
  "schema_version": 1,
  "source": "chat",
  "title": "佛韵半日游",
  "duration": "约4小时",
  "duration_mode": "半天",
  "spots": [
    { "name": "梵宫", "description": "欣赏建筑艺术" },
    { "name": "九龙灌浴", "description": "观看精彩表演" }
  ],
  "tips": "建议提前确认表演时间。",
  "interests": ["建筑艺术"]
}
```

约束：

- `route_plan` 必须是可结构化克隆的普通对象，不能直接传递 Vue/Pinia Proxy。
- URL 只保留 `from=chat`，不写入游客原始对话和路线正文。
- `chat_query`、`chat_reply` 仅属于 `POST /api/chat/route` 请求体或内部重试上下文，不是页面跳转参数。
- 直接打开 `/route?from=chat`、复制到新标签或缺失 History State 时，页面显示“路线快照已失效”属于预期降级。
- `duration_mode` 仅接受“半天”或“全天”；路线页会据此恢复时长选择。
- 景点名称应使用 `/api/spots` 返回的标准名称，且至少两个景点具有有效坐标，地图才能规划路线。

## 已修复问题

### 路线快照在跳转时丢失

原实现把 Pinia 中的响应式 `msg.routePlan` 直接放进 `router.push.state`。浏览器无法结构化克隆 Proxy，Vue Router 降级为普通导航后只保留 URL，导致路线页提示快照失效。

现已在 `ChatView.goToRoute` 边界执行 JSON 深拷贝，确保写入 `history.state.route_plan` 的是普通对象。

### 语音路线没有推荐按钮

原 `/api/chat/voice` 仅返回普通回复，未生成 `route_plan`；前端语音消息也未保存路线快照。现已让语音路线请求复用文本路线生成协议，并将快照写入 assistant 消息。

### 全天路线状态未恢复

原路线页消费快照后只同步兴趣，不同步 `duration_mode`。现已在合法值为“半天/全天”时同步 `aiDuration`。

### 地图初始化竞态

`ScenicMap.initMap()` 已在 `ready=true` 后检查 `props.activeRoute` 并补画，无需再次修改。

## 关键文件

- `frontend-visitor/src/views/ChatView.vue`
- `frontend-visitor/src/composables/useWebSocket.ts`
- `frontend-visitor/src/views/RouteView.vue`
- `frontend-visitor/src/components/ScenicMap.vue`
- `frontend-visitor/src/types/route.ts`
- `backend/app/api/chat.py`
- `backend/tests/test_chat_snapshot.py`
- `backend/tests/test_chat_voice_route.py`

## 验证标准

1. 文本路线回复出现“路线推荐”。
2. 点击后 URL 为 `/route?from=chat`，无 `chat_query`。
3. `window.history.state.route_plan` 存在且可 `JSON.stringify`。
4. 控制台无 `DataCloneError`。
5. 路线页不显示快照失效，卡片、景点顺序和地图路线正常。
6. 从快照进入路线页时不再次请求 `POST /api/chat/route`。
7. 全天路线进入后“全天”按钮处于选中状态。
8. 语音路线响应包含 `route_plan`，普通语音问答不包含。
9. 后端路线测试与游客端生产构建通过。
