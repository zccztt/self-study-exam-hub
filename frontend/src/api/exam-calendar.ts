import apiClient from './client'

// ------------------------------------------------------------------
// Types for widgets (internal, mapped from backend response)
// ------------------------------------------------------------------

export interface ExamEvent {
  id: string
  title: string
  date: string
  description?: string
  status: 'active' | 'upcoming' | 'ended'
  days_until: number | null
  urgency: 'critical' | 'warning' | 'attention' | 'normal'
  highlight: boolean
}

export interface TimelineItem {
  exam_date: string
  suggested_subjects: number
  registration_period: string
}

export interface StudyPlanSuggestion {
  remaining_subjects: number
  required_sessions: number
  can_finish_on_time?: boolean
  recommendation?: string
  timeline?: TimelineItem[]
}

// ------------------------------------------------------------------
// Raw backend types
// ------------------------------------------------------------------

interface RawCountdown {
  date: string
  days_remaining: number
  status: string
}

interface RawEvent {
  type: string
  name: string
  countdown: RawCountdown
  dates?: string[]
  note?: string
  register_start?: string
  register_end?: string
  status?: string
}

interface RawPlanSession {
  name: string
  exam_date: string
  register_start: string
  register_end: string
  suggested_count: number
}

interface RawSuggestion {
  remaining_subjects: number
  sessions_needed: number
  total_capacity: number
  feasible: boolean
  advice: string
  plan: RawPlanSession[]
}

// ------------------------------------------------------------------
// API with mapping
// ------------------------------------------------------------------

export const examCalendarApi = {
  async getUpcomingEvents(): Promise<ExamEvent[]> {
    const res = await apiClient.get<{ code: number; data: RawEvent[] }>('/exam-calendar/upcoming')
    return res.data.data.map((raw, idx) => {
      const dateStr = raw.dates ? raw.dates.join('、') : raw.countdown.date
      const days = raw.countdown.days_remaining
      let status: ExamEvent['status'] = 'upcoming'
      if (raw.status === 'open' || raw.status === 'active') status = 'active'
      else if (raw.countdown.status === 'passed') status = 'ended'

      // Compute urgency on client side from days_remaining
      let urgency: 'critical' | 'warning' | 'attention' | 'normal' = 'normal'
      if (days <= 0) urgency = 'critical'
      else if (days <= 7) urgency = 'critical'
      else if (days <= 30) urgency = 'warning'
      else if (days <= 60) urgency = 'attention'

      return {
        id: `${raw.type}-${idx}`,
        title: raw.name,
        date: dateStr,
        description: raw.note || (raw.register_start ? `报名: ${raw.register_start} ~ ${raw.register_end}` : undefined),
        status,
        days_until: days,
        urgency,
        highlight: days <= 30,
      }
    })
  },

  async getStudyPlanSuggestion(remaining: number, targetDate?: string): Promise<StudyPlanSuggestion> {
    const params: Record<string, any> = { remaining }
    if (targetDate) params.target_date = targetDate
    const res = await apiClient.get<{ code: number; data: RawSuggestion }>('/exam-calendar/study-plan-suggestion', { params })
    const raw = res.data.data
    return {
      remaining_subjects: raw.remaining_subjects,
      required_sessions: raw.sessions_needed,
      can_finish_on_time: raw.feasible,
      recommendation: raw.advice,
      timeline: raw.plan.map((s) => ({
        exam_date: s.exam_date,
        suggested_subjects: s.suggested_count,
        registration_period: `${s.register_start} ~ ${s.register_end}`,
      })),
    }
  },
}
