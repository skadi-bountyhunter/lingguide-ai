<template>
  <div class="knowledge animate-fade-up">
    <div class="page-hd">
      <div><h2>📚 知识库管理</h2><p>管理景区知识文档与常见问答</p></div>
      <el-upload :before-upload="handleUpload" :show-file-list="false" accept=".docx,.txt,.md">
        <el-button type="primary"><el-icon><Upload /></el-icon>上传文档</el-button>
      </el-upload>
    </div>

    <!-- 文档列表 -->
    <div class="card section-card">
      <div class="sec-hd"><h3>📄 知识文档</h3></div>
      <el-table :data="documents" v-loading="loading" style="width:100%">
        <el-table-column prop="filename" label="文件名" />
        <el-table-column prop="file_type" label="类型" width="80" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="s"><el-tag :type="s.row.status==='ready'||s.row.status==='done'?'success':'warning'" size="small">{{ statusLabel(s.row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数" width="80" />
        <el-table-column label="错误信息" min-width="180" show-overflow-tooltip>
          <template #default="s">{{ s.row.error_message || '—' }}</template>
        </el-table-column>
        <el-table-column prop="uploaded_at" label="上传时间" width="170" />
        <el-table-column label="操作" width="120">
          <template #default="s"><el-button type="danger" size="small" text @click="handleDelete(s.row.id)">删除</el-button></template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading&&documents.length===0" description="暂无文档" />
    </div>

    <!-- FAQ 管理 -->
    <div class="card section-card">
      <div class="sec-hd"><h3>❓ 常见问答 (FAQ)</h3><el-button size="small" @click="openCreate"><el-icon><Plus /></el-icon>添加</el-button></div>
      <el-table :data="faqs" style="width:100%">
        <el-table-column prop="question" label="问题" min-width="200" />
        <el-table-column prop="answer" label="答案" min-width="300" show-overflow-tooltip />
        <el-table-column label="实体" min-width="150"><template #default="s">{{ s.row.entities?.join('、') }}</template></el-table-column>
        <el-table-column prop="intent" label="意图" width="150" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="s">
            <el-button type="primary" size="small" text @click="openEdit(s.row)">编辑</el-button>
            <el-button type="danger" size="small" text @click="handleDeleteFaq(s.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 统计 -->
    <div class="card section-card">
      <div class="sec-hd"><h3>📊 知识库状态</h3></div>
      <div class="stats-row">
        <div class="st-item"><span class="st-num">{{ stats.chunk_count||0 }}</span><span class="st-desc">知识分块</span></div>
        <div class="st-item"><span class="st-num">{{ faqs.length }}</span><span class="st-desc">FAQ 问答</span></div>
      </div>
    </div>

    <!-- FAQ 新增/编辑对话框 -->
    <el-dialog v-model="showFaqDialog" :title="editingFaq.id ? '编辑 FAQ' : '添加 FAQ'" width="560px" :close-on-click-modal="false">
      <el-form :model="editingFaq" label-position="top">
        <el-form-item label="问题" required><el-input v-model="editingFaq.question" placeholder="如：灵山大佛有多高？" /></el-form-item>
        <el-form-item label="答案" required><el-input v-model="editingFaq.answer" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="实体（空格、逗号或顿号分隔）" required><el-input v-model="editingFaq.entities" placeholder="如：九龙灌浴 九龙浴佛" /></el-form-item>
        <el-form-item label="意图" required><el-input v-model="editingFaq.intent" placeholder="如：performance_time" /></el-form-item>
        <el-form-item label="意图关键词（空格、逗号或顿号分隔）" required><el-input v-model="editingFaq.intent_keywords" placeholder="如：表演时间 几点 什么时候" /></el-form-item>
        <el-form-item label="精确问题（可选，空格、逗号或顿号分隔）"><el-input v-model="editingFaq.exact_questions" placeholder="如：九龙灌浴几点表演" /></el-form-item>
        <el-form-item label="兼容检索文本（可选）"><el-input v-model="editingFaq.match_text" placeholder="历史兼容字段，不参与高置信 FAQ 命中" /></el-form-item>
        <el-form-item label="标签">
          <el-select v-model="editingFaq.tags" multiple placeholder="选择标签">
            <el-option label="景点" value="景点"/><el-option label="历史" value="历史"/><el-option label="交通" value="交通"/>
            <el-option label="票务" value="票务"/><el-option label="餐饮" value="餐饮"/><el-option label="攻略" value="攻略"/>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="showFaqDialog=false">取消</el-button><el-button type="primary" :loading="saving" @click="handleSaveFaq">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/services/api'

interface FaqForm {
  id?: number
  question: string
  answer: string
  match_text: string
  tags: string[]
  entities: string
  intent: string
  intent_keywords: string
  exact_questions: string
}

function emptyFaq(): FaqForm {
  return { question:'', answer:'', match_text:'', tags:[], entities:'', intent:'', intent_keywords:'', exact_questions:'' }
}

const documents = ref<any[]>([])
const faqs = ref<any[]>([])
const stats = ref<any>({})
const loading = ref(false)
const saving = ref(false)
const showFaqDialog = ref(false)
const editingFaq = reactive<FaqForm>(emptyFaq())

function splitTerms(value: string) {
  return [...new Set(value.split(/[\s,，、]+/).map(item => item.trim()).filter(Boolean))]
}

function openCreate() {
  Object.assign(editingFaq, emptyFaq())
  showFaqDialog.value = true
}

function openEdit(row: any) {
  Object.assign(editingFaq, {
    id: row.id,
    question: row.question || '',
    answer: row.answer || '',
    match_text: row.match_text || '',
    tags: [...(row.tags || [])],
    entities: (row.entities || []).join(' '),
    intent: row.intent || '',
    intent_keywords: (row.intent_keywords || []).join(' '),
    exact_questions: (row.exact_questions || []).join(' '),
  })
  showFaqDialog.value = true
}

onMounted(() => { fetchAll() })

async function fetchAll() {
  try {
    const [docRes, faqRes, statRes] = await Promise.all([
      api.get('/api/knowledge/documents'), api.get('/api/knowledge/faqs'), api.get('/api/knowledge/stats'),
    ])
    documents.value = docRes.data; faqs.value = faqRes.data; stats.value = statRes.data
  } catch { ElMessage.error('知识库数据加载失败') }
}

async function handleUpload(file: File) {
  loading.value = true
  try {
    const fd = new FormData(); fd.append('file', file)
    await api.post('/api/knowledge/documents/upload', fd); ElMessage.success('文档上传并处理成功'); await fetchAll()
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || '上传失败') }
  finally { loading.value = false }
  return false
}

async function handleDelete(documentId: string) {
  try { await api.delete(`/api/knowledge/documents/${documentId}`); ElMessage.success('删除成功'); await fetchAll() }
  catch { ElMessage.error('删除失败') }
}

function errorMessage(error: any, fallback: string) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  if (Array.isArray(detail)) return detail.map(item => item.msg).join('；') || fallback
  return fallback
}

async function handleSaveFaq() {
  const entities = splitTerms(editingFaq.entities)
  const intentKeywords = splitTerms(editingFaq.intent_keywords)
  const exactQuestions = splitTerms(editingFaq.exact_questions)
  if (!editingFaq.question.trim() || !editingFaq.answer.trim() || !entities.length || !editingFaq.intent.trim() || !intentKeywords.length) {
    ElMessage.warning('请填写问题、答案、实体、意图和意图关键词')
    return
  }
  const payload = {
    question: editingFaq.question.trim(), answer: editingFaq.answer.trim(), match_text: editingFaq.match_text.trim(),
    tags: editingFaq.tags, entities, intent: editingFaq.intent.trim(), intent_keywords: intentKeywords,
    exact_questions: exactQuestions,
  }
  saving.value = true
  try {
    if (editingFaq.id) await api.put(`/api/knowledge/faqs/${editingFaq.id}`, payload)
    else await api.post('/api/knowledge/faqs', payload)
    ElMessage.success(editingFaq.id ? 'FAQ 更新成功' : 'FAQ 添加成功')
    showFaqDialog.value = false
    await fetchAll()
  } catch (e: any) {
    const detail = e.response?.data?.detail
    if (detail?.conflicts?.length) {
      const conflictText = detail.conflicts.map((item: any) => {
        const fields = [...(item.shared_questions || []), ...(item.shared_entities || []), ...(item.shared_intent_keywords || [])]
        return `FAQ ${item.existing_id}: ${fields.join('、') || '规则冲突'}`
      }).join('；')
      ElMessage.error(`${detail.message || 'FAQ 规则冲突'}：${conflictText}`)
    } else {
      ElMessage.error(errorMessage(e, editingFaq.id ? 'FAQ 更新失败' : 'FAQ 添加失败'))
    }
  }
  finally { saving.value = false }
}

async function handleDeleteFaq(id: number) {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确定要删除这条 FAQ 吗？', '确认删除', { type: 'warning' })
    await api.delete(`/api/knowledge/faqs/${id}`); ElMessage.success('删除成功'); await fetchAll()
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(errorMessage(e, '删除失败'))
  }
}

function statusLabel(s: string) { return {uploaded:'已上传',processing:'处理中',ready:'已完成',done:'已完成',failed:'失败',deleted:'已删除'}[s]||s }
</script>

<style scoped>
.knowledge { display:flex; flex-direction:column; gap:24px; }
.page-hd { display:flex; justify-content:space-between; align-items:center; }
.page-hd h2 { font-size:1rem; font-weight:700; color:var(--color-text-primary); }
.page-hd p { font-size:0.75rem; color:var(--color-text-muted); margin-top:4px; }
.section-card { padding:20px; }
.sec-hd { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.sec-hd h3 { font-size:0.875rem; font-weight:700; color:var(--color-text-primary); }
.stats-row { display:flex; gap:40px; }
.st-item { display:flex; flex-direction:column; align-items:center; }
.st-num { font-size:1.5rem; font-weight:700; color:var(--color-text-primary); }
.st-desc { font-size:0.85rem; color:var(--color-text-muted); margin-top:4px; }
</style>
