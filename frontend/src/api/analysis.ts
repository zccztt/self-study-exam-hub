import apiClient, { unwrap } from './client'

export interface KnowledgePoint {
  id: number
  name: string
  description?: string
  importance: string
  frequency: number
  detail?: KnowledgePointDetail
}

export interface KnowledgePointDetail {
  overview: string
  chapter_name?: string
  importance_label?: string
  linked_question_count?: number
  exam_focus: string[]
  answer_template: string[]
  common_mistakes: string[]
  study_advice: string[]
}

export interface KnowledgeTreeChapter {
  id: number
  name: string
  order: number
  description?: string
  points: KnowledgePoint[]
}

export interface KnowledgeTree {
  subject_id: number
  chapters: KnowledgeTreeChapter[]
}

export interface HighFrequencyPoint extends KnowledgePoint {
  trend: 'up' | 'stable' | string
  trend_slope?: number
  next_year_prediction?: number
  chapter_name?: string
  question_count?: number
  confidence?: number
  reason?: string
}

export interface TrendPoint {
  year: number
  count: number
}

export interface PointTrend {
  subject_id: number
  point_id: number
  values: TrendPoint[]
  trend?: 'up' | 'down' | 'stable' | string
  trend_slope?: number
  next_year_prediction?: number
}

export interface WordCloudItem {
  word: string
  weight: number
}

export interface ChapterHeatmapItem {
  id: number
  name: string
  frequency: number
}

export interface ChapterHeatmap {
  subject_id: number
  chapters: ChapterHeatmapItem[]
}

export interface QuestionTypeItem {
  question_type: string
  count: number
  percentage: number
}

export interface QuestionTypeDistribution {
  subject_id: number
  total: number
  items: QuestionTypeItem[]
}

export const analysisApi = {
  getKnowledgeTree: (subjectId: number) =>
    unwrap<KnowledgeTree>(apiClient.get(`/analysis/knowledge-tree/${subjectId}`)),
  getHighFrequencyPoints: (subjectId: number, limit = 20) =>
    unwrap<HighFrequencyPoint[]>(
      apiClient.get(`/analysis/high-frequency/${subjectId}`, { params: { limit } }),
    ),
  getPointTrend: (subjectId: number, pointId: number, years = 5) =>
    unwrap<PointTrend>(
      apiClient.get(`/analysis/trend/${subjectId}/${pointId}`, { params: { years } }),
    ),
  getWordCloud: (subjectId: number) =>
    unwrap<WordCloudItem[]>(apiClient.get(`/analysis/word-cloud/${subjectId}`)),
  getChapterHeatmap: (subjectId: number) =>
    unwrap<ChapterHeatmap>(apiClient.get(`/analysis/chapter-heatmap/${subjectId}`)),
  getQuestionTypeDistribution: (subjectId: number) =>
    unwrap<QuestionTypeDistribution>(apiClient.get(`/analysis/question-types/${subjectId}`)),
  predictNextExam: (subjectId: number) =>
    unwrap<HighFrequencyPoint[]>(apiClient.get(`/analysis/prediction/${subjectId}`)),
}
