import { onUnmounted, ref } from 'vue'
import { getAuthToken, type NotificationRecord } from '../services/profile'

interface NotificationSocketOptions {
  onNotification: (notification: NotificationRecord) => void
}

/** 通知 WebSocket：首帧认证，并在异常断开后按上限退避重连。 */
export function useNotificationSocket(options: NotificationSocketOptions) {
  const connected = ref(false)
  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  let stopped = false

  function scheduleReconnect() {
    if (stopped || reconnectTimer || !getAuthToken()) return
    const delay = Math.min(30000, 1000 * 2 ** reconnectAttempts)
    reconnectAttempts += 1
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  function connect() {
    if (socket || stopped || !getAuthToken()) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const current = new WebSocket(`${protocol}//${window.location.host}/api/profile/notifications/ws`)
    socket = current

    current.onopen = () => {
      if (socket !== current) return
      connected.value = true
      reconnectAttempts = 0
      current.send(JSON.stringify({ auth_token: getAuthToken() }))
    }

    current.onmessage = (event) => {
      if (socket !== current) return
      try {
        const payload = JSON.parse(event.data)
        const notification = payload.notification || payload.data || payload
        if (notification?.id != null) options.onNotification(notification as NotificationRecord)
      } catch {
        console.warn('收到无法解析的通知消息')
      }
    }

    current.onclose = () => {
      if (socket !== current) return
      socket = null
      connected.value = false
      scheduleReconnect()
    }

    current.onerror = () => current.close()
  }

  function disconnect() {
    stopped = true
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = null
    const current = socket
    socket = null
    current?.close()
    connected.value = false
  }

  onUnmounted(disconnect)

  return { connected, connect, disconnect }
}
