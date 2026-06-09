import React, { FormEvent, useEffect, useMemo, useState } from 'react'
import { DailyTask, plannerApi, PlanPhase, PlanTask, StudyPlan, TimeAllocation, WeakPoint } from '../api/planner'
import { sessionStore } from '../api/session'
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
    if (weeks.length > 12) break
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
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedSubjects, setSelectedSubjects] = useState<number[]>([])
  const [examDate, setExamDate] = useState('2026-10-24')
  const [dailyHours, setDailyHours] = useState(2)
  const [currentPlan, setCurrentPlan] = useState<StudyPlan | null>(null)
  const [dailyTasks, setDailyTasks] = useState<DailyTask[]>([])
  const [weakPoints, setWeakPoints] = useState<WeakPoint[]>([])
  const [allocation, setAllocation] = useState<TimeAllocation | null>(null)
  const [actualHours, setActualHours] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const subjectNameById = useMemo(
    () => new Map(subjects.map((subject) => [subject.id, subject.name])),
    [subjects],
  )

  const loadPlannerData = async (preferredSubjectId?: number) => {
    setError('')
    try {
      const userId = sessionStore.getUserId()
      const [planData, taskData] = await Promise.all([
        plannerApi.getLatestPlan(userId),
        plannerApi.getDailyTasks(userId),
      ])
      setCurrentPlan(planData)
      setDailyTasks(taskData)

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
        const subjectData = await subjectApi.list()
        setSubjects(subjectData)
        if (subjectData[0]) {
          setSelectedSubjects([subjectData[0].id])
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
        exam_date: new Date(`${examDate}T00:00:00`).toISOString(),
        subjects: selectedSubjects,
        daily_hours: dailyHours,
      })
      setCurrentPlan(plan)
      setMessage('学习计划已生成')
      const [taskData, weakData, allocationData] = await Promise.all([
        plannerApi.getDailyTasks(sessionStore.getUserId()),
        plannerApi.getWeakPoints(selectedSubjects[0], sessionStore.getUserId()),
        plannerApi.allocateTime(plan.plan_data.days || 30, plan.daily_hours, selectedSubjects[0], sessionStore.getUserId()),
      ])
      setDailyTasks(taskData)
      setWeakPoints(weakData)
      setAllocation(plan.plan_data.allocation || allocationData)
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成学习计划失败')
    } finally {
      setLoading(false)
    }
  }

  const completeTask = async (taskId: number) => {
    setError('')
    try {
      const parsedHours = Number(actualHours[taskId])
      const progress = await plannerApi.updateProgress(
        [{ id: taskId, actual_hours: Number.isFinite(parsedHours) && parsedHours > 0 ? parsedHours : undefined }],
        sessionStore.getUserId(),
      )
      setDailyTasks((current) =>
        current.map((task) =>
          task.id === taskId
            ? {
                ...task,
                is_completed: true,
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
            <div className="text-sm font-medium text-blue-600">系统化备考计划</div>
            <h1 className="mt-1 text-3xl font-bold text-slate-950">学习规划</h1>
            <p className="mt-2 text-sm text-slate-500">
              默认按 2026 年 10 月自考窗口规划，可根据本省公告调整考试日期。
            </p>
          </div>
          <div className="rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-700">
            建议流程：阶段目标 → 周目标 → 每日任务 → 错题复盘
          </div>
        </div>
      </section>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}
      {message && <div className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-green-700">{message}</div>}

      <form onSubmit={handleGenerate} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">创建学习计划</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">考试日期</label>
            <input
              type="date"
              value={examDate}
              onChange={(event) => setExamDate(event.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">每日可用学习时长</label>
            <select
              value={dailyHours}
              onChange={(event) => setDailyHours(Number(event.target.value))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg"
            >
              {[1, 2, 3, 4, 5, 6].map((hours) => (
                <option key={hours} value={hours}>
                  {hours}小时
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">报考科目</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {subjects.map((subject) => (
                <label key={subject.id} className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selectedSubjects.includes(subject.id)}
                    onChange={() => toggleSubject(subject.id)}
                    className="rounded"
                  />
                  <span className="text-sm">{subject.name}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full md:w-auto px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-60"
        >
          {loading ? '处理中...' : '生成学习计划'}
        </button>
      </form>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between mb-4">
          <h2 className="text-xl font-semibold">当前学习计划</h2>
          {currentPlan && (
            <div className="text-sm text-gray-600">
              距离考试还有 <span className="font-bold text-blue-500">{daysUntil(currentPlan.exam_date)}</span> 天
            </div>
          )}
        </div>

        {currentPlan ? (
          <>
            <div className="mb-6">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>
                  {formatDate(currentPlan.exam_date)} · 每日 {currentPlan.daily_hours} 小时
                </span>
                <span>{progress.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div className="bg-blue-500 h-3 rounded-full" style={{ width: `${Math.min(100, progress)}%` }} />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-lg border border-gray-200 p-4">
                <div className="text-sm text-gray-500">计划天数</div>
                <div className="mt-1 text-2xl font-bold">{currentPlan.plan_data.days || planTasks.length}</div>
              </div>
              <div className="rounded-lg border border-gray-200 p-4">
                <div className="text-sm text-gray-500">预计通过率</div>
                <div className="mt-1 text-2xl font-bold">
                  {currentPlan.expected_pass_rate ? `${Math.round(currentPlan.expected_pass_rate * 100)}%` : '-'}
                </div>
              </div>
              <div className="rounded-lg border border-gray-200 p-4">
                <div className="text-sm text-gray-500">报考科目</div>
                <div className="mt-1 text-sm">
                  {currentPlan.subjects.map((id) => subjectNameById.get(id) || `科目 ${id}`).join('、')}
                </div>
              </div>
            </div>
            {allocation && (
              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
                <div className="rounded-lg border border-gray-200 p-4">
                  <div className="text-sm text-gray-500">总学习时长</div>
                  <div className="mt-1 text-xl font-bold">{allocation.total_hours} 小时</div>
                </div>
                <div className="rounded-lg border border-red-100 bg-red-50 p-4">
                  <div className="text-sm text-red-700">薄弱点强化</div>
                  <div className="mt-1 text-xl font-bold text-red-700">{allocation.weak_points_hours} 小时</div>
                </div>
                <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                  <div className="text-sm text-blue-700">高频考点</div>
                  <div className="mt-1 text-xl font-bold text-blue-700">{allocation.high_frequency_hours} 小时</div>
                </div>
                <div className="rounded-lg border border-green-100 bg-green-50 p-4">
                  <div className="text-sm text-green-700">复盘巩固</div>
                  <div className="mt-1 text-xl font-bold text-green-700">{allocation.review_hours} 小时</div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-gray-500">暂无学习计划</div>
        )}
      </div>

      {currentPlan && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold">学习日历</h2>
                <p className="mt-1 text-sm text-slate-500">按周查看每日刷题、复习和视频任务。</p>
              </div>
              <div className="text-sm text-slate-500">展示 {Math.min(planTasks.length, 84)} 项计划任务</div>
            </div>
            <div className="mt-4 overflow-x-auto">
              <div className="min-w-[840px]">
                <div className="grid grid-cols-7 gap-2 text-center text-xs font-medium text-slate-500">
                  {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => (
                    <div key={day}>{day}</div>
                  ))}
                </div>
                <div className="mt-2 space-y-2">
                  {planCalendarWeeks.map((week) => (
                    <div key={week[0].date} className="grid grid-cols-7 gap-2">
                      {week.map((day) => (
                        <div
                          key={day.date}
                          className={`min-h-28 rounded-lg border p-2 ${
                            day.tasks.length > 0 ? 'border-blue-100 bg-blue-50' : 'border-slate-100 bg-slate-50'
                          }`}
                        >
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <span className="text-xs font-medium text-slate-600">{day.date.slice(5)}</span>
                            {day.date === dateKey(new Date()) && (
                              <span className="rounded-full bg-blue-600 px-2 py-0.5 text-[10px] text-white">今天</span>
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
                        </div>
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
                            ? 'bg-blue-500'
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
                    <span className="rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700">{block.minutes} 分钟</span>
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
                  <div className="text-sm font-semibold text-blue-600">第 {goal.week} 周 · {formatDate(goal.start_date)}</div>
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
                <div key={item.date} className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3">
                  <div className="text-sm font-semibold text-blue-700">{formatDate(item.date)}</div>
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
        <h2 className="text-xl font-semibold mb-4">今日学习任务</h2>
        <div className="space-y-3">
          {dailyTasks.map((task) => (
            <div
              key={task.id}
              className={`flex items-center gap-4 p-4 border rounded-lg ${
                task.is_completed ? 'bg-gray-50 border-gray-200' : 'border-blue-200 bg-blue-50'
              }`}
            >
              <input
                type="checkbox"
                checked={task.is_completed}
                disabled={task.is_completed}
                onChange={() => void completeTask(task.id)}
                className="w-5 h-5 rounded"
              />
              <div className="flex-1">
                <div className={`font-medium ${task.is_completed ? 'text-gray-500 line-through' : ''}`}>
                  {subjectNameById.get(task.subject_id) || `科目 ${task.subject_id}`} · 刷题 {task.question_count} 道
                </div>
                <div className="text-sm text-gray-500">
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
                    className="w-24 rounded border border-gray-300 px-2 py-2 text-sm"
                    placeholder="小时"
                  />
                  <button
                    type="button"
                    onClick={() => void completeTask(task.id)}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                  >
                    完成
                  </button>
                </div>
              )}
            </div>
          ))}
          {dailyTasks.length === 0 && <div className="text-gray-500">今天暂无任务</div>}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">薄弱点识别</h2>
        <div className="space-y-3">
          {weakPoints.map((item) => {
            const mastery = Math.round(item.mastery_level * 100)
            return (
              <div key={item.point_id} className="flex flex-col gap-3 p-4 border border-gray-200 rounded-lg md:flex-row md:items-center">
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
                      <span className="rounded bg-blue-100 px-2 py-1 text-xs text-blue-700">
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
                    <span className="text-sm text-gray-600">掌握度:</span>
                    <div className="flex-1 max-w-xs bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${mastery < 60 ? 'bg-red-500' : 'bg-yellow-500'}`}
                        style={{ width: `${mastery}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-600">{mastery}%</span>
                  </div>
                </div>
              </div>
            )
          })}
          {weakPoints.length === 0 && <div className="text-gray-500">暂无薄弱点数据</div>}
        </div>
      </div>
    </div>
  )
}

export default PlannerPage
