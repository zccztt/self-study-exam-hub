import axios, { AxiosResponse } from 'axios'

export interface ApiEnvelope<T> {
  code: number
  data: T
  message?: string
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function unwrap<T>(request: Promise<AxiosResponse<ApiEnvelope<T>>>): Promise<T> {
  const response = await request
  const payload = response.data
  if (payload.code !== 0) {
    throw new Error(payload.message || 'Request failed')
  }
  return payload.data
}

export default apiClient
