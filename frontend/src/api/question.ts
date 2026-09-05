import apiClient, { unwrap } from './client'
import { sessionStore } from './session'

export interface Question {
  id: number
  content: string
  question_type: string
  options: string[]
  difficulty: string
  year?: number
  month?: number
  frequency: number
  subject_id: number
  subject_code?: string
  subject_name?: string
  chapter_id?: number
  score: number
  source?: string
  source_url?: string
  is_online?: boolean
  is_favorited?: boolean
  favorite_tags?: string[]
  favorite_note?: string
  answer?: string
  explanation?: string
}

export interface SearchQuestionsParams {
  keyword?: string
  subject_id?: number
  subject_code?: string
  subject_query?: string
  years?: number[]
  question_types?: string[]
  difficulty?: string
  chapter_ids?: number[]
  high_frequency?: boolean
  online_search?: boolean
  page?: number
  page_size?: number
}

export interface QuestionSearchResult {
  total: number
  page: number
  page_size: number
  local_count?: number
  online_count?: number
  online_enabled?: boolean
  items: Question[]
}

const serializeParams = (params: SearchQuestionsParams) => ({
  ...params,
  years: params.years?.join(','),
  question_types: params.question_types?.join(','),
  chapter_ids: params.chapter_ids?.join(','),
})

export const questionApi = {
  searchQuestions: (params: SearchQuestionsParams, signal?: AbortSignal) =>
    unwrap<QuestionSearchResult>(apiClient.get('/questions/search', { params: serializeParams(params), signal })),
  getQuestionDetail: (questionId: number) => unwrap<Question>(apiClient.get(`/questions/${questionId}`)),
  addToFavorites: (questionId: number, tags?: string[]) =>
    unwrap<{ success: boolean }>(apiClient.post('/questions/favorites', { question_id: questionId, tags })),
  removeFromFavorites: (questionId: number, userId = sessionStore.getUserId()) =>
    unwrap<{ success: boolean }>(apiClient.delete(`/questions/favorites/${userId}/${questionId}`)),
  getFavorites: (userId = sessionStore.getUserId(), page = 1, pageSize = 20) =>
    unwrap<QuestionSearchResult>(
      apiClient.get(`/questions/favorites/${userId}`, {
        params: { page, page_size: pageSize },
      }),
    ),
  getHighFrequencyQuestions: (subjectId: number, limit = 50) =>
    unwrap<Question[]>(apiClient.get(`/questions/high-frequency/${subjectId}`, { params: { limit } })),
}
