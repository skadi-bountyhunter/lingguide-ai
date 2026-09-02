import { computed, ref, watch } from 'vue'

export const VOICE_SETTINGS_KEY = 'lingguide_voice_settings_v1'

export interface VoiceSettings {
  version: 1
  voiceKey: string
  rate: number
  volume: number
}

export const voiceOptions = [
  { key: '温柔女声', labelKey: 'voice.voices.xiaoyan' },
  { key: '知性女声', labelKey: 'voice.voices.xiaoyu' },
  { key: '稳重男声', labelKey: 'voice.voices.xiaomei' },
  { key: '亲切男声', labelKey: 'voice.voices.xiaofeng' },
] as const

export const rateOptions = [
  { value: 0.8, labelKey: 'voice.rates.slow' },
  { value: 1, labelKey: 'voice.rates.normal' },
  { value: 1.2, labelKey: 'voice.rates.fast' },
] as const

const defaults: VoiceSettings = {
  version: 1,
  voiceKey: voiceOptions[0].key,
  rate: 1,
  volume: 0.8,
}

function loadSettings(): VoiceSettings {
  try {
    const raw = JSON.parse(localStorage.getItem(VOICE_SETTINGS_KEY) || 'null') as Partial<VoiceSettings> | null
    if (raw?.version !== 1) return { ...defaults }
    const voiceKey = voiceOptions.some(option => option.key === raw.voiceKey) ? raw.voiceKey! : defaults.voiceKey
    const rate = rateOptions.some(option => option.value === raw.rate) ? raw.rate! : defaults.rate
    const volume = Math.min(1, Math.max(0, Number(raw.volume ?? defaults.volume)))
    return { version: 1, voiceKey, rate, volume }
  } catch {
    return { ...defaults }
  }
}

const settings = ref<VoiceSettings>(loadSettings())
let watching = false

export function useVoiceSettings() {
  if (!watching) {
    watching = true
    watch(settings, value => localStorage.setItem(VOICE_SETTINGS_KEY, JSON.stringify(value)), { deep: true })
  }

  return {
    settings,
    volumePercent: computed({
      get: () => Math.round(settings.value.volume * 100),
      set: value => { settings.value.volume = Number(value) / 100 },
    }),
    voiceOptions,
    rateOptions,
  }
}
