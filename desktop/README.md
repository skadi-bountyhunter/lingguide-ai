# 灵境导游桌面端

## 构建前置

- Windows x64、Node.js 与 npm。
- 先生成 `frontend-visitor/dist`、`frontend-admin/dist`。
- 先将后端冻结为 `backend/dist/lingguide-backend/lingguide-backend.exe`；该程序须读取桌面端传入的环境变量，并向 stdout 输出一行 `LINGGUIDE_READY {"port":动态端口}`。
- 后端须在动态端口提供 `/api/health`、`/api/readiness`、游客 SPA `/` 和管理 SPA `/admin/`。
- 后端须使用：
  - `LINGGUIDE_DATA_ROOT`：可写数据根目录。
  - `LINGGUIDE_RESOURCE_ROOT`：打包资源根目录。
  - `LINGGUIDE_ADMIN_TOKEN`：本次进程随机管理令牌。
- `extraResources` 的源文件可暂时不存在，不影响源码测试；正式打包前必须补齐。

## 命令

```bash
# 首次锁定依赖；由构建环境生成真实 integrity，不手写锁文件
npm install --package-lock-only
npm install

# 开发运行
npm run dev

# 仅运行 Node 内置测试
npm test

# 输出 Windows x64 解包目录，不生成安装包
npm run build:dir
```

开发态启动的是 `backend/launcher.py`；可用 `LINGGUIDE_PYTHON` 指定 Python。打包态启动 `resources/backend/lingguide-backend.exe`。默认数据目录为 exe 同级 `LingGuideData`，测试可用 `LINGGUIDE_DATA_ROOT` 覆盖。
