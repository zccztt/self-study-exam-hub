/**
 * 题库相关 API
 */
import apiClient from './client'

export interface SearchQuestionsParams {
  keyword?: string
  subject_id?: number
  years?: number[]
  question_types?: string[]
  difficulty?: string
  chapter_ids?: number[]
  high_frequency?: boolean
  page?: number
  page_size?: number
}

export const questionApi = {
  // 搜索题目
  searchQuestions: (params: SearchQuestionsParams) =>
    apiClient.get('/questions/search', { params }),

  // 获取题目详情
  getQuestionDetail: (questionId: number) =>
    apiClient.get(`/questions/${questionId}`),

  // 添加到收藏
  addToFavorites: (questionId: number, tags?: string[]) =>
    apiClient.post('/questions/favorites', {
      question_id: questionId,
      tags,
    }),

  // 获取高频题目
  getHighFrequencyQuestions: (subjectId: number, limit = 50) =>
    apiClient.get('/questions/high-frequency', {
      params: { subject_id: subjectId, limit },
    }),
}
