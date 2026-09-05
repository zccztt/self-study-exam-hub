import React, { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { enrollmentApi, EnrollmentListItem, EnrollmentSubjectsData, Province, School, Major, SubjectStatusItem } from '../api/enrollment'
import { useAuthStore } from '../stores/useAuthStore'
import UpcomingExamWidget from '../components/UpcomingExamWidget'
import StudyPlanWidget from '../components/StudyPlanWidget'
import CourseRecommendationWidget from '../components/CourseRecommendationWidget'

// ------------------------------------------------------------------
// Sub-components
// ------------------------------------------------------------------

const statusLabel: Record<string, { text: string; color: string; icon: string }> = {
  passed: { text: '已过', color: 'text-green-700 bg-green-50 border-green-200', icon: '✅' },
  failed: { text: '未过', color: 'text-red-700 bg-red-50 border-red-200', icon: '❌' },
  not_taken: { text: '未考', color: 'text-slate-500 bg-slate-50 border-slate-200', icon: '⬜' },
}

const courseTypeLabel: Record<string, string> = {
  required: '必考课',
  elective: '选考课',
  additional: '加考课',
}

// ------------------------------------------------------------------
// Mark Score Modal
// ------------------------------------------------------------------

interface MarkModalProps {
  item: SubjectStatusItem
  enrollmentId: number
  onClose: () => void
  onSaved: () => void
}

const MarkModal: React.FC<MarkModalProps> = ({ item, enrollmentId, onClose, onSaved }) => {
  const [score, setScore] = useState<string>(item.score != null ? String(item.score) : '')
  const [examDate, setExamDate] = useState<string>(item.exam_date || '')
  const [status, setStatus] = useState<string>(item.status)
  const [loading, setLoading] = useState(false)

  const handleSave = async () => {
    setLoading(true)
    try {
      const numScore = score ? parseFloat(score) : null
      let finalStatus = status
      if (numScore != null && status === 'not_taken') {
        finalStatus = numScore >= 60 ? 'passed' : 'failed'
      }
      await enrollmentApi.updateSubjectStatus({
        enrollment_id: enrollmentId,
        subject_id: item.subject_id,
        status: finalStatus,
        score: numScore,
        exam_date: examDate || null,
      })
      onSaved()
    } catch (e: any) {
      alert(e.message || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-4 text-lg font-semibold">标记成绩 - {item.code} {item.name}</h3>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">状态</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="not_taken">未考</option>
              <option value="passed">已过</option>
              <option value="failed">已考未过</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">成绩</label>
            <input
              type="number"
              min={0}
              max={100}
              value={score}
              onChange={(e) => setScore(e.target.value)}
              placeholder="输入考试分数"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">考试日期</label>
            <input
              type="date"
              value={examDate}
              onChange={(e) => setExamDate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onClose} className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50">
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// Subject Table
// ------------------------------------------------------------------

interface SubjectGroupProps {
  title: string
  items: SubjectStatusItem[]
  enrollmentId: number
  onRefresh: () => void
}

const SubjectGroup: React.FC<SubjectGroupProps> = ({ title, items, enrollmentId, onRefresh }) => {
  const [markItem, setMarkItem] = useState<SubjectStatusItem | null>(null)

  if (items.length === 0) return null

  return (
    <div className="mb-6">
      <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
        {title}
        <span className="text-xs font-normal text-slate-400">({items.length}门)</span>
      </h4>
      <div className="space-y-2">
        {items.map((item) => {
          const st = statusLabel[item.status] || statusLabel.not_taken
          return (
            <div
              key={item.subject_id}
              className={`flex items-center justify-between rounded-lg border px-4 py-3 ${st.color}`}
            >
              <div className="flex items-center gap-3">
                <span>{st.icon}</span>
                <span className="text-sm font-medium text-slate-800">{item.code}</span>
                <span className="text-sm text-slate-700">{item.name}</span>
                {item.credits && <span className="text-xs text-slate-400">{item.credits}学分</span>}
                {item.replaced_from_code && (
                  <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded" title={item.replacement_note || ''}>
                    原{item.replaced_from_code}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                {item.score != null && <span className="text-sm font-medium">{item.score}分</span>}
                {item.exam_date && <span className="text-xs text-slate-400">{item.exam_date}</span>}
                <button
                  onClick={() => setMarkItem(item)}
                  className="rounded-md bg-white/80 px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50"
                >
                  {item.status === 'not_taken' ? '标记成绩' : '修改'}
                </button>
              </div>
            </div>
          )
        })}
      </div>
      {markItem && (
        <MarkModal
          item={markItem}
          enrollmentId={enrollmentId}
          onClose={() => setMarkItem(null)}
          onSaved={() => {
            setMarkItem(null)
            onRefresh()
          }}
        />
      )}
    </div>
  )
}

// ------------------------------------------------------------------
// Replacement Table — 新旧课程替代对照表
// ------------------------------------------------------------------

const ReplacementTable: React.FC<{ subjects: SubjectStatusItem[] }> = ({ subjects }) => {
  const replacements = subjects.filter((s) => s.replaced_from_code)
  if (replacements.length === 0) return null

  // 分组: 公共课替代 vs 专业课替代
  const publicCodes = new Set(['15041', '15042', '15043', '15044'])
  const publicItems = replacements.filter((s) => publicCodes.has(s.code))
  const professionalItems = replacements.filter((s) => !publicCodes.has(s.code))

  const renderTable = (items: SubjectStatusItem[]) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-amber-200 text-left text-amber-900">
            <th className="pb-2 pr-3 font-semibold">新代码</th>
            <th className="pb-2 pr-3 font-semibold">新课程名称</th>
            <th className="pb-2 pr-3 font-semibold">原代码</th>
            <th className="pb-2 pr-3 font-semibold">原课程名称</th>
            <th className="pb-2 font-semibold">对照说明 / 顶替关系</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.subject_id} className="border-b border-amber-100">
              <td className="py-2.5 pr-3 font-mono font-medium text-amber-900">{item.code}</td>
              <td className="py-2.5 pr-3 text-slate-800">{item.name}</td>
              <td className="py-2.5 pr-3 font-mono text-slate-500 line-through">{item.replaced_from_code}</td>
              <td className="py-2.5 pr-3 text-slate-500">{item.replaced_from_name}</td>
              <td className="py-2.5 text-xs leading-5 text-amber-700">{item.replacement_note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className="mt-6 space-y-4">
      <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-5">
        <h4 className="mb-3 flex items-center gap-2 text-base font-semibold text-amber-800">
          <span>{'🔄'}</span> 新旧课程替代对照表
        </h4>
        <p className="mb-4 text-sm text-amber-700">
          自2025年起，全国自学考试课程代码已全面调整。<strong>已通过旧课程的考生，成绩可直接替代对应新课程，无需重新考试。</strong>
        </p>

        {publicItems.length > 0 && (
          <div className="mb-5">
            <h5 className="mb-2 text-sm font-semibold text-amber-800">一、公共政治课替代（全专业通用）</h5>
            {renderTable(publicItems)}
          </div>
        )}

        {professionalItems.length > 0 && (
          <div className="mb-3">
            <h5 className="mb-2 text-sm font-semibold text-amber-800">二、专业课替代</h5>
            {renderTable(professionalItems)}
          </div>
        )}

        <div className="mt-4 space-y-2 rounded-lg bg-amber-100/60 p-3">
          <p className="text-xs font-medium text-amber-800">{'ℹ️'} 重要提示：</p>
          <ul className="list-inside list-disc space-y-1 text-xs text-amber-700">
            <li>如您已通过原课程代码的考试，请直接将新课程标记为"已过"，系统会自动统计进毕业进度。</li>
            <li>河北省自2026年起按新专业计划执行，之前已通过的旧代码课程成绩继续有效。</li>
            <li>新增课程（如 15040 习近平新时代中国特色社会主义思想概论）无旧代码对应，需单独报考。</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// Enrollment Detail View
// ------------------------------------------------------------------

interface DetailViewProps {
  enrollment: EnrollmentListItem
  onBack: () => void
}

const DetailView: React.FC<DetailViewProps> = ({ enrollment, onBack }) => {
  const navigate = useNavigate()
  const [data, setData] = useState<EnrollmentSubjectsData | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await enrollmentApi.getEnrollmentSubjects(enrollment.id)
      setData(res)
    } catch (e: any) {
      alert(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [enrollment.id])

  if (loading) return <div className="py-10 text-center text-slate-400">加载中...</div>
  if (!data) return null

  const { progress, subjects } = data
  const pct = Math.round(progress.completion_rate * 100)

  return (
    <div>
      <button onClick={onBack} className="mb-4 text-sm text-blue-600 hover:underline">
        ← 返回报考列表
      </button>

      {/* Header card */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              📋 {data.enrollment.major_name} - {data.enrollment.school_name}
            </h3>
            <p className="text-sm text-slate-500">{data.enrollment.province_name}</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">{pct}%</div>
            <div className="text-xs text-slate-500">
              {progress.passed}/{progress.total} 门已过
            </div>
          </div>
        </div>
        {/* Progress bar */}
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="mt-2 flex gap-4 text-xs text-slate-500">
          <span>学分: {progress.earned_credits}/{progress.total_credits}</span>
          <span>已过 {progress.passed}</span>
          <span>未过 {progress.failed}</span>
          <span>待考 {progress.not_taken}</span>
        </div>
      </div>

      {/* Subject groups */}
      <SubjectGroup title={courseTypeLabel.required} items={subjects.required} enrollmentId={enrollment.id} onRefresh={load} />
      <SubjectGroup title={courseTypeLabel.elective} items={subjects.elective} enrollmentId={enrollment.id} onRefresh={load} />
      <SubjectGroup title={courseTypeLabel.additional} items={subjects.additional} enrollmentId={enrollment.id} onRefresh={load} />

      {/* 新旧课程替代对照表 */}
      <ReplacementTable subjects={[...subjects.required, ...subjects.elective, ...subjects.additional]} />

      {/* Action buttons */}
      {progress.not_taken + progress.failed > 0 && (
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            onClick={() => navigate(`/planner?enrollment_id=${enrollment.id}`)}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            📝 生成学习计划（仅剩余科目）
          </button>
          <button
            onClick={() => navigate('/questions')}
            className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            📚 开始学习剩余科目
          </button>
        </div>
      )}
    </div>
  )
}

// ------------------------------------------------------------------
// Create Enrollment Form
// ------------------------------------------------------------------

interface CreateFormProps {
  onCreated: () => void
}

const CreateForm: React.FC<CreateFormProps> = ({ onCreated }) => {
  const [provinces, setProvinces] = useState<Province[]>([])
  const [schools, setSchools] = useState<School[]>([])
  const [majors, setMajors] = useState<Major[]>([])
  const [provinceId, setProvinceId] = useState<number | undefined>()
  const [schoolId, setSchoolId] = useState<number | undefined>()
  const [majorId, setMajorId] = useState<number | undefined>()
  const [targetDate, setTargetDate] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    enrollmentApi.getProvinces().then(setProvinces).catch(() => {})
  }, [])

  useEffect(() => {
    if (provinceId) {
      enrollmentApi.getSchools(provinceId).then(setSchools).catch(() => {})
      setSchoolId(undefined)
      setMajorId(undefined)
      setMajors([])
    }
  }, [provinceId])

  useEffect(() => {
    if (provinceId && schoolId) {
      enrollmentApi.getMajors({ province_id: provinceId, school_id: schoolId }).then(setMajors).catch(() => {})
      setMajorId(undefined)
    }
  }, [schoolId])

  const handleSubmit = async () => {
    if (!majorId) {
      alert('请选择专业')
      return
    }
    setLoading(true)
    try {
      await enrollmentApi.createEnrollment(majorId, targetDate || undefined)
      onCreated()
    } catch (e: any) {
      alert(e.message || '报考失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <h3 className="mb-5 text-lg font-semibold text-slate-900">选择报考信息</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">省份</label>
          <select
            value={provinceId ?? ''}
            onChange={(e) => setProvinceId(e.target.value ? Number(e.target.value) : undefined)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">请选择省份</option>
            {provinces.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">院校</label>
          <select
            value={schoolId ?? ''}
            onChange={(e) => setSchoolId(e.target.value ? Number(e.target.value) : undefined)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            disabled={!provinceId}
          >
            <option value="">请选择院校</option>
            {schools.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">专业</label>
          <select
            value={majorId ?? ''}
            onChange={(e) => setMajorId(e.target.value ? Number(e.target.value) : undefined)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            disabled={!schoolId}
          >
            <option value="">请选择专业</option>
            {majors.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}({m.level === 'bk' ? '本科' : '专科'})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">目标毕业时间（选填）</label>
          <input
            type="text"
            placeholder="如：2027-06 或 2027-06-01"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <p className="mt-1 text-xs text-slate-400">支持 YYYY-MM 或 YYYY-MM-DD 格式，留空也可</p>
        </div>
      </div>
      <div className="mt-6">
        <button
          onClick={handleSubmit}
          disabled={!majorId || loading}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? '注册中...' : '确认报考'}
        </button>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// Main Page
// ------------------------------------------------------------------

const EnrollmentPage: React.FC = () => {
  const user = useAuthStore((s) => s.user)
  const [enrollments, setEnrollments] = useState<EnrollmentListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [selectedEnrollment, setSelectedEnrollment] = useState<EnrollmentListItem | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editDate, setEditDate] = useState('')
  const [editLoading, setEditLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const loadEnrollments = async () => {
    setLoading(true)
    try {
      const data = await enrollmentApi.listEnrollments()
      setEnrollments(data)
    } catch {
      // Not logged in or other error
      setEnrollments([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user) {
      loadEnrollments()
    } else {
      setLoading(false)
    }
  }, [user])

  const handleDelete = async (enrollmentId: number) => {
    if (!confirm('确定要删除该报考记录吗？删除后相关科目状态也会清除。')) return
    setDeletingId(enrollmentId)
    try {
      await enrollmentApi.deleteEnrollment(enrollmentId)
      await loadEnrollments()
    } catch (e: any) {
      alert(e.message || '删除失败')
    } finally {
      setDeletingId(null)
    }
  }

  const handleEditSave = async (enrollmentId: number) => {
    setEditLoading(true)
    try {
      await enrollmentApi.updateEnrollment(enrollmentId, editDate || null)
      setEditingId(null)
      setEditDate('')
      await loadEnrollments()
    } catch (e: any) {
      alert(e.message || '保存失败')
    } finally {
      setEditLoading(false)
    }
  }

  // Not logged in
  if (!user) {
    return (
      <div className="mx-auto max-w-4xl py-16 text-center">
        <div className="rounded-xl border border-slate-200 bg-white p-10">
          <div className="text-4xl">🎓</div>
          <h2 className="mt-4 text-xl font-bold text-slate-900">登录后管理你的报考计划</h2>
          <p className="mt-2 text-sm text-slate-500">
            选择报考院校和专业，系统自动列出所有考试科目，跟踪你的通过进度。
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

  // Detail view
  if (selectedEnrollment) {
    return (
      <div className="mx-auto max-w-4xl">
        <DetailView enrollment={selectedEnrollment} onBack={() => setSelectedEnrollment(null)} />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900">我的报考</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {showCreate ? '收起' : '+ 新增报考'}
        </button>
      </div>

      {showCreate && (
        <CreateForm
          onCreated={() => {
            setShowCreate(false)
            loadEnrollments()
          }}
        />
      )}

      {!showCreate && enrollments.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <UpcomingExamWidget />
            <StudyPlanWidget />
          </div>
          <CourseRecommendationWidget />
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-center">
            <p className="text-sm text-slate-600">完善个人学习档案，获取更精准的报考建议</p>
            <Link
              to="/profile"
              className="mt-2 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              👤 前往用户中心
            </Link>
          </div>
        </>
      )}

      {loading ? (
        <div className="py-10 text-center text-slate-400">加载中...</div>
      ) : enrollments.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center">
          <p className="text-slate-500">还没有报考记录</p>
          <p className="mt-1 text-sm text-slate-400">点击上方「新增报考」选择你的目标专业</p>
        </div>
      ) : (
        <div className="space-y-4">
          {enrollments.map((item) => {
            const pct = Math.round(item.progress.completion_rate * 100)
            const isEditing = editingId === item.id
            return (
              <div
                key={item.id}
                className="rounded-xl border border-slate-200 bg-white p-5 transition hover:border-blue-300 hover:shadow-md"
              >
                <div className="flex items-center justify-between">
                  <div
                    className="flex-1 cursor-pointer"
                    onClick={() => setSelectedEnrollment(item)}
                  >
                    <h3 className="font-semibold text-slate-900">
                      {item.major_name}({item.level === 'bk' ? '本科' : '专科'})
                    </h3>
                    <p className="text-sm text-slate-500">
                      {item.school_name} · {item.province_name}
                      {item.target_date && (
                        <span className="ml-2 text-xs text-blue-500">目标: {item.target_date}</span>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right" onClick={() => setSelectedEnrollment(item)} style={{ cursor: 'pointer' }}>
                      <div className="text-xl font-bold text-blue-600">{pct}%</div>
                      <div className="text-xs text-slate-400">
                        {item.progress.passed}/{item.progress.total}
                      </div>
                    </div>
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingId(isEditing ? null : item.id)
                          setEditDate(item.target_date || '')
                        }}
                        className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-500 hover:bg-slate-50 hover:text-blue-600"
                      >
                        {isEditing ? '取消' : '编辑'}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(item.id)
                        }}
                        disabled={deletingId === item.id}
                        className="rounded-md border border-red-100 px-2 py-1 text-xs text-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                      >
                        {deletingId === item.id ? '删除中...' : '删除'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Edit row */}
                {isEditing && (
                  <div className="mt-3 flex items-center gap-3 rounded-lg border border-blue-100 bg-blue-50/50 p-3" onClick={(e) => e.stopPropagation()}>
                    <label className="text-sm text-slate-600">目标毕业时间:</label>
                    <input
                      type="text"
                      value={editDate}
                      onChange={(e) => setEditDate(e.target.value)}
                      placeholder="如 2027-06"
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                    />
                    <button
                      onClick={() => handleEditSave(item.id)}
                      disabled={editLoading}
                      className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {editLoading ? '保存中...' : '保存'}
                    </button>
                  </div>
                )}

                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100" onClick={() => setSelectedEnrollment(item)} style={{ cursor: 'pointer' }}>
                  <div
                    className="h-full rounded-full bg-blue-500 transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default EnrollmentPage
