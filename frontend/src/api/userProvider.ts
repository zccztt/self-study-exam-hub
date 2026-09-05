import apiClient, { unwrap } from './client'

export interface UserProviderConfig {
  id: number
  user_id: number
  config_type: 'ai' | 'search'
  name: string
  provider_type: string | null
  base_url: string
  model: string | null
  api_key_preview: string
  timeout: number
  is_active: boolean
  description: string | null
  created_at: string | null
  updated_at: string | null
}

export interface UserProviderCreate {
  config_type: 'ai' | 'search'
  name: string
  base_url: string
  api_key: string
  model?: string
  provider_type?: string
  timeout?: number
  description?: string
}

export interface UserProviderUpdate {
  name?: string
  base_url?: string
  api_key?: string
  model?: string
  provider_type?: string
  timeout?: number
  description?: string
  is_active?: boolean
}

export interface EffectiveConfig {
  ai: {
    source: string
    count: number
    providers: { name: string; model: string; base_url: string; source: string }[]
  }
  search: {
    source: string
    tavily_count: number
    has_search_api: boolean
  }
}

export const userProviderApi = {
  list: (configType?: string) =>
    unwrap<UserProviderConfig[]>(apiClient.get('/user/providers', { params: configType ? { config_type: configType } : {} })),

  get: (id: number) =>
    unwrap<UserProviderConfig>(apiClient.get(`/user/providers/${id}`)),

  create: (data: UserProviderCreate) =>
    unwrap<UserProviderConfig>(apiClient.post('/user/providers', data)),

  update: (id: number, data: UserProviderUpdate) =>
    unwrap<UserProviderConfig>(apiClient.put(`/user/providers/${id}`, data)),

  delete: (id: number) =>
    unwrap<{ message: string }>(apiClient.delete(`/user/providers/${id}`)),

  effective: () =>
    unwrap<EffectiveConfig>(apiClient.get('/user/providers/effective')),
}
