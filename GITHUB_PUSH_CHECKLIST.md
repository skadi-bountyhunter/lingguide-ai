# 灵境导游 - GitHub 推送安全清单

## ✅ 已完成的安全加固

### 1. .gitignore 完善
- 环境变量文件：`.env`, `backend/.env`, `scripts/*.env`
- 数据库文件：`*.db`, `*.sqlite3`, `backend/app/data/`, `backend/app/chroma_store/`
- 打包产物：`release/`, `desktop/dist/`, `build/`, `dist/`
- 调试配置：`.chrome-cdp-profile/`, `.chrome-debug-profile/`, `.playwright-mcp/`
- 测试文件：`*.jpeg`, `*.jpg`, `*.png`, `_docx_*/`, `临时资源存放/`

### 2. 环境变量模板
- 创建 `.env.example` - 后端配置示例
- 创建 `scripts/.env.example` - 高德地图配置示例

### 3. 硬编码凭据清理
- `scripts/calibrate_spots.html` - 已移除高德 Key 和 securityJsCode，改为占位符

---

## 🔴 推送前必须手动操作

### 1. 初始化 Git 仓库
```bash
git init
git add .
git commit -m "Initial commit: 灵境导游 AI 数字人导览系统"
```

### 2. 检查敏感文件是否被排除
```bash
git status
# 确认以下文件 NOT 出现在待提交列表：
# - backend/.env
# - backend/app/data/lingguide.db
# - backend/app/chroma_store/chroma.sqlite3
# - backups/
# - release/
# - scripts/calibrate_spots.html 中的真实 Key（应为占位符）
```

### 3. 备份本地敏感文件（推送前）
```bash
# 建议在项目外单独备份：
cp backend/.env ../lingguide-secrets/backend.env
cp backend/app/data/lingguide.db ../lingguide-secrets/
```

### 4. 推送到 GitHub
```bash
git remote add origin https://github.com/你的用户名/灵境导游.git
git branch -M main
git push -u origin main
```

---

## ⚠️ 注意事项

1. **首次 clone 后需要手动配置**：
   - 复制 `.env.example` → `backend/.env` 并填入真实值
   - 复制 `scripts/.env.example` → `scripts/.env`（如需使用校准脚本）
   - 运行 `backend/app/init_db.py` 初始化数据库

2. **CI/CD 配置**（如使用）：
   - 在 GitHub Secrets 中配置所有环境变量
   - 数据库使用 PostgreSQL 等外部服务，不要提交 SQLite 文件

3. **协作者提醒**：
   - 在 README 中说明环境变量配置步骤
   - 提供 `.env.example` 文件作为参考

---

## 📋 可选：进一步清理

如需减小仓库体积，可删除以下非必需文件后再推送：

```bash
# 临时文档和测试截图
rm -f *.jpeg *.jpg *.png
rm -rf _docx_* 临时资源存放/

# 本地调试配置
rm -rf .chrome-cdp-profile/ .chrome-debug-profile/

# 历史工作日志（可选保留）
rm -f WORK-LOG-*.md 今日工作日志-*.md
```

---

**当前状态**：已完成 .gitignore 配置和敏感文件清理，可以安全 `git init` 并推送。
