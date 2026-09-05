import apiClient, { unwrap } from './client'

export interface FlashcardItem {
  id: number
  front: string
  back: string
  card_type: 'auto' | 'custom'
  tags: string | null
  ease_factor: number
  interval_days: number
  repetitions: number
  subject_id: number
  knowledge_point_id: number | null
  question_id: number | null
}

export interface DueCardsResult {
  total_due: number
  items: FlashcardItem[]
}

export interface FlashcardStats {
  total: number
  due_today: number
  mastered: number
  learning: number
}

export interface GenerateResult {
  created_count: number
  skipped_count: number
  message: string
}

export interface ReviewResult {
  card_id: number
  next_review: string
  interval_days: number
  ease_factor: number
  repetitions: number
}

export const flashcardApi = {
  generate: (subjectId: number) =>
    unwrap<GenerateResult>(apiClient.post('/flashcards/generate', { subject_id: subjectId })),

  getDueCards: (subjectId?: number, limit = 20) =>
    unwrap<DueCardsResult>(
      apiClient.get('/flashcards/due', {
        params: { subject_id: subjectId, limit },
      }),
    ),

  reviewCard: (cardId: number, quality: number) =>
    unwrap<ReviewResult>(apiClient.post(`/flashcards/${cardId}/review`, { quality })),

  getStats: (subjectId?: number) =>
    unwrap<FlashcardStats>(
      apiClient.get('/flashcards/stats', {
        params: subjectId ? { subject_id: subjectId } : {},
      }),
    ),

  createCustom: (subjectId: number, front: string, back: string, tags?: string) =>
    unwrap<{ id: number; front: string; back: string; card_type: string; tags: string | null }>(
      apiClient.post('/flashcards/custom', { subject_id: subjectId, front, back, tags }),
    ),

  suspendCard: (cardId: number, suspend = true) =>
    unwrap<{ success: boolean }>(apiClient.patch(`/flashcards/${cardId}/suspend`, { suspend })),

  deleteCard: (cardId: number) =>
    unwrap<{ success: boolean }>(apiClient.delete(`/flashcards/${cardId}`)),
}
