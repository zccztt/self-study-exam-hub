import { useEffect, useState } from 'react'

export default function OfflineIndicator() {
  const [online, setOnline] = useState(navigator.onLine)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    const handleOnline = () => { setOnline(true); setDismissed(false) }
    const handleOffline = () => setOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (online || dismissed) return null

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm animate-slide-up">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-amber-600">⚠</span>
          <div>
            <span className="font-medium text-amber-800">当前处于离线状态</span>
            <span className="ml-2 text-amber-700">仅可查看已缓存的内容，新数据将在联网后同步。</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="rounded-md px-2 py-1 text-amber-600 hover:bg-amber-100 transition-colors"
          aria-label="关闭"
        >
          ✕
        </button>
      </div>
    </div>
  )
}
