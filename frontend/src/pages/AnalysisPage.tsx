import React, { useEffect, useMemo, useState } from 'react'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import {
  analysisApi,
  ChapterHeatmap,
  HotspotAlert,
  HighFrequencyPoint,
  KnowledgeNetwork,
  KnowledgeTree,
  PointTrend,
  QuestionTypeDistribution,
  ScoreTrend,
  WordCloudItem,
} from '../api/analysis'
import { sessionStore } from '../api/session'
import { subjectApi, Subject } from '../api/subject'

echarts.use([GraphChart, TooltipComponent, CanvasRenderer])

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
}
const CURRENT_EXAM_YEAR = new Date().getFullYear()

const AnalysisPage: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [knowledgeTree, setKnowledgeTree] = useState<KnowledgeTree | null>(null)
  const [highFrequencyPoints, setHighFrequencyPoints] = useState<HighFrequencyPoint[]>([])
  const [chapterHeatmap, setChapterHeatmap] = useState<ChapterHeatmap | null>(null)
  const [typeDistribution, setTypeDistribution] = useState<QuestionTypeDistribution | null>(null)
  const [wordCloud, setWordCloud] = useState<WordCloudItem[]>([])
  const [knowledgeNetwork, setKnowledgeNetwork] = useState<KnowledgeNetwork | null>(null)
  const [hotspots, setHotspots] = useState<HotspotAlert[]>([])
  const [prediction, setPrediction] = useState<HighFrequencyPoint[]>([])
  const [scoreTrend, setScoreTrend] = useState<ScoreTrend | null>(null)
  const [selectedPoint, setSelectedPoint] = useState<HighFrequencyPoint | null>(null)
  const [pointTrend, setPointTrend] = useState<PointTrend | null>(null)
  const [loading, setLoading] = useState(false)
  const [trendLoading, setTrendLoading] = useState(false)
  const [error, setError] = useState('')

  const loadAnalysis = async (nextSubjectId: number) => {
    setLoading(true)
    setError('')
    try {
      const [
        treeData,
        highFrequencyData,
        heatmapData,
        typeData,
        wordCloudData,
        networkData,
        predictionData,
        hotspotData,
        scoreTrendData,
      ] =
        await Promise.all([
          analysisApi.getKnowledgeTree(nextSubjectId),
          analysisApi.getHighFrequencyPoints(nextSubjectId, 20),
          analysisApi.getChapterHeatmap(nextSubjectId),
          analysisApi.getQuestionTypeDistribution(nextSubjectId),
          analysisApi.getWordCloud(nextSubjectId),
          analysisApi.getKnowledgeNetwork(nextSubjectId, 30),
          analysisApi.predictNextExam(nextSubjectId),
          analysisApi.getHotspots(nextSubjectId),
          analysisApi.getScoreTrends(sessionStore.getUserId(), nextSubjectId, 20),
        ])
      setKnowledgeTree(treeData)
      setHighFrequencyPoints(highFrequencyData)
      setChapterHeatmap(heatmapData)
      setTypeDistribution(typeData)
      setWordCloud(wordCloudData)
      setKnowledgeNetwork(networkData)
      setHotspots(hotspotData)
      setPrediction(predictionData)
      setScoreTrend(scoreTrendData)
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
  const maxEdgeWeight = Math.max(1, ...(knowledgeNetwork?.edges || []).map((item) => item.weight))
  const maxScoreRate = Math.max(1, ...(scoreTrend?.values || []).map((item) => item.score_rate))
  const maxChapterScoreRate = Math.max(1, ...(scoreTrend?.chapters || []).map((item) => item.score_rate))
  const selectedDetail = selectedPoint?.detail
  const networkChartOption = useMemo(
    () => ({
      tooltip: {
        trigger: 'item',
        formatter: (params: { dataType?: string; data?: { name?: string; value?: number } }) => {
          if (params.dataType === 'edge') return '共现关系'
          return `${params.data?.name || ''}<br/>频次：${params.data?.value || 0}`
        },
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          label: { show: true, position: 'right', formatter: '{b}' },
          force: { repulsion: 180, edgeLength: [70, 150], friction: 0.25 },
          data: (knowledgeNetwork?.nodes || []).map((node) => ({
            id: String(node.id),
            name: node.name,
            value: node.frequency,
            symbolSize: Math.max(24, Math.min(64, 20 + node.frequency * 2)),
            itemStyle: {
              color: node.trend === 'up' ? '#16a34a' : node.importance === 'high' ? '#dc2626' : '#2563eb',
            },
          })),
          links: (knowledgeNetwork?.edges || []).map((edge) => ({
            source: String(edge.source),
            target: String(edge.target),
            value: edge.weight,
            lineStyle: {
              width: Math.max(1, (edge.weight / maxEdgeWeight) * 5),
              opacity: 0.55,
            },
          })),
          lineStyle: { color: '#94a3b8', curveness: 0.18 },
          emphasis: { focus: 'adjacency', lineStyle: { width: 4 } },
        },
      ],
    }),
    [knowledgeNetwork, maxEdgeWeight],
  )

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
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-medium text-blue-600">{CURRENT_EXAM_YEAR} 高频考点库</div>
            <h1 className="mt-1 text-3xl font-bold text-slate-950">考点分析</h1>
            <p className="mt-2 text-sm text-slate-500">按章节、频次、题型和趋势拆解重点，选中考点可查看详细作答说明。</p>
          </div>
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
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}
      {loading && <div className="mb-4 rounded-lg bg-blue-50 px-4 py-3 text-blue-700">分析数据加载中...</div>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {[
          ['高频考点', highFrequencyPoints.length, '已建立详细说明'],
          ['章节数', knowledgeTree?.chapters.length || 0, '知识树覆盖'],
          ['题型数', typeDistribution?.items.length || 0, '客观题与主观题'],
          ['预测点', prediction.length, '下次考试关注'],
        ].map(([label, value, desc]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-sm text-slate-500">{label}</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">{value}</div>
            <div className="mt-1 text-sm text-slate-500">{desc}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">成绩趋势</h2>
              <p className="mt-1 text-sm text-slate-500">按当前科目统计最近考试得分率。</p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs ${
                scoreTrend?.summary.trend === 'up'
                  ? 'bg-green-50 text-green-700'
                  : scoreTrend?.summary.trend === 'down'
                    ? 'bg-red-50 text-red-700'
                    : 'bg-slate-100 text-slate-600'
              }`}
            >
              {scoreTrend?.summary.trend === 'up' ? '上升' : scoreTrend?.summary.trend === 'down' ? '下降' : '稳定'}
            </span>
          </div>
          <div className="mt-5 grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="text-sm text-slate-500">考试场次</div>
              <div className="mt-1 text-2xl font-bold">{scoreTrend?.summary.sessions || 0}</div>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="text-sm text-slate-500">平均得分率</div>
              <div className="mt-1 text-2xl font-bold">{scoreTrend?.summary.average_score_rate || 0}%</div>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="text-sm text-slate-500">最近得分率</div>
              <div className="mt-1 text-2xl font-bold">{scoreTrend?.summary.latest_score_rate || 0}%</div>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {(scoreTrend?.values || []).slice(-6).map((item) => (
              <div key={item.session_id} className="flex items-center gap-3">
                <div className="w-24 text-xs text-slate-500">{item.date || '未提交'}</div>
                <div className="flex-1 rounded-full bg-slate-100 h-6">
                  <div
                    className="flex h-6 items-center justify-end rounded-full bg-blue-500 pr-2 text-xs font-medium text-white"
                    style={{ width: `${Math.max(8, (item.score_rate / maxScoreRate) * 100)}%` }}
                  >
                    {item.score_rate}%
                  </div>
                </div>
              </div>
            ))}
            {scoreTrend?.values.length === 0 && <div className="text-sm text-slate-500">暂无考试成绩记录</div>}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">章节得分表现</h2>
          <p className="mt-1 text-sm text-slate-500">根据考试错题反推章节正确率，优先关注低分章节。</p>
          <div className="mt-5 space-y-3">
            {(scoreTrend?.chapters || []).slice(0, 8).map((item) => (
              <div key={item.chapter_id} className="rounded-lg border border-slate-200 px-4 py-3">
                <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium text-slate-800">{item.chapter_name}</span>
                  <span className="text-slate-500">
                    {item.correct_count}/{item.total_count} · 错 {item.wrong_count}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className={`h-2 rounded-full ${item.score_rate < 60 ? 'bg-red-500' : item.score_rate < 80 ? 'bg-amber-500' : 'bg-green-500'}`}
                    style={{ width: `${Math.max(8, (item.score_rate / maxChapterScoreRate) * 100)}%` }}
                  />
                </div>
                <div className="mt-1 text-xs text-slate-500">正确率 {item.score_rate}%</div>
              </div>
            ))}
            {scoreTrend?.chapters.length === 0 && <div className="text-sm text-slate-500">暂无章节成绩数据</div>}
          </div>
        </section>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">高频考点 Top 20</h2>
        <div className="space-y-3">
          {highFrequencyPoints.map((point, index) => (
            <button
              key={point.id}
              type="button"
              onClick={() => void selectPoint(point)}
              className={`flex w-full flex-col gap-3 rounded-lg border p-4 text-left transition lg:flex-row lg:items-center ${
                selectedPoint?.id === point.id ? 'border-blue-400 bg-blue-50 shadow-sm' : 'border-slate-200 bg-white hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-4 flex-1">
                <div className="w-10 text-2xl font-bold text-gray-400">#{index + 1}</div>
                <div className="flex-1">
                  <div className="font-medium">{point.name}</div>
                  <div className="text-sm text-gray-500">
                    频次 {point.frequency}，重要度 {point.importance}
                    {point.chapter_name ? `，章节：${point.chapter_name}` : ''}
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

      {selectedPoint && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="text-sm font-medium text-blue-600">当前考点</div>
              <h2 className="mt-1 text-2xl font-bold text-slate-950">{selectedPoint.name}</h2>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
                {selectedDetail?.overview || selectedPoint.description || '暂无详细说明'}
              </p>
            </div>
            <div className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">
              {selectedDetail?.importance_label || selectedPoint.importance} · 关联题 {selectedPoint.question_count || 0} 道
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
            {[
              ['命题重点', selectedDetail?.exam_focus || []],
              ['答题模板', selectedDetail?.answer_template || []],
              ['常见易错', selectedDetail?.common_mistakes || []],
              ['学习建议', selectedDetail?.study_advice || []],
            ].map(([title, items]) => (
              <div key={title as string} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <h3 className="font-semibold text-slate-950">{title as string}</h3>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                  {(items as string[]).map((item) => (
                    <li key={item}>• {item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
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

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">考试大纲树</h2>
          <div className="space-y-4">
            {(knowledgeTree?.chapters || []).map((chapter) => (
              <div key={chapter.id} className="border-l-4 border-blue-100 pl-4">
                <div className="font-medium">{chapter.name}</div>
                {chapter.description && (
                  <div className="mt-1 text-sm leading-6 text-gray-500">{chapter.description}</div>
                )}
                <div className="mt-2 flex flex-wrap gap-2">
                  {chapter.points.map((point) => (
                    <span key={point.id} className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-700">
                      {point.name} · {point.frequency}
                    </span>
                  ))}
                  {chapter.points.length === 0 && (
                    <span className="text-sm text-gray-500">该章节暂无考点</span>
                  )}
                </div>
              </div>
            ))}
            {knowledgeTree?.chapters.length === 0 && <div className="text-gray-500">暂无大纲数据</div>}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">知识点关联网络</h2>
          {(knowledgeNetwork?.nodes.length || 0) > 0 ? (
            <ReactEChartsCore echarts={echarts} option={networkChartOption} style={{ height: 360, width: '100%' }} />
          ) : (
            <div className="text-gray-500">暂无知识点共现关系</div>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">新增热点预警</h2>
          <div className="space-y-3">
            {hotspots.map((alert) => (
              <div
                key={alert.point_id}
                className={`rounded-lg border px-4 py-3 ${
                  alert.severity === 'high'
                    ? 'border-red-200 bg-red-50'
                    : 'border-amber-200 bg-amber-50'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium text-slate-950">{alert.name}</div>
                  <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-600">
                    {Math.round(alert.confidence * 100)}%
                  </span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {alert.chapter_name || '综合考点'} · 趋势斜率 {alert.trend_slope}
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{alert.message}</p>
              </div>
            ))}
            {hotspots.length === 0 && <div className="text-gray-500">暂无热点预警</div>}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
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
