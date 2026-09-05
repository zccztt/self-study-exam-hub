import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser } from '../api/auth'

interface AuthState {
  user: AuthUser | null
  token: string | null
  refreshToken: string | null
  setAuth: (user: AuthUser, token: string, refreshToken: string) => void
  setUser: (user: AuthUser) => void
  logout: () => void
  getUserId: (defaultId?: number) => number
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      setAuth: (user, token, refreshToken) => {
        set({ user, token, refreshToken })
        // Keep localStorage in sync for apiClient interceptor
        localStorage.setItem('token', token)
        localStorage.setItem('refresh_token', refreshToken)
        localStorage.setItem('user', JSON.stringify(user))
        window.dispatchEvent(new Event('session-changed'))
        // Load favorites after login
        import('./useFavoritesStore').then(({ useFavoritesStore }) => {
          useFavoritesStore.getState().loadFavorites()
        })
      },
      setUser: (user) => {
        set({ user })
        localStorage.setItem('user', JSON.stringify(user))
        window.dispatchEvent(new Event('session-changed'))
      },
      logout: () => {
        set({ user: null, token: null, refreshToken: null })
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        window.dispatchEvent(new Event('session-changed'))
        // Clear favorites on logout
        import('./useFavoritesStore').then(({ useFavoritesStore }) => {
          useFavoritesStore.getState().reset()
        })
      },
      getUserId: (defaultId = 1) => get().user?.id || defaultId,
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
      }),
    }
  )
)
