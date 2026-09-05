import apiClient, { unwrap } from './client'

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

export interface Province {
  id: number
  code: string
  name: string
}

export interface School {
  id: number
  name: string
  province_id: number
  code: string | null
  logo_url: string | null
}

export interface Major {
  id: number
  code: string
  name: string
  level: string
  province_id: number
  school_id: number
  total_credits: number | null
  description: string | null
}

export interface MajorSubjectItem {
  subject_id: number
  code: string
  name: string
  course_type: string
  credits: number | null
  sort_order: number
}

export interface EnrollmentProgress {
  total: number
  passed: number
  failed: number
  not_taken: number
  total_credits: number
  earned_credits: number
  completion_rate: number
}

export interface EnrollmentListItem {
  id: number
  major_id: number
  major_code: string
  major_name: string
  level: string
  school_name: string
  province_name: string
  target_date: string | null
  is_active: boolean
  created_at: string | null
  progress: EnrollmentProgress
}

export interface SubjectStatusItem {
  subject_id: number
  code: string
  name: string
  credits: number | null
  course_type: string
  status: 'not_taken' | 'passed' | 'failed'
  score: number | null
  exam_date: string | null
  attempt_count: number
  certificate_no: string | null
  note: string | null
  /** 旧课程代码(如果当前课程是由旧代码替代而来) */
  replaced_from_code?: string | null
  replaced_from_name?: string | null
  replacement_note?: string | null
}

export interface EnrollmentSubjectsData {
  enrollment: {
    id: number
    major_name: string
    school_name: string
    province_name: string
    target_date: string | null
  }
  progress: EnrollmentProgress
  subjects: {
    required: SubjectStatusItem[]
    elective: SubjectStatusItem[]
    additional: SubjectStatusItem[]
  }
}

export interface SubjectStatusUpdateResult {
  subject_id: number
  status: string
  score: number | null
  exam_date: string | null
  attempt_count: number
}

export interface ReplacementMapItem {
  new_code: string
  new_name: string
  old_code: string
  old_name: string
  note: string
}

export interface CourseRecommendationItem {
  code: string
  name: string
  credits: number | null
  course_type: string
  category: string
  status: string
  priority_score: number
  question_count: number
  reason: string
  estimated_hours: number
}

export interface SprintWeek {
  period: string
  focus: string
  tasks: string[]
  courses: { code: string; name: string }[]
}

export interface SprintPlan {
  course_count: number
  total_hours: number
  sprint_weeks: number
  daily_hours: number
  picks: { code: string; name: string; credits: number | null; reason: string }[]
  weeks: SprintWeek[]
  tips: string[]
}

export interface StudyPhase {
  phase: number
  courses: { code: string; name: string; credits: number | null; hours: number }[]
  total_hours: number
  weeks_needed: number
  daily_hours: number
  strategy: string
}

export interface StudyPlan {
  total_courses: number
  total_phases: number
  daily_hours: number
  phases: StudyPhase[]
  message?: string
}

export interface CourseRecommendation {
  user_profile: Record<string, any>
  total_remaining: number
  total_passed: number
  recommendations: CourseRecommendationItem[]
  next_exam_picks: CourseRecommendationItem[]
  study_plan: StudyPlan | null
  sprint_plan: SprintPlan | null
  message?: string
}

// ------------------------------------------------------------------
// API
// ------------------------------------------------------------------

export const enrollmentApi = {
  // Public lookups
  getProvinces: () => unwrap<Province[]>(apiClient.get('/enrollment/provinces')),

  getSchools: (provinceId?: number) =>
    unwrap<School[]>(apiClient.get('/enrollment/schools', { params: provinceId ? { province_id: provinceId } : {} })),

  getMajors: (params: { province_id?: number; school_id?: number; level?: string; q?: string }) =>
    unwrap<Major[]>(apiClient.get('/enrollment/majors', { params })),

  getMajorSubjects: (majorId: number) =>
    unwrap<MajorSubjectItem[]>(apiClient.get(`/enrollment/majors/${majorId}/subjects`)),

  // User enrollment
  createEnrollment: (majorId: number, targetDate?: string) =>
    unwrap<{ id: number; user_id: number; major_id: number; target_date: string | null }>(
      apiClient.post('/enrollment', { major_id: majorId, target_date: targetDate || null }),
    ),

  listEnrollments: () => unwrap<EnrollmentListItem[]>(apiClient.get('/enrollment/list')),

  deleteEnrollment: (enrollmentId: number) =>
    unwrap<{ success?: boolean }>(apiClient.delete(`/enrollment/${enrollmentId}`)),

  updateEnrollment: (enrollmentId: number, targetDate?: string | null) =>
    unwrap<{ id: number; target_date: string | null }>(apiClient.put(`/enrollment/${enrollmentId}`, { target_date: targetDate ?? null })),

  // Subjects & status
  getEnrollmentSubjects: (enrollmentId: number) =>
    unwrap<EnrollmentSubjectsData>(apiClient.get(`/enrollment/${enrollmentId}/subjects`)),

  updateSubjectStatus: (params: {
    enrollment_id: number
    subject_id: number
    status: string
    score?: number | null
    exam_date?: string | null
    certificate_no?: string | null
    note?: string | null
  }) => unwrap<SubjectStatusUpdateResult>(apiClient.put('/enrollment/subject-status', params)),

  getProgress: (enrollmentId: number) =>
    unwrap<EnrollmentProgress>(apiClient.get(`/enrollment/${enrollmentId}/progress`)),

  getRemainingSubjects: (enrollmentId: number) =>
    unwrap<number[]>(apiClient.get(`/enrollment/${enrollmentId}/remaining-subjects`)),

  /** 获取全部新旧课程替代对照（无需登录） */
  getReplacementMap: () =>
    unwrap<ReplacementMapItem[]>(apiClient.get('/enrollment/replacement-map')),

  /** 获取个性化报考课程建议和学习计划 */
  getCourseRecommendation: (enrollmentId?: number) =>
    unwrap<CourseRecommendation>(apiClient.get('/enrollment/recommendation', {
      params: enrollmentId ? { enrollment_id: enrollmentId } : {},
    })),
}
