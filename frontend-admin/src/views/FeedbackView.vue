<template>
  <div class="feedback-page animate-fade-up">
    <div class="page-hd">
      <div><h2>💬 反馈管理</h2><p>查看游客意见并跟进处理结果</p></div>
      <div class="hd-stats">共 <b>{{ total }}</b> 条反馈</div>
    </div>

    <!-- 状态筛选与反馈列表 -->
    <div class="card section-card">
      <div class="toolbar">
        <div class="sec-title">
          <h3>反馈列表</h3>
          <span>按处理状态筛选</span>
        </div>
        <el-select v-model="statusFilter" class="status-filter" @change="handleFilterChange">
          <el-option label="全部状态" value="" />
          <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
      </div>

      <el-table :data="feedbacks" v-loading="loading" style="width:100%">
        <el-table-column label="反馈内容" min-width="280">
          <template #default="scope">
            <div class="content-cell">
              <span class="content-title">{{ scope.row.content || '—' }}</span>
              <span>{{ categoryLabel(scope.row.category) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="提交用户" min-width="150">
          <template #default="scope">{{ userLabel(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)" size="small">{{ statusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="180">
          <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" text @click="openDetail(scope.row)">查看处理</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && feedbacks.length === 0" description="当前筛选下暂无反馈" />

      <div v-if="total > pageSize" class="pager-row">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchFeedbacks"
        />
      </div>
    </div>

    <!-- 反馈详情与处理弹窗 -->
    <el-dialog v-model="dialogVisible" title="反馈详情" width="min(620px, 92vw)" :close-on-click-modal="false">
      <div v-if="selectedFeedback" class="detail-panel">
        <div class="detail-meta">
          <div><span>提交用户</span><strong>{{ userLabel(selectedFeedback) }}</strong></div>
          <div><span>反馈类型</span><strong>{{ categoryLabel(selectedFeedback.category) }}</strong></div>
          <div><span>提交时间</span><strong>{{ formatDate(selectedFeedback.created_at) }}</strong></div>
        </div>
        <div class="feedback-content">
          <span>反馈内容</span>
          <p>{{ selectedFeedback.content || '—' }}</p>
        </div>
        <el-form label-position="top">
          <el-form-item label="处理状态" required>
            <el-select v-model="editStatus" style="width:100%">
              <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="管理员回复">
            <el-input
              v-model="adminReply"
              type="textarea"
              :rows="4"
              maxlength="1000"
              show-word-limit
              placeholder="填写回复内容或处理说明"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveFeedback">保存处理结果</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/services/api'
import { ElMessage } from 'element-plus'

// 反馈字段兼容接口返回的用户摘要信息。
interface FeedbackItem {
  id: string | number
  content?: string
  category?: string
  status?: string
  admin_reply?: string | null
  created_at?: string
  phone?: string
  nickname?: string
  user_phone?: string
  user_nickname?: string
  user?: { phone?: string; nickname?: string }
}

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' },
]

const feedbacks = ref<FeedbackItem[]>([])
const loading = ref(false)
const saving = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const statusFilter = ref('')
const dialogVisible = ref(false)
const selectedFeedback = ref<FeedbackItem | null>(null)
const editStatus = ref('pending')
const adminReply = ref('')

function errorMessage(error: any, fallback: string) {
  return error.response?.data?.detail || fallback
}

async function fetchFeedbacks() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page: page.value, page_size: pageSize }
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await api.get('/api/admin/feedback', { params })
    feedbacks.value = Array.isArray(data) ? data : (data.items || [])
    total.value = Array.isArray(data) ? data.length : (data.total || 0)
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '反馈数据加载失败'))
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  page.value = 1
  void fetchFeedbacks()
}

function openDetail(row: FeedbackItem) {
  selectedFeedback.value = row
  editStatus.value = row.status || 'pending'
  adminReply.value = row.admin_reply || ''
  dialogVisible.value = true
}

async function saveFeedback() {
  if (!selectedFeedback.value) return
  saving.value = true
  try {
    await api.patch(
      `/api/admin/feedback/${selectedFeedback.value.id}`,
      { status: editStatus.value, admin_reply: adminReply.value.trim() },
    )
    ElMessage.success('反馈处理结果已更新')
    dialogVisible.value = false
    await fetchFeedbacks()
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '反馈更新失败'))
  } finally {
    saving.value = false
  }
}

function statusLabel(status?: string) {
  return statusOptions.find(option => option.value === status)?.label || status || '未知'
}

function statusType(status?: string): '' | 'info' | 'success' | 'warning' | 'danger' {
  return { pending: 'warning', processing: 'info', resolved: 'success', closed: 'info' }[status || ''] as '' | 'info' | 'success' | 'warning' | 'danger' || ''
}

function categoryLabel(category?: string) {
  return { suggestion: '意见建议', complaint: '问题投诉', consultation: '咨询', praise: '表扬', other: '其他' }[category || ''] || category || '未分类'
}

function userLabel(item: FeedbackItem) {
  const nickname = item.user?.nickname || item.user_nickname || item.nickname
  const phone = item.user?.phone || item.user_phone || item.phone
  return nickname && phone ? `${nickname}（${phone}）` : nickname || phone || '匿名用户'
}

function formatDate(value?: string) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(fetchFeedbacks)
</script>

<style scoped>
.feedback-page { display:flex; flex-direction:column; gap:24px; }
.page-hd { display:flex; justify-content:space-between; align-items:center; gap:16px; }
.page-hd h2 { font-size:1rem; font-weight:700; color:var(--color-text-primary); }
.page-hd p { margin-top:4px; font-size:.75rem; color:var(--color-text-muted); }
.hd-stats { font-size:.875rem; color:var(--color-text-secondary); }
.hd-stats b { color:var(--color-primary); }
.section-card { padding:20px; }
.toolbar { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:16px; }
.sec-title { display:flex; align-items:baseline; gap:10px; }
.sec-title h3 { font-size:.875rem; font-weight:700; color:var(--color-text-primary); }
.sec-title span { font-size:.75rem; color:var(--color-text-muted); }
.status-filter { width:150px; }
.content-cell { display:flex; flex-direction:column; gap:5px; }
.content-title { color:var(--color-text-primary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.content-cell span:last-child { font-size:.7rem; color:var(--color-text-muted); }
.pager-row { display:flex; justify-content:center; margin-top:18px; }
.detail-panel { display:flex; flex-direction:column; gap:20px; }
.detail-meta { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; }
.detail-meta div { padding:12px; border-radius:10px; background:var(--color-bg-elevated); }
.detail-meta span, .feedback-content > span { display:block; margin-bottom:5px; font-size:.7rem; color:var(--color-text-muted); }
.detail-meta strong { display:block; font-size:.8rem; font-weight:600; color:var(--color-text-primary); overflow-wrap:anywhere; }
.feedback-content { padding:14px 16px; border-left:3px solid var(--color-primary); border-radius:0 10px 10px 0; background:var(--color-primary-bg); }
.feedback-content p { color:var(--color-text-primary); font-size:.875rem; line-height:1.7; white-space:pre-wrap; overflow-wrap:anywhere; }
@media (max-width:700px) {
  .page-hd, .toolbar { align-items:flex-start; flex-direction:column; }
  .status-filter { width:100%; }
  .detail-meta { grid-template-columns:1fr; }
}
</style>
