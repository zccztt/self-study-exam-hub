import apiClient, { unwrap } from './client'

export interface Subject {
  id: number
  name: string
  code: string
  category: string
  exam_duration: number
  total_score: number
  description?: string
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

export const subjectApi = {
  list: (q?: string) => unwrap<Subject[]>(apiClient.get('/subjects', { params: q ? { q } : undefined })),
  detail: (subjectId: number) => unwrap<SubjectDetail>(apiClient.get(`/subjects/${subjectId}`)),
}
