import type { AuthResult, AuthUser } from './auth'
import { useAuthStore } from '../stores/useAuthStore'

const SESSION_CHANGED_EVENT = 'session-changed'

export const sessionStore = {
  saveAuth(result: AuthResult) {
    const refreshToken = 'refresh_token' in result
      ? (result as unknown as { refresh_token: string }).refresh_token
      : ''
    useAuthStore.getState().setAuth(result.user, result.access_token, refreshToken)
  },
  clear() {
    useAuthStore.getState().logout()
  },
  getUser(): AuthUser | null {
    return useAuthStore.getState().user
  },
  getToken() {
    return useAuthStore.getState().token
  },
  getRefreshToken() {
    return useAuthStore.getState().refreshToken
  },
  saveUser(user: AuthUser) {
    useAuthStore.getState().setUser(user)
  },
  getUserId(defaultUserId = 1) {
    return useAuthStore.getState().getUserId(defaultUserId)
  },
  eventName: SESSION_CHANGED_EVENT,
}
