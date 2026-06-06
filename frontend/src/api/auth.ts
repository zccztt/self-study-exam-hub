import apiClient, { unwrap } from './client'

export interface AuthUser {
  id: number
  username: string
  email: string
  full_name?: string
  is_active: boolean
}

export interface AuthResult {
  access_token: string
  token_type: string
  user: AuthUser
}

export const authApi = {
  register: (params: { username: string; email: string; password: string; full_name?: string }) =>
    unwrap<AuthResult>(apiClient.post('/auth/register', params)),
  login: (params: { username: string; password: string }) =>
    unwrap<AuthResult>(apiClient.post('/auth/login', params)),
  me: () => unwrap<AuthUser>(apiClient.get('/auth/me')),
}
