/** 灵山胜境景区景点数据类型 + 接口取数（首页 + 详情页共用） */
import axios from 'axios'
import { i18n } from '../i18n'

export interface ScenicSpot {
  id?: number
  /** 稳定的后端名称，用于路由、收藏、足迹和地图匹配。 */
  canonicalName: string
  /** 当前 locale 对应的展示名称。 */
  displayName: string
  /** 当前 locale 对应的展示标签。 */
  displayTags: string[]
  /** 稳定的中文标签，用于兴趣筛选与后端匹配。 */
  canonicalTags: string[]
  /** 旧字段别名，保留给尚未迁移的调用方。 */
  name: string
  icon: string
  image: string
  desc: string          // 短描述（首页列表用）
  fullDesc: string      // 完整介绍（详情页用，段落以 \n\n 分隔）
  tags: string[]
  duration: string
  distance: string
  highlights: string[]
  hours: string
  ticket: string
  tips: string[]
  bestSeason: string
  nearby: string[]      // 周边景点 canonical 名称列表
  translationStatus: 'source' | 'translated' | 'fallback'
  lng?: number          // 经度（高德 GCJ-02）
  lat?: number          // 纬度
}

export interface CarouselItem {
  image: string
  canonicalName: string
  displayName: string
  displayTags: string[]
  /** 旧字段别名，兼容旧轮播响应。 */
  title: string
  subtitle: string
}

function localeParams() {
  return { locale: i18n.global.locale.value }
}

/** 后端 snake_case → 前端 camelCase，并兼容旧 name/tags 字段。 */
function mapSpot(raw: any): ScenicSpot {
  const canonicalName = String(raw.canonical_name || raw.canonicalName || raw.name || '')
  const displayName = String(raw.display_name || raw.displayName || raw.name || canonicalName)
  const displayTags = raw.display_tags || raw.displayTags || raw.tags || []
  return {
    id: raw.id,
    canonicalName,
    displayName,
    displayTags,
    canonicalTags: raw.canonical_tags || raw.canonicalTags || raw.tags || [],
    name: canonicalName,
    icon: raw.icon || '',
    image: raw.image || '',
    desc: raw.desc || '',
    fullDesc: raw.full_desc || raw.fullDesc || '',
    tags: displayTags,
    duration: raw.duration || '',
    distance: raw.distance || '',
    highlights: raw.highlights || [],
    hours: raw.hours || '',
    ticket: raw.ticket || '',
    tips: raw.tips || [],
    bestSeason: raw.best_season || raw.bestSeason || '',
    nearby: Array.isArray(raw.canonical_nearby || raw.nearby)
      ? (raw.canonical_nearby || raw.nearby).map((item: any) => String(item?.canonical_name || item?.canonicalName || item))
      : [],
    translationStatus: raw.translation_status || raw.translationStatus || 'source',
    lng: raw.lng,
    lat: raw.lat,
  }
}

function mapCarousel(raw: any): CarouselItem {
  const canonicalName = String(raw.canonical_name || raw.canonicalName || raw.title || raw.name || '')
  const displayName = String(raw.display_name || raw.displayName || raw.title || raw.name || canonicalName)
  return {
    image: raw.image || '',
    canonicalName,
    displayName,
    displayTags: raw.display_tags || raw.displayTags || raw.tags || [],
    title: canonicalName,
    subtitle: raw.subtitle || raw.desc || '',
  }
}

/** 拉取景点列表（按 sort_order 升序） */
export async function fetchSpots(): Promise<ScenicSpot[]> {
  const { data } = await axios.get('/api/spots', { params: localeParams() })
  return data.map(mapSpot)
}

/** 拉取单个景点详情 */
export async function fetchSpot(name: string): Promise<ScenicSpot> {
  const { data } = await axios.get(`/api/spots/${encodeURIComponent(name)}`, { params: localeParams() })
  return mapSpot(data)
}

/** 拉取首页轮播 */
export async function fetchCarousel(): Promise<CarouselItem[]> {
  const { data } = await axios.get('/api/spots/carousel', { params: localeParams() })
  return data.map(mapCarousel)
}
