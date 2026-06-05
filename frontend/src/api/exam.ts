/**
 * 考试相关 API
 */
import apiClient from './client'

export interface GeneratePaperParams {
  subject_id: number
  mode: 'real_exam' | 'random' | 'chapter' | 'wrong_questions'
  config?: Record<string, any>
}

export interface StartExamParams {
  paper_id: number
}

export const examApi = {
  // 生成试卷
  generatePaper: (params: GeneratePaperParams) =>
    apiClient.post('/exam/generate', params),

  // 开始考试
  startExam: (params: StartExamParams) =>
    apiClient.post('/exam/start', params),

  // 提交答案
  submitAnswer: (sessionId: string, questionId: number, answer: string) =>
    apiClient.post(`/exam/sessions/${sessionId}/answer`, {
      question_id: questionId,
      answer,
    }),

  // 提交试卷
  submitPaper: (sessionId: string) =>
    apiClient.post(`/exam/sessions/${sessionId}/submit`),

  // 获取考试历史
  getExamHistory: (userId: number) =>
    apiClient.get(`/exam/history/${userId}`),
}
