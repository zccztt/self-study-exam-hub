import React, { useEffect, useState } from 'react'
import { enrollmentApi, EnrollmentListItem, SubjectStatusItem } from '../api/enrollment'
import { examCalendarApi, StudyPlanSuggestion } from '../api/exam-calendar'
import { useAuthStore } from '../stores/useAuthStore'

const StudyPlanWidget: React.FC = () => {
  const user = useAuthStore((s) => s.user)
  const [enrollments, setEnrollments] = useState<EnrollmentListItem[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [suggestion, setSuggestion] = useState<StudyPlanSuggestion | null>(null)
  const [loading, setLoading] = useState(true)
  const [calcLoading, setCalcLoading] = useState(false)

  useEffect(() => {
    if (!user) {
      setLoading(false)
      return
    }
    enrollmentApi.listEnrollments()
      .then((data) => {
        setEnrollments(data)
        // Auto-select all
        setSelectedIds(data.map((e) => e.id))
      })
      .catch(() => setEnrollments([]))
      .finally(() => setLoading(false))
  }, [user])

  const toggleSelection = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  useEffect(() => {
    if (selectedIds.length === 0) {
      setSuggestion(null)
      return
    }
    const loadSuggestion = async () => {
      setCalcLoading(true)
      try {
        // Load all subjects from selected enrollments
        const results = await Promise.all(
          selectedIds.map((id) => enrollmentApi.getEnrollmentSubjects(id)),
        )

        // Merge and deduplicate subjects by code
        const subjectMap = new Map<string, SubjectStatusItem>()
        for (const data of results) {
          const subjects = [
            ...data.subjects.required,
            ...data.subjects.elective,
            ...data.subjects.additional,
          ]
          for (const s of subjects) {
            const existing = subjectMap.get(s.code)
            if (!existing || (s.status === 'passed' && existing.status !== 'passed')) {
              subjectMap.set(s.code, s)
            }
          }
        }

        const remaining = Array.from(subjectMap.values()).filter(
          (s) => s.status !== 'passed',
        ).length

        // Use earliest target date
        const targetDates = selectedIds
          .map((id) => enrollments.find((e) => e.id === id)?.target_date)
          .filter((d): d is string => !!d)
        const earliestTarget = targetDates.length > 0 ? targetDates.sort()[0] : undefined

        const plan = await examCalendarApi.getStudyPlanSuggestion(remaining, earliestTarget)
        setSuggestion(plan)
      } catch {
        setSuggestion(null)
      } finally {
        setCalcLoading(false)
      }
    }
    void loadSuggestion()
  }, [selectedIds])

  if (!user || loading) {
    return null
  }

  if (enrollments.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-bold text-slate-950">📋 报考建议</h3>
        <p className="mt-2 text-sm text-slate-500">暂无报考记录，请先新增报考。</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-bold text-slate-950">📋 报考建议</h3>
      <p className="mt-1 text-sm text-slate-500">选择报考专业，综合生成备考建议（可多选）</p>

      {/* Multi-select */}
      <div className="mt-4 space-y-2">
        {enrollments.map((enrollment) => {
          const checked = selectedIds.includes(enrollment.id)
          const remaining = enrollment.progress.not_taken + enrollment.progress.failed
          return (
            <label
              key={enrollment.id}
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition ${
                checked
                  ? 'border-blue-300 bg-blue-50'
                  : 'border-slate-200 bg-slate-50 hover:border-blue-200'
              }`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggleSelection(enrollment.id)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-900 truncate">
                  {enrollment.major_name}({enrollment.level === 'bk' ? '本科' : '专科'})
                </div>
                <div className="text-xs text-slate-500">
                  {enrollment.school_name} · 剩余{remaining}科
                </div>
              </div>
            </label>
          )
        })}
      </div>

      {/* Results */}
      {calcLoading ? (
        <div className="mt-4 py-4 text-center text-sm text-slate-400">分析中...</div>
      ) : suggestion ? (
        <div className="mt-4 space-y-3">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg bg-blue-50 p-3 text-center">
              <div className="text-xl font-bold text-blue-700">{suggestion.remaining_subjects}</div>
              <div className="text-xs text-blue-600">剩余科目</div>
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <div className="text-xl font-bold text-green-700">{suggestion.required_sessions}</div>
              <div className="text-xs text-green-600">需要考期</div>
            </div>
            <div className={`rounded-lg p-3 text-center ${suggestion.can_finish_on_time ? 'bg-green-50' : 'bg-amber-50'}`}>
              <div className={`text-xl font-bold ${suggestion.can_finish_on_time ? 'text-green-700' : 'text-amber-700'}`}>
                {suggestion.can_finish_on_time ? '✅' : '⚠️'}
              </div>
              <div className={`text-xs ${suggestion.can_finish_on_time ? 'text-green-600' : 'text-amber-600'}`}>
                {suggestion.can_finish_on_time ? '可按期完成' : '时间紧张'}
              </div>
            </div>
          </div>

          {/* Advice */}
          {suggestion.recommendation && (
            <div className="rounded-lg bg-blue-50 p-3">
              <p className="text-sm leading-6 text-blue-800">💡 {suggestion.recommendation}</p>
            </div>
          )}

          {/* Timeline */}
          {suggestion.timeline && suggestion.timeline.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-600">建议报考时间线</div>
              {suggestion.timeline.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5">
                  <div>
                    <div className="text-sm font-medium text-slate-900">{item.exam_date} 考期</div>
                    <div className="text-xs text-slate-500">报名: {item.registration_period}</div>
                  </div>
                  <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
                    报{item.suggested_subjects}科
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Tips */}
          <div className="rounded-lg bg-amber-50 p-3">
            <p className="text-xs font-medium text-amber-800">💡 报考小贴士</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-amber-700">
              <li>每次考试最多报4科，建议公共课+专业课搭配</li>
              <li>实践课需对应理论课先通过后方可报考</li>
              <li>关注省考试院官网，及时了解报名时间变动</li>
            </ul>
          </div>
        </div>
      ) : selectedIds.length > 0 ? null : (
        <div className="mt-4 text-center text-sm text-slate-400">请选择至少一个报考专业</div>
      )}
    </div>
  )
}

export default StudyPlanWidget
