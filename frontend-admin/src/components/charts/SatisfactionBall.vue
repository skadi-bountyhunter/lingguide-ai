<template>
  <div class="satisfaction-ball">
    <v-chart
      v-if="!loading && data"
      class="ball-canvas"
      :option="option"
    />
    <div v-if="loading" class="ball-loading">加载中…</div>
    <p v-if="!loading && data" class="ball-meta">
      {{ data.sample_count.toLocaleString() }} 条有效样本
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
// echarts-liquidfill 副作用导入，自动注册 liquidFill 图类型
import 'echarts-liquidfill'
import api from '@/services/api'

use([CanvasRenderer])

interface SatisfactionData {
  score: number
  percentage: number
  sample_count: number
}

type Period = 'today' | '7d' | '30d'

const props = defineProps<{
  period?: Period
}>()

const data = ref<SatisfactionData | null>(null)
const loading = ref(false)

function periodToDays(p: Period): number {
  return p === 'today' ? 1 : p === '7d' ? 7 : 30
}

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get<SatisfactionData>('/api/analytics/satisfaction', {
      params: { days: periodToDays(props.period ?? '7d') },
    })
    data.value = res.data
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.period, fetchData)

onMounted(fetchData)

const option = computed(() => {
  const score = data.value?.score ?? 0.5
  return {
    series: [
      {
        type: 'liquidFill',
        data: [score, Math.max(0, score - 0.06), Math.max(0, score - 0.12)],
        radius: '82%',
        color: [
          'rgba(45,106,79,.8)',
          'rgba(82,183,136,.7)',
          'rgba(149,213,178,.6)',
        ],
        backgroundStyle: {
          borderWidth: 3,
          borderColor: '#2d6a4f',
          color: '#edf5ee',
        },
        outline: { show: false },
        label: {
          show: true,
          formatter: () =>
            `${data.value?.percentage.toFixed(1) ?? '--'}%\n满意度`,
          fontSize: 26,
          color: '#18312d',
          insideColor: '#fff',
          fontWeight: 'bold',
          lineHeight: 36,
        },
      },
    ],
  }
})
</script>

<style scoped>
.satisfaction-ball {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  justify-content: center;
}
.ball-canvas {
  width: 100%;
  height: 200px;
}
.ball-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aaa;
  font-size: 13px;
  height: 240px;
}
.ball-meta {
  margin: 6px 0 0;
  font-size: 11px;
  color: #aaa;
}
</style>
