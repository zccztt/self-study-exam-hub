import apiClient, { unwrap } from './client'
import { Question } from './question'
import { sessionStore } from './session'

export type ExamMode = 'real_exam' | 'random' | 'chapter' | 'wrong_questions' | 'weak_point'

export interface GeneratePaperParams {
  subject_id: number
  mode: ExamMode
  config?: Record<string, unknown>
}

export interface ConstraintReport {
  algorithm: string
  requested_count: number
  target_count: number
  selected_count: number
  available_count: number
  question_type_target: Record<string, number>
  question_type_actual: Record<string, number>
  difficulty_target: Record<string, number>
  difficulty_actual: Record<string, number>
  chapter_coverage_target_count: number
  chapter_coverage_actual_count: number
  chapter_coverage_actual: number
  covered_chapter_ids: number[]
  target_chapter_ids: number[]
  recent_done_excluded_count?: number
  satisfied: boolean
  relaxed: string[]
}

export interface GeneratedPaper {
  exam_id: number | null
  subject_id: number
  mode: ExamMode
  name?: string
  total_score: number
  duration: number
  requested_question_count?: number
  available_question_count?: number
  online_generated_count?: number
  saved_online_question_count?: number
  question_count: number
  questions: Question[]
  message?: string | null
  constraint_report?: ConstraintReport
}

export interface ExamSession {
  session_id: string
  exam_id: number
  start_time: string
  end_time: string
  duration: number
  status: string
}

export interface ExamSessionDetail extends ExamHistoryItem {
  duration: number
  paper: GeneratedPaper
  result?: ScoreResult
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
  subjective_count?: number
  auto_scored_count?: number
  manual_count: number
  accuracy: number
  wrong_questions: number[]
  question_analysis: Array<{
    question_id: number
    content: string
    question_type?: string
    options?: string[]
    user_answer: string
    correct_answer: string
    is_correct: boolean | null
    score: number
    full_score: number
    explanation?: string
    final_explanation?: string
    grading_method?: string
    scoring_points?: Array<{
      label: string
      score: number
      earned_score: number
      matched_keywords?: string[]
      missing_keywords?: string[]
      comment?: string
    }>
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

export interface WeakPoint {
  point_id: number
  name: string
  description: string
  chapter_id: number
  subject_id: number
  mastery_level: number
  correct_count: number
  wrong_count: number
  priority: 'high' | 'medium'
}

export interface WeakPointResult {
  items: WeakPoint[]
  total: number
}

export const examApi = {
  getWeakPoints: (userId = sessionStore.getUserId(), subjectId?: number) =>
    unwrap<WeakPointResult>(
      apiClient.get(`/exam/weak-points/${userId}`, {
        params: subjectId ? { subject_id: subjectId } : {},
      }),
    ),
  generatePaper: (params: GeneratePaperParams) =>
    unwrap<GeneratedPaper>(apiClient.post('/exam/generate', params, { timeout: 120000 })),
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
  getSession: (sessionId: string) => unwrap<ExamSessionDetail>(apiClient.get(`/exam/session/${sessionId}`)),
  cancelSession: (sessionId: string) => unwrap<ExamHistoryItem>(apiClient.delete(`/exam/session/${sessionId}`)),
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
  exportWrongQuestions: async (
    params: WrongQuestionParams = {},
    format: 'markdown' | 'csv' | 'word' = 'markdown',
  ) => {
    const response = await apiClient.get(`/exam/wrong-questions/${params.user_id || sessionStore.getUserId()}/export`, {
      params: { ...serializeWrongQuestionParams(params), format },
      responseType: 'blob',
    })
    return response.data as Blob
  },
  updateWrongQuestion: (
    questionId: number,
    payload: { is_mastered?: boolean; tags?: string[]; note?: string },
    userId = sessionStore.getUserId(),
  ) => unwrap<WrongQuestionItem>(apiClient.patch(`/exam/wrong-questions/${userId}/${questionId}`, payload)),
  removeWrongQuestion: (questionId: number, userId = sessionStore.getUserId()) =>
    unwrap<{ success: boolean }>(apiClient.delete(`/exam/wrong-questions/${userId}/${questionId}`)),
}
