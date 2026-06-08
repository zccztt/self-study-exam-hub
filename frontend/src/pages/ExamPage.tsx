import React, { FormEvent, useEffect, useMemo, useState } from 'react'
import { examApi, ExamHistoryItem, ExamMode, ExamSession, GeneratedPaper, ScoreResult } from '../api/exam'
import { Question } from '../api/question'
import { sessionStore } from '../api/session'
import { Chapter, subjectApi, Subject } from '../api/subject'

const examModeLabels: Record<ExamMode, { title: string; description: string }> = {
  real_exam: { title: '年份卷', description: '按 2026 备考年份筛选题库' },
  random: { title: '随机组卷', description: '按题库条件随机抽题' },
  chapter: { title: '章节练习', description: '针对章节范围练习' },
  wrong_questions: { title: '错题重做', description: '从错题本重新组卷' },
}

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
}

const optionLetters = ['A', 'B', 'C', 'D', 'E', 'F']

const formatTime = (seconds: number) => {
  const safeSeconds = Math.max(0, seconds)
  const minutes = Math.floor(safeSeconds / 60)
  const remainSeconds = safeSeconds % 60
  return `${minutes.toString().padStart(2, '0')}:${remainSeconds.toString().padStart(2, '0')}`
}

const normalizeQuestionLimit = (value: number) => {
  const parsed = Number.isFinite(value) ? Math.floor(value) : 20
  return Math.max(1, Math.min(100, parsed))
}

const ExamPage: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedSubjectId, setSelectedSubjectId] = useState('')
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [selectedChapterIds, setSelectedChapterIds] = useState<number[]>([])
  const [examMode, setExamMode] = useState<ExamMode>('real_exam')
  const [year, setYear] = useState('2026')
  const [limit, setLimit] = useState(20)
  const [onlineFallback, setOnlineFallback] = useState(true)
  const [saveOnlineQuestions, setSaveOnlineQuestions] = useState(false)
  const [paper, setPaper] = useState<GeneratedPaper | null>(null)
  const [session, setSession] = useState<ExamSession | null>(null)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null)
  const [history, setHistory] = useState<ExamHistoryItem[]>([])
  const [now, setNow] = useState(Date.now())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const subjectNameById = useMemo(
    () => new Map(subjects.map((subject) => [subject.id, subject.name])),
    [subjects],
  )
  const selectedSubject = subjects.find((subject) => String(subject.id) === selectedSubjectId)
  const answeredCount = paper?.questions.filter((question) => answers[question.id]?.trim()).length || 0
  const remainingSeconds = session ? Math.floor((new Date(session.end_time).getTime() - now) / 1000) : 0

  const loadHistory = async () => {
    try {
      const data = await examApi.getHistory(sessionStore.getUserId(), 1, 10)
      setHistory(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : '考试历史加载失败')
    }
  }

  useEffect(() => {
    const initialize = async () => {
      setLoading(true)
      try {
        const [subjectData, historyData] = await Promise.all([
          subjectApi.list(),
          examApi.getHistory(sessionStore.getUserId(), 1, 10),
        ])
        setSubjects(subjectData)
        if (subjectData[0]) setSelectedSubjectId(String(subjectData[0].id))
        setHistory(historyData.items)
      } catch (err) {
        setError(err instanceof Error ? err.message : '初始化考试模块失败')
      } finally {
        setLoading(false)
      }
    }
    void initialize()
  }, [])

  useEffect(() => {
    const loadChapters = async () => {
      setSelectedChapterIds([])
      if (!selectedSubjectId) {
        setChapters([])
        return
      }
      try {
        const detail = await subjectApi.detail(Number(selectedSubjectId))
        setChapters(detail.chapters)
      } catch (err) {
        setError(err instanceof Error ? err.message : '章节加载失败')
      }
    }
    void loadChapters()
  }, [selectedSubjectId])

  useEffect(() => {
    if (!session || scoreResult) return undefined
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [session, scoreResult])

  const generateAndStart = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setScoreResult(null)

    if (!selectedSubjectId) {
      setError('请选择考试科目')
      return
    }

    setLoading(true)
    try {
      const requestedLimit = normalizeQuestionLimit(limit)
      setLimit(requestedLimit)
      const config: Record<string, unknown> = {
        limit: requestedLimit,
        duration: selectedSubject?.exam_duration || 120,
        online_fallback: onlineFallback,
        save_online_questions: saveOnlineQuestions,
      }
      if (examMode === 'real_exam') config.year = Number(year)
      if (examMode === 'wrong_questions') config.user_id = sessionStore.getUserId()
      if (examMode === 'chapter') {
        if (selectedChapterIds.length === 0) {
          setError('请选择至少一个练习章节')
          return
        }
        config.chapter_ids = selectedChapterIds
      }

      const generatedPaper = await examApi.generatePaper({
        subject_id: Number(selectedSubjectId),
        mode: examMode,
        config,
      })
      setPaper(generatedPaper)
      setAnswers({})
      setMessage(generatedPaper.message || '')

      if (!generatedPaper.exam_id) {
        setSession(null)
        setMessage(generatedPaper.message || '没有匹配到可用题目')
        return
      }

      const startedSession = await examApi.startExam(generatedPaper.exam_id, sessionStore.getUserId())
      setSession(startedSession)
      setNow(Date.now())
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成试卷失败')
    } finally {
      setLoading(false)
    }
  }

  const saveAnswer = async (questionId: number, answer: string) => {
    if (!session) return
    try {
      await examApi.submitAnswer(session.session_id, questionId, answer)
    } catch (err) {
      setError(err instanceof Error ? err.message : '答案保存失败')
    }
  }

  const setAndSaveAnswer = (questionId: number, answer: string) => {
    setAnswers((current) => ({ ...current, [questionId]: answer }))
    void saveAnswer(questionId, answer)
  }

  const toggleMultipleAnswer = (questionId: number, letter: string) => {
    const selected = new Set((answers[questionId] || '').split('').filter(Boolean))
    if (selected.has(letter)) {
      selected.delete(letter)
    } else {
      selected.add(letter)
    }
    const nextAnswer = optionLetters.filter((item) => selected.has(item)).join('')
    setAndSaveAnswer(questionId, nextAnswer)
  }

  const submitPaper = async () => {
    if (!session || !paper) return
    setLoading(true)
    setError('')
    try {
      await Promise.all(
        paper.questions.map((question) =>
          examApi.submitAnswer(session.session_id, question.id, answers[question.id] || ''),
        ),
      )
      const score = await examApi.submitPaper(session.session_id)
      setScoreResult(score)
      await loadHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : '交卷失败')
    } finally {
      setLoading(false)
    }
  }

  const resetExam = () => {
    setPaper(null)
    setSession(null)
    setAnswers({})
    setScoreResult(null)
    setMessage('')
  }

  const toggleChapter = (chapterId: number) => {
    setSelectedChapterIds((current) =>
      current.includes(chapterId)
        ? current.filter((item) => item !== chapterId)
        : [...current, chapterId],
    )
  }

  const renderQuestionInput = (question: Question) => {
    const answer = answers[question.id] || ''

    if (question.question_type === 'single_choice') {
      return (
        <div className="space-y-2">
          {question.options.map((option, index) => {
            const letter = optionLetters[index]
            return (
              <label key={`${question.id}-${letter}`} className="flex items-center gap-2 rounded border border-gray-200 px-3 py-2">
                <input
                  type="radio"
                  name={`question-${question.id}`}
                  value={letter}
                  checked={answer === letter}
                  onChange={() => setAndSaveAnswer(question.id, letter)}
                />
                <span>
                  {letter}. {option}
                </span>
              </label>
            )
          })}
        </div>
      )
    }

    if (question.question_type === 'multiple_choice') {
      return (
        <div className="space-y-2">
          {question.options.map((option, index) => {
            const letter = optionLetters[index]
            return (
              <label key={`${question.id}-${letter}`} className="flex items-center gap-2 rounded border border-gray-200 px-3 py-2">
                <input
                  type="checkbox"
                  checked={answer.includes(letter)}
                  onChange={() => toggleMultipleAnswer(question.id, letter)}
                />
                <span>
                  {letter}. {option}
                </span>
              </label>
            )
          })}
        </div>
      )
    }

    return (
      <textarea
        value={answer}
        onChange={(event) =>
          setAnswers((current) => ({ ...current, [question.id]: event.target.value }))
        }
        onBlur={() => void saveAnswer(question.id, answers[question.id] || '')}
        rows={4}
        className="w-full rounded-lg border border-gray-300 px-4 py-3"
        placeholder="输入答案"
      />
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
        <h1 className="text-3xl font-bold">模拟考试</h1>
        {session && !scoreResult && (
          <div className="rounded-lg bg-blue-50 px-4 py-2 text-blue-700">
            剩余时间 {formatTime(remainingSeconds)}
          </div>
        )}
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}
      {message && <div className="mb-4 rounded-lg bg-yellow-50 px-4 py-3 text-yellow-700">{message}</div>}

      {!paper && (
        <>
          <form onSubmit={generateAndStart} className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">选择考试配置</h2>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">选择科目</label>
              <select
                value={selectedSubjectId}
                onChange={(event) => setSelectedSubjectId(event.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">请选择科目</option>
                {subjects.map((subject) => (
                  <option key={subject.id} value={subject.id}>
                    {subject.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">考试模式</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(Object.keys(examModeLabels) as ExamMode[]).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setExamMode(mode)}
                    className={`p-4 border-2 rounded-lg text-left transition-colors ${
                      examMode === mode ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-semibold mb-1">{examModeLabels[mode].title}</div>
                    <div className="text-sm text-gray-600">{examModeLabels[mode].description}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {examMode === 'real_exam' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">选择年份</label>
                  <select
                    value={year}
                    onChange={(event) => setYear(event.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  >
                    {[2026].map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">题目数量</label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={limit}
                  onChange={(event) => setLimit(normalizeQuestionLimit(Number(event.target.value)))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>
            </div>

            {examMode === 'chapter' && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">练习章节</label>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {chapters.map((chapter) => (
                    <label key={chapter.id} className="flex items-center gap-2 rounded border border-gray-200 px-3 py-2">
                      <input
                        type="checkbox"
                        checked={selectedChapterIds.includes(chapter.id)}
                        onChange={() => toggleChapter(chapter.id)}
                      />
                      <span className="text-sm">{chapter.name}</span>
                    </label>
                  ))}
                </div>
                {chapters.length === 0 && <div className="text-sm text-gray-500">当前科目暂无章节数据</div>}
              </div>
            )}

            {examMode !== 'wrong_questions' && (
              <div className="mb-6 grid grid-cols-1 gap-3 md:grid-cols-2">
                <label className="flex items-start gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={onlineFallback}
                    onChange={(event) => setOnlineFallback(event.target.checked)}
                    className="mt-1"
                  />
                  <span>
                    <span className="block text-sm font-medium text-gray-800">题库无题时线上生成</span>
                    <span className="block text-xs text-gray-500">本地没有匹配题时，按课程代码和科目名称搜索题源生成试题。</span>
                  </span>
                </label>
                <label className="flex items-start gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={saveOnlineQuestions}
                    onChange={(event) => setSaveOnlineQuestions(event.target.checked)}
                    className="mt-1"
                    disabled={!onlineFallback}
                  />
                  <span>
                    <span className="block text-sm font-medium text-gray-800">保存线上生成题到题库</span>
                    <span className="block text-xs text-gray-500">勾选后生成题会正式入库，后续同科目组卷优先复用本地题。</span>
                  </span>
                </label>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-500 text-white py-3 rounded-lg font-semibold hover:bg-blue-600 transition-colors disabled:opacity-60"
            >
              {loading ? '生成中...' : '生成试卷并开始'}
            </button>
          </form>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">考试历史</h2>
            <div className="space-y-3">
              {history.map((item) => (
                <div key={item.session_id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <div className="font-medium">试卷 #{item.exam_id}</div>
                    <div className="text-sm text-gray-500">
                      {item.start_time ? new Date(item.start_time).toLocaleString() : '-'}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-blue-500">{item.score ?? '-'}分</div>
                    <div className="text-sm text-gray-500">{item.status}</div>
                  </div>
                </div>
              ))}
              {history.length === 0 && <div className="text-gray-500">暂无考试历史</div>}
            </div>
          </div>
        </>
      )}

      {paper && session && !scoreResult && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold">{paper.name || examModeLabels[paper.mode].title}</h2>
                <div className="mt-1 text-sm text-gray-600">
                  {subjectNameById.get(paper.subject_id) || `科目 ${paper.subject_id}`} · {paper.question_count}题
                  {paper.requested_question_count && paper.requested_question_count !== paper.question_count
                    ? `（请求 ${paper.requested_question_count}，题库匹配 ${paper.available_question_count ?? paper.question_count}）`
                    : ''}{' '}
                  · 总分{' '}
                  {paper.total_score}
                  {paper.online_generated_count ? ` · 线上生成 ${paper.online_generated_count}题` : ''}
                  {paper.saved_online_question_count ? ` · 已入库 ${paper.saved_online_question_count}题` : ''}
                </div>
              </div>
              <div className="text-sm text-gray-600">
                已答 {answeredCount} / {paper.question_count}
              </div>
            </div>
          </div>

          {paper.questions.map((question, index) => (
            <div key={question.id} className="bg-white rounded-lg shadow p-6">
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <span className="rounded bg-gray-100 px-2 py-1 text-sm text-gray-700">第 {index + 1} 题</span>
                <span className="rounded bg-blue-100 px-2 py-1 text-sm text-blue-700">
                  {questionTypeLabels[question.question_type] || question.question_type}
                </span>
                <span className="rounded bg-green-100 px-2 py-1 text-sm text-green-700">{question.score} 分</span>
              </div>
              <div className="mb-4 whitespace-pre-wrap text-gray-900">{question.content}</div>
              {renderQuestionInput(question)}
            </div>
          ))}

          <div className="sticky bottom-4 rounded-lg bg-white p-4 shadow-lg">
            <button
              type="button"
              disabled={loading}
              onClick={() => void submitPaper()}
              className="w-full rounded-lg bg-blue-500 py-3 font-semibold text-white hover:bg-blue-600 disabled:opacity-60"
            >
              {loading ? '交卷中...' : '提交试卷'}
            </button>
          </div>
        </div>
      )}

      {paper && scoreResult && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-2xl font-bold">考试结果</h2>
                <div className="mt-2 text-gray-600">
                  客观题正确 {scoreResult.correct_count} / {scoreResult.objective_count || scoreResult.total_count}，
                  正确率 {Math.round(scoreResult.accuracy * 100)}%
                  {scoreResult.manual_count > 0 ? `，${scoreResult.manual_count} 道主观题待人工评分` : ''}
                </div>
              </div>
              <div className="text-4xl font-bold text-blue-500">
                {scoreResult.score} / {scoreResult.total_score}
              </div>
            </div>
            <button
              type="button"
              onClick={resetExam}
              className="mt-6 rounded-lg border border-blue-500 px-4 py-2 text-blue-500 hover:bg-blue-50"
            >
              返回考试配置
            </button>
          </div>

          {scoreResult.question_analysis.map((item, index) => (
            <div key={item.question_id} className="bg-white rounded-lg shadow p-6">
              <div className="mb-2 flex items-center gap-2">
                <span className="font-semibold">第 {index + 1} 题</span>
                {item.is_correct === true && <span className="rounded bg-green-100 px-2 py-1 text-sm text-green-700">正确</span>}
                {item.is_correct === false && <span className="rounded bg-red-100 px-2 py-1 text-sm text-red-700">错误</span>}
                {item.is_correct === null && <span className="rounded bg-gray-100 px-2 py-1 text-sm text-gray-700">待人工评分</span>}
              </div>
              <div className="whitespace-pre-wrap text-gray-900">{item.content}</div>
              <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                <div className="rounded bg-gray-50 p-3">你的答案：{item.user_answer || '-'}</div>
                <div className="rounded bg-gray-50 p-3">参考答案：{item.correct_answer || '-'}</div>
              </div>
              {item.explanation && <div className="mt-3 rounded bg-blue-50 p-3 text-sm text-blue-800">{item.explanation}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ExamPage
