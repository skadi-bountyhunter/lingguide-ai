<template>
  <div class="routes animate-fade-up">
    <div class="page-hd">
      <div><h2>🗺️ 路线管理</h2><p>编辑游客端预设经典路线（路线页实时展示）</p></div>
      <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增路线</el-button>
    </div>

    <!-- 路线列表 -->
    <div class="card section-card">
      <div class="sec-hd"><h3>📋 路线列表</h3><span class="cnt">共 {{ routes.length }} 条</span></div>
      <el-table :data="routes" v-loading="loading" style="width:100%">
        <el-table-column label="图标" width="70">
          <template #default="r"><span class="route-icon">{{ r.row.icon || '📍' }}</span></template>
        </el-table-column>
        <el-table-column prop="title" label="路线名" min-width="140" />
        <el-table-column label="包含景点" min-width="220">
          <template #default="r">
            <el-tag v-for="s in r.row.spots" :key="s" size="small" type="info" style="margin-right:4px;margin-bottom:2px">{{ s }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="140">
          <template #default="r">
            <el-tag v-for="t in r.row.tags" :key="t" size="small" style="margin-right:4px">{{ t }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="时长" width="80" />
        <el-table-column prop="difficulty" label="难度" width="80" />
        <el-table-column prop="sort_order" label="排序" width="70" />
        <el-table-column label="操作" width="160">
          <template #default="r">
            <el-button size="small" @click="openEdit(r.row)">编辑</el-button>
            <el-button type="danger" size="small" text @click="handleDelete(r.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && routes.length === 0" description="暂无路线，点击右上角新增" />
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showDialog" :title="editing.id ? '编辑路线' : '新增路线'" width="min(720px, 92vw)" top="6vh" class="route-dialog" body-class="route-dialog__body" append-to-body :close-on-click-modal="false">
      <el-form :model="editing" label-position="top">
        <!-- 基本信息 -->
        <div class="form-group-title">基本信息</div>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="路线名" required>
            <el-input v-model="editing.title" placeholder="如：佛韵深度游" />
          </el-form-item></el-col>
          <el-col :span="6"><el-form-item label="图标（emoji）">
            <el-input v-model="editing.icon" placeholder="🛕" />
          </el-form-item></el-col>
          <el-col :span="6"><el-form-item label="排序">
            <el-input-number v-model="editing.sort_order" :min="0" controls-position="right" style="width:100%" />
          </el-form-item></el-col>
        </el-row>
        <el-form-item label="简介">
          <el-input v-model="editing.desc" type="textarea" :rows="2" maxlength="100" show-word-limit />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="游览时长"><el-input v-model="editing.duration" placeholder="3.5h" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="路程"><el-input v-model="editing.distance" placeholder="4.2km" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="难度">
            <el-select v-model="editing.difficulty" placeholder="轻松/适中" style="width:100%">
              <el-option label="轻松" value="轻松" />
              <el-option label="适中" value="适中" />
              <el-option label="较难" value="较难" />
            </el-select>
          </el-form-item></el-col>
        </el-row>

        <!-- 包含景点 -->
        <div class="form-group-title">包含景点</div>
        <el-form-item label="景点（回车添加，按游览顺序）">
          <el-select v-model="editing.spots" multiple filterable allow-create default-first-option
            :reserve-keyword="false" placeholder="输入景点名后回车" style="width:100%" />
        </el-form-item>
        <el-form-item label="分类标签（回车添加）">
          <el-select v-model="editing.tags" multiple filterable allow-create default-first-option
            :reserve-keyword="false" placeholder="如：佛教文化、自然风光" style="width:100%" />
        </el-form-item>

        <!-- 贴士 -->
        <div class="form-group-title">游览贴士</div>
        <el-form-item label="贴士">
          <el-input v-model="editing.tip" type="textarea" :rows="2" placeholder="如：建议上午前往，避开午后人流高峰" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/services/api'

interface RouteItem {
  id?: number
  title: string
  icon: string
  duration: string
  distance: string
  difficulty: string
  desc: string
  spots: string[]
  tags: string[]
  tip: string
  sort_order: number
}

const routes = ref<RouteItem[]>([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)

const emptyRoute = (): RouteItem => ({
  title: '', icon: '', duration: '', distance: '', difficulty: '',
  desc: '', spots: [], tags: [], tip: '', sort_order: 0,
})
const editing = reactive<RouteItem>(emptyRoute())

onMounted(() => fetchRoutes())

async function fetchRoutes() {
  loading.value = true
  try {
    const { data } = await api.get('/api/routes')
    routes.value = data
  } catch { ElMessage.error('加载路线失败') }
  finally { loading.value = false }
}

function openCreate() {
  Object.assign(editing, emptyRoute())
  showDialog.value = true
}

function openEdit(row: RouteItem) {
  Object.assign(editing, JSON.parse(JSON.stringify(row)))
  showDialog.value = true
}

async function handleSave() {
  if (!editing.title.trim()) { ElMessage.warning('请填写路线名'); return }
  editing.spots = editing.spots.filter(x => x.trim())
  editing.tags = editing.tags.filter(x => x.trim())
  saving.value = true
  try {
    if (editing.id) {
      await api.put(`/api/routes/${editing.id}`, editing)
      ElMessage.success('已更新')
    } else {
      await api.post('/api/routes', editing)
      ElMessage.success('已新增')
    }
    showDialog.value = false
    await fetchRoutes()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally { saving.value = false }
}

async function handleDelete(row: RouteItem) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.title}」？此操作不可恢复。`, '提示', { type: 'warning' })
    await api.delete(`/api/routes/${row.id}`)
    ElMessage.success('已删除')
    await fetchRoutes()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.routes { display:flex; flex-direction:column; gap:24px; }
.page-hd { display:flex; justify-content:space-between; align-items:center; }
.page-hd h2 { font-size:1rem; font-weight:700; color:var(--color-text-primary); }
.page-hd p { font-size:0.75rem; color:var(--color-text-muted); margin-top:4px; }
.section-card { padding:20px; }
.sec-hd { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.sec-hd h3 { font-size:0.875rem; font-weight:700; color:var(--color-text-primary); }
.cnt { font-size:0.75rem; color:var(--color-text-muted); }
.route-icon { font-size:1.25rem; }

.form-group-title {
  font-size:0.8rem; font-weight:700; color:var(--color-primary);
  margin:4px 0 12px; padding-left:8px; border-left:3px solid var(--color-primary);
}

:global(.route-dialog) {
  max-height: none;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
}

:global(.route-dialog .el-dialog__header) {
  padding: 18px 24px 12px;
  margin-right: 0;
  border-bottom: 1px solid rgba(0,0,0,0.06);
}

:global(.route-dialog__body) {
  flex: 1;
  max-height: calc(88vh - 134px);
  overflow-y: auto;
  padding: 18px 24px 8px;
}

:global(.route-dialog .el-dialog__footer) {
  padding: 14px 24px 18px;
  border-top: 1px solid rgba(0,0,0,0.06);
  background: #fff;
}
</style>
