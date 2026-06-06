import React, { FormEvent, useEffect, useMemo, useState } from 'react'
import { DailyTask, plannerApi, StudyPlan, TimeAllocation, WeakPoint } from '../api/planner'
import { sessionStore } from '../api/session'
import { subjectApi, Subject } from '../api/subject'

const formatDate = (value: string) => new Date(value).toLocaleDateString()

const daysUntil = (value: string) => {
  const target = new Date(value).getTime()
  const now = new Date().setHours(0, 0, 0, 0)
  return Math.max(0, Math.ceil((target - now) / 86400000))
}

const PlannerPage: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedSubjects, setSelectedSubjects] = useState<number[]>([])
  const [examDate, setExamDate] = useState('')
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

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">学习规划</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}
      {message && <div className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-green-700">{message}</div>}

      <form onSubmit={handleGenerate} className="bg-white rounded-lg shadow p-6 mb-6">
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

      <div className="bg-white rounded-lg shadow p-6 mb-6">
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

      <div className="bg-white rounded-lg shadow p-6 mb-6">
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

      <div className="bg-white rounded-lg shadow p-6">
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
