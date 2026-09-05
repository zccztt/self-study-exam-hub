import apiClient, { unwrap } from './client'

export interface DashboardData {
  user_count: number
  subject_count: number
  question_count: number
  video_count: number
  chapter_count: number
  exam_session_count: number
}

export interface AdminUser {
  id: number
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  created_at: string | null
}

export interface AdminSubject {
  id: number
  code: string
  name: string
  category: string
  description: string | null
  exam_duration: number
  total_score: number
  created_at: string | null
}

export interface AdminQuestion {
  id: number
  subject_id: number
  content: string
  question_type: string
  options: any
  answer: string
  explanation: string | null
  year: number | null
  month: number | null
  chapter_id: number | null
  difficulty: string
  frequency: number
  score: number
  created_at: string | null
}

export interface AdminVideo {
  id: number
  title: string
  url: string
  source: string
  duration: number | null
  author: string | null
  subject_id: number
  chapter_id: number | null
  description: string | null
  tags: string[] | null
  is_active: number
  created_at: string | null
}

export interface AdminChapter {
  id: number
  subject_id: number
  name: string
  order: number
  parent_id: number | null
  description: string | null
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export const adminApi = {
  dashboard: () => unwrap<DashboardData>(apiClient.get('/admin/dashboard')),

  // Users
  listUsers: (params: { page?: number; page_size?: number; keyword?: string } = {}) =>
    unwrap<PaginatedResult<AdminUser>>(apiClient.get('/admin/users', { params })),
  createUser: (data: { username: string; email: string; password: string; full_name?: string; is_superuser?: boolean }) =>
    unwrap<AdminUser>(apiClient.post('/admin/users', data)),
  updateUser: (id: number, data: { email?: string; full_name?: string; is_active?: boolean; is_superuser?: boolean }) =>
    unwrap<AdminUser>(apiClient.put(`/admin/users/${id}`, data)),
  deleteUser: (id: number) => unwrap<{ success: boolean }>(apiClient.delete(`/admin/users/${id}`)),

  // Subjects
  listSubjects: (params: { page?: number; page_size?: number; keyword?: string } = {}) =>
    unwrap<PaginatedResult<AdminSubject>>(apiClient.get('/admin/subjects', { params })),
  createSubject: (data: { code: string; name: string; category?: string; description?: string; exam_duration?: number; total_score?: number }) =>
    unwrap<AdminSubject>(apiClient.post('/admin/subjects', data)),
  updateSubject: (id: number, data: { code: string; name: string; category?: string; description?: string; exam_duration?: number; total_score?: number }) =>
    unwrap<AdminSubject>(apiClient.put(`/admin/subjects/${id}`, data)),
  deleteSubject: (id: number) => unwrap<{ success: boolean }>(apiClient.delete(`/admin/subjects/${id}`)),

  // Questions
  listQuestions: (params: { page?: number; page_size?: number; subject_id?: number; question_type?: string; keyword?: string } = {}) =>
    unwrap<PaginatedResult<AdminQuestion>>(apiClient.get('/admin/questions', { params })),
  createQuestion: (data: any) => unwrap<AdminQuestion>(apiClient.post('/admin/questions', data)),
  updateQuestion: (id: number, data: any) => unwrap<AdminQuestion>(apiClient.put(`/admin/questions/${id}`, data)),
  deleteQuestion: (id: number) => unwrap<{ success: boolean }>(apiClient.delete(`/admin/questions/${id}`)),
  importQuestions: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return unwrap<{ imported: number; errors: string[] }>(apiClient.post('/admin/questions/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    }))
  },

  // Videos
  listVideos: (params: { page?: number; page_size?: number; subject_id?: number; keyword?: string } = {}) =>
    unwrap<PaginatedResult<AdminVideo>>(apiClient.get('/admin/videos', { params })),
  createVideo: (data: any) => unwrap<AdminVideo>(apiClient.post('/admin/videos', data)),
  updateVideo: (id: number, data: any) => unwrap<AdminVideo>(apiClient.put(`/admin/videos/${id}`, data)),
  deleteVideo: (id: number) => unwrap<{ success: boolean }>(apiClient.delete(`/admin/videos/${id}`)),

  // Chapters
  listChapters: (subjectId?: number) =>
    unwrap<AdminChapter[]>(apiClient.get('/admin/chapters', { params: subjectId ? { subject_id: subjectId } : {} })),
  createChapter: (data: { subject_id: number; name: string; order?: number; parent_id?: number; description?: string }) =>
    unwrap<AdminChapter>(apiClient.post('/admin/chapters', data)),
  updateChapter: (id: number, data: { subject_id: number; name: string; order?: number; parent_id?: number; description?: string }) =>
    unwrap<AdminChapter>(apiClient.put(`/admin/chapters/${id}`, data)),
  deleteChapter: (id: number) => unwrap<{ success: boolean }>(apiClient.delete(`/admin/chapters/${id}`)),
}
