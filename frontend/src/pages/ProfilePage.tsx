import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi, AuthUser } from '../api/auth'
import { enrollmentApi, CourseRecommendation, CourseRecommendationItem, EnrollmentListItem } from '../api/enrollment'
import { examApi } from '../api/exam'
import { useAuthStore } from '../stores/useAuthStore'
import { sessionStore } from '../api/session'
import UserProvidersSection from '../components/UserProvidersSection'

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

const fieldClass =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

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


// ------------------------------------------------------------------
// A. Profile Card
// ------------------------------------------------------------------

const ProfileCard: React.FC<{ user: AuthUser; enrollments: EnrollmentListItem[]; examCount: number }> = ({
  user,
  enrollments,
  examCount,
}) => {
  const initials = (user.full_name || user.username || '?').slice(0, 2).toUpperCase()
  const totalPassed = enrollments.reduce((acc, e) => acc + (e.progress?.passed || 0), 0)

  return (
    <div className="rounded-xl border border-slate-200 bg-gradient-to-r from-blue-600 to-blue-700 p-6 text-white shadow-sm">
      <div className="flex items-center gap-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/20 text-xl font-bold">
          {initials}
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-bold">{user.full_name || user.username}</h2>
          <p className="mt-0.5 text-sm text-blue-100">{user.email}</p>
          {user.current_job && <p className="mt-0.5 text-sm text-blue-200">{user.current_job}</p>}
        </div>
      </div>
      <div className="mt-5 grid grid-cols-3 gap-4">
        <div className="rounded-lg bg-white/10 p-3 text-center">
          <div className="text-2xl font-bold">{totalPassed}</div>
          <div className="text-xs text-blue-200">已过科目</div>
        </div>
        <div className="rounded-lg bg-white/10 p-3 text-center">
          <div className="text-2xl font-bold">{enrollments.length}</div>
          <div className="text-xs text-blue-200">在学专业</div>
        </div>
        <div className="rounded-lg bg-white/10 p-3 text-center">
          <div className="text-2xl font-bold">{examCount}</div>
          <div className="text-xs text-blue-200">模拟考试</div>
        </div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// B. Profile Edit Form
// ------------------------------------------------------------------

const ProfileForm: React.FC<{ user: AuthUser }> = ({ user }) => {
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const [currentJob, setCurrentJob] = useState(user.current_job || '')
  const [educationBg, setEducationBg] = useState(user.education_background || '')
  const [educationMajor, setEducationMajor] = useState(user.education_major || '')
  const [skills, setSkills] = useState(user.skills || '')
  const [studyHours, setStudyHours] = useState(String(user.study_hours_per_day || 3))
  const [examExp, setExamExp] = useState(user.exam_experience || 'none')
  const [learnPref, setLearnPref] = useState(user.learning_preference || 'practice')

  useEffect(() => {
    setCurrentJob(user.current_job || '')
    setEducationBg(user.education_background || '')
    setEducationMajor(user.education_major || '')
    setSkills(user.skills || '')
    setStudyHours(String(user.study_hours_per_day || 3))
    setExamExp(user.exam_experience || 'none')
    setLearnPref(user.learning_preference || 'practice')
  }, [user])

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    try {
      const updated = await authApi.updateProfile({
        current_job: currentJob || undefined,
        education_background: educationBg || undefined,
        education_major: educationMajor || undefined,
        skills: skills || undefined,
        study_hours_per_day: Number(studyHours) || undefined,
        exam_experience: examExp || undefined,
        learning_preference: learnPref || undefined,
      })
      sessionStore.saveUser(updated)
      useAuthStore.getState().setUser(updated)
      setMessage('✅ 个人信息已保存，报考建议将根据您的信息重新生成')
    } catch (e: any) {
      setMessage('❌ ' + (e.message || '保存失败'))
    } finally {
      setSaving(false)
    }
  }

  const isComplete = currentJob && educationBg && studyHours

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">👤 个人学习档案</h3>
          <p className="mt-1 text-xs text-slate-500">
            完善信息后，系统将根据您的背景生成更精准的报考建议和学习计划
          </p>
        </div>
        {!isComplete && (
          <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
            ⚠️ 信息不完整
          </span>
        )}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">当前职业</label>
          <input
            value={currentJob}
            onChange={(e) => setCurrentJob(e.target.value)}
            placeholder="如：IT工程师、教师、在校生..."
            className={fieldClass}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">学历背景</label>
          <select value={educationBg} onChange={(e) => setEducationBg(e.target.value)} className={fieldClass}>
            <option value="">请选择</option>
            <option value="初中">初中</option>
            <option value="高中/中专">高中/中专</option>
            <option value="大专">大专</option>
            <option value="本科">本科</option>
            <option value="研究生及以上">研究生及以上</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">原专业方向</label>
          <input
            value={educationMajor}
            onChange={(e) => setEducationMajor(e.target.value)}
            placeholder="如：计算机、法学、管理..."
            className={fieldClass}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">技能标签（逗号分隔）</label>
          <input
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            placeholder="如：编程,英语,会计..."
            className={fieldClass}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">每日可用学习时间</label>
          <select value={studyHours} onChange={(e) => setStudyHours(e.target.value)} className={fieldClass}>
            <option value="1">1小时</option>
            <option value="2">2小时</option>
            <option value="3">3小时</option>
            <option value="4">4小时</option>
            <option value="5">5小时以上</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">自考经验</label>
          <select value={examExp} onChange={(e) => setExamExp(e.target.value)} className={fieldClass}>
            <option value="none">无经验（首次报考）</option>
            <option value="beginner">初学者（考过1-2次）</option>
            <option value="experienced">有经验（考过3次以上）</option>
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs font-medium text-slate-600">学习偏好</label>
          <div className="flex gap-3">
            {(['video', 'reading', 'practice'] as const).map((v) => (
              <label
                key={v}
                className={`flex-1 cursor-pointer rounded-lg border p-3 text-center text-sm transition ${
                  learnPref === v
                    ? 'border-blue-500 bg-blue-50 font-medium text-blue-700'
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <input
                  type="radio"
                  name="learnPref"
                  value={v}
                  checked={learnPref === v}
                  onChange={() => setLearnPref(v)}
                  className="sr-only"
                />
                {v === 'video' ? '🎬 看视频' : v === 'reading' ? '📖 看教材' : '✏️ 刷题'}
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? '保存中...' : '💾 保存信息'}
        </button>
        {message && <span className="text-xs">{message}</span>}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// C. Course Recommendation
// ------------------------------------------------------------------

const RecommendationSection: React.FC<{ enrollments: EnrollmentListItem[] }> = ({ enrollments }) => {
  const [data, setData] = useState<CourseRecommendation | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'picks' | 'all' | 'study' | 'sprint'>('picks')
  const [selectedEnrollmentId, setSelectedEnrollmentId] = useState<number | undefined>(undefined)

  const load = (enrollmentId?: number) => {
    setLoading(true)
    enrollmentApi
      .getCourseRecommendation(enrollmentId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(selectedEnrollmentId)
  }, [selectedEnrollmentId])

  if (enrollments.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <div className="text-3xl">🎓</div>
        <h3 className="mt-3 text-base font-semibold text-slate-900">请先添加报考专业</h3>
        <p className="mt-1 text-sm text-slate-500">添加报考信息后，系统将基于您的档案智能推荐报考科目</p>
        <Link
          to="/enrollment"
          className="mt-4 inline-block rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          前往我的报考
        </Link>
      </div>
    )
  }

  const tabs = [
    { key: 'picks' as const, label: '下次报考建议', icon: '📝' },
    { key: 'all' as const, label: '全部推荐排序', icon: '📊' },
    { key: 'study' as const, label: '学习计划', icon: '📅' },
    { key: 'sprint' as const, label: '冲刺计划', icon: '🔥' },
  ]

  const renderPicks = (picks: CourseRecommendationItem[]) => (
    <div className="space-y-3">
      {picks.length === 0 ? (
        <p className="py-4 text-center text-sm text-slate-400">暂无推荐</p>
      ) : (
        <>
          <div className="rounded-lg bg-blue-50 p-3">
            <p className="text-sm font-medium text-blue-800">
              📝 下次考试建议报考以下 {Math.min(picks.length, 4)} 门课程（已根据您的背景智能排序）
            </p>
          </div>
          {picks.map((item, idx) => (
            <div key={item.code} className={`rounded-lg border p-4 ${priorityColor(item.priority_score)}`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-xs font-bold shadow-sm">
                      {idx + 1}
                    </span>
                    <span className="text-sm font-semibold">
                      {item.code} {item.name}
                    </span>
                    <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs font-medium">
                      {priorityLabel(item.priority_score)}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    <span className="rounded bg-white/60 px-1.5 py-0.5">{item.credits}学分</span>
                    <span className="rounded bg-white/60 px-1.5 py-0.5">
                      {item.course_type === 'required' ? '必考' : item.course_type === 'elective' ? '选考' : '加考'}
                    </span>
                    <span className="rounded bg-white/60 px-1.5 py-0.5">约{item.estimated_hours}h</span>
                    {item.question_count > 0 && (
                      <span className="rounded bg-white/60 px-1.5 py-0.5">{item.question_count}题</span>
                    )}
                  </div>
                  <div className="mt-2 text-xs leading-5 opacity-80">💡 {item.reason}</div>
                </div>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )

  const renderStudyPlan = () => {
    const plan = data?.study_plan
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
              <span className="text-xs text-slate-500">
                约{phase.total_hours}h · {phase.weeks_needed}周
              </span>
            </div>
            <div className="mt-2 space-y-1">
              {phase.courses.map((c) => (
                <div key={c.code} className="flex items-center justify-between rounded bg-slate-50 px-3 py-1.5 text-xs">
                  <span className="font-medium text-slate-800">
                    {c.code} {c.name}
                  </span>
                  <span className="text-slate-500">
                    {c.credits}分 · {c.hours}h
                  </span>
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
    const sprint = data?.sprint_plan
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
            <div
              key={p.code}
              className="flex items-center justify-between rounded-lg border border-orange-100 bg-orange-50/50 px-3 py-2"
            >
              <span className="text-sm font-medium text-slate-800">
                {p.code} {p.name}
              </span>
              <span className="text-xs text-slate-500">{p.credits}分</span>
            </div>
          ))}
        </div>
        {sprint.weeks.map((week, idx) => (
          <div key={idx} className="rounded-lg border border-slate-200 bg-white p-4">
            <h4 className="text-sm font-semibold text-slate-800">{week.period}</h4>
            <p className="mt-1 text-xs text-blue-600">🎯 {week.focus}</p>
            <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs text-slate-600">
              {week.tasks.map((task, i) => (
                <li key={i}>{task}</li>
              ))}
            </ul>
          </div>
        ))}
        <div className="rounded-lg bg-amber-50 p-3">
          <p className="text-xs font-medium text-amber-800">💡 备考小贴士</p>
          <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-amber-700">
            {sprint.tips.map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </ul>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">🎯 个性化报考建议</h3>
        <div className="flex items-center gap-3">
          {enrollments.length > 1 && (
            <select
              value={selectedEnrollmentId ?? ''}
              onChange={(e) => setSelectedEnrollmentId(e.target.value ? Number(e.target.value) : undefined)}
              className="rounded-lg border border-slate-300 px-2 py-1 text-xs"
            >
              <option value="">综合全部专业</option>
              {enrollments.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.major_name}
                </option>
              ))}
            </select>
          )}
          {data && (
            <div className="flex gap-2 text-xs text-slate-500">
              <span>已过 {data.total_passed} 门</span>
              <span>·</span>
              <span>剩余 {data.total_remaining} 门</span>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-3 flex gap-1 overflow-x-auto border-b border-slate-100 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium transition ${
              activeTab === tab.key ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="mt-4">
        {loading ? (
          <div className="py-6 text-center text-sm text-slate-400">正在生成个性化建议...</div>
        ) : !data ? (
          <div className="py-6 text-center text-sm text-slate-400">加载失败，请刷新重试</div>
        ) : (
          <>
            {activeTab === 'picks' && renderPicks(data.next_exam_picks)}
            {activeTab === 'all' && renderPicks(data.recommendations)}
            {activeTab === 'study' && renderStudyPlan()}
            {activeTab === 'sprint' && renderSprint()}
          </>
        )}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// D. Exam Stats Overview
// ------------------------------------------------------------------

const ExamStatsSection: React.FC = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState<{
    total: number
    completed: number
    avgScore: number
    passRate: number
  } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    examApi
      .getHistory(sessionStore.getUserId(), 1, 100)
      .then((res) => {
        const completed = res.items.filter((i) => i.status === 'completed')
        const scored = completed.filter((i) => i.score != null)
        const avgScore =
          scored.length > 0 ? Math.round(scored.reduce((s, i) => s + (i.score || 0), 0) / scored.length) : 0
        const passed = scored.filter(
          (i) => i.score != null && i.total_count != null && i.score >= 60,
        ).length
        setStats({
          total: res.total,
          completed: completed.length,
          avgScore,
          passRate: scored.length > 0 ? Math.round((passed / scored.length) * 100) : 0,
        })
      })
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="py-4 text-center text-sm text-slate-400">加载考试数据...</div>

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">📊 考试概览</h3>
        <button
          onClick={() => navigate('/exam')}
          className="text-xs font-medium text-blue-600 hover:text-blue-700"
        >
          查看全部记录 →
        </button>
      </div>
      {stats && stats.total > 0 ? (
        <div className="mt-4 grid grid-cols-4 gap-3">
          <div className="rounded-lg bg-slate-50 p-3 text-center">
            <div className="text-xl font-bold text-slate-800">{stats.total}</div>
            <div className="text-xs text-slate-500">总场次</div>
          </div>
          <div className="rounded-lg bg-green-50 p-3 text-center">
            <div className="text-xl font-bold text-green-700">{stats.completed}</div>
            <div className="text-xs text-green-600">已完成</div>
          </div>
          <div className="rounded-lg bg-blue-50 p-3 text-center">
            <div className="text-xl font-bold text-blue-700">{stats.avgScore}</div>
            <div className="text-xs text-blue-600">平均分</div>
          </div>
          <div className="rounded-lg bg-amber-50 p-3 text-center">
            <div className="text-xl font-bold text-amber-700">{stats.passRate}%</div>
            <div className="text-xs text-amber-600">及格率</div>
          </div>
        </div>
      ) : (
        <div className="mt-4 rounded-lg bg-slate-50 p-6 text-center">
          <p className="text-sm text-slate-500">还没有考试记录</p>
          <button
            onClick={() => navigate('/exam')}
            className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            开始模拟考试
          </button>
        </div>
      )}
    </div>
  )
}

// ------------------------------------------------------------------
// E. Quick Actions
// ------------------------------------------------------------------

const QuickActions: React.FC = () => {
  const navigate = useNavigate()
  const actions = [
    { icon: '🎓', label: '我的报考', desc: '管理报考专业和科目进度', to: '/enrollment' },
    { icon: '📝', label: '学习规划', desc: '生成每日学习计划', to: '/planner' },
    { icon: '📖', label: '模拟考试', desc: '组卷模拟真实考试', to: '/exam' },
    { icon: '📚', label: '题库搜索', desc: '按科目章节搜索练习', to: '/questions' },
    { icon: '📈', label: '考点分析', desc: '高频考点和难点分析', to: '/analysis' },
    { icon: '⭐', label: '收藏错题', desc: '管理收藏和错题本', to: '/favorites' },
  ]

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-base font-semibold text-slate-900">⚡ 快捷入口</h3>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {actions.map((a) => (
          <button
            key={a.to}
            onClick={() => navigate(a.to)}
            className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 text-left transition hover:border-blue-300 hover:bg-blue-50/50"
          >
            <span className="text-xl">{a.icon}</span>
            <div>
              <div className="text-sm font-medium text-slate-800">{a.label}</div>
              <div className="text-xs text-slate-500">{a.desc}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// Main Page
// ------------------------------------------------------------------

const ProfilePage: React.FC = () => {
  const user = useAuthStore((s) => s.user)
  const [enrollments, setEnrollments] = useState<EnrollmentListItem[]>([])
  const [examCount, setExamCount] = useState(0)

  useEffect(() => {
    if (!user) return
    enrollmentApi
      .listEnrollments()
      .then(setEnrollments)
      .catch(() => setEnrollments([]))
    examApi
      .getHistory(user.id, 1, 1)
      .then((res) => setExamCount(res.total))
      .catch(() => setExamCount(0))
  }, [user])

  // Not logged in
  if (!user) {
    return (
      <div className="mx-auto max-w-4xl py-16 text-center">
        <div className="rounded-xl border border-slate-200 bg-white p-10">
          <div className="text-4xl">👤</div>
          <h2 className="mt-4 text-xl font-bold text-slate-900">登录后查看您的学习档案</h2>
          <p className="mt-2 text-sm text-slate-500">
            完善个人信息，系统将根据您的工作背景、历史专业、技能和已考科目，智能推荐报考课程和学习计划。
          </p>
          <Link
            to="/auth"
            className="mt-6 inline-block rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            去登录 / 注册
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* A: Profile Card */}
      <ProfileCard user={user} enrollments={enrollments} examCount={examCount} />

      {/* B: Profile Edit Form */}
      <ProfileForm user={user} />

      {/* C: Course Recommendation */}
      <RecommendationSection enrollments={enrollments} />

      {/* D: Exam Stats */}
      <ExamStatsSection />

      {/* E: Quick Actions */}
      <QuickActions />

      {/* F: Provider Config Section */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <UserProvidersSection />
      </div>
    </div>
  )
}

export default ProfilePage
