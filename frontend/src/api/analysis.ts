import apiClient, { unwrap } from './client'

export interface KnowledgePoint {
  id: number
  name: string
  importance: string
  frequency: number
}

export interface KnowledgeTreeChapter {
  id: number
  name: string
  order: number
  points: KnowledgePoint[]
}

export interface KnowledgeTree {
  subject_id: number
  chapters: KnowledgeTreeChapter[]
}

export interface HighFrequencyPoint extends KnowledgePoint {
  trend: 'up' | 'stable' | string
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
