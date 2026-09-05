import apiClient, { unwrap } from './client'

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

export interface ExamSession {
  name: string
  exam_dates: string[]
  register_start: string
  register_end: string
  score_release: string
  note: string
}

export interface ExamYearSchedule {
  year: number
  sessions: ExamSession[]
}

export interface CountdownInfo {
  date: string
  days_remaining: number
  status: 'upcoming' | 'today' | 'passed'
}

export interface UpcomingEvent {
  type: 'exam' | 'registration' | 'score'
  name: string
  countdown: CountdownInfo
  dates?: string[]
  note?: string
  register_start?: string
  register_end?: string
  status?: 'upcoming' | 'open' | 'closed'
}

export interface PlanSession {
  name: string
  exam_date: string
  register_start: string
  register_end: string
  suggested_count: number
}

export interface StudyPlanSuggestion {
  remaining_subjects: number
  target_date: string | null
  sessions_needed: number
  total_capacity: number
  feasible: boolean
  advice: string
  plan: PlanSession[]
}

// ------------------------------------------------------------------
// API
// ------------------------------------------------------------------

export const examCalendarApi = {
  getSchedule: (year?: number) =>
    unwrap<ExamYearSchedule[]>(apiClient.get('/exam-calendar/schedule', { params: year ? { year } : {} })),

  getUpcoming: () =>
    unwrap<UpcomingEvent[]>(apiClient.get('/exam-calendar/upcoming')),

  getStudyPlanSuggestion: (remaining: number, targetDate?: string | null) =>
    unwrap<StudyPlanSuggestion>(
      apiClient.get('/exam-calendar/study-plan-suggestion', {
        params: { remaining, ...(targetDate ? { target_date: targetDate } : {}) },
      }),
    ),
}
