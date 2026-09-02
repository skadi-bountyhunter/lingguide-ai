import axios from 'axios'

/** 管理端统一请求客户端；桌面版按请求获取短期管理令牌。 */
const api = axios.create()

api.interceptors.request.use(async (config) => {
  const getAdminToken = window.lingguideDesktop?.getAdminToken
  if (!getAdminToken) return config

  const token = await getAdminToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default api
