<template>
  <div class="dashboard-page animate-fade-up">
    <header class="dashboard-hero">
      <div class="hero-copy">
        <span class="hero-kicker">LINGGUIDE · OPERATIONS</span>
        <h2>运营交互总览</h2>
        <p>所有指标均由已落库的游客交互记录实时聚合，按中国标准时间统计。</p>
      </div>
      <div class="hero-tools">
        <div class="period-switch" role="group" aria-label="统计周期">
          <button
            v-for="item in periodOptions"
            :key="item.value"
            type="button"
            :class="{ active: period === item.value }"
            :disabled="loading"
            @click="changePeriod(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
        <el-button plain :loading="loading" @click="loadOverview">
          <el-icon><RefreshRight /></el-icon>刷新数据
        </el-button>
      </div>
      <div class="hero-meta">
        <span class="live-dot" :class="{ paused: Boolean(loadError) }" />
        <span>{{ dataStatus }}</span>
        <span class="meta-divider" />
        <span>{{ periodDescription }}</span>
      </div>
    </header>

    <section v-if="loading && !overview" class="loading-grid" aria-label="正在加载运营数据">
      <div v-for="index in 4" :key="index" class="skeleton-card" />
    </section>

    <template v-else-if="overview">
      <section class="metric-grid" :class="{ stale: Boolean(loadError) }">
        <article v-for="metric in metrics" :key="metric.label" class="metric-card card">
          <div class="metric-topline">
            <span class="metric-icon" :class="metric.tone"><el-icon><component :is="metric.icon" /></el-icon></span>
            <span class="metric-source">{{ metric.source }}</span>
          </div>
          <strong>{{ metric.value }}</strong>
          <span class="metric-label">{{ metric.label }}</span>
          <p>{{ metric.note }}</p>
        </article>
        <article class="metric-card satisfaction-metric-card card">
          <div class="section-header compact">
            <div>
              <span class="section-kicker">SATISFACTION</span>
              <h3>整体满意度</h3>
            </div>
          </div>
          <SatisfactionBall :period="period" />
        </article>
      </section>

      <p v-if="loadError" class="refresh-warning">
        <el-icon><WarningFilled /></el-icon>{{ loadError }} 当前保留上次成功加载的数据。
      </p>

      <section class="chart-grid" :class="{ stale: Boolean(loadError) }">
        <article class="chart-card card">
          <div class="section-header">
            <div>
              <span class="section-kicker">ACTIVITY</span>
              <h3>交互趋势</h3>
              <p>{{ trendDescription }}</p>
            </div>
            <span class="section-total">{{ overview.summary.interaction_count.toLocaleString() }} 条</span>
          </div>
          <v-chart v-if="hasInteractionData" class="chart" :option="interactionChartOption" autoresize />
          <el-empty v-else description="当前范围暂无交互记录" :image-size="78" />
        </article>

        <article class="chart-card card">
          <div class="section-header">
            <div>
              <span class="section-kicker">EMOTION SIGNAL</span>
              <h3>平均输入情绪得分</h3>
              <p>基于游客输入的情绪分析，非满意度或人工评价。</p>
            </div>
            <span class="section-total">{{ formattedEmotion }}</span>
          </div>
          <v-chart v-if="hasEmotionData" class="chart" :option="emotionChartOption" autoresize />
          <el-empty v-else description="当前范围暂无有效情绪样本" :image-size="78" />
        </article>
      </section>

      <section class="analytics3d-grid" :class="{ stale: Boolean(loadError) }">
        <article class="analytics3d-card analytics3d-card--wide card">
          <div class="section-header compact">
            <div>
              <span class="section-kicker">VISITOR PINS · HEATMAP</span>
              <h3>游客标记热力图</h3>
              <p>游客在景区地图打点的位置分布，反映实际停留和关注区域。</p>
            </div>
          </div>
          <PinsHeatmap :days="30" />
        </article>

        <article class="analytics3d-card analytics3d-card--wide card">
          <div class="section-header">
            <div>
              <span class="section-kicker">EMOTION · SPACETIME MATRIX</span>
              <h3>情绪时空强度矩阵</h3>
              <p>各景点分时段情绪分均值，须游客发起含景点上下文的对话后才有数据。</p>
            </div>
          </div>
          <EmotionBar3D />
        </article>
      </section>

      <section class="detail-grid" :class="{ stale: Boolean(loadError) }">
        <article class="questions-card card">
          <div class="section-header">
            <div>
              <span class="section-kicker">REPEATED QUESTIONS</span>
              <h3>重复问句 TOP 8</h3>
              <p>按完整原始问句的真实出现次数排序。</p>
            </div>
            <span class="section-total">{{ overview.top_questions.length }} 项</span>
          </div>
          <el-empty v-if="!overview.top_questions.length" description="当前范围暂无重复问句" :image-size="72" />
          <ol v-else class="question-list">
            <li v-for="(question, index) in overview.top_questions" :key="question.question">
              <span class="question-rank" :class="{ top: index < 3 }">{{ String(index + 1).padStart(2, '0') }}</span>
              <p :title="question.question">{{ question.question }}</p>
              <b>{{ question.count }}<small>次</small></b>
            </li>
          </ol>
        </article>

        <article class="analytics3d-card wordcloud-card card">
          <div class="section-header compact">
            <div>
              <span class="section-kicker">KEYWORD CLOUD</span>
              <h3>游客反馈词云</h3>
              <p>游客问句 jieba 分词高频词。</p>
            </div>
          </div>
          <FeedbackWordCloud :period="period" />
        </article>

        <article class="activity-card card">
          <div class="section-header compact">
            <div>
              <span class="section-kicker">RECENT ACTIVITY</span>
              <h3>最近活动</h3>
              <p>最近 {{ overview.activity.window_minutes }} 分钟的真实落库记录。</p>
            </div>
          </div>
          <div class="activity-values">
            <div>
              <span><el-icon><UserFilled /></el-icon>活跃会话</span>
              <strong>{{ overview.activity.active_session_count }}</strong>
            </div>
            <div>
              <span><el-icon><ChatDotRound /></el-icon>交互次数</span>
              <strong>{{ overview.activity.interaction_count }}</strong>
            </div>
          </div>
          <dl class="mode-summary">
            <div v-for="item in modeDistribution" :key="item.mode">
              <dt><i :style="{ background: modeColor(item.mode) }" />{{ modeLabel(item.mode) }}</dt>
              <dd>{{ item.count }} 条</dd>
            </div>
          </dl>
        </article>

        <article class="mode-card card">
          <div class="section-header compact">
            <div>
              <span class="section-kicker">CHANNEL MIX</span>
              <h3>交互方式构成</h3>
              <p>当前统计范围内文本、语音及其他方式的实际分布。</p>
            </div>
          </div>
          <div class="mode-list">
            <div v-for="item in modeDistribution" :key="item.mode" class="mode-row">
              <div class="mode-head">
                <span><i :style="{ background: modeColor(item.mode) }" />{{ modeLabel(item.mode) }}</span>
                <b>{{ item.count }} 条 <em>{{ ratioText(item.ratio) }}</em></b>
              </div>
              <div class="mode-track"><span :style="{ width: ratioWidth(item.ratio), background: modeColor(item.mode) }" /></div>
            </div>
          </div>
        </article>
      </section>

      <el-collapse class="data-collapse">
        <el-collapse-item title="查看图表明细数据" name="data-table">
          <div class="data-table-wrap">
            <table>
              <thead><tr><th>时间桶</th><th>交互次数</th><th>平均输入情绪得分</th><th>情绪样本数</th></tr></thead>
              <tbody>
                <tr v-for="(bucket, index) in overview.interaction_trend.buckets" :key="bucket.start">
                  <td>{{ bucket.label }}</td>
                  <td>{{ bucket.count }}</td>
                  <td>{{ scoreText(overview.emotion_trend.buckets[index]?.avg_score) }}</td>
                  <td>{{ overview.emotion_trend.buckets[index]?.sample_count ?? 0 }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </el-collapse-item>
      </el-collapse>
    </template>

    <section v-else class="empty-state card">
      <el-empty description="暂未能加载运营数据">
        <el-button type="primary" @click="loadOverview">重新加载</el-button>
      </el-empty>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import type { EChartsOption } from 'echarts'
import { BarChart, LineChart } from 'echarts/charts'
import { AriaComponent, GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ChatDotRound, Connection, Timer, TrendCharts } from '@element-plus/icons-vue'
import api from '@/services/api'
import EmotionBar3D from '@/components/charts/EmotionBar3D.vue'
import SatisfactionBall from '@/components/charts/SatisfactionBall.vue'
import FeedbackWordCloud from '@/components/charts/FeedbackWordCloud.vue'
import PinsHeatmap from '@/components/charts/PinsHeatmap.vue'

use([AriaComponent, BarChart, CanvasRenderer, GridComponent, LineChart, TooltipComponent])

type Period = 'today' | '7d' | '30d'
type Mode = 'text' | 'voice' | 'other'

interface ValueMetric {
  value: number | null
  sample_count: number
}

interface TrendBucket {
  start: string
  end: string
  label: string
  count?: number
  avg_score?: number | null
  sample_count?: number
}

interface ModeItem {
  mode: Mode
  count: number
  ratio: number | null
}

interface DashboardOverview {
  period: Period
  timezone: string
  generated_at: string
  range: { start: string; end: string; end_exclusive: boolean }
  summary: {
    interaction_count: number
    session_count: number
    avg_thinking_time_ms: ValueMetric
    avg_emotion_score: ValueMetric
  }
  activity: {
    window_minutes: number
    active_session_count: number
    interaction_count: number
  }
  mode_distribution: { total: number; items: ModeItem[] }
  interaction_trend: { granularity: 'hour' | 'day'; buckets: TrendBucket[] }
  emotion_trend: { granularity: 'hour' | 'day'; buckets: TrendBucket[] }
  top_questions: Array<{ question: string; count: number }>
}

const periodOptions: Array<{ value: Period; label: string }> = [
  { value: 'today', label: '今日' },
  { value: '7d', label: '近 7 天' },
  { value: '30d', label: '近 30 天' },
]

const period = ref<Period>('today')
const overview = ref<DashboardOverview | null>(null)
const loading = ref(false)
const loadError = ref('')
let requestSequence = 0
let refreshTimer: ReturnType<typeof setInterval> | undefined

const modeDistribution = computed(() => overview.value?.mode_distribution.items || [])
const hasInteractionData = computed(() => Boolean(overview.value?.summary.interaction_count))
const hasEmotionData = computed(() => overview.value?.emotion_trend.buckets.some((bucket) => bucket.avg_score !== null && bucket.avg_score !== undefined))
const formattedEmotion = computed(() => scoreText(overview.value?.summary.avg_emotion_score.value))
const dataStatus = computed(() => {
  if (loadError.value) return '最近一次刷新失败'
  if (!overview.value) return '等待加载数据'
  return `已同步 · ${formatDateTime(overview.value.generated_at)}`
})
const periodDescription = computed(() => {
  if (!overview.value) return '统计范围：—'
  return `统计范围：${formatRange(overview.value.range.start, overview.value.range.end)}`
})
const trendDescription = computed(() => overview.value?.interaction_trend.granularity === 'hour'
  ? '按小时汇总，展示今天已开始的时段。'
  : '按中国自然日汇总，今天统计截至本次刷新时刻。')

const metrics = computed(() => {
  const summary = overview.value?.summary
  if (!summary) return []
  return [
    { icon: ChatDotRound, label: '交互次数', value: summary.interaction_count.toLocaleString(), note: '统计范围内成功落库的交互记录。', source: '真实交互', tone: 'green' },
    { icon: Connection, label: '服务会话', value: summary.session_count.toLocaleString(), note: '按 session_id 去重，不等同于实名游客。', source: '去重统计', tone: 'jade' },
    { icon: Timer, label: '平均处理耗时', value: formatDuration(summary.avg_thinking_time_ms.value), note: metricSampleNote(summary.avg_thinking_time_ms, '条有效时长样本'), source: '端到端耗时', tone: 'amber' },
    { icon: TrendCharts, label: '平均输入情绪得分', value: scoreText(summary.avg_emotion_score.value), note: metricSampleNote(summary.avg_emotion_score, '条有效情绪样本'), source: '输入情绪', tone: 'lake' },
  ]
})

const interactionChartOption = computed<EChartsOption>(() => {
  const buckets = overview.value?.interaction_trend.buckets || []
  return {
    animationDuration: 500,
    aria: { enabled: true, description: '交互趋势柱状图，展示所选周期各时间桶的真实交互次数。' },
    grid: { left: 12, right: 12, top: 24, bottom: 28, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#18312d',
      borderWidth: 0,
      textStyle: { color: '#ffffff' },
      formatter: (params: unknown) => {
        const item = Array.isArray(params) ? params[0] as { axisValue: string; value: number } : params as { axisValue: string; value: number }
        return `${item.axisValue}<br/>交互次数：<b>${item.value}</b>`
      },
    },
    xAxis: {
      type: 'category',
      data: buckets.map((bucket) => bucket.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dce6df' } },
      axisLabel: { color: '#7d8b84', fontSize: 10, interval: buckets.length > 12 ? 'auto' : 0 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: 'rgba(24, 49, 45, 0.08)' } },
      axisLabel: { color: '#8b9a92', fontSize: 10 },
    },
    series: [{
      type: 'bar',
      name: '交互次数',
      data: buckets.map((bucket) => bucket.count || 0),
      barMaxWidth: 24,
      itemStyle: { color: '#008300', borderRadius: [4, 4, 0, 0] },
      emphasis: { itemStyle: { color: '#006F00' } },
    }],
  }
})

const emotionChartOption = computed<EChartsOption>(() => {
  const buckets = overview.value?.emotion_trend.buckets || []
  return {
    animationDuration: 500,
    aria: { enabled: true, description: '平均输入情绪得分折线图，得分范围为零到一，缺少样本的时间桶不会连线。' },
    grid: { left: 12, right: 12, top: 24, bottom: 28, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#18312d',
      borderWidth: 0,
      textStyle: { color: '#ffffff' },
      formatter: (params: unknown) => {
        const item = Array.isArray(params) ? params[0] as { dataIndex: number; axisValue: string; value: number | null } : params as { dataIndex: number; axisValue: string; value: number | null }
        const bucket = buckets[item.dataIndex]
        return `${item.axisValue}<br/>平均得分：<b>${scoreText(item.value)}</b><br/>有效样本：${bucket?.sample_count || 0} 条`
      },
    },
    xAxis: {
      type: 'category',
      data: buckets.map((bucket) => bucket.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dce6df' } },
      axisLabel: { color: '#7d8b84', fontSize: 10, interval: buckets.length > 12 ? 'auto' : 0 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      interval: 0.25,
      splitLine: { lineStyle: { color: 'rgba(24, 49, 45, 0.08)' } },
      axisLabel: { color: '#8b9a92', fontSize: 10, formatter: (value: number) => value.toFixed(2) },
    },
    series: [{
      type: 'line',
      name: '平均输入情绪得分',
      data: buckets.map((bucket) => bucket.avg_score ?? null),
      connectNulls: false,
      showSymbol: false,
      smooth: 0.25,
      lineStyle: { color: '#B15F14', width: 2 },
      itemStyle: { color: '#B15F14' },
      areaStyle: { color: 'rgba(177, 95, 20, 0.10)' },
      emphasis: { focus: 'series', scale: true },
    }],
  }
})

async function loadOverview() {
  const sequence = ++requestSequence
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await api.get<DashboardOverview>('/api/dashboard/overview', {
      params: { period: period.value },
      headers: { 'Cache-Control': 'no-store' },
    })
    if (sequence === requestSequence) overview.value = data
  } catch (error: any) {
    if (sequence === requestSequence) {
      loadError.value = error?.response?.data?.detail || error?.message || '运营数据加载失败'
      ElMessage.error(loadError.value)
    }
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

function changePeriod(value: Period) {
  if (period.value === value) return
  period.value = value
  void loadOverview()
}

function formatDuration(value: number | null): string {
  if (value === null) return '—'
  return value >= 1000 ? `${(value / 1000).toFixed(value >= 10000 ? 1 : 2)}s` : `${Math.round(value)}ms`
}

function scoreText(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toFixed(3)
}

function metricSampleNote(metric: ValueMetric, suffix: string): string {
  return metric.sample_count ? `${metric.sample_count} ${suffix}` : '暂无有效样本'
}

function modeLabel(mode: Mode): string {
  return { text: '文本交互', voice: '语音交互', other: '其他方式' }[mode]
}

function modeColor(mode: Mode): string {
  return { text: '#008300', voice: '#EDA100', other: '#2A78D6' }[mode]
}

function ratioText(ratio: number | null): string {
  return ratio === null ? '—' : `${(ratio * 100).toFixed(1)}%`
}

function ratioWidth(ratio: number | null): string {
  return ratio === null ? '0%' : `${Math.max(ratio * 100, 0)}%`
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(value))
}

function formatRange(start: string, end: string): string {
  return `${formatDateTime(start)} — ${formatDateTime(end)}`
}

onMounted(() => {
  void loadOverview()
  refreshTimer = setInterval(() => void loadOverview(), 60_000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.dashboard-page { --ink:#18312d; --deep:#123e3a; --jade:#2d6a4f; --mint:#edf5ee; --sand:#f5f1e8; --amber:#b07d4f; display:flex; flex-direction:column; gap:22px; max-width:1280px; }
.dashboard-hero { position:relative; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:22px; min-height:178px; padding:28px 30px 24px; overflow:hidden; border-radius:20px; color:#fff; background:linear-gradient(112deg,var(--deep),#1f6359 62%,#328373); box-shadow:0 16px 32px rgba(18,62,58,.16); }
.dashboard-hero::after { content:'灵'; position:absolute; right:36px; top:-44px; color:rgba(255,255,255,.07); font:900 192px/1 Georgia,serif; transform:rotate(-7deg); }
.hero-copy,.hero-tools,.hero-meta { position:relative; z-index:1; }.hero-copy { max-width:660px; }.hero-kicker,.section-kicker { display:block; font-size:10px; font-weight:700; letter-spacing:.18em; }.hero-kicker { color:#cbe8d9; }.hero-copy h2 { margin:8px 0 6px; font-size:1.62rem; letter-spacing:.02em; }.hero-copy p { max-width:610px; color:rgba(255,255,255,.78); font-size:.8rem; line-height:1.7; }.hero-tools { display:flex; align-items:flex-start; gap:10px; }.period-switch { display:flex; padding:3px; border:1px solid rgba(255,255,255,.18); border-radius:10px; background:rgba(8,39,34,.24); }.period-switch button { min-width:56px; padding:6px 8px; color:rgba(255,255,255,.67); border:0; border-radius:7px; background:transparent; font-size:.7rem; cursor:pointer; transition:.2s ease; }.period-switch button:hover:not(:disabled) { color:#fff; }.period-switch button.active { color:#183c36; font-weight:700; background:#e9f1e7; }.period-switch button:disabled { cursor:wait; }.hero-tools :deep(.el-button--default) { border-color:rgba(255,255,255,.35); color:#fff; background:rgba(255,255,255,.08); }.hero-meta { grid-column:1/-1; align-self:end; display:flex; align-items:center; gap:8px; color:rgba(255,255,255,.72); font-size:.68rem; }.live-dot { width:7px; height:7px; border-radius:50%; background:#68d691; box-shadow:0 0 0 4px rgba(104,214,145,.16); }.live-dot.paused { background:#f0bd71; box-shadow:0 0 0 4px rgba(240,189,113,.16); }.meta-divider { width:1px; height:12px; background:rgba(255,255,255,.25); }
.loading-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; }
.metric-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)) minmax(0,1.1fr); gap:16px; }.skeleton-card { height:158px; border-radius:16px; background:linear-gradient(90deg,#edf1ed 25%,#f8faf8 37%,#edf1ed 63%); background-size:400% 100%; animation:shimmer 1.35s infinite; }.metric-card { display:flex; flex-direction:column; min-height:158px; padding:14px 16px; border-color:rgba(24,49,45,.07); }.metric-topline { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }.metric-icon { display:grid; width:32px; height:32px; place-items:center; border-radius:10px; font-size:16px; }.metric-icon.green { color:#2d6a4f; background:#e8f3ea; }.metric-icon.jade { color:#317567; background:#e4f1ef; }.metric-icon.amber { color:#a76525; background:#faf0e3; }.metric-icon.lake { color:#397493; background:#e6f1f6; }.metric-source { color:#8a9990; font-size:.61rem; font-weight:600; letter-spacing:.01em; }.metric-card strong { color:var(--ink); font-size:1.65rem; font-weight:800; letter-spacing:-.03em; line-height:1.1; }.metric-label { margin-top:5px; color:#3d5249; font-size:.78rem; font-weight:700; }.metric-card p { margin:6px 0 0; color:#8a9891; font-size:.64rem; line-height:1.45; }.stale { opacity:.62; }.refresh-warning { display:flex; align-items:center; gap:6px; margin:-10px 0 -4px; color:#9b692c; font-size:.72rem; }.refresh-warning .el-icon { color:#c47b25; }
.chart-grid { display:grid; grid-template-columns:1.35fr 1fr; gap:18px; }
.analytics3d-grid { display:grid; grid-template-columns:1fr; gap:18px; align-items:stretch; }
.analytics3d-card { display:flex; flex-direction:column; padding:21px; border-color:rgba(24,49,45,.07); }
.analytics3d-card--wide { grid-column:1/-1; }
.satisfaction-metric-card { padding:16px; overflow:hidden; }
.satisfaction-metric-card .section-header { min-height:auto; margin-bottom:6px; }
.satisfaction-metric-card .section-header h3 { margin:4px 0 0; font-size:.88rem; }
.satisfaction-metric-card .section-header p { display:none; }
.wordcloud-card { padding:18px; }.chart-card,.questions-card,.activity-card,.mode-card { padding:21px; border-color:rgba(24,49,45,.07); }.section-header { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; min-height:58px; }.section-header.compact { min-height:52px; }.section-kicker { color:#63917b; font-size:.6rem; }.section-header h3 { margin:5px 0 3px; color:var(--ink); font-size:.98rem; }.section-header p { max-width:430px; color:#7c8c84; font-size:.69rem; line-height:1.5; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }.section-total { flex-shrink:0; padding:5px 8px; color:#467360; border-radius:99px; background:#edf5ee; font-size:.68rem; font-weight:700; }.chart { width:100%; height:250px; margin-top:6px; }.chart-card :deep(.el-empty) { height:256px; }
.detail-grid { display:grid; grid-template-columns:1.2fr 0.9fr 0.9fr 0.9fr; gap:18px; }.question-list { display:flex; flex-direction:column; gap:3px; margin:14px 0 0; padding:0; list-style:none; }.question-list li { display:grid; grid-template-columns:28px minmax(0,1fr) auto; align-items:center; gap:10px; min-height:37px; padding:4px 0; border-bottom:1px solid #edf1ee; }.question-list li:last-child { border-bottom:0; }.question-rank { display:grid; width:25px; height:25px; place-items:center; color:#87968e; border-radius:7px; background:#f1f4f1; font:700 .61rem/1 ui-monospace,SFMono-Regular,Menlo,monospace; }.question-rank.top { color:#965a20; background:#faeddb; }.question-list p { overflow:hidden; margin:0; color:#4a5e55; font-size:.73rem; text-overflow:ellipsis; white-space:nowrap; }.question-list b { color:#2d614e; font-size:.76rem; }.question-list small { margin-left:2px; color:#91a097; font-size:.63rem; font-weight:500; }.questions-card :deep(.el-empty) { height:220px; }
.activity-values { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:15px 0 13px; }.activity-values div { padding:12px 10px; border:1px solid #e4ece6; border-radius:11px; background:#f9fbf9; }.activity-values span { display:flex; align-items:center; gap:4px; color:#71827a; font-size:.65rem; }.activity-values strong { display:block; margin-top:5px; color:#274f40; font-size:1.3rem; }.mode-summary { display:grid; gap:6px; margin:0; padding-top:10px; border-top:1px dashed #dce7df; }.mode-summary div { display:flex; justify-content:space-between; gap:10px; color:#708078; font-size:.68rem; }.mode-summary dt { display:flex; align-items:center; gap:6px; }.mode-summary dd { margin:0; color:#4f655b; font-weight:700; }.mode-summary i,.mode-head i { display:inline-block; width:7px; height:7px; border-radius:50%; }
.mode-list { display:grid; gap:15px; margin-top:17px; }.mode-head { display:flex; justify-content:space-between; gap:12px; margin-bottom:6px; color:#60736a; font-size:.68rem; }.mode-head span { display:flex; align-items:center; gap:6px; }.mode-head b { color:#416554; font-size:.68rem; }.mode-head em { margin-left:3px; color:#95a29b; font-size:.62rem; font-style:normal; font-weight:500; }.mode-track { height:7px; overflow:hidden; border-radius:99px; background:#edf1ed; }.mode-track span { display:block; height:100%; min-width:0; border-radius:inherit; transition:width .45s ease; }
.data-collapse { padding:0 16px; border:1px solid rgba(24,49,45,.08); border-radius:14px; background:#fff; }.data-collapse :deep(.el-collapse-item__header) { height:46px; color:#466256; border-bottom:0; font-size:.72rem; font-weight:700; }.data-collapse :deep(.el-collapse-item__wrap) { border-bottom:0; }.data-table-wrap { overflow:auto; padding:0 0 14px; }table { width:100%; border-collapse:collapse; color:#52665d; font-size:.7rem; }th,td { padding:10px 12px; text-align:left; border-bottom:1px solid #edf1ee; }th { color:#829189; background:#f8faf8; font-size:.64rem; font-weight:700; }tbody tr:last-child td { border-bottom:0; }.empty-state { padding:36px; }
@keyframes shimmer { 0% { background-position:100% 0 } 100% { background-position:0 0 } }
@media (max-width:1120px) {
  .metric-grid,.loading-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .satisfaction-metric-card { grid-column:1/-1; }
  .detail-grid { grid-template-columns:1fr 1fr; }
  .questions-card,.wordcloud-card { grid-column:1/-1; }
  .chart-grid { grid-template-columns:1fr; }
  .analytics3d-grid { grid-template-columns:1fr; }
}
@media (max-width:760px) {
  .dashboard-hero { grid-template-columns:1fr; padding:24px 20px 20px; }
  .dashboard-hero::after { right:-8px; font-size:160px; }
  .hero-tools { align-items:stretch; flex-direction:column; }
  .period-switch { width:100%; }
  .period-switch button { flex:1; }
  .hero-tools :deep(.el-button) { width:100%; margin:0; }
  .hero-meta { grid-column:auto; flex-wrap:wrap; }
  .metric-grid,.loading-grid,.detail-grid { grid-template-columns:1fr; }
  .questions-card,.wordcloud-card { grid-column:auto; }
  .metric-card { min-height:140px; }
  .chart-card,.questions-card,.activity-card,.mode-card,.wordcloud-card { padding:17px; }
  .chart { height:230px; }
  .section-header { min-height:auto; }
  .section-header p { max-width:245px; }
  .section-total { display:none; }
}
</style>
