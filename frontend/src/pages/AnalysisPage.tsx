import React, { useEffect, useState } from 'react'
import {
  analysisApi,
  ChapterHeatmap,
  HighFrequencyPoint,
  KnowledgeTree,
  PointTrend,
  QuestionTypeDistribution,
  WordCloudItem,
} from '../api/analysis'
import { subjectApi, Subject } from '../api/subject'

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
}

const AnalysisPage: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [knowledgeTree, setKnowledgeTree] = useState<KnowledgeTree | null>(null)
  const [highFrequencyPoints, setHighFrequencyPoints] = useState<HighFrequencyPoint[]>([])
  const [chapterHeatmap, setChapterHeatmap] = useState<ChapterHeatmap | null>(null)
  const [typeDistribution, setTypeDistribution] = useState<QuestionTypeDistribution | null>(null)
  const [wordCloud, setWordCloud] = useState<WordCloudItem[]>([])
  const [prediction, setPrediction] = useState<HighFrequencyPoint[]>([])
  const [selectedPoint, setSelectedPoint] = useState<HighFrequencyPoint | null>(null)
  const [pointTrend, setPointTrend] = useState<PointTrend | null>(null)
  const [loading, setLoading] = useState(false)
  const [trendLoading, setTrendLoading] = useState(false)
  const [error, setError] = useState('')

  const loadAnalysis = async (nextSubjectId: number) => {
    setLoading(true)
    setError('')
    try {
      const [treeData, highFrequencyData, heatmapData, typeData, wordCloudData, predictionData] =
        await Promise.all([
          analysisApi.getKnowledgeTree(nextSubjectId),
          analysisApi.getHighFrequencyPoints(nextSubjectId, 20),
          analysisApi.getChapterHeatmap(nextSubjectId),
          analysisApi.getQuestionTypeDistribution(nextSubjectId),
          analysisApi.getWordCloud(nextSubjectId),
          analysisApi.predictNextExam(nextSubjectId),
        ])
      setKnowledgeTree(treeData)
      setHighFrequencyPoints(highFrequencyData)
      setChapterHeatmap(heatmapData)
      setTypeDistribution(typeData)
      setWordCloud(wordCloudData)
      setPrediction(predictionData)
      setSelectedPoint(highFrequencyData[0] || null)
      if (highFrequencyData[0]) {
        const trendData = await analysisApi.getPointTrend(nextSubjectId, highFrequencyData[0].id, 5)
        setPointTrend(trendData)
      } else {
        setPointTrend(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '考点分析加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const initialize = async () => {
      try {
        const subjectData = await subjectApi.list()
        setSubjects(subjectData)
        if (subjectData[0]) {
          setSubjectId(String(subjectData[0].id))
          await loadAnalysis(subjectData[0].id)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '初始化考点分析失败')
      }
    }
    void initialize()
  }, [])

  const maxPointFrequency = Math.max(1, ...highFrequencyPoints.map((point) => point.frequency))
  const maxChapterFrequency = Math.max(1, ...(chapterHeatmap?.chapters || []).map((chapter) => chapter.frequency))
  const maxWordWeight = Math.max(1, ...wordCloud.map((item) => item.weight))
  const maxTrendCount = Math.max(1, ...(pointTrend?.values || []).map((item) => item.count))

  const selectPoint = async (point: HighFrequencyPoint) => {
    setSelectedPoint(point)
    setTrendLoading(true)
    setError('')
    try {
      const data = await analysisApi.getPointTrend(Number(subjectId), point.id, 5)
      setPointTrend(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '考点趋势加载失败')
    } finally {
      setTrendLoading(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
        <h1 className="text-3xl font-bold">考点分析</h1>
        <select
          value={subjectId}
          onChange={(event) => {
            setSubjectId(event.target.value)
            if (event.target.value) void loadAnalysis(Number(event.target.value))
          }}
          className="w-full md:w-80 px-4 py-2 border border-gray-300 rounded-lg bg-white"
        >
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}
      {loading && <div className="mb-4 rounded-lg bg-blue-50 px-4 py-3 text-blue-700">分析数据加载中...</div>}

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">高频考点 Top 20</h2>
        <div className="space-y-3">
          {highFrequencyPoints.map((point, index) => (
            <button
              key={point.id}
              type="button"
              onClick={() => void selectPoint(point)}
              className={`flex w-full flex-col gap-3 p-4 border rounded-lg text-left lg:flex-row lg:items-center ${
                selectedPoint?.id === point.id ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-4 flex-1">
                <div className="w-10 text-2xl font-bold text-gray-400">#{index + 1}</div>
                <div className="flex-1">
                  <div className="font-medium">{point.name}</div>
                  <div className="text-sm text-gray-500">
                    历史频次 {point.frequency}，重要度 {point.importance}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 lg:w-72">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${(point.frequency / maxPointFrequency) * 100}%` }}
                  />
                </div>
                <span className={point.trend === 'up' ? 'text-green-600' : 'text-gray-500'}>
                  {point.trend === 'up' ? '上升' : point.trend === 'down' ? '下降' : '稳定'}
                </span>
              </div>
            </button>
          ))}
          {highFrequencyPoints.length === 0 && !loading && <div className="text-gray-500">暂无高频考点数据</div>}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h2 className="text-xl font-semibold">考点年度趋势</h2>
          <div className="text-sm text-gray-500">{selectedPoint?.name || '未选择考点'}</div>
        </div>
        {trendLoading && <div className="text-sm text-blue-700">趋势加载中...</div>}
        {!trendLoading && selectedPoint && (
          <div className="space-y-3">
            {(pointTrend?.values || []).map((item) => (
              <div key={item.year} className="flex items-center gap-3">
                <div className="w-16 text-sm text-gray-600">{item.year}</div>
                <div className="flex-1 rounded-full bg-gray-200 h-6">
                  <div
                    className="flex h-6 items-center justify-end rounded-full bg-teal-500 pr-2 text-xs font-medium text-white"
                    style={{ width: `${Math.max(8, (item.count / maxTrendCount) * 100)}%` }}
                  >
                    {item.count}
                  </div>
                </div>
              </div>
            ))}
            {pointTrend?.values.length === 0 && <div className="text-gray-500">暂无年度趋势数据</div>}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">章节出题频次</h2>
          <div className="space-y-3">
            {(chapterHeatmap?.chapters || []).map((chapter) => (
              <div key={chapter.id} className="flex items-center gap-3">
                <div className="text-sm text-gray-600 w-48 truncate">{chapter.name}</div>
                <div className="flex-1 bg-gray-200 rounded-full h-6">
                  <div
                    className="h-6 rounded-full bg-orange-500 flex items-center justify-end pr-2 text-xs text-white font-medium"
                    style={{ width: `${Math.max(8, (chapter.frequency / maxChapterFrequency) * 100)}%` }}
                  >
                    {chapter.frequency}
                  </div>
                </div>
              </div>
            ))}
            {chapterHeatmap?.chapters.length === 0 && <div className="text-gray-500">暂无章节频次数据</div>}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">题型分布</h2>
          <div className="space-y-4">
            {(typeDistribution?.items || []).map((item) => (
              <div key={item.question_type}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">
                    {questionTypeLabels[item.question_type] || item.question_type}
                  </span>
                  <span className="text-sm text-gray-600">
                    {item.count}题 ({item.percentage}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${item.percentage}%` }} />
                </div>
              </div>
            ))}
            {typeDistribution?.items.length === 0 && <div className="text-gray-500">暂无题型数据</div>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">考试大纲树</h2>
          <div className="space-y-4">
            {(knowledgeTree?.chapters || []).map((chapter) => (
              <div key={chapter.id} className="border-l-4 border-blue-100 pl-4">
                <div className="font-medium">{chapter.name}</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {chapter.points.map((point) => (
                    <span key={point.id} className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-700">
                      {point.name} · {point.frequency}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {knowledgeTree?.chapters.length === 0 && <div className="text-gray-500">暂无大纲数据</div>}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">考点词云</h2>
          <div className="flex flex-wrap gap-3">
            {wordCloud.map((item) => (
              <span
                key={item.word}
                className="rounded-full bg-green-50 px-3 py-1 text-green-700"
                style={{ fontSize: `${12 + (item.weight / maxWordWeight) * 12}px` }}
              >
                {item.word}
              </span>
            ))}
            {wordCloud.length === 0 && <div className="text-gray-500">暂无词云数据</div>}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">下次考试预测</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {prediction.map((point) => (
            <div key={point.id} className="rounded-lg border border-gray-200 p-4">
              <div className="font-medium">{point.name}</div>
              <div className="mt-2 text-sm text-gray-600">
                置信度 {Math.round((point.confidence || 0) * 100)}%，历史频次 {point.frequency}
              </div>
              {point.reason && <div className="mt-2 text-sm text-gray-500">{point.reason}</div>}
            </div>
          ))}
          {prediction.length === 0 && !loading && <div className="text-gray-500">暂无预测数据</div>}
        </div>
      </div>
    </div>
  )
}

export default AnalysisPage
