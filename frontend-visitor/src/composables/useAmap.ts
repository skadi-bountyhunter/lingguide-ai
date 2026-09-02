/** 高德地图 JS API 2.0 加载器 */
import { ref } from 'vue'

const loaded = ref(false)
const loading = ref(false)
let loadPromise: Promise<void> | null = null

const AMAP_KEY = import.meta.env.VITE_AMAP_KEY || ''
const AMAP_SECURITY_CODE = import.meta.env.VITE_AMAP_SECURITY_CODE || ''
const AMAP_VERSION = '2.0'

export function useAmap() {
  async function load(): Promise<void> {
    if (loaded.value && window.AMap) return
    if (!AMAP_KEY) throw new Error('高德地图未配置')
    if (loadPromise) return loadPromise

    loading.value = true
    loadPromise = new Promise<void>((resolve, reject) => {
      if (AMAP_SECURITY_CODE) window._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY_CODE }
      const script = document.createElement('script')
      script.src = `https://webapi.amap.com/maps?v=${AMAP_VERSION}&key=${AMAP_KEY}`
      script.onload = () => {
        if (!window.AMap) {
          reject(new Error('高德地图加载失败'))
          return
        }
        loaded.value = true
        resolve()
      }
      script.onerror = () => reject(new Error('高德地图加载失败'))
      document.head.appendChild(script)
    }).catch((error) => {
      loadPromise = null
      throw error
    }).finally(() => {
      loading.value = false
    })
    return loadPromise!
  }

  return { load, loaded, loading }
}
