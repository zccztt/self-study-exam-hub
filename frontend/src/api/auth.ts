import apiClient, { unwrap } from './client'

export interface AuthUser {
  id: number
  username: string
  email: string
  full_name?: string
  is_active: boolean
  is_superuser?: boolean
  current_job?: string
  education_background?: string
  education_major?: string
  skills?: string
  study_hours_per_day?: number
  exam_experience?: string
  learning_preference?: string
}

export interface AuthResult {
  access_token: string
  refresh_token: string
  token_type: string
  user: AuthUser
}

export interface TokenResult {
  access_token: string
  refresh_token: string
  token_type: string
}

export const authApi = {
  register: (params: { username: string; email: string; password: string; full_name?: string }) =>
    unwrap<AuthResult>(apiClient.post('/auth/register', params)),
  login: (params: { username: string; password: string }) =>
    unwrap<AuthResult>(apiClient.post('/auth/login', params)),
  refresh: (refreshToken: string) =>
    unwrap<TokenResult>(apiClient.post('/auth/refresh', { refresh_token: refreshToken })),
  me: () => unwrap<AuthUser>(apiClient.get('/auth/me')),
  updateProfile: (params: {
    email?: string
    full_name?: string
    current_job?: string
    education_background?: string
    education_major?: string
    skills?: string
    study_hours_per_day?: number
    exam_experience?: string
    learning_preference?: string
  }) =>
    unwrap<AuthUser>(apiClient.patch('/auth/profile', params)),
  changePassword: (params: { current_password: string; new_password: string }) =>
    unwrap<{ success: boolean }>(apiClient.post('/auth/password', params)),
  requestPasswordReset: (email: string) =>
    unwrap<{ accepted: boolean; delivery_available: boolean }>(
      apiClient.post('/auth/forgot-password', { email }),
    ),
  resetPassword: (token: string, newPassword: string) =>
    unwrap<{ success: boolean }>(
      apiClient.post('/auth/reset-password', { token, new_password: newPassword }),
    ),
}
