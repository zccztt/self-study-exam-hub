import type { AuthResult, AuthUser } from './auth'

const TOKEN_KEY = 'token'
const USER_KEY = 'user'
const SESSION_CHANGED_EVENT = 'session-changed'

const notifySessionChanged = () => {
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT))
}

export const sessionStore = {
  saveAuth(result: AuthResult) {
    localStorage.setItem(TOKEN_KEY, result.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(result.user))
    notifySessionChanged()
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    notifySessionChanged()
  },
  getUser(): AuthUser | null {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as AuthUser
    } catch {
      return null
    }
  },
  getToken() {
    return localStorage.getItem(TOKEN_KEY)
  },
  saveUser(user: AuthUser) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    notifySessionChanged()
  },
  getUserId(defaultUserId = 1) {
    return sessionStore.getUser()?.id || defaultUserId
  },
  eventName: SESSION_CHANGED_EVENT,
}
