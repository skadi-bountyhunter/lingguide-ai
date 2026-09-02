<template>
  <div class="spots animate-fade-up">
    <div class="page-hd">
      <div><h2>🏔️ 景点管理</h2><p>编辑景区景点详情卡片内容（游客端实时展示）</p></div>
      <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增景点</el-button>
    </div>

    <!-- 景点列表 -->
    <div class="card section-card">
      <div class="sec-hd"><h3>📄 景点列表</h3><span class="cnt">共 {{ spots.length }} 处</span></div>
      <el-table :data="spots" v-loading="loading" style="width:100%">
        <el-table-column label="图片" width="90">
          <template #default="s">
            <img v-if="s.row.image" :src="s.row.image" class="thumb" />
            <span v-else class="no-img">无</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column label="标签" min-width="160">
          <template #default="s">
            <el-tag v-for="t in s.row.tags" :key="t" size="small" style="margin-right:4px">{{ t }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="时长" width="80" />
        <el-table-column prop="sort_order" label="排序" width="70" />
        <el-table-column label="操作" width="160">
          <template #default="s">
            <el-button size="small" @click="openEdit(s.row)">编辑</el-button>
            <el-button type="danger" size="small" text @click="handleDelete(s.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && spots.length === 0" description="暂无景点，点击右上角新增" />
    </div>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showDialog" :title="editing.id ? '编辑景点' : '新增景点'" width="min(760px, 92vw)" top="6vh" class="spot-dialog" body-class="spot-dialog__body" append-to-body :close-on-click-modal="false">
      <el-form :model="editing" label-position="top">
        <!-- 基本信息 -->
        <div class="form-group-title">基本信息</div>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="名称" required>
            <el-input v-model="editing.name" placeholder="如：灵山大佛" />
          </el-form-item></el-col>
          <el-col :span="6"><el-form-item label="图标（emoji）">
            <el-input v-model="editing.icon" placeholder="✨" />
          </el-form-item></el-col>
          <el-col :span="6"><el-form-item label="排序">
            <el-input-number v-model="editing.sort_order" :min="0" controls-position="right" style="width:100%" />
          </el-form-item></el-col>
        </el-row>
        <el-form-item label="图片 URL">
          <el-input v-model="editing.image" placeholder="/images/xxx.jpeg 或外链" />
        </el-form-item>
        <el-form-item label="短描述（首页列表用）">
          <el-input v-model="editing.desc" type="textarea" :rows="2" maxlength="80" show-word-limit />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="游览时长"><el-input v-model="editing.duration" placeholder="1.5h" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="距入口"><el-input v-model="editing.distance" placeholder="0.8km" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="最佳季节"><el-input v-model="editing.best_season" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="标签（回车添加）">
          <el-select v-model="editing.tags" multiple filterable allow-create default-first-option
            :reserve-keyword="false" placeholder="输入后回车" style="width:100%" />
        </el-form-item>

        <!-- 介绍 -->
        <div class="form-group-title">景点介绍</div>
        <el-form-item label="完整介绍（段落之间用空行分隔）">
          <el-input v-model="editing.full_desc" type="textarea" :rows="6" />
        </el-form-item>

        <!-- 亮点 / 贴士 -->
        <div class="form-group-title">核心亮点</div>
        <div class="dyn-list">
          <div v-for="(h, i) in editing.highlights" :key="'h'+i" class="dyn-row">
            <el-input v-model="editing.highlights[i]" placeholder="如：88米世界最高青铜立像" />
            <el-button type="danger" text @click="editing.highlights.splice(i,1)"><el-icon><Delete /></el-icon></el-button>
          </div>
          <el-button size="small" @click="editing.highlights.push('')"><el-icon><Plus /></el-icon>添加亮点</el-button>
        </div>

        <div class="form-group-title">游览贴士</div>
        <div class="dyn-list">
          <div v-for="(t, i) in editing.tips" :key="'t'+i" class="dyn-row">
            <el-input v-model="editing.tips[i]" placeholder="如：建议顺时针绕佛三圈祈福" />
            <el-button type="danger" text @click="editing.tips.splice(i,1)"><el-icon><Delete /></el-icon></el-button>
          </div>
          <el-button size="small" @click="editing.tips.push('')"><el-icon><Plus /></el-icon>添加贴士</el-button>
        </div>

        <!-- 实用信息 -->
        <div class="form-group-title">实用信息</div>
        <el-form-item label="开放时间"><el-input v-model="editing.hours" /></el-form-item>
        <el-form-item label="门票信息"><el-input v-model="editing.ticket" /></el-form-item>

        <!-- 周边景点 -->
        <div class="form-group-title">周边景点</div>
        <el-form-item label="周边景点（多选）">
          <el-select v-model="editing.nearby" multiple placeholder="选择周边景点" style="width:100%">
            <el-option v-for="s in spots" :key="s.id" :label="s.name" :value="s.name"
              :disabled="s.name === editing.name" />
          </el-select>
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

interface SpotItem {
  id?: number
  name: string
  icon: string
  image: string
  desc: string
  full_desc: string
  tags: string[]
  duration: string
  distance: string
  highlights: string[]
  hours: string
  ticket: string
  tips: string[]
  best_season: string
  nearby: string[]
  sort_order: number
}

const spots = ref<SpotItem[]>([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)

const emptySpot = (): SpotItem => ({
  name: '', icon: '', image: '', desc: '', full_desc: '',
  tags: [], duration: '', distance: '', highlights: [], hours: '',
  ticket: '', tips: [], best_season: '', nearby: [], sort_order: 0,
})
const editing = reactive<SpotItem>(emptySpot())

onMounted(() => fetchSpots())

async function fetchSpots() {
  loading.value = true
  try {
    const { data } = await api.get('/api/spots')
    spots.value = data
  } catch { ElMessage.error('加载景点失败') }
  finally { loading.value = false }
}

function openCreate() {
  Object.assign(editing, emptySpot())
  showDialog.value = true
}

function openEdit(row: SpotItem) {
  Object.assign(editing, JSON.parse(JSON.stringify(row)))
  showDialog.value = true
}

async function handleSave() {
  if (!editing.name.trim()) { ElMessage.warning('请填写景点名称'); return }
  // 过滤空字符串
  editing.highlights = editing.highlights.filter(x => x.trim())
  editing.tips = editing.tips.filter(x => x.trim())
  saving.value = true
  try {
    if (editing.id) {
      await api.put(`/api/spots/${editing.id}`, editing)
      ElMessage.success('已更新')
    } else {
      await api.post('/api/spots', editing)
      ElMessage.success('已新增')
    }
    showDialog.value = false
    await fetchSpots()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally { saving.value = false }
}

async function handleDelete(row: SpotItem) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」？此操作不可恢复。`, '提示', { type: 'warning' })
    await api.delete(`/api/spots/${row.id}`)
    ElMessage.success('已删除')
    await fetchSpots()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.spots { display:flex; flex-direction:column; gap:24px; }
.page-hd { display:flex; justify-content:space-between; align-items:center; }
.page-hd h2 { font-size:1rem; font-weight:700; color:var(--color-text-primary); }
.page-hd p { font-size:0.75rem; color:var(--color-text-muted); margin-top:4px; }
.section-card { padding:20px; }
.sec-hd { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.sec-hd h3 { font-size:0.875rem; font-weight:700; color:var(--color-text-primary); }
.cnt { font-size:0.75rem; color:var(--color-text-muted); }
.thumb { width:60px; height:40px; object-fit:cover; border-radius:6px; }
.no-img { font-size:0.75rem; color:var(--color-text-muted); }

.form-group-title {
  font-size:0.8rem; font-weight:700; color:var(--color-primary);
  margin:8px 0 12px; padding-left:8px; border-left:3px solid var(--color-primary);
}
.dyn-list { display:flex; flex-direction:column; gap:8px; margin-bottom:16px; }
.dyn-row { display:flex; gap:8px; align-items:center; }

:global(.spot-dialog) {
  max-height: none;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
}

:global(.spot-dialog .el-dialog__header) {
  padding: 18px 24px 12px;
  margin-right: 0;
  border-bottom: 1px solid rgba(0,0,0,0.06);
}

:global(.spot-dialog__body) {
  flex: 1;
  max-height: calc(88vh - 134px);
  overflow-y: auto;
  padding: 18px 24px 8px;
}

:global(.spot-dialog .el-dialog__footer) {
  padding: 14px 24px 18px;
  border-top: 1px solid rgba(0,0,0,0.06);
  background: #fff;
}
</style>
