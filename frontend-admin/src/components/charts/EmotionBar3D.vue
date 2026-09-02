<template>
  <div class="emotion-bar3d">
    <div class="bar3d-controls">
      <div class="period-switch" role="group" aria-label="统计周期">
        <button
          v-for="opt in DAY_OPTIONS"
          :key="opt.value"
          type="button"
          :class="{ active: days === opt.value }"
          :disabled="loading"
          @click="setDays(opt.value)"
        >{{ opt.label }}</button>
      </div>
      <span v-if="!loading && hasData" class="sample-hint">{{ totalCount.toLocaleString() }} 条记录</span>
    </div>

    <v-chart
      v-if="hasData"
      class="bar3d-canvas"
      :option="option"
      autoresize
    />
    <el-empty
      v-else-if="!loading"
      description="暂无景点情绪数据，游客对话时需选择所在景点才会产生记录"
      :image-size="72"
    />
    <div v-if="loading" class="bar3d-loading">加载中…</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent, VisualMapComponent } from 'echarts/components'
// echarts-gl 以副作用 import 自动注册所有3D组件（grid3D/bar3D等）
import 'echarts-gl'
import api from '@/services/api'

use([CanvasRenderer, TooltipComponent, VisualMapComponent])

interface EmotionPoint {
  hour: number
  spot_name: string
  spot_id: string
  avg_score: number
  count: number
}

const HOURS = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`)

const DAY_OPTIONS = [
  { label: '今日', value: 1 },
  { label: '近7天', value: 7 },
  { label: '近30天', value: 30 },
]

const days = ref(7)
const points = ref<EmotionPoint[]>([])
const loading = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get<{ days: number; data: EmotionPoint[] }>(
      '/api/analytics/emotion-3d',
      { params: { days: days.value } },
    )
    points.value = res.data.data ?? []
  } catch {
    points.value = []
  } finally {
    loading.value = false
  }
}

function setDays(val: number) {
  days.value = val
  fetchData()
}

onMounted(fetchData)

const hasData = computed(() => points.value.length > 0)
const totalCount = computed(() => points.value.reduce((s, p) => s + p.count, 0))

const option = computed(() => {
  const spotSet = new Set<string>()
  points.value.forEach(p => spotSet.add(p.spot_name))
  const spots = Array.from(spotSet)

  const seriesData = points.value.map(p => ({
    value: [HOURS[p.hour], p.spot_name, p.avg_score] as [string, string, number],
    count: p.count,
  }))

  return {
    tooltip: {
      formatter: (params: any) => {
        const [hourStr, spotName, score] = params.value as [string, string, number]
        const cnt = (params.data as { count: number }).count
        return `<b>${spotName}</b><br/>${hourStr} 时段<br/>情绪均值：<b>${(score as number).toFixed(3)}</b><br/>样本量：${cnt}`
      },
    },
    visualMap: {
      show: true,
      min: 0,
      max: 1,
      dimension: 2,
      inRange: { color: ['#e84040', '#f5c518', '#52c41a'] },
      text: ['好', '差'],
      textStyle: { color: '#888', fontSize: 11 },
      orient: 'vertical',
      right: 8,
      top: 'middle',
    },
    grid3D: {
      boxWidth: 160,
      boxDepth: 80,
      boxHeight: 60,
      viewControl: {
        distance: 260,
        alpha: 20,
        beta: 30,
        autoRotate: false,
      },
      light: {
        main: { intensity: 1.2, shadow: true },
        ambient: { intensity: 0.3 },
      },
    },
    xAxis3D: {
      type: 'category',
      name: '时段',
      data: HOURS,
      axisLabel: { color: '#888', fontSize: 9 },
      nameTextStyle: { color: '#aaa', fontSize: 11 },
    },
    yAxis3D: {
      type: 'category',
      name: '景点',
      data: spots,
      axisLabel: { color: '#888', fontSize: 9 },
      nameTextStyle: { color: '#aaa', fontSize: 11 },
    },
    zAxis3D: {
      type: 'value',
      name: '情绪分',
      min: 0,
      max: 1,
      nameTextStyle: { color: '#aaa', fontSize: 11 },
    },
    series: [
      {
        type: 'bar3D',
        data: seriesData,
        shading: 'lambert',
        label: { show: false },
        itemStyle: { opacity: 0.88 },
        emphasis: { itemStyle: { opacity: 1 } },
      },
    ],
  }
})
</script>

<style scoped>
.emotion-bar3d {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.bar3d-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.period-switch {
  display: flex;
  gap: 4px;
}
.period-switch button {
  padding: 4px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  color: #606266;
  transition: all 0.15s;
  line-height: 1.5;
}
.period-switch button.active {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}
.period-switch button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.sample-hint {
  font-size: 11px;
  color: #aaa;
}
.bar3d-canvas {
  flex: 1;
  min-height: 320px;
}
.bar3d-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aaa;
  font-size: 13px;
  min-height: 320px;
}
</style>
