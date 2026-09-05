import apiClient, { unwrap } from './client'
import { Question } from './question'
import { ExamSession } from './exam'
import { sessionStore } from './session'

export type PaperType = 'real' | 'mock' | ''

export interface PastPaper {
  id: number
  subject_id: number
  subject_name: string
  name: string
  year: number
  month: number
  province_name?: string | null
  total_score: number
  duration: number
  question_count: number
  source?: string | null
  paper_type: 'real' | 'mock'
}

export interface PastPaperDetail extends PastPaper {
  paper_config?: Record<string, unknown> | null
  questions: Question[]
}

export interface PastPaperListResult {
  total: number
  page: number
  page_size: number
  items: PastPaper[]
}

export interface PastPaperSubject {
  subject_id: number
  code: string
  name: string
  paper_count: number
}

export interface PastPaperListParams {
  subject_id?: number
  year?: number
  month?: number
  province_id?: number
  paper_type?: PaperType
  keyword?: string
  page?: number
  page_size?: number
}

export const pastPaperApi = {
  list: (params: PastPaperListParams = {}) =>
    unwrap<PastPaperListResult>(apiClient.get('/past-papers', { params })),

  getDetail: (paperId: number) =>
    unwrap<PastPaperDetail>(apiClient.get(`/past-papers/${paperId}`)),

  start: (paperId: number) =>
    unwrap<ExamSession>(
      apiClient.post(`/past-papers/${paperId}/start`, {
        user_id: sessionStore.getUserId(),
      }),
    ),

  getSubjects: (paperType?: PaperType) =>
    unwrap<PastPaperSubject[]>(
      apiClient.get('/past-papers/subjects', {
        params: paperType ? { paper_type: paperType } : {},
      }),
    ),

  getYears: (subjectId?: number, paperType?: PaperType) =>
    unwrap<number[]>(
      apiClient.get('/past-papers/years', {
        params: {
          ...(subjectId ? { subject_id: subjectId } : {}),
          ...(paperType ? { paper_type: paperType } : {}),
        },
      }),
    ),
}
