import axios, { AxiosResponse, InternalAxiosRequestConfig } from 'axios'

export interface ApiEnvelope<T> {
  code: number
  data: T
  message?: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Create a long-timeout client for AI analysis and online generation endpoints.
 * These can take 20-30 seconds to respond.
 */
export const longApiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

type RetriableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean }
let refreshPromise: Promise<string> | null = null

const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('Missing refresh token')
  const response = await axios.post<ApiEnvelope<{ access_token: string; refresh_token: string }>>(
    `${apiBaseUrl}/auth/refresh`,
    { refresh_token: refreshToken },
  )
  const tokens = response.data.data
  localStorage.setItem('token', tokens.access_token)
  localStorage.setItem('refresh_token', tokens.refresh_token)
  return tokens.access_token
}

const authInterceptor = (config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

apiClient.interceptors.request.use(authInterceptor)
longApiClient.interceptors.request.use(authInterceptor)

const responseErrorInterceptor = async (error: any) => {
  const status = error?.response?.status
  const requestConfig = error?.config as RetriableRequestConfig | undefined
  const requestUrl = String(requestConfig?.url || '')
  const canRefresh = status === 401
    && !requestConfig?._retry
    && !requestUrl.includes('/auth/login')
    && !requestUrl.includes('/auth/refresh')
    && Boolean(localStorage.getItem('refresh_token'))

  if (canRefresh && requestConfig) {
    requestConfig._retry = true
    try {
      refreshPromise ||= refreshAccessToken().finally(() => {
        refreshPromise = null
      })
      const accessToken = await refreshPromise
      requestConfig.headers.Authorization = `Bearer ${accessToken}`
      return apiClient.request(requestConfig)
    } catch {
      // Fall through to session cleanup and login redirect.
    }
  }

  const detail = error?.response?.data?.detail
  const validationMessage = Array.isArray(detail)
    ? detail.map((item: any) => item?.msg).filter(Boolean).join('；')
    : ''
  const message =
    typeof detail === 'string'
      ? detail
      : validationMessage || error?.message || '请求失败，请稍后重试。'

  if (status === 401 && !String(error?.config?.url || '').includes('/auth/login')) {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    window.dispatchEvent(new Event('session-changed'))
    const next = `${window.location.pathname}${window.location.search}`
    if (!window.location.pathname.endsWith('/auth')) {
      window.location.assign(`${import.meta.env.BASE_URL}auth?next=${encodeURIComponent(next)}`)
    }
  }

  return Promise.reject(new Error(message))
}

apiClient.interceptors.response.use((response) => response, responseErrorInterceptor)
longApiClient.interceptors.response.use((response) => response, responseErrorInterceptor)

export async function unwrap<T>(request: Promise<AxiosResponse<ApiEnvelope<T>>>): Promise<T> {
  const response = await request
  const payload = response.data
  if (payload.code !== 0) {
    throw new Error(payload.message || 'Request failed')
  }
  return payload.data
}

export default apiClient
