import apiClient, { unwrap } from './client'
import { sessionStore } from './session'

export interface StudyPlan {
  id: number
  user_id: number
  exam_date: string
  daily_hours: number
  subjects: number[]
  preferences: Record<string, unknown>
  plan_data: {
    days?: number
    allocation?: TimeAllocation
    tasks?: PlanTask[]
    phases?: PlanPhase[]
    weekly_goals?: WeeklyGoal[]
    daily_template?: FocusBlock[]
    milestones?: Milestone[]
    mock_exams?: MockExamNode[]
    sprint_plan?: SprintPlanItem[]
    review_schedule?: ReviewScheduleItem[]
    resource_strategy?: Array<{ type: string; action: string }>
    risk_alerts?: string[]
    ai_advice?: AIAdvice
  }
  status: string
  completion_rate: number
  expected_pass_rate?: number
  created_at?: string
}

export type StudyPlanSummary = Omit<StudyPlan, 'preferences' | 'plan_data'>

export interface StudyPlanHistoryResult {
  total: number
  page: number
  page_size: number
  items: StudyPlanSummary[]
}

export interface FocusBlock {
  name: string
  minutes: number
  content: string
}

export interface PlanTask {
  date: string
  subject_id: number
  chapter_ids: number[]
  task_type?: string
  estimated_hours?: number
  question_count: number
  video_ids: number[]
  review_points: Array<{ id: number; name: string }>
  focus_blocks?: FocusBlock[]
}

export interface PlanPhase {
  name: string
  start_date: string
  end_date: string
  goal: string
}

export interface WeeklyGoal {
  week: number
  start_date: string
  subject_id?: number
  focus_points: Array<{ id?: number; name: string }>
  target: string
}

export interface Milestone {
  date: string
  title: string
  check: string
}

export interface MockExamNode {
  date: string
  subject_id: number
  title: string
  duration_minutes: number
  review_focus: string[]
}

export interface SprintPlanItem {
  date: string
  day: number
  action: string
  focus_points: Array<{ id?: number; name?: string }>
}

export interface ReviewScheduleItem {
  date: string
  review_type?: string
  review_points: Array<Record<string, unknown>>
}

export interface DailyTask {
  id: number
  plan_id: number
  user_id: number
  task_date: string
  subject_id: number
  chapter_ids: number[]
  question_count: number
  video_ids: number[]
  review_points: Array<{ id: number; name: string }>
  focus_blocks?: FocusBlock[]
  is_completed: boolean
  actual_hours?: number
}

export interface WeakPoint {
  point_id: number
  name: string
  chapter_id?: number
  mastery_level: number
  description?: string
  allocated_hours?: number
  wrong_count?: number
  priority: 'high' | 'medium' | string
  reason?: string
}

export interface ProgressResult {
  completion_rate: number
  completed: number
  total: number
}

export interface TimeAllocation {
  total_hours: number
  weak_points_hours: number
  high_frequency_hours: number
  review_hours: number
  weak_points: WeakPoint[]
  high_frequency_points: Array<Record<string, unknown>>
}

export interface AIAdvice {
  overall_assessment: string
  study_strategy: string
  subject_advice: Array<{ subject: string; advice: string; priority: string }>
  daily_plan_suggestion: string
  risk_warnings: string[]
  motivation: string
  error?: string
}

export const plannerApi = {
  generatePlan: (params: {
    user_id?: number
    exam_date: string
    subjects?: number[]
    daily_hours: number
    preferences?: Record<string, unknown>
    enrollment_id?: number
    user_context?: string
  }) => unwrap<StudyPlan>(apiClient.post('/planner/generate', { user_id: sessionStore.getUserId(), ...params })),
  getAIAdvice: (params: {
    user_context: string
    exam_date?: string
    subjects?: number[]
    daily_hours?: number
  }) => unwrap<AIAdvice>(apiClient.post('/planner/ai-advice', { user_id: sessionStore.getUserId(), ...params })),
  getLatestPlan: (userId = sessionStore.getUserId()) => unwrap<StudyPlan | null>(apiClient.get(`/planner/latest/${userId}`)),
  getPlanHistory: (userId = sessionStore.getUserId(), page = 1, pageSize = 10) =>
    unwrap<StudyPlanHistoryResult>(
      apiClient.get(`/planner/plans/${userId}`, { params: { page, page_size: pageSize } }),
    ),
  activatePlan: (planId: number, userId = sessionStore.getUserId()) =>
    unwrap<StudyPlan>(apiClient.post(`/planner/plans/${userId}/${planId}/activate`)),
  deletePlan: (planId: number, userId = sessionStore.getUserId()) =>
    unwrap<{ success: boolean }>(apiClient.delete(`/planner/plans/${userId}/${planId}`)),
  getDailyTasks: (userId = sessionStore.getUserId(), date?: string) =>
    unwrap<DailyTask[]>(
      apiClient.get(`/planner/daily-tasks/${userId}`, {
        params: date ? { date } : undefined,
      }),
    ),
  getWeakPoints: (subjectId: number, userId = sessionStore.getUserId()) =>
    unwrap<WeakPoint[]>(apiClient.get(`/planner/weak-points/${userId}/${subjectId}`)),
  updateProgress: (completedTasks: Array<{ id: number; is_completed?: boolean; actual_hours?: number }>, userId = sessionStore.getUserId()) =>
    unwrap<ProgressResult>(
      apiClient.post('/planner/progress', {
        user_id: userId,
        completed_tasks: completedTasks,
      }),
    ),
  allocateTime: (totalDays: number, dailyHours: number, subjectId?: number, userId = sessionStore.getUserId()) =>
    unwrap<TimeAllocation>(
      apiClient.get('/planner/allocation', {
        params: {
          total_days: totalDays,
          daily_hours: dailyHours,
          subject_id: subjectId,
          user_id: userId,
        },
      }),
    ),
}
