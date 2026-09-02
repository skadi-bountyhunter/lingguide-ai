import type { Citation, RetrievalTrace } from './retrieval'

export interface RouteSpot {
  /** canonical 中文名称，用于地图匹配。 */
  name: string
  /** 当前 locale 对应的展示名称。 */
  display_name?: string
  description: string
  evidence_ids?: string[]
  /** 该景点实际游览时长（分钟），来自后端 Spot.duration；0 表示未提供，前端降级为 30 分钟兜底。 */
  duration_min?: number
}

export interface RoutePlan {
  schema_version?: number
  source: 'chat' | 'manual'
  title: string
  duration: string
  duration_mode?: '半天' | '全天'
  spots: RouteSpot[]
  tips: string
  interests: string[]
  sources?: string[]
  citations?: Citation[]
  retrieval?: RetrievalTrace
  traceId?: string
  trace_id?: string
  index_version?: string
}

export interface SavedRoute extends RoutePlan {
  id: number
  created_at: string
}

export interface ActiveMapRoute {
  title: string
  spots: string[]
}

export interface PresetRoute {
  title: string
  icon: string
  duration: string
  distance: string
  difficulty: string
  desc: string
  spots: string[]
  tags: string[]
  tip: string
  display_title?: string
  display_duration?: string
  display_distance?: string
  display_difficulty?: string
  display_desc?: string
  display_spots?: string[]
  display_tags?: string[]
  display_tip?: string
}
