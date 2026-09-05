import React, { useEffect, useState } from 'react'
import { examCalendarApi, ExamEvent } from '../api/exam-calendar'

const UpcomingExamWidget: React.FC = () => {
  const [events, setEvents] = useState<ExamEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    examCalendarApi.getUpcomingEvents()
      .then(setEvents)
      .catch(() => {
        // API not available, silently hide widget
        setEvents([])
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return null
  }

  if (events.length === 0) {
    return null
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-bold text-slate-950">⏰ 即将到来</h3>
      <p className="mt-1 text-sm text-slate-500">近期重要时间节点</p>

      <div className="mt-4 space-y-3">
        {events.slice(0, 4).map((event, idx) => {
          const days = event.days_until
          const urgency = event.urgency

          // 根据紧急程度设置样式和动画
          let urgentClass = 'border-slate-200 bg-slate-50'
          let countdownColor = 'text-slate-900'
          let pulseAnimation = ''

          if (event.status === 'active') {
            urgentClass = 'border-green-200 bg-green-50'
            countdownColor = 'text-green-700'
          } else if (urgency === 'critical') {
            urgentClass = 'border-red-200 bg-red-50 shadow-lg'
            countdownColor = 'text-red-700'
            pulseAnimation = 'animate-pulse'
          } else if (urgency === 'warning') {
            urgentClass = 'border-orange-200 bg-orange-50 shadow-md'
            countdownColor = 'text-orange-700'
          } else if (urgency === 'attention') {
            urgentClass = 'border-yellow-200 bg-yellow-50'
            countdownColor = 'text-yellow-700'
          }

          const statusBadge =
            event.status === 'active'
              ? <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">进行中</span>
              : urgency === 'critical'
                ? <span className={`rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700 ${pulseAnimation}`}>紧急</span>
                : urgency === 'warning'
                  ? <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700">即将开始</span>
                  : urgency === 'attention'
                    ? <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">注意</span>
                    : null

          return (
            <div key={idx} className={`rounded-lg border p-4 transition-all ${urgentClass}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-900">{event.title}</span>
                    {statusBadge}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{event.date}</div>
                  {event.description && (
                    <div className="mt-1 text-xs text-slate-500">{event.description}</div>
                  )}
                </div>
                {days !== null && days >= 0 && (
                  <div className="text-right">
                    <div className={`text-3xl font-bold ${countdownColor} ${pulseAnimation}`}>{days}</div>
                    <div className="text-xs text-slate-500">天后</div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default UpcomingExamWidget
