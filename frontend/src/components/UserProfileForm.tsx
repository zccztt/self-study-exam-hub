import React, { useEffect, useState } from 'react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/useAuthStore'
import { sessionStore } from '../api/session'

const fieldClass = 'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

const UserProfileForm: React.FC = () => {
  const user = useAuthStore((s) => s.user)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const [currentJob, setCurrentJob] = useState(user?.current_job || '')
  const [educationBg, setEducationBg] = useState(user?.education_background || '')
  const [educationMajor, setEducationMajor] = useState(user?.education_major || '')
  const [skills, setSkills] = useState(user?.skills || '')
  const [studyHours, setStudyHours] = useState(String(user?.study_hours_per_day || 3))
  const [examExp, setExamExp] = useState(user?.exam_experience || 'none')
  const [learnPref, setLearnPref] = useState(user?.learning_preference || 'practice')

  useEffect(() => {
    if (user) {
      setCurrentJob(user.current_job || '')
      setEducationBg(user.education_background || '')
      setEducationMajor(user.education_major || '')
      setSkills(user.skills || '')
      setStudyHours(String(user.study_hours_per_day || 3))
      setExamExp(user.exam_experience || 'none')
      setLearnPref(user.learning_preference || 'practice')
    }
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
      setMessage('✅ 个人信息已保存，建议将根据您的信息进行个性化推荐')
    } catch (e: any) {
      setMessage('❌ ' + (e.message || '保存失败'))
    } finally {
      setSaving(false)
    }
  }

  const isComplete = currentJob && educationBg && studyHours

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-base font-semibold text-slate-900">👤 个人学习档案</h3>
      <p className="mt-1 text-xs text-slate-500">完善信息后，系统将根据您的背景生成更精准的报考建议和学习计划</p>

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
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">学习偏好</label>
          <select value={learnPref} onChange={(e) => setLearnPref(e.target.value)} className={fieldClass}>
            <option value="video">看视频为主</option>
            <option value="reading">看教材为主</option>
            <option value="practice">刷题为主</option>
          </select>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存信息'}
        </button>
        {!isComplete && (
          <span className="text-xs text-amber-600">⚠️ 请至少填写职业、学历和学习时间以获取更精准的建议</span>
        )}
        {message && <span className="text-xs">{message}</span>}
      </div>
    </div>
  )
}

export default UserProfileForm
