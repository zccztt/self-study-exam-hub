import apiClient, { unwrap } from './client'

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

export interface AIProvider {
  id: number
  name: string
  base_url: string
  model: string  // comma-separated or JSON array
  api_key_preview: string
  timeout: number
  weight: number
  roles: string[] | null
  is_active: boolean
  priority: number
  description: string | null
  last_test_at: string | null
  last_test_ok: boolean | null
  created_at: string | null
  updated_at: string | null
}

export interface AIProviderCreate {
  name: string
  base_url: string
  model: string
  api_key: string
  timeout?: number
  weight?: number
  roles?: string[]
  priority?: number
  description?: string
}

export interface AIProviderUpdate {
  name?: string
  base_url?: string
  model?: string
  api_key?: string
  timeout?: number
  weight?: number
  roles?: string[]
  priority?: number
  description?: string
  is_active?: boolean
}

export interface SearchProvider {
  id: number
  name: string
  provider_type: string
  base_url: string
  api_key_preview: string
  timeout: number
  weight: number
  is_active: boolean
  priority: number
  description: string | null
  last_test_at: string | null
  last_test_ok: boolean | null
  created_at: string | null
  updated_at: string | null
}

export interface SearchProviderCreate {
  name: string
  provider_type: string
  base_url: string
  api_key: string
  timeout?: number
  weight?: number
  priority?: number
  description?: string
}

export interface SearchProviderUpdate {
  name?: string
  provider_type?: string
  base_url?: string
  api_key?: string
  timeout?: number
  weight?: number
  priority?: number
  description?: string
  is_active?: boolean
}

export interface TestResult {
  success: boolean
  reply?: string
  status_code?: number
  latency_ms: number
  error: string | null
  model?: string  // which model was tested
}

export interface BatchTestResult {
  model: string
  success: boolean
  reply?: string
  latency_ms: number
  error: string | null
}

// ------------------------------------------------------------------
// API
// ------------------------------------------------------------------

export const adminProviderApi = {
  // ---- AI Providers ----
  listAI: (includeInactive = false) =>
    unwrap<AIProvider[]>(apiClient.get('/admin/ai-providers', { params: { include_inactive: includeInactive } })),

  getAI: (id: number) =>
    unwrap<AIProvider>(apiClient.get(`/admin/ai-providers/${id}`)),

  createAI: (data: AIProviderCreate) =>
    unwrap<AIProvider>(apiClient.post('/admin/ai-providers', data)),

  updateAI: (id: number, data: AIProviderUpdate) =>
    unwrap<AIProvider>(apiClient.put(`/admin/ai-providers/${id}`, data)),

  deleteAI: (id: number) =>
    unwrap<{ message: string }>(apiClient.delete(`/admin/ai-providers/${id}`)),

  testAI: (id: number, prompt?: string, model?: string) =>
    unwrap<TestResult>(apiClient.post(`/admin/ai-providers/${id}/test`, {
      ...(prompt ? { prompt } : {}),
      ...(model ? { model } : {}),
    })),

  testAIBatch: (id: number, models: string[], prompt?: string) =>
    unwrap<BatchTestResult[]>(apiClient.post(`/admin/ai-providers/${id}/test-batch`, {
      models,
      ...(prompt ? { prompt } : {}),
    })),

  fetchModels: (base_url: string, api_key: string, provider_id?: number) =>
    unwrap<string[]>(apiClient.post('/admin/ai-providers/fetch-models',
      provider_id ? { provider_id } : { base_url, api_key }
    )),

  reloadAI: () =>
    unwrap<{ loaded: number; source: string; message?: string }>(apiClient.post('/admin/ai-providers/reload')),

  // ---- Search Providers ----
  listSearch: (includeInactive = false) =>
    unwrap<SearchProvider[]>(apiClient.get('/admin/search-providers', { params: { include_inactive: includeInactive } })),

  getSearch: (id: number) =>
    unwrap<SearchProvider>(apiClient.get(`/admin/search-providers/${id}`)),

  createSearch: (data: SearchProviderCreate) =>
    unwrap<SearchProvider>(apiClient.post('/admin/search-providers', data)),

  updateSearch: (id: number, data: SearchProviderUpdate) =>
    unwrap<SearchProvider>(apiClient.put(`/admin/search-providers/${id}`, data)),

  deleteSearch: (id: number) =>
    unwrap<{ message: string }>(apiClient.delete(`/admin/search-providers/${id}`)),

  testSearch: (id: number, prompt?: string) =>
    unwrap<TestResult>(apiClient.post(`/admin/search-providers/${id}/test`, prompt ? { prompt } : {})),

  reloadSearch: () =>
    unwrap<{ tavily_count: number; search_api: boolean; sources: string[] }>(
      apiClient.post('/admin/search-providers/reload'),
    ),
}
