<template>
  <div class="pins-heatmap">
    <div ref="mapEl" class="heatmap-canvas" />
    <div v-if="mapLoading" class="heatmap-overlay">
      <el-icon class="is-loading"><Loading /></el-icon>
    </div>
    <div v-else-if="mapError" class="heatmap-overlay">
      <el-empty :description="mapError" :image-size="64" />
    </div>
    <div v-else-if="total === 0" class="heatmap-overlay">
      <el-empty description="暂无游客浏览数据" :image-size="64" />
    </div>
    <div class="heatmap-meta">近 {{ days }} 天 · {{ total }} 次浏览</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { useAmap } from '@/composables/useAmap'
import api from '@/services/api'

const props = withDefaults(defineProps<{ days?: number }>(), { days: 30 })

const mapEl = ref<HTMLDivElement | null>(null)
const mapLoading = ref(true)
const mapError = ref('')
const total = ref(0)

let map: any = null
let heatmap: any = null
const { load } = useAmap()

const CENTER: [number, number] = [120.100, 31.423]

async function init() {
  if (!mapEl.value) return
  try {
    await load()
    map = new window.AMap.Map(mapEl.value, {
      zoom: 15,
      center: CENTER,
      mapStyle: 'amap://styles/dark',
      resizeEnable: true,
    })
    window.AMap.plugin(['AMap.HeatMap'], () => {
      heatmap = new window.AMap.HeatMap(map, {
        radius: 25,
        opacity: [0, 0.85],
        gradient: {
          0.4: 'rgb(0,104,55)',
          0.65: 'rgb(255,217,47)',
          0.85: 'rgb(253,141,60)',
          1.0: 'rgb(215,25,28)',
        },
      })
      loadData()
    })
  } catch (error) {
    mapError.value = error instanceof Error ? error.message : '地图暂不可用'
    mapLoading.value = false
  }
}

async function loadData() {
  try {
    const { data } = await api.get<{ total: number; points: { lng: number; lat: number; count: number }[] }>('/api/visits/heatmap', {
      params: { days: props.days },
    })
    total.value = data.total
    if (heatmap && data.points.length) {
      heatmap.setDataSet({ data: data.points, max: 5 })
    }
  } catch {
    mapError.value = '热力图数据暂不可用'
  } finally {
    mapLoading.value = false
  }
}

onMounted(init)
onUnmounted(() => map?.destroy())
</script>

<style scoped>
.pins-heatmap {
  position: relative;
  width: 100%;
  height: 480px;
  border-radius: 8px;
  overflow: hidden;
  background: #0d1f1b;
}
.heatmap-canvas {
  width: 100%;
  height: 100%;
}
.heatmap-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(13, 31, 27, 0.7);
  font-size: 14px;
  color: #a8bdb7;
  gap: 8px;
}
.heatmap-meta {
  position: absolute;
  bottom: 8px;
  right: 12px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  pointer-events: none;
}
</style>
