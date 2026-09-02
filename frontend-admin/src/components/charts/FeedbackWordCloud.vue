<template>
  <div class="feedback-wordcloud">
    <span v-if="!loading && words.length" class="wc-hint">{{ words.length }} 个词</span>
    <v-chart
      v-if="hasData"
      class="wc-canvas"
      :option="option"
      autoresize
    />
    <el-empty
      v-else-if="!loading"
      description="暂无游客问句数据"
      :image-size="64"
    />
    <div v-if="loading" class="wc-loading">加载中…</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
// echarts-wordcloud 副作用导入，自动注册 wordCloud 图类型
import 'echarts-wordcloud'
import api from '@/services/api'

use([CanvasRenderer])

interface WordItem {
  name: string
  value: number
}

type Period = 'today' | '7d' | '30d'

const PALETTE = [
  '#2d6a4f', '#40916c', '#52b788',
  '#74c69d', '#1b4332', '#095e43', '#1a7850',
]

const props = defineProps<{
  period?: Period
}>()

const words = ref<WordItem[]>([])
const loading = ref(false)

function periodToDays(p: Period): number {
  return p === 'today' ? 1 : p === '7d' ? 7 : 30
}

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get<{ days: number; data: WordItem[] }>(
      '/api/analytics/word-freq',
      { params: { days: periodToDays(props.period ?? '7d'), top_n: 80 } },
    )
    words.value = res.data.data ?? []
  } catch {
    words.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.period, fetchData)

onMounted(fetchData)

const hasData = computed(() => words.value.length > 0)

const option = computed(() => ({
  series: [
    {
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '96%',
      height: '96%',
      sizeRange: [12, 46],
      rotationRange: [-30, 30],
      rotationStep: 15,
      gridSize: 8,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: () => PALETTE[Math.floor(Math.random() * PALETTE.length)],
      },
      emphasis: {
        focus: 'self',
        textStyle: { textShadowBlur: 6, textShadowColor: 'rgba(0,0,0,.2)' },
      },
      data: words.value,
    },
  ],
}))
</script>

<style scoped>
.feedback-wordcloud {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.wc-hint {
  font-size: 11px;
  color: #aaa;
  margin-bottom: 6px;
  text-align: center;
}
.wc-canvas {
  flex: 1;
  min-height: 300px;
}
.wc-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aaa;
  font-size: 13px;
  min-height: 200px;
}
</style>
