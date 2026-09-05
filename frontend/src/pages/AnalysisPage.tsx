import React, { useEffect, useMemo, useState } from 'react'
import echarts from '@/lib/echarts'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import {
  analysisApi,
  AIHotspotAnalysis,
  AnswerTemplatesResult,
  ChapterHeatmap,
  HotspotAlert,
  HighFrequencyPoint,
  KnowledgeNetwork,
  KnowledgeTree,
  PointTrend,
  QuestionTypeDistribution,
  ScoreTrend,
  SprintReport,
  WordCloudItem,
} from '../api/analysis'
import { enrollmentApi } from '../api/enrollment'
import { sessionStore } from '../api/session'
import { useEnrolledSubjectFilter } from '../hooks/useEnrolledSubjectFilter'
import EnrolledSubjectToggle from '../components/EnrolledSubjectToggle'

// echarts modules are registered in @/lib/echarts

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
  const { subjects, onlyEnrolled, setOnlyEnrolled, hasEnrollments, isLoggedIn } = useEnrolledSubjectFilter()
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
  // New: sprint report, AI analysis, answer templates
  const [sprintReport, setSprintReport] = useState<SprintReport | null>(null)
  const [sprintLoading, setSprintLoading] = useState(false)
  const [aiAnalysis, setAiAnalysis] = useState<AIHotspotAnalysis | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [answerTemplates, setAnswerTemplates] = useState<AnswerTemplatesResult | null>(null)
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'analysis' | 'sprint' | 'templates'>('analysis')

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
    if (subjects.length === 0 || subjectId) return
    const initialize = async () => {
      try {
        const enrollmentData = await enrollmentApi.listEnrollments().catch(() => [])

        // Default to first enrolled remaining subject, or first subject
        let defaultSubjectId = subjects[0]?.id
        if (enrollmentData.length > 0) {
          try {
            const remaining = await enrollmentApi.getRemainingSubjects(enrollmentData[0].id)
            if (remaining.length > 0) defaultSubjectId = remaining[0]
          } catch { /* ignore */ }
        }

        if (defaultSubjectId) {
          setSubjectId(String(defaultSubjectId))
          await loadAnalysis(defaultSubjectId)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '初始化考点分析失败')
      }
    }
    void initialize()
  }, [subjects])

  const loadSprintReport = async () => {
    if (!subjectId) return
    setSprintLoading(true)
    try {
      const data = await analysisApi.getSprintReport(sessionStore.getUserId(), Number(subjectId))
      setSprintReport(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '冲刺报告加载失败')
    } finally {
      setSprintLoading(false)
    }
  }

  const loadAiAnalysis = async () => {
    if (!subjectId) return
    setAiLoading(true)
    try {
      const data = await analysisApi.aiAnalyzeHotspots(Number(subjectId))
      setAiAnalysis(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI 分析加载失败（可能受速率限制）')
    } finally {
      setAiLoading(false)
    }
  }

  const loadAnswerTemplates = async () => {
    if (answerTemplates) return // already loaded
    setTemplatesLoading(true)
    try {
      const data = await analysisApi.getAnswerTemplates()
      setAnswerTemplates(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '答题模板加载失败')
    } finally {
      setTemplatesLoading(false)
    }
  }

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
        <div className="flex flex-col gap-2 md:flex-row md:items-center">
          <EnrolledSubjectToggle
            onlyEnrolled={onlyEnrolled}
            setOnlyEnrolled={setOnlyEnrolled}
            hasEnrollments={hasEnrollments}
            isLoggedIn={isLoggedIn}
          />
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
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}
      {loading && <div className="mb-4 rounded-lg bg-blue-50 px-4 py-3 text-blue-700">分析数据加载中...</div>}

      {/* Tab navigation */}
      <div className="flex gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
        {[
          { key: 'analysis' as const, label: '考点分析' },
          { key: 'sprint' as const, label: '冲刺报告' },
          { key: 'templates' as const, label: '答题模板' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              setActiveTab(tab.key)
              if (tab.key === 'sprint' && !sprintReport) loadSprintReport()
              if (tab.key === 'templates' && !answerTemplates) loadAnswerTemplates()
            }}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.key ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sprint Report Tab */}
      {activeTab === 'sprint' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-slate-900">考前冲刺报告</h2>
            <div className="flex gap-2">
              <button
                onClick={loadSprintReport}
                disabled={sprintLoading}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
              >
                {sprintLoading ? '加载中...' : '刷新'}
              </button>
              <button
                onClick={loadAiAnalysis}
                disabled={aiLoading}
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {aiLoading ? 'AI 分析中...' : '🤖 AI 深度分析'}
              </button>
            </div>
          </div>

          {sprintReport && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <h3 className="font-semibold text-slate-900">当前评估</h3>
                <div className="mt-3 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-500">预估得分</span>
                    <span className="text-lg font-bold text-blue-600">{sprintReport.current_assessment.estimated_score}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-500">通过概率</span>
                    <span className="font-medium">{sprintReport.current_assessment.pass_probability.label} ({sprintReport.current_assessment.pass_probability.percent}%)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-500">近期趋势</span>
                    <span className="text-sm">{sprintReport.current_assessment.recent_trend}</span>
                  </div>
                  {sprintReport.days_remaining != null && (
                    <div className="flex justify-between">
                      <span className="text-sm text-slate-500">距考试</span>
                      <span className="font-bold text-amber-600">{sprintReport.days_remaining} 天</span>
                    </div>
                  )}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <h3 className="font-semibold text-slate-900">通过策略</h3>
                <div className="mt-3 space-y-2">
                  <div className="text-sm text-slate-500">目标分数：<span className="font-bold text-slate-900">{sprintReport.pass_strategy.target_score}</span></div>
                  <div className="mt-2">
                    {sprintReport.pass_strategy.focus_advice.map((advice, i) => (
                      <div key={i} className="mt-1 flex items-start gap-2 text-sm text-slate-700">
                        <span className="text-blue-500">•</span> {advice}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              {sprintReport.review_checklist.must_review_points.length > 0 && (
                <div className="md:col-span-2 rounded-xl border border-slate-200 bg-white p-5">
                  <h3 className="font-semibold text-slate-900 mb-3">必复习考点</h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {sprintReport.review_checklist.must_review_points.map((point) => (
                      <div key={point.point_id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                        <span className="text-sm font-medium text-slate-800">{point.name}</span>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-slate-400">频次{point.frequency}</span>
                          <span className={point.priority === 'high' ? 'text-red-500 font-bold' : 'text-amber-500'}>
                            {point.priority === 'high' ? '必考' : '重点'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {aiAnalysis && (
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
              <h3 className="flex items-center gap-2 font-semibold text-blue-900">
                🤖 AI 深度分析
              </h3>
              <p className="mt-2 text-sm text-blue-800">{aiAnalysis.summary}</p>
              {aiAnalysis.top_predictions.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-blue-900 mb-2">重点预测</h4>
                  <div className="space-y-2">
                    {aiAnalysis.top_predictions.map((pred, i) => (
                      <div key={i} className="rounded-lg bg-white/70 p-3">
                        <div className="flex justify-between">
                          <span className="font-medium text-slate-900">{pred.name}</span>
                          <span className="text-xs text-blue-600">置信度 {Math.round(pred.confidence * 100)}%</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-600">{pred.reason}</p>
                        <p className="mt-1 text-xs text-blue-700">💡 {pred.study_tip}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {aiAnalysis.exam_tips.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-blue-900 mb-1">应试技巧</h4>
                  {aiAnalysis.exam_tips.map((tip, i) => (
                    <div key={i} className="text-sm text-blue-800">• {tip}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {!sprintReport && !sprintLoading && (
            <div className="rounded-xl border border-dashed border-slate-300 py-12 text-center text-slate-500">
              选择科目后点击「刷新」生成冲刺报告
            </div>
          )}
        </div>
      )}

      {/* Answer Templates Tab */}
      {activeTab === 'templates' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900">答题模板与技巧</h2>
          {templatesLoading && <div className="text-slate-400">加载中...</div>}
          {answerTemplates && (
            <>
              {answerTemplates.exam_tips && (
                <div className="rounded-xl border border-amber-100 bg-amber-50 p-5">
                  <h3 className="font-semibold text-amber-900">📝 考试提醒</h3>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2 text-sm text-amber-800">
                    <div>⏱ 时间管理：{answerTemplates.exam_tips.time_management}</div>
                    <div>📋 答题顺序：{answerTemplates.exam_tips.answer_order}</div>
                  </div>
                  {answerTemplates.exam_tips.key_reminders.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {answerTemplates.exam_tips.key_reminders.map((r, i) => (
                        <div key={i} className="text-sm text-amber-700">• {r}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div className="grid gap-4 md:grid-cols-2">
                {Object.values(answerTemplates).filter((v): v is NonNullable<typeof v> => v != null && typeof v === 'object' && 'templates' in v).map((group: any) => (
                  <div key={group.question_type} className="rounded-xl border border-slate-200 bg-white p-5">
                    <h3 className="font-semibold text-slate-900">{group.label}</h3>
                    {group.templates.map((tpl: any, i: number) => (
                      <div key={i} className="mt-3 rounded-lg border border-slate-100 p-3">
                        <div className="text-sm font-medium text-slate-800">{tpl.name}</div>
                        <div className="mt-1 text-xs text-slate-500">结构：{tpl.structure}</div>
                        {tpl.score_range && <div className="mt-1 text-xs text-blue-600">分值：{tpl.score_range}</div>}
                        <div className="mt-2 rounded bg-slate-50 p-2 text-xs text-slate-700 whitespace-pre-line">{tpl.example_frame}</div>
                        {tpl.scoring_tips.length > 0 && (
                          <div className="mt-2">
                            <div className="text-xs font-medium text-green-700">得分技巧：</div>
                            {tpl.scoring_tips.map((tip: string, j: number) => (
                              <div key={j} className="text-xs text-green-600">• {tip}</div>
                            ))}
                          </div>
                        )}
                        {tpl.common_mistakes.length > 0 && (
                          <div className="mt-2">
                            <div className="text-xs font-medium text-red-700">常见错误：</div>
                            {tpl.common_mistakes.map((m: string, j: number) => (
                              <div key={j} className="text-xs text-red-600">• {m}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </>
          )}
          {!answerTemplates && !templatesLoading && (
            <div className="rounded-xl border border-dashed border-slate-300 py-12 text-center text-slate-500">
              暂无答题模板数据
            </div>
          )}
        </div>
      )}

      {/* Original analysis content - only show on analysis tab */}
      {activeTab === 'analysis' && (
      <>

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
      </>
      )}
    </div>
  )
}

export default AnalysisPage
