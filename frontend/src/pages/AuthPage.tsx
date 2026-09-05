import React, { FormEvent, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../api/auth'
import { sessionStore } from '../api/session'

type AuthMode = 'login' | 'register' | 'forgot' | 'reset'

// Auto-generate email from username
const autoEmail = (username: string) => {
  if (!username || username.length < 3) return ''
  return `${username}@self-study.local`
}

const AuthPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const resetToken = searchParams.get('reset_token') || ''
  const [mode, setMode] = useState<AuthMode>(() => resetToken ? 'reset' : 'login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [emailManual, setEmailManual] = useState(false) // 用户是否手动修改过邮箱
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // 注册模式下自动填充邮箱
  useEffect(() => {
    if (mode === 'register' && !emailManual) {
      setEmail(autoEmail(username))
    }
  }, [username, mode, emailManual])

  const fillDemoAccount = () => {
    setMode('login')
    setUsername('demo')
    setPassword('demo123456')
    setError('')
    setSuccess('')
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)
    try {
      if (mode === 'forgot') {
        const result = await authApi.requestPasswordReset(email)
        setSuccess(
          result.delivery_available
            ? '如果该邮箱已注册，重置链接将发送到你的邮箱。'
            : '当前环境未配置邮件服务，请联系管理员重置密码。',
        )
        return
      }
      if (mode === 'reset') {
        if (!resetToken) throw new Error('密码重置链接缺少凭证。')
        if (password !== confirmPassword) throw new Error('两次输入的密码不一致。')
        await authApi.resetPassword(resetToken, password)
        setPassword('')
        setConfirmPassword('')
        setMode('login')
        setSuccess('密码已重置，请使用新密码登录。')
        navigate('/auth', { replace: true })
        return
      }
      const result =
        mode === 'login'
          ? await authApi.login({ username, password })
          : await authApi.register({
              username,
              email,
              password,
              full_name: fullName.trim() || undefined,
            })
      sessionStore.saveAuth(result)
      const next = searchParams.get('next')
      navigate(next && next.startsWith('/') ? next : '/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-6 px-4 py-10 lg:grid-cols-[0.9fr_1.1fr]">
      <aside className="rounded-xl border border-slate-200 bg-slate-950 p-6 text-white shadow-sm">
        <div className="text-sm font-medium text-brand-200">演示环境</div>
        <h1 className="mt-3 text-2xl font-bold">默认登录账号已自动维护</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          初始化脚本会幂等创建或修复演示账号，便于展示题库、组卷、错题归档和学习计划完整流程。
        </p>
        <div className="mt-6 rounded-lg bg-white/10 p-4">
          <div className="text-sm text-slate-300">用户名</div>
          <div className="text-2xl font-bold">demo</div>
          <div className="mt-3 text-sm text-slate-300">密码</div>
          <div className="text-2xl font-bold">demo123456</div>
        </div>
        <button
          type="button"
          onClick={fillDemoAccount}
          className="mt-5 w-full rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-brand-50"
        >
          填入演示账号
        </button>
      </aside>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {mode === 'login' || mode === 'register' ? (
          <div className="mb-6 flex rounded-lg border border-slate-200 bg-slate-50 p-1">
            <button
              type="button"
              onClick={() => { setMode('login'); setError(''); setSuccess('') }}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium ${
                mode === 'login' ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-white'
              }`}
            >
              登录
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setError(''); setSuccess('') }}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium ${
                mode === 'register' ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-white'
              }`}
            >
              注册
            </button>
          </div>
        ) : (
          <div className="mb-6 flex items-center justify-between border-b border-slate-200 pb-4">
            <h2 className="text-xl font-semibold text-slate-950">
              {mode === 'forgot' ? '找回密码' : '设置新密码'}
            </h2>
            {mode === 'forgot' && (
              <button type="button" onClick={() => setMode('login')} className="text-sm font-medium text-brand-700 hover:text-brand-800">
                返回登录
              </button>
            )}
          </div>
        )}

        {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        {success && <div className="mb-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}

        <form onSubmit={submit} className="space-y-4">
          {(mode === 'login' || mode === 'register') && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">用户名</label>
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder={mode === 'login' ? '用户名或邮箱' : '3-50位字母、数字、下划线'}
                autoComplete={mode === 'login' ? 'username' : 'new-username'}
                className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                required
                minLength={3}
                maxLength={50}
                pattern={mode === 'register' ? '[A-Za-z0-9_]+' : undefined}
              />
            </div>
          )}
          {mode === 'register' && (
            <>
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-sm font-medium text-slate-700">邮箱</label>
                  {!emailManual && email && (
                    <span className="text-xs text-slate-400">自动生成，可修改</span>
                  )}
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value)
                    setEmailManual(true)
                  }}
                  placeholder="your@email.com"
                  autoComplete="email"
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">姓名<span className="ml-1 text-xs text-slate-400">（选填）</span></label>
                <input
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="你的名字"
                  autoComplete="name"
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                />
              </div>
            </>
          )}
          {mode === 'forgot' && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">注册邮箱</label>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                required
              />
            </div>
          )}
          {mode !== 'forgot' && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                {mode === 'reset' ? '新密码' : '密码'}
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={mode === 'register' ? '至少8位字符' : ''}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 pr-12 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                  required
                  minLength={8}
                  maxLength={128}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  tabIndex={-1}
                >
                  {showPassword ? '隐藏' : '显示'}
                </button>
              </div>
              {mode === 'register' && password.length > 0 && (
                <div className="mt-1.5">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded-full ${
                          password.length >= level * 3
                            ? level <= 2 ? 'bg-red-400' : level === 3 ? 'bg-yellow-400' : 'bg-green-500'
                            : 'bg-slate-200'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    {password.length < 8 ? '密码至少8位' : password.length < 12 ? '建议使用更长密码' : '密码强度良好'}
                  </p>
                </div>
              )}
            </div>
          )}
          {mode === 'reset' && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">确认新密码</label>
              <input
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                className={`w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-brand-100 ${
                  confirmPassword && confirmPassword !== password
                    ? 'border-red-300 focus:border-red-500'
                    : 'border-slate-300 focus:border-brand-500'
                }`}
                required
                minLength={8}
                maxLength={128}
              />
              {confirmPassword && confirmPassword !== password && (
                <p className="mt-1 text-xs text-red-500">两次输入的密码不一致</p>
              )}
            </div>
          )}
          {mode === 'login' && (
            <div className="text-right">
              <button type="button" onClick={() => { setMode('forgot'); setError(''); setSuccess('') }} className="text-sm font-medium text-brand-700 hover:text-brand-800">
                忘记密码
              </button>
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-brand-600 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {loading
              ? '处理中...'
              : mode === 'login'
                ? '登录'
                : mode === 'register'
                  ? '注册并登录'
                  : mode === 'forgot'
                    ? '发送重置邮件'
                    : '重置密码'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default AuthPage
