import React, { useEffect, useState } from 'react'
import { enrollmentApi, CourseRecommendation, CourseRecommendationItem } from '../api/enrollment'
import { useAuthStore } from '../stores/useAuthStore'

const priorityColor = (score: number) => {
  if (score >= 80) return 'bg-red-50 border-red-200 text-red-700'
  if (score >= 65) return 'bg-orange-50 border-orange-200 text-orange-700'
  if (score >= 50) return 'bg-blue-50 border-blue-200 text-blue-700'
  return 'bg-slate-50 border-slate-200 text-slate-600'
}

const priorityLabel = (score: number) => {
  if (score >= 80) return '强烈推荐'
  if (score >= 65) return '推荐'
  if (score >= 50) return '建议'
  return '可选'
}

const CourseRecommendationWidget: React.FC = () => {
  const user = useAuthStore((s) => s.user)
  const [data, setData] = useState<CourseRecommendation | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'picks' | 'all' | 'study' | 'sprint'>('picks')

  useEffect(() => {
    if (!user) return
    setLoading(true)
    enrollmentApi
      .getCourseRecommendation()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [user])

  if (!user) return null
  if (loading) return <div className="py-4 text-center text-sm text-slate-400">正在生成个性化建议...</div>
  if (!data || data.message) {
    return data?.message ? <div className="text-sm text-slate-500">{data.message}</div> : null
  }

  const renderPicks = (picks: CourseRecommendationItem[]) => (
    <div className="space-y-3">
      <div className="rounded-lg bg-blue-50 p-3">
        <p className="text-sm font-medium text-blue-800">
          📝 下次考试建议报考以下 {picks.length} 门课程（已根据您的背景智能排序）
        </p>
      </div>
      {picks.map((item, idx) => (
        <div key={item.code} className={`rounded-lg border p-4 ${priorityColor(item.priority_score)}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-xs font-bold shadow-sm">{idx + 1}</span>
                <span className="text-sm font-semibold">{item.code} {item.name}</span>
                <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs font-medium">
                  {priorityLabel(item.priority_score)}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span className="rounded bg-white/60 px-1.5 py-0.5">{item.credits}学分</span>
                <span className="rounded bg-white/60 px-1.5 py-0.5">{item.course_type === 'required' ? '必考' : '选考'}</span>
                <span className="rounded bg-white/60 px-1.5 py-0.5">约{item.estimated_hours}h</span>
                {item.question_count > 0 && <span className="rounded bg-white/60 px-1.5 py-0.5">{item.question_count}题</span>}
              </div>
              <div className="mt-2 text-xs leading-5 opacity-80">💡 {item.reason}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )

  const renderStudyPlan = () => {
    const plan = data.study_plan
    if (!plan || plan.message) return <div className="text-sm text-slate-500">{plan?.message || '暂无学习计划'}</div>

    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-blue-50 p-3 text-center">
            <div className="text-xl font-bold text-blue-700">{plan.total_courses}</div>
            <div className="text-xs text-blue-600">剩余课程</div>
          </div>
          <div className="rounded-lg bg-green-50 p-3 text-center">
            <div className="text-xl font-bold text-green-700">{plan.total_phases}</div>
            <div className="text-xs text-green-600">考期安排</div>
          </div>
          <div className="rounded-lg bg-amber-50 p-3 text-center">
            <div className="text-xl font-bold text-amber-700">{plan.daily_hours}h</div>
            <div className="text-xs text-amber-600">每日学习</div>
          </div>
        </div>

        {plan.phases.map((phase) => (
          <div key={phase.phase} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-slate-800">
                第{phase.phase}考期（{phase.courses.length}门）
              </h4>
              <span className="text-xs text-slate-500">约{phase.total_hours}h · {phase.weeks_needed}周</span>
            </div>
            <div className="mt-2 space-y-1">
              {phase.courses.map((c) => (
                <div key={c.code} className="flex items-center justify-between rounded bg-slate-50 px-3 py-1.5 text-xs">
                  <span className="font-medium text-slate-800">{c.code} {c.name}</span>
                  <span className="text-slate-500">{c.credits}分 · {c.hours}h</span>
                </div>
              ))}
            </div>
            <div className="mt-2 text-xs text-blue-600">📋 {phase.strategy}</div>
          </div>
        ))}
      </div>
    )
  }

  const renderSprint = () => {
    const sprint = data.sprint_plan
    if (!sprint) return <div className="text-sm text-slate-500">暂无冲刺计划</div>

    return (
      <div className="space-y-3">
        <div className="rounded-lg bg-orange-50 p-3">
          <p className="text-sm font-medium text-orange-800">
            🔥 {sprint.sprint_weeks}周冲刺计划 · 每日{sprint.daily_hours}小时 · {sprint.course_count}门课
          </p>
        </div>

        <div className="space-y-2">
          {sprint.picks.map((p) => (
            <div key={p.code} className="flex items-center justify-between rounded-lg border border-orange-100 bg-orange-50/50 px-3 py-2">
              <span className="text-sm font-medium text-slate-800">{p.code} {p.name}</span>
              <span className="text-xs text-slate-500">{p.credits}分</span>
            </div>
          ))}
        </div>

        {sprint.weeks.map((week, idx) => (
          <div key={idx} className="rounded-lg border border-slate-200 bg-white p-4">
            <h4 className="text-sm font-semibold text-slate-800">{week.period}</h4>
            <p className="mt-1 text-xs text-blue-600">🎯 {week.focus}</p>
            <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs text-slate-600">
              {week.tasks.map((task, i) => <li key={i}>{task}</li>)}
            </ul>
          </div>
        ))}

        <div className="rounded-lg bg-amber-50 p-3">
          <p className="text-xs font-medium text-amber-800">💡 备考小贴士</p>
          <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-amber-700">
            {sprint.tips.map((tip, i) => <li key={i}>{tip}</li>)}
          </ul>
        </div>
      </div>
    )
  }

  const tabs = [
    { key: 'picks' as const, label: '下次报考建议', icon: '📝' },
    { key: 'all' as const, label: '全部推荐排序', icon: '📊' },
    { key: 'study' as const, label: '学习计划', icon: '📅' },
    { key: 'sprint' as const, label: '冲刺计划', icon: '🔥' },
  ]

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">🎯 个性化报考建议</h3>
        <div className="flex gap-2 text-xs text-slate-500">
          <span>已过 {data.total_passed} 门</span>
          <span>·</span>
          <span>剩余 {data.total_remaining} 门</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-3 flex gap-1 overflow-x-auto border-b border-slate-100 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium transition ${
              activeTab === tab.key
                ? 'bg-blue-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="mt-4">
        {activeTab === 'picks' && renderPicks(data.next_exam_picks)}
        {activeTab === 'all' && renderPicks(data.recommendations)}
        {activeTab === 'study' && renderStudyPlan()}
        {activeTab === 'sprint' && renderSprint()}
      </div>
    </div>
  )
}

export default CourseRecommendationWidget
