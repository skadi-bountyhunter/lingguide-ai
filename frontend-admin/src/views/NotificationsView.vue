<template>
  <div class="notifications-page animate-fade-up">
    <div class="page-hd">
      <div><h2>🔔 通知管理</h2><p>向全体游客或指定用户发布通知</p></div>
      <el-button type="primary" @click="openPublish"><el-icon><Plus /></el-icon>发布通知</el-button>
    </div>

    <!-- 已发布通知列表 -->
    <div class="card section-card">
      <div class="sec-hd">
        <h3>通知列表</h3>
        <span>共 {{ total }} 条</span>
      </div>
      <el-table :data="notifications" v-loading="loading" style="width:100%">
        <el-table-column label="通知内容" min-width="320">
          <template #default="scope">
            <div class="notice-cell">
              <strong>{{ scope.row.title || '未命名通知' }}</strong>
              <span>{{ scope.row.content || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="120">
          <template #default="scope">
            <el-tag size="small" effect="plain">{{ categoryLabel(scope.row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发送对象" min-width="170">
          <template #default="scope">
            <span :class="{ 'all-users': !scope.row.target_user_id }">{{ targetLabel(scope.row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" width="180">
          <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && notifications.length === 0" description="暂无已发布通知" />

      <div v-if="total > pageSize" class="pager-row">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchNotifications"
        />
      </div>
    </div>

    <!-- 通知发布弹窗 -->
    <el-dialog v-model="dialogVisible" title="发布通知" width="min(600px, 92vw)" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="通知标题" required>
          <el-input v-model="form.title" maxlength="100" show-word-limit placeholder="输入简明的通知标题" />
        </el-form-item>
        <el-form-item label="通知分类" required>
          <el-select v-model="form.category" style="width:100%">
            <el-option v-for="option in categoryOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="发送对象" required>
          <el-radio-group v-model="targetType">
            <el-radio value="all">全体用户</el-radio>
            <el-radio value="user">指定用户</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="targetType === 'user'" label="选择用户" required>
          <el-select
            v-model="targetUserId"
            filterable
            clearable
            :loading="usersLoading"
            placeholder="按昵称或手机号选择用户"
            style="width:100%"
          >
            <el-option v-for="user in users" :key="user.id" :label="userOptionLabel(user)" :value="user.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="通知内容" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="5"
            maxlength="2000"
            show-word-limit
            placeholder="输入需要告知游客的完整内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="publishing" @click="publishNotification">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '@/services/api'
import { ElMessage } from 'element-plus'

// 通知列表保留可选用户摘要，以兼容不同的接口序列化形式。
interface NotificationItem {
  id: string | number
  title?: string
  content?: string
  category?: string
  target_user_id?: string | number | null
  target_user?: { phone?: string; nickname?: string }
  target_user_phone?: string
  target_user_nickname?: string
  created_at?: string
}

interface UserItem {
  id: string | number
  phone?: string
  nickname?: string
}

const categoryOptions = [
  { label: '系统通知', value: 'system' },
  { label: '活动通知', value: 'activity' },
  { label: '服务提醒', value: 'service' },
  { label: '安全提醒', value: 'alert' },
]

const notifications = ref<NotificationItem[]>([])
const users = ref<UserItem[]>([])
const loading = ref(false)
const usersLoading = ref(false)
const publishing = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const dialogVisible = ref(false)
const targetType = ref<'all' | 'user'>('all')
const targetUserId = ref<string | number | undefined>()
const form = reactive({ title: '', content: '', category: 'system' })

function errorMessage(error: any, fallback: string) {
  return error.response?.data?.detail || fallback
}

async function fetchNotifications() {
  loading.value = true
  try {
    const { data } = await api.get('/api/admin/notifications', {
      params: { page: page.value, page_size: pageSize },
    })
    notifications.value = Array.isArray(data) ? data : (data.items || [])
    total.value = Array.isArray(data) ? data.length : (data.total || 0)
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '通知数据加载失败'))
  } finally {
    loading.value = false
  }
}

async function fetchUsers() {
  if (users.value.length || usersLoading.value) return
  usersLoading.value = true
  try {
    const { data } = await api.get('/api/users', {
      params: { page: 1, page_size: 100 },
    })
    users.value = Array.isArray(data) ? data : (data.items || [])
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '用户列表加载失败'))
  } finally {
    usersLoading.value = false
  }
}

function openPublish() {
  Object.assign(form, { title: '', content: '', category: 'system' })
  targetType.value = 'all'
  targetUserId.value = undefined
  dialogVisible.value = true
  void fetchUsers()
}

async function publishNotification() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('请填写通知标题和内容')
    return
  }
  if (targetType.value === 'user' && targetUserId.value === undefined) {
    ElMessage.warning('请选择目标用户')
    return
  }

  const payload: { title: string; content: string; category: string; target_user_id?: string | number } = {
    title: form.title.trim(),
    content: form.content.trim(),
    category: form.category,
  }
  if (targetType.value === 'user' && targetUserId.value !== undefined) payload.target_user_id = targetUserId.value

  publishing.value = true
  try {
    await api.post('/api/admin/notifications', payload)
    ElMessage.success('通知已发布')
    dialogVisible.value = false
    page.value = 1
    await fetchNotifications()
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '通知发布失败'))
  } finally {
    publishing.value = false
  }
}

function categoryLabel(category?: string) {
  return categoryOptions.find(option => option.value === category)?.label || category || '未分类'
}

function targetLabel(item: NotificationItem) {
  if (!item.target_user_id) return '全体用户'
  const nickname = item.target_user?.nickname || item.target_user_nickname
  const phone = item.target_user?.phone || item.target_user_phone
  return nickname && phone ? `${nickname}（${phone}）` : nickname || phone || `用户 ${item.target_user_id}`
}

function userOptionLabel(user: UserItem) {
  return user.nickname && user.phone ? `${user.nickname}（${user.phone}）` : user.nickname || user.phone || `用户 ${user.id}`
}

function formatDate(value?: string) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(fetchNotifications)
</script>

<style scoped>
.notifications-page { display:flex; flex-direction:column; gap:24px; }
.page-hd { display:flex; justify-content:space-between; align-items:center; gap:16px; }
.page-hd h2 { font-size:1rem; font-weight:700; color:var(--color-text-primary); }
.page-hd p { margin-top:4px; font-size:.75rem; color:var(--color-text-muted); }
.section-card { padding:20px; }
.sec-hd { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.sec-hd h3 { font-size:.875rem; font-weight:700; color:var(--color-text-primary); }
.sec-hd span { font-size:.75rem; color:var(--color-text-muted); }
.notice-cell { display:flex; flex-direction:column; gap:6px; }
.notice-cell strong { color:var(--color-text-primary); font-size:.875rem; }
.notice-cell span { max-width:520px; color:var(--color-text-secondary); font-size:.75rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.all-users { color:var(--color-primary); font-weight:600; }
.pager-row { display:flex; justify-content:center; margin-top:18px; }
@media (max-width:700px) {
  .page-hd { align-items:flex-start; flex-direction:column; }
}
</style>
