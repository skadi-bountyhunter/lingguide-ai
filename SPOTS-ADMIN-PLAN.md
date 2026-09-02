# 景点详情卡片后台可编辑（前后端打通）实施计划

## 背景

目前景点详情卡片完全是前端硬编码：`frontend-visitor/src/data/spots.ts` 里写死了 6 个景点（`SCENIC_SPOTS`）+ 4 个轮播项（`CAROUSEL_ITEMS`），`HomeView` 和 `SpotDetailView` 直接 `import` 这份数据。后端没有景点模型和 API，后台管理端（`frontend-admin`）也没有景点管理页。

**目标**：新建一整条链路，让运营在后台管理端增删改景点内容，游客端实时从后端接口读取展示。

### 已确认的决策

- 图片**仅填 URL 字段**（复用现有 `/images/*` 静态资源或外链），不做上传
- 游客端**纯接口、无静态兜底**（删除 `spots.ts` 里的静态数据，仅保留类型）
- 后端用 **SQLite 持久化**（ORM 模型，与 `Favorite` 模式一致）

### 额外发现：端口错配（必须一并修复，否则接口打不通）

后端实际监听 **5000**（`启动.bat`: `uvicorn --port 5000`），但两个前端的 vite proxy 都指错了：

- `frontend-visitor/vite.config.ts`:32 → `target: 'http://localhost:5001'` ❌（5001 是 TTS CosyVoice）
- `frontend-admin/vite.config.ts`:16 → `target: 'http://localhost:8000'` ❌

两处都要改成 `http://localhost:5000`。

---

## 实施步骤

### 一、后端：新增 spots 模块

#### 1. 模型 `backend/app/models/spot.py`（新建）

参照 `models/favorite.py` 的简洁风格。字段对齐前端 `ScenicSpot` 接口：

```python
class Spot(Base):
    __tablename__ = "spots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)  # 景点名（路由用）
    icon = Column(String, default="")
    image = Column(String, default="")           # 图片 URL
    desc = Column(String, default="")            # 首页短描述
    full_desc = Column(Text, default="")         # 详情完整介绍（\n\n 分段）
    tags = Column(Text, default="[]")            # JSON 数组
    duration = Column(String, default="")
    distance = Column(String, default="")
    highlights = Column(Text, default="[]")      # JSON 数组
    hours = Column(String, default="")
    ticket = Column(String, default="")
    tips = Column(Text, default="[]")            # JSON 数组
    best_season = Column(String, default="")
    nearby = Column(Text, default="[]")          # JSON 数组（景点名）
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

给 `tags/highlights/tips/nearby` 加同 `FAQ.tags_list` 一样的 `@property` list getter/setter（参考 `models/__init__.py`:90-97）。

#### 2. 模型注册 `backend/app/models/__init__.py`

在文件末尾 `from app.models.favorite import Favorite` 下方加 `from app.models.spot import Spot`，确保 `init_db` 能建表（`database.py`:34 `import app.models`）。

#### 3. API `backend/app/api/spots.py`（新建）

参照 `api/profile.py`（Favorite CRUD）和 `api/knowledge.py`（FAQ CRUD）的混合风格。`APIRouter(prefix="/api/spots", tags=["景点"])`。

公开接口（游客端）：

- `GET /api/spots` → 列表，按 `sort_order` 升序，返回完整字段
- `GET /api/spots/{name}` → 单个详情，404 处理
- `GET /api/spots/carousel` → 轮播，取前 4 个景点组装 `{image, title:name, subtitle:desc}`

管理接口（后台 CRUD，与现有 knowledge/profile 管理接口一致，不做鉴权）：

- `POST /api/spots` → 新增
- `PUT /api/spots/{id}` → 更新
- `DELETE /api/spots/{id}` → 删除

Pydantic 模型 `SpotCreate` / `SpotUpdate` / `SpotOut`，`SpotOut` 用 `from_attributes=True`，list 字段用 `list[str]`。

#### 4. 种子数据

首次启动若 `spots` 表为空，用现 `spots.ts` 的 6 条数据 seed 一次（硬编码为 Python 列表常量，只在表空时插入）。

#### 5. 路由注册 `backend/app/main.py`

`from app.api import ... spots`，`app.include_router(spots.router)`。

### 二、后台管理端：新增景点管理页

#### 6. `frontend-admin/src/views/SpotsView.vue`（新建）

参照 `KnowledgeView.vue` 的结构（page-hd + section-card + el-table + el-dialog）。功能：

- 表格列：图片缩略图 / 名称 / 标签 / 游览时长 / 排序 / 操作（编辑/删除）
- 顶部「新增景点」按钮
- 编辑对话框：分组表单
  - 基本：名称、图标、图片URL、短描述、标签(多选输入)、时长、距离、最佳季节、排序
  - 介绍：fullDesc（textarea，提示用空行分段）
  - 亮点/贴士：动态增删的字符串列表
  - 实用：开放时间、门票
  - 周边：从现有景点列表多选（el-select multiple，选项来自 `/api/spots`，排除自身）
- axios 调 `/api/spots` 系列，复用 `KnowledgeView` 的 `ElMessage` 提示模式

#### 7. 路由 `frontend-admin/src/router.ts`

加 `{ path: '/spots', name: 'spots', component: () => import('./views/SpotsView.vue') }`。

#### 8. 侧边栏 `frontend-admin/src/App.vue`

`navItems` 加 `{ path: '/spots', label: '景点管理', icon: '<svg...>' }`（地图标记图标），`titles` 映射加 `'/spots': '景点内容管理'`。

### 三、游客端：改为接口取数

#### 9. `frontend-visitor/src/data/spots.ts`

- 保留 `ScenicSpot` / `CarouselItem` 接口定义（类型还要用）
- 删除 `SCENIC_SPOTS` 和 `CAROUSEL_ITEMS` 静态数据
- 导出 `fetchSpots(): Promise<ScenicSpot[]>` 和 `fetchCarousel(): Promise<CarouselItem[]>`，axios 调 `/api/spots`、`/api/spots/carousel`，字段映射（snake_case → camelCase）

#### 10. `frontend-visitor/src/views/HomeView.vue`

`spots` / `carouselItems` 改为 `ref`，`onMounted` 调 `fetchSpots()`/`fetchCarousel()`，加 loading 态。轮播自动播放逻辑保留。

#### 11. `frontend-visitor/src/views/SpotDetailView.vue`

- `spot` 改为 `ref`，`onMounted` 按 `route.params.name` 调 `/api/spots/{name}`
- `nearbySpots` 根据返回的 `nearby` 名称数组从已加载列表过滤
- 加 loading / 未找到的空态

### 四、端口错配修复

#### 12. `frontend-visitor/vite.config.ts`

`target: 'http://localhost:5001'` → `http://localhost:5000`

#### 13. `frontend-admin/vite.config.ts`

`target: 'http://localhost:8000'` → `http://localhost:5000`，补 `ws: true`

---

## 关键复用点

- ORM 模式：`backend/app/models/favorite.py`（最简）+ `models/__init__.py` 的 JSON list property
- CRUD API 模式：`backend/app/api/profile.py`（Favorite 的 select/add/delete）
- 管理页 UI 模式：`frontend-admin/src/views/KnowledgeView.vue`（表格 + 对话框 + ElMessage）
- 字段映射：后端 snake_case ↔ 前端 camelCase，在 `spots.ts` 的 fetch 函数里统一转

## 验证

1. 启动后端 `uvicorn app.main:app --reload --port 5000`，确认 `http://localhost:5000/docs` 出现 `/api/spots` 系列接口，`GET /api/spots` 返回 6 条种子数据
2. 启动管理端 `cd frontend-admin && npm run dev`（:3001），访问 `/spots`：
   - 能看到 6 条景点列表
   - 编辑某景点（改名称/亮点），保存后表格刷新
   - 新增一个景点，游客端首页能看到
3. 启动游客端 `cd frontend-visitor && npm run dev`（:3000）：
   - 首页景点列表、轮播正常加载（验证 proxy 修复）
   - 点进详情页，字段正确展示
   - 后台改某景点后，刷新游客端看到变化
4. 浏览器预览（CDP :9222）截图首页 + 详情页确认渲染正常
