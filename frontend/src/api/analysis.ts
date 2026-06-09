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

export interface KnowledgeNetworkNode {
  id: number
  name: string
  chapter_name?: string
  frequency: number
  trend?: string
  importance?: string
  question_count?: number
}

export interface KnowledgeNetworkEdge {
  source: number
  target: number
  weight: number
  source_name?: string
  target_name?: string
}

export interface KnowledgeNetwork {
  subject_id: number
  nodes: KnowledgeNetworkNode[]
  edges: KnowledgeNetworkEdge[]
}

export interface HotspotAlert {
  point_id: number
  name: string
  chapter_name?: string
  severity: 'high' | 'medium' | string
  trend: string
  trend_slope: number
  confidence: number
  priority_score: number
  message: string
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

export interface ScoreTrendValue {
  session_id: string
  exam_id: number
  exam_name: string
  date?: string
  subject_id: number
  subject_name: string
  score: number
  total_score: number
  score_rate: number
  mode: string
}

export interface SubjectScoreTrend {
  subject_id: number
  subject_name: string
  sessions: number
  average_score_rate: number
  best_score_rate: number
  latest_score_rate: number
  trend_slope: number
  trend: string
  values: Array<{ date?: string; score_rate: number }>
}

export interface ChapterScoreTrend {
  chapter_id: number
  chapter_name: string
  total_count: number
  wrong_count: number
  correct_count: number
  score_rate: number
}

export interface ScoreTrendSummary {
  sessions: number
  average_score_rate: number
  latest_score_rate: number
  best_score_rate: number
  trend_slope: number
  trend: string
}

export interface ScoreTrend {
  user_id: number
  subject_id?: number
  summary: ScoreTrendSummary
  values: ScoreTrendValue[]
  subjects: SubjectScoreTrend[]
  chapters: ChapterScoreTrend[]
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
  getKnowledgeNetwork: (subjectId: number, limit = 30) =>
    unwrap<KnowledgeNetwork>(
      apiClient.get(`/analysis/knowledge-network/${subjectId}`, { params: { limit } }),
    ),
  getChapterHeatmap: (subjectId: number) =>
    unwrap<ChapterHeatmap>(apiClient.get(`/analysis/chapter-heatmap/${subjectId}`)),
  getQuestionTypeDistribution: (subjectId: number) =>
    unwrap<QuestionTypeDistribution>(apiClient.get(`/analysis/question-types/${subjectId}`)),
  predictNextExam: (subjectId: number) =>
    unwrap<HighFrequencyPoint[]>(apiClient.get(`/analysis/prediction/${subjectId}`)),
  getHotspots: (subjectId: number) =>
    unwrap<HotspotAlert[]>(apiClient.get(`/analysis/hotspots/${subjectId}`)),
  getScoreTrends: (userId: number, subjectId?: number, limit = 20) =>
    unwrap<ScoreTrend>(
      apiClient.get(`/analysis/score-trends/${userId}`, {
        params: { subject_id: subjectId, limit },
      }),
    ),
}
