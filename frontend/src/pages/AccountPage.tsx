import React, { FormEvent, useState } from 'react'
import { authApi } from '../api/auth'
import { sessionStore } from '../api/session'
import StudyReminderSettings from '../components/StudyReminderSettings'

const fieldClass = 'w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

const AccountPage: React.FC = () => {
  const user = sessionStore.getUser()
  const [email, setEmail] = useState(user?.email || '')
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')
    try {
      const updated = await authApi.updateProfile({ email: email.trim(), full_name: fullName.trim() })
      sessionStore.saveUser(updated)
      setMessage('个人资料已更新。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '个人资料更新失败')
    } finally {
      setLoading(false)
    }
  }

  const savePassword = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')
    if (newPassword !== confirmPassword) {
      setError('两次输入的新密码不一致。')
      return
    }
    setLoading(true)
    try {
      await authApi.changePassword({ current_password: currentPassword, new_password: newPassword })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setMessage('密码已修改，下次登录请使用新密码。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '密码修改失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <section>
        <div className="text-sm font-medium text-brand-600">Account</div>
        <h1 className="mt-1 text-3xl font-bold text-slate-950">账户设置</h1>
        <p className="mt-2 text-sm text-slate-500">管理个人资料和登录密码。</p>
      </section>

      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {message && <div className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">{message}</div>}

      <div className="grid gap-6 md:grid-cols-2">
        <form onSubmit={saveProfile} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">个人资料</h2>
          <div className="mt-5 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">用户名</label>
              <input value={user?.username || ''} disabled className={`${fieldClass} bg-slate-100 text-slate-500`} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">姓名</label>
              <input value={fullName} onChange={(event) => setFullName(event.target.value)} maxLength={100} className={fieldClass} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">邮箱</label>
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required className={fieldClass} />
            </div>
          </div>
          <button type="submit" disabled={loading} className="mt-5 w-full rounded-lg bg-brand-600 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60">
            保存资料
          </button>
        </form>

        <form onSubmit={savePassword} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">修改密码</h2>
          <div className="mt-5 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">当前密码</label>
              <input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required className={fieldClass} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">新密码</label>
              <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} required className={fieldClass} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">确认新密码</label>
              <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={8} required className={fieldClass} />
            </div>
          </div>
          <button type="submit" disabled={loading} className="mt-5 w-full rounded-lg bg-slate-900 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60">
            修改密码
          </button>
        </form>
      </div>

      <StudyReminderSettings />
    </div>
  )
}

export default AccountPage
