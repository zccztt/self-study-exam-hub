import { useCallback, useEffect, useState } from 'react'

const REMINDER_KEY = 'study_reminder_config'

export interface ReminderConfig {
  enabled: boolean
  /** Hour of day (0-23) to send reminder */
  hour: number
  /** Minute (0-59) */
  minute: number
  /** Days of week enabled (0=Sun, 1=Mon ... 6=Sat) */
  days: number[]
  /** Custom message */
  message: string
}

const defaultConfig: ReminderConfig = {
  enabled: false,
  hour: 20,
  minute: 0,
  days: [1, 2, 3, 4, 5, 6, 0], // all days
  message: '今天的学习任务完成了吗？每天坚持，离通过更近一步！',
}

function loadConfig(): ReminderConfig {
  try {
    const stored = localStorage.getItem(REMINDER_KEY)
    if (stored) return { ...defaultConfig, ...JSON.parse(stored) }
  } catch { /* ignore */ }
  return defaultConfig
}

function saveConfig(config: ReminderConfig) {
  localStorage.setItem(REMINDER_KEY, JSON.stringify(config))
}

async function requestPermission(): Promise<boolean> {
  if (!('Notification' in window)) return false
  if (Notification.permission === 'granted') return true
  if (Notification.permission === 'denied') return false
  const result = await Notification.requestPermission()
  return result === 'granted'
}

function showNotification(config: ReminderConfig) {
  if (Notification.permission !== 'granted') return
  const notification = new Notification('📚 自考备考提醒', {
    body: config.message,
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    tag: 'study-reminder',
    requireInteraction: false,
  })
  notification.onclick = () => {
    window.focus()
    notification.close()
  }
}

export function useStudyReminder() {
  const [config, setConfig] = useState<ReminderConfig>(loadConfig)
  const [permissionGranted, setPermissionGranted] = useState(
    typeof Notification !== 'undefined' && Notification.permission === 'granted',
  )
  const [supported] = useState(() => 'Notification' in window)

  const updateConfig = useCallback((updates: Partial<ReminderConfig>) => {
    setConfig((current) => {
      const next = { ...current, ...updates }
      saveConfig(next)
      return next
    })
  }, [])

  const enable = useCallback(async () => {
    const granted = await requestPermission()
    setPermissionGranted(granted)
    if (granted) {
      updateConfig({ enabled: true })
    }
    return granted
  }, [updateConfig])

  const disable = useCallback(() => {
    updateConfig({ enabled: false })
  }, [updateConfig])

  // Check every minute if it's time to send a reminder
  useEffect(() => {
    if (!config.enabled || !permissionGranted) return

    let lastFiredKey = ''

    const checkTime = () => {
      const now = new Date()
      const dayKey = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}-${config.hour}-${config.minute}`

      if (
        now.getHours() === config.hour &&
        now.getMinutes() === config.minute &&
        config.days.includes(now.getDay()) &&
        lastFiredKey !== dayKey
      ) {
        lastFiredKey = dayKey
        showNotification(config)
      }
    }

    // Check immediately and then every 30 seconds
    checkTime()
    const interval = setInterval(checkTime, 30000)
    return () => clearInterval(interval)
  }, [config, permissionGranted])

  return {
    config,
    supported,
    permissionGranted,
    enable,
    disable,
    updateConfig,
  }
}
