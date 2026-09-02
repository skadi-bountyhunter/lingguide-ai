<template>
  <div class="rag-diagnostics">
    <div class="page-hd">
      <div><h2>🧭 RAG 诊断</h2><p>查看索引对账、检索证据与任务状态</p></div>
      <el-button :loading="loading" @click="loadAll">刷新</el-button>
    </div>

    <div class="card section-card">
      <div class="sec-hd"><h3>索引健康</h3><el-tag :type="health.status === 'healthy' ? 'success' : 'warning'">{{ health.status || '未知' }}</el-tag></div>
      <div class="stats-row">
        <div class="st-item"><span class="st-num">{{ health.canonical_chunks || 0 }}</span><span class="st-desc">Canonical 分块</span></div>
        <div class="st-item"><span class="st-num">{{ health.fts_rows || 0 }}</span><span class="st-desc">FTS 行</span></div>
        <div class="st-item"><span class="st-num">{{ health.vector_rows || 0 }}</span><span class="st-desc">向量</span></div>
        <div class="st-item"><span class="st-num">{{ health.legacy_orphan_estimate || 0 }}</span><span class="st-desc">历史差异</span></div>
      </div>
      <p class="index-meta">版本：{{ health.index_version || '未知' }} · Manifest：{{ health.manifest_id || '未激活' }}</p>
      <p class="index-meta">FTS：{{ health.fts_namespace || '—' }} · Vector：{{ health.vector_collection || '—' }}</p>
      <p v-if="health.checks" class="index-meta">严格校验：{{ passedChecks }}/{{ Object.keys(health.checks).length }} 通过</p>
    </div>

    <div class="card section-card">
      <div class="sec-hd"><h3>最近运行</h3><span class="section-note">最近 {{ runtimeSummary.window_size }} 条已完成交互</span></div>
      <template v-if="runtimeSummary.request_count">
        <div class="stats-row">
          <div class="st-item"><span class="st-num">{{ runtimeSummary.request_count }}</span><span class="st-desc">有效请求</span></div>
          <div class="st-item"><span class="st-num">{{ formatMs(runtimeSummary.end_to_end.p50_ms) }}</span><span class="st-desc">端到端 P50</span></div>
          <div class="st-item"><span class="st-num">{{ formatMs(runtimeSummary.end_to_end.p95_ms) }}</span><span class="st-desc">端到端 P95</span></div>
          <div class="st-item"><span class="st-num">{{ formatMs(runtimeSummary.retrieval.p50_ms) }}</span><span class="st-desc">检索 P50</span></div>
          <div class="st-item"><span class="st-num">{{ formatMs(runtimeSummary.retrieval.p95_ms) }}</span><span class="st-desc">检索 P95</span></div>
          <div class="st-item"><span class="st-num">{{ formatPercent(runtimeSummary.degraded.rate) }}</span><span class="st-desc">降级率</span></div>
          <div class="st-item"><span class="st-num">{{ formatPercent(runtimeSummary.channel_abnormal.rate) }}</span><span class="st-desc">通道异常率</span></div>
        </div>
        <p class="index-meta">记录范围：{{ formatDate(runtimeSummary.first_recorded_at) }} 至 {{ formatDate(runtimeSummary.last_recorded_at) }}</p>
        <div class="channel-grid">
          <div v-for="channel in channelMetrics" :key="channel.key" class="channel-item">
            <span class="channel-name">{{ channel.label }}</span>
            <strong>{{ formatMs(channel.data.avg_latency_ms) }}</strong>
            <span>{{ channel.data.sample_count }} 次执行</span>
          </div>
        </div>
      </template>
      <el-empty v-else description="暂无带检索轨迹的已完成交互" :image-size="64" />
    </div>

    <div class="card section-card">
      <div class="sec-hd"><h3>测试检索</h3></div>
      <div class="test-row">
        <el-input v-model="query" maxlength="500" placeholder="输入要诊断的问题" @keyup.enter="runSearch" />
        <el-button type="primary" :loading="searching" @click="runSearch">检索</el-button>
      </div>
      <div v-if="searchResult" class="result-meta">路由：{{ searchResult.retrieval?.chosen_route || searchResult.retrieval?.route }} · 追踪号：{{ searchResult.trace_id }}</div>
      <el-table v-if="searchResult?.results?.length" :data="searchResult.results" style="width:100%;margin-top:12px">
        <el-table-column prop="rank" label="#" width="55" />
        <el-table-column prop="source" label="来源" width="180" />
        <el-table-column prop="confidence" label="置信度" width="95" />
        <el-table-column prop="content" label="Canonical 证据" show-overflow-tooltip />
      </el-table>
      <el-empty v-else-if="searchResult" description="没有通过置信度过滤的证据" />
    </div>

    <div class="card section-card">
      <div class="sec-hd"><h3>索引任务</h3></div>
      <el-table :data="jobs" style="width:100%">
        <el-table-column prop="id" label="任务" min-width="180" />
        <el-table-column prop="job_type" label="类型" width="110" />
        <el-table-column prop="state" label="状态" width="100" />
        <el-table-column prop="attempt" label="尝试" width="70" />
        <el-table-column prop="error_message" label="错误" show-overflow-tooltip />
      </el-table>
      <el-empty v-if="!jobs.length" description="暂无索引任务" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '@/services/api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const searching = ref(false)
const query = ref('')
interface LatencyMetric {
  sample_count: number
  p50_ms: number
  p95_ms: number
}

interface ChannelMetric {
  sample_count: number
  avg_latency_ms: number | null
}

interface RuntimeSummary {
  window_size: number
  request_count: number
  first_recorded_at: string | null
  last_recorded_at: string | null
  end_to_end: LatencyMetric
  retrieval: LatencyMetric
  degraded: { count: number; rate: number }
  channel_abnormal: { count: number; rate: number }
  channels: Record<string, ChannelMetric>
}

const CHANNELS = [
  { key: 'structured', label: 'Structured' },
  { key: 'fts', label: 'FTS' },
  { key: 'bge', label: 'BGE' },
  { key: 'weather', label: 'Weather' },
  { key: 'llm', label: 'LLM' },
] as const

const EMPTY_CHANNEL: ChannelMetric = { sample_count: 0, avg_latency_ms: null }
const EMPTY_SUMMARY: RuntimeSummary = {
  window_size: 100,
  request_count: 0,
  first_recorded_at: null,
  last_recorded_at: null,
  end_to_end: { sample_count: 0, p50_ms: 0, p95_ms: 0 },
  retrieval: { sample_count: 0, p50_ms: 0, p95_ms: 0 },
  degraded: { count: 0, rate: 0 },
  channel_abnormal: { count: 0, rate: 0 },
  channels: {},
}

const health = ref<Record<string, any>>({})
const jobs = ref<any[]>([])
const searchResult = ref<any>(null)
const runtimeSummary = ref<RuntimeSummary>(EMPTY_SUMMARY)
const passedChecks = computed(() => Object.values(health.value.checks || {}).filter(Boolean).length)
const channelMetrics = computed(() => CHANNELS.map(channel => ({
  ...channel,
  data: runtimeSummary.value.channels[channel.key] || EMPTY_CHANNEL,
})))

function formatMs(value: number | null | undefined) {
  return value == null ? '—' : `${Math.round(value)} ms`
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

async function loadAll() {
  loading.value = true
  try {
    const [healthResponse, jobsResponse, runtimeResponse] = await Promise.all([
      api.get('/api/rag-admin/health'),
      api.get('/api/rag-admin/jobs'),
      api.get<RuntimeSummary>('/api/rag-admin/runtime-summary'),
    ])
    health.value = healthResponse.data
    jobs.value = jobsResponse.data
    runtimeSummary.value = runtimeResponse.data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'RAG 诊断数据加载失败')
  } finally {
    loading.value = false
  }
}

async function runSearch() {
  if (!query.value.trim()) return
  searching.value = true
  try {
    const { data } = await api.post('/api/rag-admin/retrieval-test', { query: query.value.trim(), top_k: 5 })
    searchResult.value = data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '检索诊断失败')
  } finally {
    searching.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.rag-diagnostics { display:flex; flex-direction:column; gap:24px; }
.page-hd { display:flex; justify-content:space-between; align-items:center; }
.page-hd h2 { font-size:1rem; font-weight:700; color:var(--color-text-primary); }
.page-hd p { font-size:.75rem; color:var(--color-text-muted); margin-top:4px; }
.section-card { padding:20px; }
.sec-hd { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.sec-hd h3 { font-size:.875rem; font-weight:700; color:var(--color-text-primary); }
.section-note { color:var(--color-text-muted); font-size:.75rem; }
.stats-row { display:flex; gap:40px; flex-wrap:wrap; }
.st-item { display:flex; flex-direction:column; align-items:center; min-width:90px; }
.st-num { font-size:1.5rem; font-weight:700; color:var(--color-text-primary); }
.st-desc { font-size:.75rem; color:var(--color-text-muted); margin-top:4px; }
.test-row { display:flex; gap:10px; }
.test-row .el-input { flex:1; }
.result-meta { margin-top:12px; color:var(--color-text-muted); font-size:12px; }
.index-meta { margin:10px 0 0; color:var(--color-text-muted); font-size:12px; overflow-wrap:anywhere; }
.channel-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(128px, 1fr)); gap:10px; margin-top:16px; }
.channel-item { display:flex; flex-direction:column; gap:4px; padding:12px; border:1px solid var(--color-primary-border); border-radius:10px; background:var(--color-primary-bg); }
.channel-item strong { color:var(--color-text-primary); font-size:.9rem; }
.channel-item span { color:var(--color-text-muted); font-size:.75rem; }
.channel-name { color:var(--color-primary) !important; font-weight:600; }
</style>
