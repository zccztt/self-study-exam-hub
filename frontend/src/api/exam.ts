import apiClient, { unwrap } from './client'
import { Question } from './question'
import { sessionStore } from './session'

export type ExamMode = 'real_exam' | 'random' | 'chapter' | 'wrong_questions'

export interface GeneratePaperParams {
  subject_id: number
  mode: ExamMode
  config?: Record<string, unknown>
}

export interface GeneratedPaper {
  exam_id: number | null
  subject_id: number
  mode: ExamMode
  name?: string
  total_score: number
  duration: number
  question_count: number
  questions: Question[]
  message?: string
}

export interface ExamSession {
  session_id: string
  exam_id: number
  start_time: string
  end_time: string
  duration: number
  status: string
}

export interface ExamHistoryItem {
  session_id: string
  exam_id: number
  user_id: number
  status: string
  answers: Record<string, string>
  score?: number
  correct_count?: number
  total_count?: number
  start_time?: string
  end_time?: string
  submitted_at?: string
}

export interface ExamHistoryResult {
  total: number
  page: number
  page_size: number
  items: ExamHistoryItem[]
}

export interface ScoreResult {
  session_id: string
  score: number
  total_score: number
  correct_count: number
  total_count: number
  objective_count: number
  manual_count: number
  accuracy: number
  wrong_questions: number[]
  question_analysis: Array<{
    question_id: number
    content: string
    user_answer: string
    correct_answer: string
    is_correct: boolean | null
    score: number | null
    full_score: number
    explanation?: string
  }>
}

export interface WrongQuestionItem {
  id: number
  user_id: number
  question_id: number
  session_id?: string
  user_answer?: string
  wrong_count: number
  is_mastered: boolean
  tags: string[]
  note?: string
  last_wrong_at?: string
  created_at?: string
  question: Question
  knowledge_points: Array<{
    id: number
    name: string
    chapter_id: number
    importance: string
    frequency: number
  }>
}

export interface WrongQuestionResult {
  total: number
  page: number
  page_size: number
  items: WrongQuestionItem[]
}

export interface WrongQuestionParams {
  user_id?: number
  subject_id?: number
  chapter_ids?: number[]
  is_mastered?: boolean
  keyword?: string
  page?: number
  page_size?: number
}

const serializeWrongQuestionParams = (params: WrongQuestionParams) => ({
  subject_id: params.subject_id,
  chapter_ids: params.chapter_ids?.join(','),
  is_mastered: params.is_mastered,
  keyword: params.keyword,
  page: params.page,
  page_size: params.page_size,
})

export const examApi = {
  generatePaper: (params: GeneratePaperParams) =>
    unwrap<GeneratedPaper>(apiClient.post('/exam/generate', params)),
  startExam: (examId: number, userId = sessionStore.getUserId()) =>
    unwrap<ExamSession>(apiClient.post('/exam/start', { exam_id: examId, user_id: userId })),
  submitAnswer: (sessionId: string, questionId: number, answer: string) =>
    unwrap<{ success: boolean; message: string; answered_count?: number }>(
      apiClient.post('/exam/submit-answer', {
        session_id: sessionId,
        question_id: questionId,
        answer,
      }),
    ),
  submitPaper: (sessionId: string) => unwrap<ScoreResult>(apiClient.post(`/exam/submit/${sessionId}`)),
  getHistory: (userId = sessionStore.getUserId(), page = 1, pageSize = 20) =>
    unwrap<ExamHistoryResult>(
      apiClient.get(`/exam/history/${userId}`, {
        params: { page, page_size: pageSize },
      }),
    ),
  getWrongQuestions: (params: WrongQuestionParams = {}) =>
    unwrap<WrongQuestionResult>(
      apiClient.get(`/exam/wrong-questions/${params.user_id || sessionStore.getUserId()}`, {
        params: serializeWrongQuestionParams(params),
      }),
    ),
  updateWrongQuestion: (
    questionId: number,
    payload: { is_mastered?: boolean; tags?: string[]; note?: string },
    userId = sessionStore.getUserId(),
  ) => unwrap<WrongQuestionItem>(apiClient.patch(`/exam/wrong-questions/${userId}/${questionId}`, payload)),
  removeWrongQuestion: (questionId: number, userId = sessionStore.getUserId()) =>
    unwrap<{ success: boolean }>(apiClient.delete(`/exam/wrong-questions/${userId}/${questionId}`)),
}
