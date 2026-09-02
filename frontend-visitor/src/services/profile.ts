import axios, { type AxiosRequestConfig } from 'axios'

export const TOKEN_KEY = 'lingguide_token'
export const USER_KEY = 'lingguide_user'

export interface ProfileStats {
  visits?: number
  favorites?: number
  routes?: number
  conversations?: number
  visit_count?: number
  saved_route_count?: number
  interaction_count?: number
  spot_favorite_count?: number
  unread_notification_count?: number
}

export interface UserProfile {
  id?: number
  phone?: string
  nickname?: string
  avatar?: string
  visit_count?: number
  favorite_count?: number
  route_count?: number
  conversation_count?: number
  stats?: ProfileStats
}

export interface FavoriteRecord {
  id: number
  item_type: 'spot' | 'route' | string
  item_id: string
  item_name: string
  item_cover?: string
  created_at?: string
}

export interface FavoriteCreate {
  item_type: 'spot' | 'route'
  item_id: string
  item_name: string
  item_cover?: string
}

export interface FavoriteCheck {
  favorited: boolean
  id: number | null
}

export interface VisitRecord {
  id: number
  item_type: 'spot' | 'route' | string
  item_id: string
  item_name: string
  item_cover?: string
  first_visited_at?: string
  last_visited_at?: string
  visit_count?: number
}

export interface VisitCreate {
  item_type?: 'spot' | 'route'
  item_id: string
  item_name: string
  item_cover?: string
}

export interface FeedbackRecord {
  id: number
  category?: string
  content: string
  status?: string
  admin_reply?: string
  created_at?: string
  updated_at?: string
}

export interface NotificationRecord {
  id: number
  title: string
  content: string
  category?: string
  type?: string
  read?: boolean
  is_read?: boolean
  created_at?: string
}

const client = axios.create()

client.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) config.headers.Authorization = token
  return config
})

client.interceptors.response.use(
  response => response,
  (error) => {
    if (error.response?.status === 401) redirectToLogin()
    return Promise.reject(error)
  },
)

/** 每次调用时读取令牌，避免登录状态变化后沿用旧值。 */
export function getAuthToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function authorizationHeaders(): Record<string, string> {
  const token = getAuthToken()
  return token ? { Authorization: token } : {}
}

export function redirectToLogin() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  if (window.location.pathname !== '/auth') window.location.assign('/auth')
}

function unwrapList<T>(data: T[] | { items?: T[]; records?: T[]; data?: T[] }): T[] {
  if (Array.isArray(data)) return data
  return data.items || data.records || data.data || []
}

export async function getMyProfile(): Promise<UserProfile> {
  const { data } = await client.get<UserProfile>('/api/profile/me')
  return data
}

export async function updateMyProfile(payload: Pick<UserProfile, 'nickname'>): Promise<UserProfile> {
  const { data } = await client.patch<UserProfile>('/api/profile/me', payload)
  return data
}

export async function getFavorites(): Promise<FavoriteRecord[]> {
  const { data } = await client.get<FavoriteRecord[] | { items?: FavoriteRecord[] }>('/api/profile/favorites')
  return unwrapList(data)
}

export async function createFavorite(payload: FavoriteCreate): Promise<FavoriteRecord> {
  const { data } = await client.post<FavoriteRecord>('/api/profile/favorites', payload)
  return data
}

export async function deleteFavorite(id: number): Promise<void> {
  await client.delete(`/api/profile/favorites/${id}`)
}

export async function checkFavorite(itemId: string, itemType: 'spot' | 'route' = 'spot'): Promise<FavoriteCheck> {
  const { data } = await client.get<FavoriteCheck>(
    `/api/profile/favorites/check/${encodeURIComponent(itemId)}`,
    { params: { item_type: itemType } },
  )
  return data
}

export async function getVisits(): Promise<VisitRecord[]> {
  const { data } = await client.get<VisitRecord[] | { items?: VisitRecord[] }>('/api/profile/visits')
  return unwrapList(data)
}

export async function createVisit(payload: VisitCreate): Promise<VisitRecord> {
  const { data } = await client.post<VisitRecord>('/api/profile/visits', payload)
  return data
}

export async function getFeedbackHistory(): Promise<FeedbackRecord[]> {
  const { data } = await client.get<FeedbackRecord[] | { items?: FeedbackRecord[] }>('/api/profile/feedback')
  return unwrapList(data)
}

export async function submitFeedback(content: string, category = 'suggestion'): Promise<FeedbackRecord> {
  const { data } = await client.post<FeedbackRecord>('/api/profile/feedback', { category, content })
  return data
}

export async function getNotifications(): Promise<NotificationRecord[]> {
  const { data } = await client.get<NotificationRecord[] | { items?: NotificationRecord[] }>('/api/profile/notifications')
  return unwrapList(data)
}

export async function markNotificationRead(id: number): Promise<NotificationRecord> {
  const { data } = await client.patch<NotificationRecord>(`/api/profile/notifications/${id}/read`)
  return data
}

export async function getUnreadNotificationCount(): Promise<number> {
  const { data } = await client.get<number | { count?: number; unread_count?: number }>('/api/profile/notifications/unread-count')
  return typeof data === 'number' ? data : Number(data.count ?? data.unread_count ?? 0)
}

/** 供已有个人路线接口复用同一套动态认证与 401 处理。 */
export async function profileRequest<T>(config: AxiosRequestConfig): Promise<T> {
  const { data } = await client.request<T>(config)
  return data
}
