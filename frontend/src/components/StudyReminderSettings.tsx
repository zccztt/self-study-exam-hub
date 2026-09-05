import React, { useState } from 'react'
import { Button, Card } from '../components/ui'
import { useStudyReminder } from '../hooks/useStudyReminder'

const dayLabels = ['日', '一', '二', '三', '四', '五', '六']

const StudyReminderSettings: React.FC = () => {
  const { config, supported, permissionGranted, enable, disable, updateConfig } = useStudyReminder()
  const [enabling, setEnabling] = useState(false)

  if (!supported) {
    return (
      <Card className="p-5">
        <div className="text-sm text-slate-500">当前浏览器不支持通知功能，无法设置学习提醒。</div>
      </Card>
    )
  }

  const handleEnable = async () => {
    setEnabling(true)
    const granted = await enable()
    setEnabling(false)
    if (!granted) {
      alert('通知权限被拒绝，请在浏览器设置中允许本站发送通知。')
    }
  }

  const toggleDay = (day: number) => {
    const days = config.days.includes(day)
      ? config.days.filter((d) => d !== day)
      : [...config.days, day].sort()
    updateConfig({ days })
  }

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-950">学习提醒</h3>
          <p className="mt-1 text-sm text-slate-500">
            设置每日提醒时间，到点后浏览器弹出通知帮助你保持备考节奏。
          </p>
        </div>
        {config.enabled ? (
          <Button variant="outline" size="sm" onClick={disable}>关闭提醒</Button>
        ) : (
          <Button size="sm" loading={enabling} onClick={() => void handleEnable()}>
            {permissionGranted ? '开启提醒' : '授权并开启'}
          </Button>
        )}
      </div>

      {config.enabled && (
        <div className="mt-5 space-y-4 animate-slide-up">
          {/* Time picker */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-700">提醒时间</label>
            <input
              type="time"
              value={`${String(config.hour).padStart(2, '0')}:${String(config.minute).padStart(2, '0')}`}
              onChange={(e) => {
                const [h, m] = e.target.value.split(':').map(Number)
                updateConfig({ hour: h, minute: m })
              }}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
            />
          </div>

          {/* Day selector */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">提醒日期</label>
            <div className="flex gap-2">
              {dayLabels.map((label, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => toggleDay(index)}
                  className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition-all ${
                    config.days.includes(index)
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'border border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom message */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">提醒内容</label>
            <input
              type="text"
              value={config.message}
              onChange={(e) => updateConfig({ message: e.target.value })}
              className="w-full rounded-lg border border-slate-200 px-3.5 py-2.5 text-sm outline-none transition-all placeholder:text-slate-400 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
              placeholder="自定义提醒内容"
            />
          </div>

          {/* Status */}
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            ✓ 提醒已开启 · 每{config.days.length === 7 ? '天' : `周${config.days.map(d => dayLabels[d]).join('、')}`}
            {' '}{String(config.hour).padStart(2, '0')}:{String(config.minute).padStart(2, '0')} 提醒
          </div>
        </div>
      )}
    </Card>
  )
}

export default StudyReminderSettings
