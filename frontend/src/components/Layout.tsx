import React, { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { authApi, AuthUser } from '../api/auth'
import { sessionStore } from '../api/session'

interface LayoutProps {
  children: React.ReactNode
}

const navItems = [
  { to: '/exam', label: '模拟考试' },
  { to: '/questions', label: '题库搜索' },
  { to: '/videos', label: '资源中心' },
  { to: '/analysis', label: '考点分析' },
  { to: '/planner', label: '学习规划' },
  { to: '/favorites', label: '收藏错题' },
]

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => sessionStore.getUser())

  useEffect(() => {
    const syncUser = () => setUser(sessionStore.getUser())
    window.addEventListener('storage', syncUser)
    window.addEventListener('focus', syncUser)
    window.addEventListener(sessionStore.eventName, syncUser)
    return () => {
      window.removeEventListener('storage', syncUser)
      window.removeEventListener('focus', syncUser)
      window.removeEventListener(sessionStore.eventName, syncUser)
    }
  }, [])

  useEffect(() => {
    if (user || !sessionStore.getToken()) return
    const loadUser = async () => {
      try {
        const currentUser = await authApi.me()
        sessionStore.saveUser(currentUser)
        setUser(currentUser)
      } catch {
        sessionStore.clear()
      }
    }
    void loadUser()
  }, [user])

  const logout = () => {
    sessionStore.clear()
    setUser(null)
  }

  return (
    <div className="min-h-screen bg-[#f4f7fb] text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <nav className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <Link to="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-sm font-bold text-white">
                自考
              </div>
              <div>
                <div className="text-base font-semibold leading-tight text-slate-950">自考备考中枢</div>
                <div className="text-xs text-slate-500">2026 公共课 · 题库 · 规划 · 错题闭环</div>
              </div>
            </Link>
            <div className="flex items-center gap-3">
              {user ? (
                <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-600">
                  <span>{user.full_name || user.username}</span>
                  <button type="button" onClick={logout} className="font-medium text-slate-950 hover:text-blue-600">
                    退出
                  </button>
                </div>
              ) : (
                <Link to="/auth" className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  登录演示
                </Link>
              )}
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-full px-3 py-2 text-sm font-medium transition ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-white hover:text-slate-950'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>

      <footer className="mt-10 border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-6 text-sm text-slate-500 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
          <span>© 2026 自考备考中枢</span>
          <span>演示账号：demo / demo123456</span>
        </div>
      </footer>
    </div>
  )
}

export default Layout
