/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// element-plus 使用自带的类型定义，不在此处覆盖

declare module '@element-plus/icons-vue' {
  import type { DefineComponent } from 'vue'
  const icons: Record<string, DefineComponent<{}, {}, any>>
  export = icons
}

interface LingguideDesktopApi {
  runtime: 'desktop'
  openAdmin?: () => Promise<void>
}

interface Window {
  lingguideDesktop?: LingguideDesktopApi
  AMap?: any
  _AMapSecurityConfig?: { securityJsCode?: string }
  XmovAvatar?: new (options: Record<string, unknown>) => any
}

interface ImportMetaEnv {
  readonly VITE_AMAP_KEY?: string
  readonly VITE_AMAP_SECURITY_CODE?: string
  readonly VITE_XINGYUN_SDK_URL?: string
}
