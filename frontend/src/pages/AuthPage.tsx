import React, { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import { sessionStore } from '../api/session'

type AuthMode = 'login' | 'register'

const AuthPage: React.FC = () => {
  const navigate = useNavigate()
  const [mode, setMode] = useState<AuthMode>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fillDemoAccount = () => {
    setMode('login')
    setUsername('demo')
    setPassword('demo123456')
    setError('')
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
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
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : mode === 'login' ? '登录失败' : '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-6 px-4 py-10 lg:grid-cols-[0.9fr_1.1fr]">
      <aside className="rounded-xl border border-slate-200 bg-slate-950 p-6 text-white shadow-sm">
        <div className="text-sm font-medium text-blue-200">演示环境</div>
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
          className="mt-5 w-full rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-blue-50"
        >
          填入演示账号
        </button>
      </aside>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium ${
              mode === 'login' ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-white'
            }`}
          >
            登录
          </button>
          <button
            type="button"
            onClick={() => setMode('register')}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium ${
              mode === 'register' ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-white'
            }`}
          >
            注册
          </button>
        </div>

        {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">用户名</label>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            />
          </div>
          {mode === 'register' && (
            <>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">邮箱</label>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">姓名</label>
                <input
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </div>
            </>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">密码</label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 py-2.5 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? '处理中...' : mode === 'login' ? '登录' : '注册并登录'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default AuthPage
