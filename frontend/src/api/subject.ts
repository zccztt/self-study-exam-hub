import apiClient, { unwrap } from './client'

const CACHE_TTL_MS = 5 * 60 * 1000
const subjectListCache = new Map<string, { expiresAt: number; promise: Promise<Subject[]> }>()
const subjectDetailCache = new Map<number, { expiresAt: number; promise: Promise<SubjectDetail> }>()

export interface Subject {
  id: number
  name: string
  code: string
  category: string
  exam_duration: number
  total_score: number
  description?: string
  question_count: number
  video_count: number
  has_content: boolean
}

export interface Chapter {
  id: number
  name: string
  order: number
  description?: string
}

export interface SubjectDetail extends Subject {
  chapters: Chapter[]
}

export interface ContentOverview {
  subject_count: number
  subjects_with_questions: number
  question_count: number
  exam_count: number
  video_count: number
}

export type LearningResourceType = 'textbook' | 'textbook_info' | 'exam_outline' | 'open_course' | 'study_materials' | 'catalog'

export interface LearningResource {
  title: string
  url: string
  resource_type: LearningResourceType
  source: string
  access_note: string
  is_free: boolean
  is_full_text: boolean
  verified: boolean
}

export interface LearningResourceResult {
  subject_id: number
  subject_code: string
  subject_name: string
  items: LearningResource[]
  has_authorized_full_text_textbook: boolean
  online_searched: boolean
  notice: string
}

export const subjectApi = {
  list: (q?: string, hasContent?: boolean) => {
    const key = `${q || ''}:${String(hasContent)}`
    const cached = subjectListCache.get(key)
    if (cached && cached.expiresAt > Date.now()) return cached.promise
    const promise = unwrap<Subject[]>(apiClient.get('/subjects', {
      params: { q: q || undefined, has_content: hasContent },
    })).catch((error) => {
      subjectListCache.delete(key)
      throw error
    })
    subjectListCache.set(key, { expiresAt: Date.now() + CACHE_TTL_MS, promise })
    return promise
  },
  overview: () => unwrap<ContentOverview>(apiClient.get('/subjects/overview')),
  detail: (subjectId: number) => {
    const cached = subjectDetailCache.get(subjectId)
    if (cached && cached.expiresAt > Date.now()) return cached.promise
    const promise = unwrap<SubjectDetail>(apiClient.get(`/subjects/${subjectId}`)).catch((error) => {
      subjectDetailCache.delete(subjectId)
      throw error
    })
    subjectDetailCache.set(subjectId, { expiresAt: Date.now() + CACHE_TTL_MS, promise })
    return promise
  },
  learningResources: (subjectId: number, onlineSearch = false) =>
    unwrap<LearningResourceResult>(apiClient.get(`/subjects/${subjectId}/learning-resources`, {
      params: { online_search: onlineSearch },
    })),
}
