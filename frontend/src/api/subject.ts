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
}

export interface SubjectDetail extends Subject {
  chapters: Chapter[]
}

export const subjectApi = {
  list: () => unwrap<Subject[]>(apiClient.get('/subjects')),
  detail: (subjectId: number) => unwrap<SubjectDetail>(apiClient.get(`/subjects/${subjectId}`)),
}
