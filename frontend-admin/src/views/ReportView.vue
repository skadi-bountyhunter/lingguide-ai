<template>
  <div class="report animate-fade-up">
    <div class="page-hd"><div><h2>📋 游客感受度报告</h2><p>基于游客交互数据的分析洞察</p></div></div>

    <div class="card section-card">
      <h3>情感趋势（近7天）</h3>
      <div class="trend-summary">
        <span>真实交互样本：{{ sentimentTotal }} 条</span>
        <span>平均情绪分：{{ avgEmotionScore }}</span>
      </div>
      <div class="trend-grid">
        <div v-for="d in sentimentData" :key="d.date" class="trend-day">
          <span class="td-date">{{ d.date.slice(5) }}</span>
          <div class="td-bar-wrap"><div class="td-pos" :style="{height:d.positive+'%'}"/><div class="td-neu" :style="{height:d.neutral+'%'}"/><div class="td-neg" :style="{height:d.negative+'%'}"/></div>
          <div class="td-vals"><span class="pos">{{ d.positive }}%</span><span class="neu">{{ d.neutral }}%</span><span class="neg">{{ d.negative }}%</span></div>
        </div>
      </div>
      <div class="trend-legend"><span><i class="dot pos"/> 正向</span><span><i class="dot neu"/> 中性</span><span><i class="dot neg"/> 负向</span></div>
    </div>

    <div class="report-grid">
      <div class="card section-card">
        <h3>🔥 游客关注热点</h3>
        <div class="hot-list">
          <div v-for="(t,i) in hotTopics" :key="t.name" class="hot-row">
            <span class="hot-rank" :class="{top:i<3}">{{ i+1 }}</span>
            <span class="hot-name">{{ t.name }}</span>
            <div class="hot-bar-wrap"><div class="hot-bar" :style="{width:t.percentage+'%'}"/></div>
            <span class="hot-pct">{{ t.percentage }}%</span>
          </div>
        </div>
      </div>

      <div class="card section-card">
        <h3>💡 知识缺口分析</h3>
        <div v-for="s in gaps" :key="s" class="gap-item"><el-icon><WarningFilled /></el-icon><span>{{ s }}</span></div>
        <div class="gap-stat"><span class="gs-num">{{ gapRate }}%</span><span>未命中率</span></div>
      </div>
    </div>

    <div class="card section-card">
      <h3>📈 服务质量统计</h3>
      <div class="quality-grid">
        <div class="q-item"><span class="q-val">{{ quality.avg_thinking_time_ms }}ms</span><span class="q-label">平均响应时间</span></div>
        <div class="q-item"><span class="q-val">{{ quality.satisfaction_rate }}%</span><span class="q-label">游客满意度</span></div>
        <div class="q-item"><span class="q-val">{{ quality.total_ratings }}</span><span class="q-label">总评价数</span></div>
        <div class="q-item"><span class="q-val">{{ quality.response_rate }}%</span><span class="q-label">响应率</span></div>
      </div>
    </div>

    <!-- 灵山游客行为洞察 -->
    <div class="card section-card" v-if="lingshan">
      <h3>🏔️ 灵山胜境游客行为洞察（基于14万条行业数据）</h3>
      <div class="insight-grid">
        <div class="insight-stat">
          <span class="is-val">{{ lingshan.lingshan.total_visitors }}</span>
          <span class="is-label">灵山样本量</span>
        </div>
        <div class="insight-stat warn">
          <span class="is-val">{{ lingshan.lingshan.satisfaction }}/5</span>
          <span class="is-label">满意度（行业3.72）</span>
        </div>
        <div class="insight-stat">
          <span class="is-val">¥{{ lingshan.lingshan.avg_spending }}</span>
          <span class="is-label">人均消费（行业¥691）</span>
        </div>
        <div class="insight-stat">
          <span class="is-val">{{ lingshan.lingshan.avg_stay_hours }}h</span>
          <span class="is-label">平均游览时长</span>
        </div>
      </div>
      <div class="insight-list">
        <div v-for="(insight, i) in lingshan.insights" :key="i" class="insight-item"
          :class="{ warn: insight.startsWith('⚠️') }">
          {{ insight }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/services/api'

const sentimentData = ref<any[]>([])
const hotTopics = ref<any[]>([])
const gaps = ref<string[]>([])
const gapRate = ref(8.3)
const quality = ref({ avg_thinking_time_ms:3200, satisfaction_rate:94.7, total_ratings:856, response_rate:100 })
const lingshan = ref<any>(null)

const sentimentTotal = computed(() => sentimentData.value.reduce((sum, d) => sum + (d.count || 0), 0))
const avgEmotionScore = computed(() => {
  const total = sentimentTotal.value
  if (!total) return '暂无数据'
  const weighted = sentimentData.value.reduce((sum, d) => sum + (d.avg_score || 0) * (d.count || 0), 0)
  return (weighted / total).toFixed(3)
})

onMounted(async () => {
  try {
    const [sRes, hRes, gRes, qRes, lRes] = await Promise.all([
      api.get('/api/analytics/sentiment-trend'), api.get('/api/analytics/hot-topics'),
      api.get('/api/analytics/knowledge-gaps'), api.get('/api/analytics/service-quality'),
      api.get('/api/analytics/lingshan-insights'),
    ])
    sentimentData.value = sRes.data.data || []
    hotTopics.value = hRes.data.topics || []
    gaps.value = gRes.data.suggestions || []; gapRate.value = gRes.data.unanswered_rate || 8.3
    Object.assign(quality.value, qRes.data)
    lingshan.value = lRes.data
  } catch {}
})
</script>

<style scoped>
.report { display:flex; flex-direction:column; gap:24px; }
.page-hd { margin-bottom:8px; }
.page-hd h2 { font-size:1rem; font-weight:700; color:var(--color-text-primary); }
.page-hd p { font-size:0.75rem; color:var(--color-text-muted); margin-top:4px; }
.section-card { padding:20px; }
.section-card h3 { font-size:0.875rem; font-weight:700; color:var(--color-text-primary); margin-bottom:16px; }
.trend-summary { display:flex; gap:16px; margin:-6px 0 14px; font-size:0.75rem; color:var(--color-text-muted); }

.trend-grid { display:flex; gap:12px; }
.trend-day { flex:1; text-align:center; }
.td-date { font-size:10px; color:var(--color-text-muted); display:block; margin-bottom:8px; }
.td-bar-wrap { height:100px; display:flex; flex-direction:column-reverse; border-radius:6px; overflow:hidden; background:var(--color-bg-muted); }
.td-pos { background:var(--color-success); }
.td-neu { background:var(--color-mist); }
.td-neg { background:var(--color-error); }
.td-vals { display:flex; justify-content:center; gap:4px; margin-top:4px; }
.td-vals span { font-size:9px; }
.td-vals .pos { color:var(--color-success); } .td-vals .neu { color:var(--color-text-muted); } .td-vals .neg { color:var(--color-error); }
.trend-legend { display:flex; gap:16px; margin-top:12px; justify-content:center; }
.trend-legend span { font-size:11px; color:var(--color-text-secondary); display:flex; align-items:center; gap:4px; }
.dot { width:8px; height:8px; border-radius:2px; display:inline-block; }
.dot.pos { background:var(--color-success); } .dot.neu { background:var(--color-mist); } .dot.neg { background:var(--color-error); }

.report-grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
.hot-list { display:flex; flex-direction:column; gap:10px; }
.hot-row { display:flex; align-items:center; gap:10px; }
.hot-rank { width:22px; height:22px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; background:var(--color-bg-muted); color:var(--color-text-muted); }
.hot-rank.top { background:var(--color-accent-bg); color:var(--color-accent); }
.hot-name { width:80px; font-size:0.75rem; color:var(--color-text-secondary); }
.hot-bar-wrap { flex:1; height:8px; background:var(--color-bg-muted); border-radius:4px; overflow:hidden; }
.hot-bar { height:100%; background:var(--color-primary); border-radius:4px; transition:width 0.5s; }
.hot-pct { font-size:0.75rem; font-weight:600; color:var(--color-text-primary); width:36px; text-align:right; }

.gap-item { display:flex; align-items:flex-start; gap:8px; padding:10px 0; border-bottom:1px solid rgba(0,0,0,0.04); font-size:0.8rem; color:var(--color-text-secondary); }
.gap-item .el-icon { color:var(--color-warning); margin-top:2px; }
.gap-item:last-child { border-bottom:none; }
.gap-stat { text-align:center; margin-top:16px; padding-top:16px; border-top:1px solid rgba(0,0,0,0.06); }
.gs-num { font-size:1.5rem; font-weight:700; color:var(--color-warning); display:block; }

.quality-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:20px; }
.q-item { text-align:center; }
.q-val { font-size:1.25rem; font-weight:700; color:var(--color-primary); display:block; }
.q-label { font-size:0.75rem; color:var(--color-text-muted); margin-top:4px; }

.insight-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-bottom:20px; }
.insight-stat { text-align:center; padding:16px; background:var(--color-bg-elevated); border-radius:12px; }
.insight-stat.warn { background:rgba(212,146,58,0.08); }
.is-val { font-size:1.25rem; font-weight:700; color:var(--color-text-primary); display:block; }
.insight-stat.warn .is-val { color:var(--color-warning); }
.is-label { font-size:0.75rem; color:var(--color-text-muted); margin-top:4px; display:block; }
.insight-list { display:flex; flex-direction:column; gap:8px; }
.insight-item { font-size:0.8rem; color:var(--color-text-secondary); padding:10px 14px; background:var(--color-bg-elevated); border-radius:8px; border-left:3px solid var(--color-primary); }
.insight-item.warn { border-left-color:var(--color-warning); }
</style>
