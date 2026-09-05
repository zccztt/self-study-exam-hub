import React, { FormEvent, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AIAdvice, DailyTask, plannerApi, PlanPhase, PlanTask, StudyPlan, StudyPlanSummary, TimeAllocation, WeakPoint } from '../api/planner'
import { enrollmentApi, EnrollmentListItem } from '../api/enrollment'
import { sessionStore } from '../api/session'
import Pagination from '../components/ui/Pagination'
import { subjectApi, Subject } from '../api/subject'

const formatDate = (value: string) => new Date(value).toLocaleDateString()

const dateKey = (value: string | Date) => {
  const date = value instanceof Date ? value : new Date(value)
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const addDays = (date: Date, days: number) => {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

const daysBetween = (start: Date, end: Date) => Math.max(0, Math.round((end.getTime() - start.getTime()) / 86400000))

const buildCalendarWeeks = (tasks: PlanTask[]) => {
  if (tasks.length === 0) return []
  const sortedTasks = [...tasks].sort((a, b) => dateKey(a.date).localeCompare(dateKey(b.date)))
  const tasksByDate = new Map<string, PlanTask[]>()
  sortedTasks.forEach((task) => {
    const key = dateKey(task.date)
    tasksByDate.set(key, [...(tasksByDate.get(key) || []), task])
  })

  const start = new Date(dateKey(sortedTasks[0].date))
  const end = new Date(dateKey(sortedTasks[sortedTasks.length - 1].date))
  const weekOffset = (start.getDay() + 6) % 7
  const cursor = addDays(start, -weekOffset)
  const weeks = []

  while (cursor <= end || weeks.length === 0 || weeks[weeks.length - 1].length < 7) {
    const week = []
    for (let index = 0; index < 7; index += 1) {
      const current = addDays(cursor, index)
      const key = dateKey(current)
      week.push({ date: key, tasks: tasksByDate.get(key) || [] })
    }
    weeks.push(week)
    cursor.setDate(cursor.getDate() + 7)
  }
  return weeks
}

const buildGanttItems = (phases: PlanPhase[]) => {
  if (phases.length === 0) return []
  const starts = phases.map((phase) => new Date(dateKey(phase.start_date)))
  const ends = phases.map((phase) => new Date(dateKey(phase.end_date)))
  const start = new Date(Math.min(...starts.map((date) => date.getTime())))
  const end = new Date(Math.max(...ends.map((date) => date.getTime())))
  const totalDays = Math.max(1, daysBetween(start, end) + 1)

  return phases.map((phase) => {
    const phaseStart = new Date(dateKey(phase.start_date))
    const phaseEnd = new Date(dateKey(phase.end_date))
    const offset = daysBetween(start, phaseStart)
    const duration = Math.max(1, daysBetween(phaseStart, phaseEnd) + 1)
    return {
      ...phase,
      left: (offset / totalDays) * 100,
      width: Math.max(6, (duration / totalDays) * 100),
      duration,
    }
  })
}

const daysUntil = (value: string) => {
  const target = new Date(value).getTime()
  const now = new Date().setHours(0, 0, 0, 0)
  return Math.max(0, Math.ceil((target - now) / 86400000))
}

const PlannerPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const enrollmentIdParam = searchParams.get('enrollment_id')
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedSubjects, setSelectedSubjects] = useState<number[]>([])
  const [examDate, setExamDate] = useState('2026-10-24')
  const [dailyHours, setDailyHours] = useState(2)
  const [currentPlan, setCurrentPlan] = useState<StudyPlan | null>(null)
  const [planHistory, setPlanHistory] = useState<StudyPlanSummary[]>([])
  const [historyPage, setHistoryPage] = useState(1)
  const [historyTotal, setHistoryTotal] = useState(0)
  const [calendarPage, setCalendarPage] = useState(1)
  const [dailyTasks, setDailyTasks] = useState<DailyTask[]>([])
  const [selectedTaskDate, setSelectedTaskDate] = useState(dateKey(new Date()))
  const [weakPoints, setWeakPoints] = useState<WeakPoint[]>([])
  const [allocation, setAllocation] = useState<TimeAllocation | null>(null)
  const [actualHours, setActualHours] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [enrollmentId, setEnrollmentId] = useState<number | null>(
    enrollmentIdParam ? Number(enrollmentIdParam) : null,
  )
  const [enrollments, setEnrollments] = useState<EnrollmentListItem[]>([])
  const [userContext, setUserContext] = useState('')
  const [aiAdvice, setAiAdvice] = useState<AIAdvice | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiConsultText, setAiConsultText] = useState('')
  const [aiConsultResult, setAiConsultResult] = useState<AIAdvice | null>(null)
  const [aiConsultLoading, setAiConsultLoading] = useState(false)
  const [aiConsultOpen, setAiConsultOpen] = useState(false)

  const subjectNameById = useMemo(
    () => new Map(subjects.map((subject) => [subject.id, subject.name])),
    [subjects],
  )

  const loadPlannerData = async (preferredSubjectId?: number, taskDate = selectedTaskDate, nextHistoryPage = historyPage) => {
    setError('')
    try {
      const userId = sessionStore.getUserId()
      const [planData, taskData, historyData] = await Promise.all([
        plannerApi.getLatestPlan(userId),
        plannerApi.getDailyTasks(userId, `${taskDate}T00:00:00`),
        plannerApi.getPlanHistory(userId, nextHistoryPage, 10),
      ])
      setCurrentPlan(planData)
      setDailyTasks(taskData)
      setPlanHistory(historyData.items)
      setHistoryPage(historyData.page)
      setHistoryTotal(historyData.total)
      if (planData?.plan_data?.ai_advice) {
        setAiAdvice(planData.plan_data.ai_advice)
      }

      const weakSubjectId = preferredSubjectId || planData?.subjects[0]
      if (weakSubjectId) {
        const [weakData, allocationData] = await Promise.all([
          plannerApi.getWeakPoints(weakSubjectId, userId),
          plannerApi.allocateTime(
            planData?.plan_data.days || 30,
            planData?.daily_hours || dailyHours,
            weakSubjectId,
            userId,
          ),
        ])
        setWeakPoints(weakData)
        setAllocation(planData?.plan_data.allocation || allocationData)
      } else {
        setWeakPoints([])
        setAllocation(planData?.plan_data.allocation || null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '学习规划数据加载失败')
    }
  }

  useEffect(() => {
    const initialize = async () => {
      setLoading(true)
      try {
        const [subjectData, enrollmentData] = await Promise.all([
          subjectApi.list(undefined, true),
          enrollmentApi.listEnrollments().catch(() => []),
        ])
        setSubjects(subjectData)
        setEnrollments(enrollmentData)
        if (subjectData[0]) {
          setSelectedSubjects([subjectData[0].id])
        }
        // 如果 URL 带了 enrollment_id，自动预加载对应剩余科目
        if (enrollmentIdParam) {
          try {
            const remaining = await enrollmentApi.getRemainingSubjects(Number(enrollmentIdParam))
            if (remaining.length > 0) {
              setSelectedSubjects(remaining)
            }
          } catch {
            // ignore - 用户可手动选择
          }
        }
        await loadPlannerData(subjectData[0]?.id)
      } catch (err) {
        setError(err instanceof Error ? err.message : '初始化学习规划失败')
      } finally {
        setLoading(false)
      }
    }
    void initialize()
  }, [])

  const toggleSubject = (subjectId: number) => {
    setSelectedSubjects((current) =>
      current.includes(subjectId)
        ? current.filter((item) => item !== subjectId)
        : [...current, subjectId],
    )
  }

  const loadDailyTasks = async (taskDate: string) => {
    setSelectedTaskDate(taskDate)
    setError('')
    try {
      const tasks = await plannerApi.getDailyTasks(sessionStore.getUserId(), `${taskDate}T00:00:00`)
      setDailyTasks(tasks)
    } catch (err) {
      setError(err instanceof Error ? err.message : '学习任务加载失败')
    }
  }

  const shiftTaskDate = (days: number) => {
    void loadDailyTasks(dateKey(addDays(new Date(`${selectedTaskDate}T00:00:00`), days)))
  }

  const loadPlanHistory = async (page: number) => {
    setError('')
    try {
      const data = await plannerApi.getPlanHistory(sessionStore.getUserId(), page, 10)
      setPlanHistory(data.items)
      setHistoryPage(data.page)
      setHistoryTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '计划历史加载失败')
    }
  }

  const activateHistoricalPlan = async (planId: number) => {
    if (!window.confirm('确定恢复这份学习计划吗？当前计划会转入历史记录。')) return
    setLoading(true)
    setError('')
    try {
      const plan = await plannerApi.activatePlan(planId)
      setSelectedSubjects(plan.subjects)
      setExamDate(dateKey(plan.exam_date))
      setDailyHours(plan.daily_hours)
      await loadPlannerData(plan.subjects[0])
      setMessage('历史学习计划已恢复。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '恢复学习计划失败')
    } finally {
      setLoading(false)
    }
  }

  const deleteHistoricalPlan = async (planId: number) => {
    if (!window.confirm('确定永久删除这份历史计划吗？相关每日任务记录也会删除。')) return
    setLoading(true)
    setError('')
    try {
      await plannerApi.deletePlan(planId)
      const nextPage = planHistory.length === 1 && historyPage > 1 ? historyPage - 1 : historyPage
      await loadPlanHistory(nextPage)
      setMessage('历史学习计划已删除。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除学习计划失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')

    if (!examDate) {
      setError('请选择考试日期')
      return
    }
    if (selectedSubjects.length === 0) {
      setError('请至少选择一门报考科目')
      return
    }

    setLoading(true)
    try {
      const plan = await plannerApi.generatePlan({
        exam_date: `${examDate}T00:00:00`,
        subjects: enrollmentId ? undefined : selectedSubjects,
        daily_hours: dailyHours,
        enrollment_id: enrollmentId || undefined,
      })
      setCurrentPlan(plan)
      setMessage('学习计划已生成')
      if (plan.plan_data?.ai_advice) {
        setAiAdvice(plan.plan_data.ai_advice)
      }
      const [taskData, weakData, allocationData, historyData] = await Promise.all([
        plannerApi.getDailyTasks(sessionStore.getUserId(), `${selectedTaskDate}T00:00:00`),
        plannerApi.getWeakPoints(selectedSubjects[0], sessionStore.getUserId()),
        plannerApi.allocateTime(plan.plan_data.days || 30, plan.daily_hours, selectedSubjects[0], sessionStore.getUserId()),
        plannerApi.getPlanHistory(sessionStore.getUserId(), 1, 10),
      ])
      setDailyTasks(taskData)
      setWeakPoints(weakData)
      setAllocation(plan.plan_data.allocation || allocationData)
      setPlanHistory(historyData.items)
      setHistoryPage(historyData.page)
      setHistoryTotal(historyData.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成学习计划失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAIGenerate = async () => {
    setError('')
    setMessage('')

    if (!examDate) {
      setError('请选择考试日期')
      return
    }
    if (selectedSubjects.length === 0) {
      setError('请至少选择一门报考科目')
      return
    }
    if (!userContext.trim()) {
      setError('请填写个人情况描述后再使用 AI 智能规划')
      return
    }

    setAiLoading(true)
    try {
      const plan = await plannerApi.generatePlan({
        exam_date: `${examDate}T00:00:00`,
        subjects: enrollmentId ? undefined : selectedSubjects,
        daily_hours: dailyHours,
        enrollment_id: enrollmentId || undefined,
        user_context: userContext.trim(),
      })
      setCurrentPlan(plan)
      setMessage('AI 智能学习计划已生成')
      if (plan.plan_data?.ai_advice) {
        setAiAdvice(plan.plan_data.ai_advice)
      }
      const [taskData, weakData, allocationData, historyData] = await Promise.all([
        plannerApi.getDailyTasks(sessionStore.getUserId(), `${selectedTaskDate}T00:00:00`),
        plannerApi.getWeakPoints(selectedSubjects[0], sessionStore.getUserId()),
        plannerApi.allocateTime(plan.plan_data.days || 30, plan.daily_hours, selectedSubjects[0], sessionStore.getUserId()),
        plannerApi.getPlanHistory(sessionStore.getUserId(), 1, 10),
      ])
      setDailyTasks(taskData)
      setWeakPoints(weakData)
      setAllocation(plan.plan_data.allocation || allocationData)
      setPlanHistory(historyData.items)
      setHistoryPage(historyData.page)
      setHistoryTotal(historyData.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI 智能规划失败')
    } finally {
      setAiLoading(false)
    }
  }

  const handleGetAIAdvice = async () => {
    if (!aiConsultText.trim()) return
    setAiConsultLoading(true)
    setError('')
    try {
      const result = await plannerApi.getAIAdvice({
        user_context: aiConsultText.trim(),
        exam_date: examDate ? `${examDate}T00:00:00` : undefined,
        subjects: selectedSubjects.length > 0 ? selectedSubjects : undefined,
        daily_hours: dailyHours,
      })
      setAiConsultResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取 AI 建议失败')
    } finally {
      setAiConsultLoading(false)
    }
  }

  const setTaskCompleted = async (taskId: number, isCompleted: boolean) => {
    setError('')
    try {
      const parsedHours = Number(actualHours[taskId])
      const progress = await plannerApi.updateProgress(
        [{ id: taskId, is_completed: isCompleted, actual_hours: Number.isFinite(parsedHours) && parsedHours > 0 ? parsedHours : undefined }],
        sessionStore.getUserId(),
      )
      setDailyTasks((current) =>
        current.map((task) =>
          task.id === taskId
            ? {
                ...task,
                is_completed: isCompleted,
                actual_hours: Number.isFinite(parsedHours) && parsedHours > 0 ? parsedHours : task.actual_hours,
              }
            : task,
        ),
      )
      setCurrentPlan((plan) => (plan ? { ...plan, completion_rate: progress.completion_rate } : plan))
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新任务进度失败')
    }
  }

  const progress = currentPlan?.completion_rate || 0
  const planTasks = currentPlan?.plan_data.tasks || []
  const planCalendarWeeks = useMemo(() => buildCalendarWeeks(planTasks), [planTasks])
  const calendarPageSize = 12
  const calendarTotalPages = Math.max(1, Math.ceil(planCalendarWeeks.length / calendarPageSize))
  const visibleCalendarWeeks = planCalendarWeeks.slice(
    (calendarPage - 1) * calendarPageSize,
    calendarPage * calendarPageSize,
  )

  useEffect(() => {
    const selectedWeekIndex = planCalendarWeeks.findIndex((week) =>
      week.some((day) => day.date === selectedTaskDate),
    )
    if (selectedWeekIndex >= 0) {
      setCalendarPage(Math.floor(selectedWeekIndex / calendarPageSize) + 1)
    } else {
      setCalendarPage((current) => Math.min(current, calendarTotalPages))
    }
  }, [selectedTaskDate, planCalendarWeeks, calendarTotalPages])
  const planPhases = currentPlan?.plan_data.phases || []
  const ganttItems = useMemo(() => buildGanttItems(planPhases), [planPhases])
  const weeklyGoals = currentPlan?.plan_data.weekly_goals || []
  const dailyTemplate = currentPlan?.plan_data.daily_template || []
  const milestones = currentPlan?.plan_data.milestones || []
  const mockExams = currentPlan?.plan_data.mock_exams || []
  const sprintPlan = currentPlan?.plan_data.sprint_plan || []
  const reviewSchedule = currentPlan?.plan_data.review_schedule || []
  const riskAlerts = currentPlan?.plan_data.risk_alerts || []
  const resourceStrategy = currentPlan?.plan_data.resource_strategy || []

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="text-sm font-medium text-brand-600">系统化备考计划</div>
            <h1 className="mt-1 text-3xl font-bold text-slate-950">学习规划</h1>
            <p className="mt-2 text-sm text-slate-500">
              默认按 2026 年 10 月自考窗口规划，可根据本省公告调整考试日期。
            </p>
          </div>
          <div className="rounded-lg bg-brand-50 px-4 py-3 text-sm text-brand-700">
            建议流程：阶段目标 → 周目标 → 每日任务 → 错题复盘
          </div>
        </div>
      </section>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}
      {message && <div className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-green-700">{message}</div>}

      <form onSubmit={handleGenerate} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">创建学习计划</h2>

        {/* Enrollment quick-select */}
        {enrollments.length > 0 && (
          <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 p-4">
            <label className="block text-sm font-medium text-blue-800 mb-2">
              从报考记录自动获取待考科目（可选）
            </label>
            <select
              value={enrollmentId ?? ''}
              onChange={(e) => {
                const val = e.target.value ? Number(e.target.value) : null
                setEnrollmentId(val)
                if (val) {
                  enrollmentApi.getRemainingSubjects(val).then((ids) => {
                    if (ids.length > 0) setSelectedSubjects(ids)
                  }).catch(() => {})
                }
              }}
              className="w-full rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">手动选择科目</option>
              {enrollments.map((en) => (
                <option key={en.id} value={en.id}>
                  {en.major_name}({en.level === 'bk' ? '本科' : '专科'}) - {en.school_name} (剩余{en.progress.not_taken + en.progress.failed}门)
                </option>
              ))}
            </select>
            {enrollmentId && (
              <p className="mt-2 text-xs text-blue-600">
                ✓ 将自动规划该专业下所有未通过的科目
              </p>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">考试日期</label>
            <input
              type="date"
              value={examDate}
              onChange={(event) => setExamDate(event.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">每日可用学习时长</label>
            <select
              value={dailyHours}
              onChange={(event) => setDailyHours(Number(event.target.value))}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            >
              {[1, 2, 3, 4, 5, 6].map((hours) => (
                <option key={hours} value={hours}>
                  {hours}小时
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-slate-700 mb-2">报考科目</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {subjects.map((subject) => (
                <label key={subject.id} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selectedSubjects.includes(subject.id)}
                    onChange={() => toggleSubject(subject.id)}
                    className="rounded"
                  />
                  <span className="text-sm">{subject.name}（{subject.question_count}题）</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* User context for AI */}
        <div className="mt-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">📝 个人情况描述（可选）</label>
          <textarea
            value={userContext}
            onChange={(event) => setUserContext(event.target.value.slice(0, 2000))}
            placeholder="例如：距离考试只有一个月，之前没有系统学习过，每天下班后有3小时可以学习，希望一次通过..."
            rows={3}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg resize-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none"
          />
          <div className="mt-1 text-right text-xs text-slate-400">{userContext.length}/2000</div>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <button
            type="submit"
            disabled={loading || aiLoading}
            className="w-full sm:w-auto px-6 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:opacity-60"
          >
            {loading ? '处理中...' : '📊 快速生成计划'}
          </button>
          <div className="relative group">
            <button
              type="button"
              disabled={aiLoading || loading || !userContext.trim()}
              onClick={() => void handleAIGenerate()}
              className="w-full sm:w-auto px-6 py-2 bg-gradient-to-r from-violet-500 to-brand-500 text-white rounded-lg hover:from-violet-600 hover:to-brand-600 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {aiLoading ? (
                <span className="inline-flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  AI 分析中...
                </span>
              ) : '🤖 AI 智能规划'}
            </button>
            {!userContext.trim() && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block whitespace-nowrap rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-white shadow-lg">
                请先填写个人情况描述
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
              </div>
            )}
          </div>
        </div>
      </form>

      {planHistory.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-xl font-semibold">计划历史</h2>
            <span className="text-sm text-slate-500">共 {historyTotal} 份</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {planHistory.map((plan) => (
              <div key={plan.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-medium text-slate-950">考试日期 {formatDate(plan.exam_date)}</div>
                    <div className="mt-1 text-sm text-slate-500">
                      {plan.subjects.map((id) => subjectNameById.get(id) || `科目 ${id}`).join('、')} · 每日 {plan.daily_hours} 小时
                    </div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs ${plan.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>
                    {plan.status === 'active' ? '当前' : '已归档'}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3 text-sm">
                  <span className="text-slate-600">完成度 {Number(plan.completion_rate || 0).toFixed(1)}%</span>
                  {plan.status !== 'active' && (
                    <div className="flex items-center gap-2">
                      {daysUntil(plan.exam_date) > 0 ? (
                        <button type="button" disabled={loading} onClick={() => void activateHistoricalPlan(plan.id)} className="rounded-md border border-brand-200 bg-white px-3 py-1.5 font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-50">
                          恢复计划
                        </button>
                      ) : (
                        <span className="text-slate-400">已过期</span>
                      )}
                      <button type="button" disabled={loading} onClick={() => void deleteHistoricalPlan(plan.id)} className="rounded-md border border-red-200 bg-white px-3 py-1.5 font-medium text-red-600 hover:bg-red-50 disabled:opacity-50">
                        删除
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          {historyTotal > 10 && (
            <Pagination
              current={historyPage}
              total={historyTotal}
              pageSize={10}
              loading={loading}
              onChange={(p) => void loadPlanHistory(p)}
              className="mt-4"
            />
          )}
        </section>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between mb-4">
          <h2 className="text-xl font-semibold">当前学习计划</h2>
          {currentPlan && (
            <div className="text-sm text-slate-600">
              距离考试还有 <span className="font-bold text-brand-500">{daysUntil(currentPlan.exam_date)}</span> 天
            </div>
          )}
        </div>

        {currentPlan ? (
          <>
            <div className="mb-6">
              <div className="flex justify-between text-sm text-slate-600 mb-2">
                <span>
                  {formatDate(currentPlan.exam_date)} · 每日 {currentPlan.daily_hours} 小时
                </span>
                <span>{progress.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-3">
                <div className="bg-brand-500 h-3 rounded-full" style={{ width: `${Math.min(100, progress)}%` }} />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-lg border border-slate-200 p-4">
                <div className="text-sm text-slate-500">计划天数</div>
                <div className="mt-1 text-2xl font-bold">{currentPlan.plan_data.days || planTasks.length}</div>
              </div>
              <div className="rounded-lg border border-slate-200 p-4">
                <div className="text-sm text-slate-500">预计通过率</div>
                <div className="mt-1 text-2xl font-bold">
                  {currentPlan.expected_pass_rate ? `${Math.round(currentPlan.expected_pass_rate * 100)}%` : '-'}
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 p-4">
                <div className="text-sm text-slate-500">报考科目</div>
                <div className="mt-1 text-sm">
                  {currentPlan.subjects.map((id) => subjectNameById.get(id) || `科目 ${id}`).join('、')}
                </div>
              </div>
            </div>
            {allocation && (
              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="text-sm text-slate-500">总学习时长</div>
                  <div className="mt-1 text-xl font-bold">{allocation.total_hours} 小时</div>
                </div>
                <div className="rounded-lg border border-red-100 bg-red-50 p-4">
                  <div className="text-sm text-red-700">薄弱点强化</div>
                  <div className="mt-1 text-xl font-bold text-red-700">{allocation.weak_points_hours} 小时</div>
                </div>
                <div className="rounded-lg border border-brand-100 bg-brand-50 p-4">
                  <div className="text-sm text-brand-700">高频考点</div>
                  <div className="mt-1 text-xl font-bold text-brand-700">{allocation.high_frequency_hours} 小时</div>
                </div>
                <div className="rounded-lg border border-green-100 bg-green-50 p-4">
                  <div className="text-sm text-green-700">复盘巩固</div>
                  <div className="mt-1 text-xl font-bold text-green-700">{allocation.review_hours} 小时</div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-slate-500">暂无学习计划</div>
        )}
      </div>

      {/* AI Advice Display */}
      {aiAdvice && (
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="bg-gradient-to-r from-violet-500 to-brand-500 px-6 py-4">
            <h2 className="text-xl font-semibold text-white">🤖 AI 个性化建议</h2>
          </div>
          <div className="p-6 space-y-5">
            {aiAdvice.error && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                ⚠️ {aiAdvice.error}
              </div>
            )}

            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-2">📊 总体评估</h3>
              <p className="text-sm leading-6 text-slate-600 whitespace-pre-line">{aiAdvice.overall_assessment}</p>
            </div>

            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-2">📚 学习策略</h3>
              <p className="text-sm leading-6 text-slate-600 whitespace-pre-line">{aiAdvice.study_strategy}</p>
            </div>

            {aiAdvice.subject_advice && aiAdvice.subject_advice.length > 0 && (
              <div className="rounded-lg border border-slate-200 p-4">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">📋 科目建议</h3>
                <div className="space-y-3">
                  {aiAdvice.subject_advice.map((item) => (
                    <div key={item.subject} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-slate-800">{item.subject}</span>
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            item.priority === 'high'
                              ? 'bg-red-100 text-red-700'
                              : item.priority === 'medium'
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-emerald-100 text-emerald-700'
                          }`}
                        >
                          {item.priority === 'high' ? '高优先' : item.priority === 'medium' ? '中优先' : '低优先'}
                        </span>
                      </div>
                      <p className="text-sm leading-6 text-slate-600">{item.advice}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-2">📅 每日安排建议</h3>
              <p className="text-sm leading-6 text-slate-600 whitespace-pre-line">{aiAdvice.daily_plan_suggestion}</p>
            </div>

            {aiAdvice.risk_warnings && aiAdvice.risk_warnings.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-800 mb-2">⚠️ 风险提示</h3>
                <ul className="space-y-1">
                  {aiAdvice.risk_warnings.map((warning, index) => (
                    <li key={index} className="text-sm leading-6 text-amber-700 flex gap-2">
                      <span className="text-amber-500">•</span>
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {aiAdvice.motivation && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                <h3 className="text-sm font-semibold text-emerald-800 mb-2">💪 加油</h3>
                <p className="text-sm leading-6 text-emerald-700 whitespace-pre-line">{aiAdvice.motivation}</p>
              </div>
            )}
          </div>
        </section>
      )}

      {currentPlan && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold">学习日历</h2>
                <p className="mt-1 text-sm text-slate-500">按周查看每日刷题、复习和视频任务。</p>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <span>共 {planTasks.length} 项任务</span>
                {calendarTotalPages > 1 && (
                  <>
                    <button type="button" disabled={calendarPage <= 1} onClick={() => setCalendarPage((page) => page - 1)} className="rounded-md border border-slate-300 bg-white px-2.5 py-1 disabled:opacity-40">上一段</button>
                    <span>{calendarPage} / {calendarTotalPages}</span>
                    <button type="button" disabled={calendarPage >= calendarTotalPages} onClick={() => setCalendarPage((page) => page + 1)} className="rounded-md border border-slate-300 bg-white px-2.5 py-1 disabled:opacity-40">下一段</button>
                  </>
                )}
              </div>
            </div>
            <div className="mt-4 overflow-x-auto">
              <div className="min-w-[840px]">
                <div className="grid grid-cols-7 gap-2 text-center text-xs font-medium text-slate-500">
                  {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => (
                    <div key={day}>{day}</div>
                  ))}
                </div>
                <div className="mt-2 space-y-2">
                  {visibleCalendarWeeks.map((week) => (
                    <div key={week[0].date} className="grid grid-cols-7 gap-2">
                      {week.map((day) => (
                        <button
                          type="button"
                          key={day.date}
                          onClick={() => void loadDailyTasks(day.date)}
                          className={`min-h-28 rounded-lg border p-2 ${
                            day.date === selectedTaskDate
                              ? 'border-brand-500 bg-brand-100 ring-2 ring-brand-100'
                              : day.tasks.length > 0
                                ? 'border-brand-100 bg-brand-50'
                                : 'border-slate-100 bg-slate-50'
                          }`}
                        >
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <span className="text-xs font-medium text-slate-600">{day.date.slice(5)}</span>
                            {day.date === dateKey(new Date()) && (
                              <span className="rounded-full bg-brand-600 px-2 py-0.5 text-[10px] text-white">今天</span>
                            )}
                          </div>
                          <div className="space-y-1">
                            {day.tasks.slice(0, 2).map((task, index) => (
                              <div key={`${day.date}-${task.subject_id}-${index}`} className="rounded bg-white px-2 py-1 text-xs text-slate-700">
                                <div className="truncate font-medium">
                                  {subjectNameById.get(task.subject_id) || `科目 ${task.subject_id}`}
                                </div>
                                <div className="mt-0.5 truncate text-slate-500">
                                  刷题 {task.question_count} · 复习 {task.review_points.length}
                                  {task.video_ids.length ? ` · 视频 ${task.video_ids.length}` : ''}
                                </div>
                              </div>
                            ))}
                            {day.tasks.length > 2 && (
                              <div className="text-xs text-slate-500">+{day.tasks.length - 2} 项</div>
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  ))}
                  {planCalendarWeeks.length === 0 && <div className="text-sm text-slate-500">生成学习计划后展示日历</div>}
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold">阶段甘特图</h2>
                <p className="mt-1 text-sm text-slate-500">按时间跨度查看基础、强化、模考和冲刺阶段。</p>
              </div>
              <div className="text-sm text-slate-500">{ganttItems.length} 个阶段</div>
            </div>
            <div className="mt-5 overflow-x-auto">
              <div className="min-w-[760px] space-y-4">
                {ganttItems.map((item, index) => (
                  <div key={`${item.name}-${item.start_date}`}>
                    <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                      <div className="font-medium text-slate-800">{item.name}</div>
                      <div className="text-slate-500">
                        {formatDate(item.start_date)} - {formatDate(item.end_date)} · {item.duration} 天
                      </div>
                    </div>
                    <div className="relative h-8 rounded-full bg-slate-100">
                      <div
                        className={`absolute top-1 h-6 rounded-full ${
                          index === 0
                            ? 'bg-brand-500'
                            : index === ganttItems.length - 1
                              ? 'bg-red-500'
                              : 'bg-emerald-500'
                        }`}
                        style={{ left: `${item.left}%`, width: `${Math.min(100 - item.left, item.width)}%` }}
                      />
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{item.goal}</p>
                  </div>
                ))}
                {ganttItems.length === 0 && <div className="text-sm text-slate-500">生成学习计划后展示甘特图</div>}
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">阶段计划</h2>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
              {planPhases.map((phase) => (
                <div key={`${phase.name}-${phase.start_date}`} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-slate-950">{phase.name}</h3>
                    <span className="text-xs text-slate-500">
                      {formatDate(phase.start_date)} - {formatDate(phase.end_date)}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{phase.goal}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">每日时间块</h2>
            <div className="mt-4 space-y-3">
              {dailyTemplate.map((block) => (
                <div key={block.name} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-950">{block.name}</span>
                    <span className="rounded-full bg-brand-50 px-2 py-1 text-xs text-brand-700">{block.minutes} 分钟</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{block.content}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
            <h2 className="text-xl font-semibold">周目标</h2>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
              {weeklyGoals.slice(0, 9).map((goal) => (
                <div key={goal.week} className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="text-sm font-semibold text-brand-600">第 {goal.week} 周 · {formatDate(goal.start_date)}</div>
                  <div className="mt-2 text-sm text-slate-600">
                    {subjectNameById.get(goal.subject_id || 0) || '综合复盘'}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {goal.focus_points.map((point) => (
                      <span key={`${goal.week}-${point.name}`} className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">
                        {point.name}
                      </span>
                    ))}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{goal.target}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">关键里程碑</h2>
            <div className="mt-4 space-y-3">
              {milestones.map((item) => (
                <div key={`${item.date}-${item.title}`} className="rounded-lg border border-slate-200 p-4">
                  <div className="text-sm text-slate-500">{formatDate(item.date)}</div>
                  <div className="mt-1 font-semibold text-slate-950">{item.title}</div>
                  <div className="mt-1 text-sm text-slate-600">{item.check}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">模考节点</h2>
            <div className="mt-4 space-y-3">
              {mockExams.slice(0, 6).map((item) => (
                <div key={`${item.date}-${item.subject_id}`} className="rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium text-indigo-950">{item.title}</div>
                    <span className="text-xs text-indigo-700">{formatDate(item.date)}</span>
                  </div>
                  <div className="mt-1 text-sm text-indigo-700">
                    {subjectNameById.get(item.subject_id) || `科目 ${item.subject_id}`} · {item.duration_minutes} 分钟
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {item.review_focus.map((focus) => (
                      <span key={`${item.date}-${focus}`} className="rounded-full bg-white px-2 py-1 text-xs text-slate-700">
                        {focus}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {mockExams.length === 0 && <div className="text-sm text-slate-500">生成学习计划后展示模考节点</div>}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">冲刺周安排</h2>
            <div className="mt-4 space-y-3">
              {sprintPlan.map((item) => (
                <div key={`${item.date}-${item.day}`} className="rounded-lg border border-red-100 bg-red-50 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium text-red-950">Day {item.day}</div>
                    <span className="text-xs text-red-700">{formatDate(item.date)}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-red-800">{item.action}</p>
                  {item.focus_points.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {item.focus_points.map((point, index) => (
                        <span key={`${item.date}-${point.name || index}`} className="rounded-full bg-white px-2 py-1 text-xs text-slate-700">
                          {point.name || `考点 ${index + 1}`}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {sprintPlan.length === 0 && <div className="text-sm text-slate-500">生成学习计划后展示冲刺周安排</div>}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">间隔复习排期</h2>
            <p className="mt-1 text-sm text-slate-500">按 1、3、7、15、30 天复习节点回看高频考点。</p>
            <div className="mt-4 space-y-3">
              {reviewSchedule.map((item) => (
                <div key={item.date} className="rounded-lg border border-brand-100 bg-brand-50 px-4 py-3">
                  <div className="text-sm font-semibold text-brand-700">{formatDate(item.date)}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(item.review_points || []).slice(0, 4).map((point, index) => (
                      <span key={`${item.date}-${String(point.name || point.id || index)}`} className="rounded-full bg-white px-2 py-1 text-xs text-slate-700">
                        {String(point.name || `考点 ${index + 1}`)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {reviewSchedule.length === 0 && <div className="text-sm text-slate-500">生成学习计划后展示复习节点</div>}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">风险提示与资源策略</h2>
            <div className="mt-4 space-y-3">
              {riskAlerts.map((alert) => (
                <div key={alert} className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {alert}
                </div>
              ))}
              {resourceStrategy.map((item) => (
                <div key={item.type} className="rounded-lg border border-slate-200 px-4 py-3">
                  <div className="font-medium text-slate-950">{item.type}</div>
                  <div className="mt-1 text-sm text-slate-600">{item.action}</div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 className="text-xl font-semibold">学习任务</h2>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={() => shiftTaskDate(-1)} className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">前一天</button>
            <button type="button" onClick={() => void loadDailyTasks(dateKey(new Date()))} className="rounded-md border border-brand-200 bg-brand-50 px-3 py-1.5 text-sm text-brand-700 hover:bg-brand-100">今天</button>
            <input
              type="date"
              value={selectedTaskDate}
              onChange={(event) => void loadDailyTasks(event.target.value)}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700"
              aria-label="选择任务日期"
            />
            <button type="button" onClick={() => shiftTaskDate(1)} className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">后一天</button>
          </div>
        </div>
        <div className="mb-4 text-sm text-slate-500">{selectedTaskDate}</div>
        <div className="space-y-3">
          {dailyTasks.map((task) => (
            <div
              key={task.id}
              className={`flex items-center gap-4 p-4 border rounded-lg ${
                task.is_completed ? 'bg-slate-50 border-slate-200' : 'border-brand-200 bg-brand-50'
              }`}
            >
              <input
                type="checkbox"
                checked={task.is_completed}
                onChange={() => void setTaskCompleted(task.id, !task.is_completed)}
                className="w-5 h-5 rounded"
              />
              <div className="flex-1">
                <div className={`font-medium ${task.is_completed ? 'text-slate-500 line-through' : ''}`}>
                  {subjectNameById.get(task.subject_id) || `科目 ${task.subject_id}`} · 刷题 {task.question_count} 道
                </div>
                <div className="text-sm text-slate-500">
                  {task.review_points.length > 0
                    ? `复习：${task.review_points.map((point) => point.name).join('、')}`
                    : '按计划推进章节练习'}
                  {task.video_ids.length > 0 ? ` · 视频 ${task.video_ids.length} 个` : ''}
                  {task.actual_hours ? ` · 实际 ${task.actual_hours} 小时` : ''}
                </div>
                {task.focus_blocks && task.focus_blocks.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {task.focus_blocks.map((block) => (
                      <span key={`${task.id}-${block.name}`} className="rounded-full bg-white px-2 py-1 text-xs text-slate-600">
                        {block.name} {block.minutes}分钟
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {!task.is_completed && (
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={0}
                    step={0.5}
                    value={actualHours[task.id] || ''}
                    onChange={(event) =>
                      setActualHours((current) => ({ ...current, [task.id]: event.target.value }))
                    }
                    className="w-24 rounded border border-slate-300 px-2 py-2 text-sm"
                    placeholder="小时"
                  />
                  <button
                    type="button"
                    onClick={() => void setTaskCompleted(task.id, true)}
                    className="px-4 py-2 bg-brand-500 text-white rounded hover:bg-brand-600 text-sm"
                  >
                    完成
                  </button>
                </div>
              )}
              {task.is_completed && (
                <button
                  type="button"
                  onClick={() => void setTaskCompleted(task.id, false)}
                  className="rounded border border-slate-300 bg-white px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
                >
                  撤销完成
                </button>
              )}
            </div>
          ))}
          {dailyTasks.length === 0 && <div className="text-slate-500">今天暂无任务</div>}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">薄弱点识别</h2>
        <div className="space-y-3">
          {weakPoints.map((item) => {
            const mastery = Math.round(item.mastery_level * 100)
            return (
              <div key={item.point_id} className="flex flex-col gap-3 p-4 border border-slate-200 rounded-lg md:flex-row md:items-center">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium">{item.name}</span>
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        item.priority === 'high' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                      }`}
                    >
                      {item.priority === 'high' ? '高优先级' : '中优先级'}
                    </span>
                    {item.allocated_hours && (
                      <span className="rounded bg-brand-100 px-2 py-1 text-xs text-brand-700">
                        {item.allocated_hours} 小时
                      </span>
                    )}
                    {item.wrong_count && (
                      <span className="rounded bg-red-100 px-2 py-1 text-xs text-red-700">
                        错 {item.wrong_count} 次
                      </span>
                    )}
                  </div>
                  {item.description && <p className="mb-3 text-sm leading-6 text-slate-600">{item.description}</p>}
                  {item.reason && <div className="mb-3 rounded bg-slate-50 px-3 py-2 text-sm text-slate-600">{item.reason}</div>}
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-600">掌握度:</span>
                    <div className="flex-1 max-w-xs bg-slate-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${mastery < 60 ? 'bg-red-500' : 'bg-yellow-500'}`}
                        style={{ width: `${mastery}%` }}
                      />
                    </div>
                    <span className="text-sm text-slate-600">{mastery}%</span>
                  </div>
                </div>
              </div>
            )
          })}
          {weakPoints.length === 0 && <div className="text-slate-500">暂无薄弱点数据</div>}
        </div>
      </div>

      {/* Standalone AI Consultation */}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">💡 AI 报考咨询</h2>
          <button
            type="button"
            onClick={() => setAiConsultOpen(!aiConsultOpen)}
            className="text-sm text-brand-600 hover:text-brand-700"
          >
            {aiConsultOpen ? '收起' : '展开'}
          </button>
        </div>

        {aiConsultOpen && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                有关报考规划、科目选择、备考策略的任何问题
              </label>
              <textarea
                value={aiConsultText}
                onChange={(event) => setAiConsultText(event.target.value.slice(0, 2000))}
                placeholder="例如：我是上班族，想尽快拿到自考本科学历，应该如何选择专业和科目？需要报班吗？"
                rows={4}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg resize-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none"
              />
              <div className="mt-1 text-right text-xs text-slate-400">{aiConsultText.length}/2000</div>
            </div>

            <button
              type="button"
              disabled={aiConsultLoading || !aiConsultText.trim()}
              onClick={() => void handleGetAIAdvice()}
              className="px-6 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {aiConsultLoading ? (
                <span className="inline-flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  AI 分析中...
                </span>
              ) : '获取 AI 建议'}
            </button>

            {aiConsultResult && (
              <div className="mt-5 rounded-lg border border-violet-200 bg-violet-50 p-5 space-y-4">
                <h3 className="text-sm font-semibold text-violet-800">AI 建议</h3>

                {aiConsultResult.error && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    ⚠️ {aiConsultResult.error}
                  </div>
                )}

                {aiConsultResult.overall_assessment && (
                  <div>
                    <h4 className="text-xs font-medium text-violet-700 mb-1">总体评估</h4>
                    <p className="text-sm leading-6 text-violet-900 whitespace-pre-line">{aiConsultResult.overall_assessment}</p>
                  </div>
                )}

                {aiConsultResult.study_strategy && (
                  <div>
                    <h4 className="text-xs font-medium text-violet-700 mb-1">学习策略</h4>
                    <p className="text-sm leading-6 text-violet-900 whitespace-pre-line">{aiConsultResult.study_strategy}</p>
                  </div>
                )}

                {aiConsultResult.daily_plan_suggestion && (
                  <div>
                    <h4 className="text-xs font-medium text-violet-700 mb-1">每日安排建议</h4>
                    <p className="text-sm leading-6 text-violet-900 whitespace-pre-line">{aiConsultResult.daily_plan_suggestion}</p>
                  </div>
                )}

                {aiConsultResult.risk_warnings && aiConsultResult.risk_warnings.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-violet-700 mb-1">风险提示</h4>
                    <ul className="space-y-1">
                      {aiConsultResult.risk_warnings.map((warning, index) => (
                        <li key={index} className="text-sm leading-6 text-violet-800 flex gap-2">
                          <span className="text-violet-500">•</span>
                          {warning}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {aiConsultResult.motivation && (
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
                    <p className="text-sm leading-6 text-emerald-800 whitespace-pre-line">{aiConsultResult.motivation}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}

export default PlannerPage
