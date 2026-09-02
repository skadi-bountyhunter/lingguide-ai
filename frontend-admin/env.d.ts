/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// Element Plus 图标包自带类型定义。

interface LingguideDesktopApi {
  runtime: 'desktop'
  getAdminToken?: () => Promise<string | null>
  openLogs?: () => Promise<void>
  restartBackend?: () => Promise<void>
}

interface Window {
  lingguideDesktop?: LingguideDesktopApi
  AMap?: any
  _AMapSecurityConfig?: { securityJsCode?: string }
}

interface ImportMetaEnv {
  readonly VITE_AMAP_KEY?: string
  readonly VITE_AMAP_SECURITY_CODE?: string
}
