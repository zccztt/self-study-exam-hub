import React, { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { examApi, ExamHistoryItem, ExamMode, ExamSession, GeneratedPaper, ScoreResult, WeakPoint } from '../api/exam'
import { Question } from '../api/question'
import { sessionStore } from '../api/session'
import { Chapter, subjectApi, Subject } from '../api/subject'
import Pagination from '../components/ui/Pagination'
import { enrollmentApi, EnrollmentListItem } from '../api/enrollment'
import { useExamHotkeys } from '../hooks/useExamHotkeys'

const examModeLabels: Record<ExamMode, { title: string; description: string }> = {
  real_exam: { title: '年份卷', description: '按当前或历年备考年份筛选题库' },
  random: { title: '随机组卷', description: '按题库条件随机抽题' },
  chapter: { title: '章节练习', description: '针对章节范围练习' },
  wrong_questions: { title: '错题重做', description: '从错题本重新组卷' },
  weak_point: { title: '薄弱专练', description: '针对掌握不足的知识点强化训练' },
}

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
}

const difficultyLabels: Record<string, string> = {
  easy: '易',
  medium: '中',
  hard: '难',
}

const defaultQuestionTypeRatio: Record<string, number> = {
  single_choice: 40,
  multiple_choice: 20,
  fill_blank: 15,
  short_answer: 15,
  essay: 5,
  case: 5,
}

const defaultDifficultyRatio: Record<string, number> = {
  easy: 30,
  medium: 50,
  hard: 20,
}

const optionLetters = ['A', 'B', 'C', 'D', 'E', 'F']
const CURRENT_EXAM_YEAR = new Date().getFullYear()
const YEAR_OPTIONS = Array.from({ length: 12 }, (_, index) => CURRENT_EXAM_YEAR - index)

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

const normalizeRatioValue = (value: number) => {
  const parsed = Number.isFinite(value) ? Math.round(value) : 0
  return Math.max(0, Math.min(100, parsed))
}

const buildRatioPayload = (ratio: Record<string, number>) =>
  Object.fromEntries(Object.entries(ratio).filter(([, value]) => value > 0))

const panelClass = 'rounded-lg border border-slate-200 bg-white shadow-sm'
const fieldClass =
  'w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100'
const labelClass = 'mb-2 block text-sm font-medium text-slate-700'
const sectionTitleClass = 'text-base font-semibold text-slate-950'
const sectionHintClass = 'mt-1 text-sm text-slate-500'

const ExamPage: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedSubjectId, setSelectedSubjectId] = useState('')
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [selectedChapterIds, setSelectedChapterIds] = useState<number[]>([])
  const [weakPoints, setWeakPoints] = useState<WeakPoint[]>([])
  const [selectedWeakPointIds, setSelectedWeakPointIds] = useState<number[]>([])
  const [weakPointsLoading, setWeakPointsLoading] = useState(false)
  const [examMode, setExamMode] = useState<ExamMode>('real_exam')
  const [year, setYear] = useState(String(CURRENT_EXAM_YEAR))
  const [limit, setLimit] = useState(20)
  const [smartConstraints, setSmartConstraints] = useState(true)
  const [chapterCoverage, setChapterCoverage] = useState(80)
  const [questionTypeRatio, setQuestionTypeRatio] = useState(defaultQuestionTypeRatio)
  const [difficultyRatio, setDifficultyRatio] = useState(defaultDifficultyRatio)
  const [onlineFallback, setOnlineFallback] = useState(true)
  const [saveOnlineQuestions, setSaveOnlineQuestions] = useState(false)
  const [paper, setPaper] = useState<GeneratedPaper | null>(null)
  const [session, setSession] = useState<ExamSession | null>(null)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [flaggedQuestions, setFlaggedQuestions] = useState<number[]>([])
  const [autoSubmitted, setAutoSubmitted] = useState(false)
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null)
  const [history, setHistory] = useState<ExamHistoryItem[]>([])
  const [historyPage, setHistoryPage] = useState(1)
  const [historyTotal, setHistoryTotal] = useState(0)
  const [now, setNow] = useState(Date.now())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [enrollments, setEnrollments] = useState<EnrollmentListItem[]>([])
  const [enrolledSubjectFilter, setEnrolledSubjectFilter] = useState(false)
  const [enrolledSubjectIds, setEnrolledSubjectIds] = useState<number[]>([])

  const subjectNameById = useMemo(
    () => new Map(subjects.map((subject) => [subject.id, subject.name])),
    [subjects],
  )
  const selectedSubject = subjects.find((subject) => String(subject.id) === selectedSubjectId)
  const answeredCount = paper?.questions.filter((question) => answers[question.id]?.trim()).length || 0
  const flaggedCount = flaggedQuestions.length
  const remainingSeconds = session ? Math.floor((new Date(session.end_time).getTime() - now) / 1000) : 0

  const updateQuestionTypeRatio = (questionType: string, value: number) => {
    setQuestionTypeRatio((current) => ({
      ...current,
      [questionType]: normalizeRatioValue(value),
    }))
  }

  const updateDifficultyRatio = (difficulty: string, value: number) => {
    setDifficultyRatio((current) => ({
      ...current,
      [difficulty]: normalizeRatioValue(value),
    }))
  }

  const loadHistory = async (page = historyPage) => {
    try {
      const data = await examApi.getHistory(sessionStore.getUserId(), page, 10)
      setHistory(data.items)
      setHistoryPage(data.page)
      setHistoryTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '考试历史加载失败')
    }
  }

  const restoreSession = async (sessionId: string) => {
    setLoading(true)
    setError('')
    try {
      const detail = await examApi.getSession(sessionId)
      setPaper(detail.paper)
      setSession({
        session_id: detail.session_id,
        exam_id: detail.exam_id,
        start_time: detail.start_time || new Date().toISOString(),
        end_time: detail.end_time || new Date().toISOString(),
        duration: detail.duration,
        status: detail.status,
      })
      setAnswers(
        Object.fromEntries(
          Object.entries(detail.answers || {}).map(([questionId, answer]) => [Number(questionId), answer]),
        ),
      )
      setSelectedSubjectId(String(detail.paper.subject_id))
      setExamMode(detail.paper.mode)
      setNow(Date.now())
      setMessage('已恢复未完成的考试和已保存答案。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '考试恢复失败')
    } finally {
      setLoading(false)
    }
  }

  const reviewCompletedSession = async (sessionId: string) => {
    setLoading(true)
    setError('')
    try {
      const detail = await examApi.getSession(sessionId)
      if (!detail.result) throw new Error('该考试暂无可查看的评分结果。')
      setPaper(detail.paper)
      setSession({
        session_id: detail.session_id,
        exam_id: detail.exam_id,
        start_time: detail.start_time || new Date().toISOString(),
        end_time: detail.end_time || new Date().toISOString(),
        duration: detail.duration,
        status: detail.status,
      })
      setAnswers(Object.fromEntries(Object.entries(detail.answers || {}).map(([id, answer]) => [Number(id), answer])))
      setScoreResult(detail.result)
      setSelectedSubjectId(String(detail.paper.subject_id))
      setMessage('正在查看历史考试的逐题评分与解析。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '考试结果加载失败')
    } finally {
      setLoading(false)
    }
  }

  const cancelSession = async (sessionId: string) => {
    if (!window.confirm('确定放弃这次考试吗？已保存答案会保留在历史记录中，但不会评分。')) return
    setLoading(true)
    setError('')
    try {
      await examApi.cancelSession(sessionId)
      if (session?.session_id === sessionId) {
        setPaper(null)
        setSession(null)
        setAnswers({})
        setFlaggedQuestions([])
        setScoreResult(null)
      }
      await loadHistory()
      setMessage('考试已放弃，可以重新生成试卷。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '放弃考试失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const initialize = async () => {
      setLoading(true)
      try {
        const [subjectData, historyData, enrollmentData] = await Promise.all([
          subjectApi.list(undefined, true),
          examApi.getHistory(sessionStore.getUserId(), 1, 10),
          enrollmentApi.listEnrollments().catch(() => []),
        ])
        setSubjects(subjectData)
        setHistory(historyData.items)
        setHistoryPage(historyData.page)
        setHistoryTotal(historyData.total)
        setEnrollments(enrollmentData)

        // If user has enrollments, collect their remaining subject IDs and pre-select first
        if (enrollmentData.length > 0) {
          try {
            const remainingIds = await enrollmentApi.getRemainingSubjects(enrollmentData[0].id)
            setEnrolledSubjectIds(remainingIds)
            if (remainingIds.length > 0) {
              setEnrolledSubjectFilter(true)
              setSelectedSubjectId(String(remainingIds[0]))
            } else if (subjectData[0]) {
              setSelectedSubjectId(String(subjectData[0].id))
            }
          } catch {
            if (subjectData[0]) setSelectedSubjectId(String(subjectData[0].id))
          }
        } else if (subjectData[0]) {
          setSelectedSubjectId(String(subjectData[0].id))
        }

        const activeSession = historyData.items.find((item) => item.status === 'in_progress')
        if (activeSession) await restoreSession(activeSession.session_id)
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
    const loadWeakPoints = async () => {
      setSelectedWeakPointIds([])
      setWeakPoints([])
      if (examMode !== 'weak_point' || !selectedSubjectId) return
      setWeakPointsLoading(true)
      try {
        const data = await examApi.getWeakPoints(sessionStore.getUserId(), Number(selectedSubjectId))
        setWeakPoints(data.items)
        setSelectedWeakPointIds(data.items.map((p) => p.point_id))
      } catch (err) {
        setError(err instanceof Error ? err.message : '薄弱知识点加载失败')
      } finally {
        setWeakPointsLoading(false)
      }
    }
    void loadWeakPoints()
  }, [examMode, selectedSubjectId])

  useEffect(() => {
    if (!session || scoreResult) return undefined
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [session, scoreResult])

  useEffect(() => {
    if (!session || scoreResult || autoSubmitted || loading || remainingSeconds > 0) return
    setAutoSubmitted(true)
    setMessage('考试时间已到，系统正在自动交卷。')
    void submitPaper()
  }, [session, scoreResult, autoSubmitted, loading, remainingSeconds])

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
        user_id: sessionStore.getUserId(),
        avoid_recent_done: true,
        recent_done_years: 3,
      }
      if (examMode !== 'wrong_questions' && examMode !== 'weak_point') config.year = Number(year)
      if (examMode === 'wrong_questions') config.user_id = sessionStore.getUserId()
      if (examMode === 'chapter') {
        if (selectedChapterIds.length === 0) {
          setError('请选择至少一个练习章节')
          return
        }
        config.chapter_ids = selectedChapterIds
      }
      if (examMode === 'weak_point') {
        if (selectedWeakPointIds.length === 0) {
          setError('没有可用的薄弱知识点，请先进行模拟考试以产生学习数据')
          return
        }
        config.point_ids = selectedWeakPointIds
        config.user_id = sessionStore.getUserId()
      }
      if (examMode !== 'wrong_questions' && smartConstraints) {
        config.constraints = {
          question_type_ratio: buildRatioPayload(questionTypeRatio),
          difficulty_ratio: buildRatioPayload(difficultyRatio),
          chapter_coverage: chapterCoverage / 100,
        }
      }

      const generatedPaper = await examApi.generatePaper({
        subject_id: Number(selectedSubjectId),
        mode: examMode,
        config,
      })
      setPaper(generatedPaper)
      setAnswers({})
      setFlaggedQuestions([])
      setAutoSubmitted(false)
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
    setFlaggedQuestions([])
    setAutoSubmitted(false)
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

  const toggleQuestionFlag = (questionId: number) => {
    setFlaggedQuestions((current) =>
      current.includes(questionId)
        ? current.filter((item) => item !== questionId)
        : [...current, questionId],
    )
  }

  const scrollToQuestion = (questionId: number) => {
    document.getElementById(`question-${questionId}`)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }

  // Track which question is currently in view for hotkey targeting
  const [visibleQuestionId, setVisibleQuestionId] = useState<number | null>(null)

  useEffect(() => {
    if (!paper || !session || scoreResult) return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const id = Number(entry.target.id.replace('question-', ''))
            if (id) setVisibleQuestionId(id)
          }
        }
      },
      { threshold: 0.5 },
    )
    paper.questions.forEach((q) => {
      const el = document.getElementById(`question-${q.id}`)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [paper, session, scoreResult])

  const hotkeyNextQuestion = useCallback(() => {
    if (!paper || !visibleQuestionId) return
    const idx = paper.questions.findIndex((q) => q.id === visibleQuestionId)
    if (idx < paper.questions.length - 1) {
      scrollToQuestion(paper.questions[idx + 1].id)
    }
  }, [paper, visibleQuestionId])

  const hotkeyPrevQuestion = useCallback(() => {
    if (!paper || !visibleQuestionId) return
    const idx = paper.questions.findIndex((q) => q.id === visibleQuestionId)
    if (idx > 0) {
      scrollToQuestion(paper.questions[idx - 1].id)
    }
  }, [paper, visibleQuestionId])

  const hotkeyFlagQuestion = useCallback(() => {
    if (visibleQuestionId) toggleQuestionFlag(visibleQuestionId)
  }, [visibleQuestionId])

  const hotkeySingleAnswer = useCallback((questionId: number, letter: string) => {
    setAndSaveAnswer(questionId, letter)
  }, [])

  const hotkeyMultipleToggle = useCallback((questionId: number, letter: string) => {
    toggleMultipleAnswer(questionId, letter)
  }, [])

  useExamHotkeys({
    active: Boolean(paper && session && !scoreResult),
    questions: paper?.questions || [],
    currentQuestionId: visibleQuestionId,
    onSingleAnswer: hotkeySingleAnswer,
    onMultipleToggle: hotkeyMultipleToggle,
    onNextQuestion: hotkeyNextQuestion,
    onPrevQuestion: hotkeyPrevQuestion,
    onFlagQuestion: hotkeyFlagQuestion,
  })

  const renderQuestionInput = (question: Question) => {
    const answer = answers[question.id] || ''

    if (question.question_type === 'single_choice') {
      return (
        <div className="space-y-2">
          {question.options.map((option, index) => {
            const letter = optionLetters[index]
            const checked = answer === letter
            return (
              <label
                key={`${question.id}-${letter}`}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 text-sm transition ${
                  checked
                    ? 'border-brand-300 bg-brand-50 text-brand-950'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <input
                  type="radio"
                  name={`question-${question.id}`}
                  value={letter}
                  checked={checked}
                  onChange={() => setAndSaveAnswer(question.id, letter)}
                  className="mt-1 h-4 w-4 border-slate-300 text-brand-600"
                />
                <span className="leading-6"><span className="font-semibold">{letter}.</span> {option}</span>
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
            const checked = answer.includes(letter)
            return (
              <label
                key={`${question.id}-${letter}`}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 text-sm transition ${
                  checked
                    ? 'border-brand-300 bg-brand-50 text-brand-950'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleMultipleAnswer(question.id, letter)}
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600"
                />
                <span className="leading-6"><span className="font-semibold">{letter}.</span> {option}</span>
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
        className={`${fieldClass} min-h-32 resize-y leading-6`}
        placeholder="输入答案"
      />
    )
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-sm font-medium text-brand-600">Exam</div>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">模拟考试</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            按科目、题型和章节约束快速生成试卷，进入限时答题后自动保存答案。
          </p>
        </div>
        {session && !scoreResult && (
          <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm font-semibold text-brand-700 shadow-sm">
            剩余时间 {formatTime(remainingSeconds)}
          </div>
        )}
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {message && <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{message}</div>}

      {!paper && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <form onSubmit={generateAndStart} className={`${panelClass} overflow-hidden`}>
            <div className="border-b border-slate-100 px-6 py-5">
              <h2 className="text-xl font-semibold text-slate-950">生成试卷</h2>
              <p className="mt-1 text-sm text-slate-500">先确定科目和模式，再按需要调整组卷策略。</p>
            </div>

            <div className="space-y-7 p-6">
              <section>
                <div className="mb-4">
                  <h3 className={sectionTitleClass}>基础信息</h3>
                  <p className={sectionHintClass}>科目会影响默认考试时长和章节范围。</p>
                </div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <div className="md:col-span-2">
                    <label className={labelClass}>选择科目</label>
                    {enrollments.length > 0 && (
                      <div className="mb-2 flex items-center gap-2">
                        <label className="flex items-center gap-1.5 text-xs text-blue-600 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={enrolledSubjectFilter}
                            onChange={(e) => setEnrolledSubjectFilter(e.target.checked)}
                            className="rounded"
                          />
                          只显示报考科目
                        </label>
                      </div>
                    )}
                    <select
                      value={selectedSubjectId}
                      onChange={(event) => setSelectedSubjectId(event.target.value)}
                      className={fieldClass}
                    >
                      <option value="">请选择科目</option>
                      {subjects
                        .filter((subject) => !enrolledSubjectFilter || enrolledSubjectIds.includes(subject.id))
                        .map((subject) => (
                        <option key={subject.id} value={subject.id}>
                          {subject.name}（{subject.question_count}题）
                        </option>
                      ))}
                    </select>
                  </div>
                  {examMode !== 'wrong_questions' && examMode !== 'weak_point' && (
                    <div>
                      <label className={labelClass}>年份</label>
                      <select value={year} onChange={(event) => setYear(event.target.value)} className={fieldClass}>
                        {YEAR_OPTIONS.map((item) => (
                          <option key={item} value={item}>
                            {item}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                  <div>
                    <label className={labelClass}>题目数量</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={limit}
                      onChange={(event) => setLimit(normalizeQuestionLimit(Number(event.target.value)))}
                      className={fieldClass}
                    />
                  </div>
                </div>
              </section>

              <section>
                <div className="mb-4">
                  <h3 className={sectionTitleClass}>考试模式</h3>
                  <p className={sectionHintClass}>选择当前练习目标，后续配置会随模式精简。</p>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {(Object.keys(examModeLabels) as ExamMode[]).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setExamMode(mode)}
                      className={`rounded-lg border p-4 text-left transition ${
                        examMode === mode
                          ? 'border-brand-500 bg-brand-50 shadow-sm ring-4 ring-brand-100'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-semibold text-slate-950">{examModeLabels[mode].title}</div>
                        <span
                          className={`h-2.5 w-2.5 rounded-full ${
                            examMode === mode ? 'bg-brand-600' : 'bg-slate-300'
                          }`}
                        />
                      </div>
                      <div className="mt-2 text-sm leading-5 text-slate-500">{examModeLabels[mode].description}</div>
                    </button>
                  ))}
                </div>
              </section>

              {examMode !== 'wrong_questions' && examMode !== 'weak_point' && (
                <section className="rounded-lg border border-slate-200 bg-slate-50/70 p-4">
                  <label className="flex items-start justify-between gap-4">
                    <span>
                      <span className={sectionTitleClass}>智能约束</span>
                      <span className={sectionHintClass}>按章节覆盖、难度和题型比例控制试卷结构。</span>
                    </span>
                    <input
                      type="checkbox"
                      checked={smartConstraints}
                      onChange={(event) => setSmartConstraints(event.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600"
                    />
                  </label>

                  {smartConstraints && (
                    <div className="mt-5 space-y-5">
                      <div>
                        <div className="mb-2 flex items-center justify-between">
                          <label className="text-sm font-medium text-slate-700">章节覆盖率</label>
                          <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-700">
                            {chapterCoverage}%
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <input
                            type="range"
                            min={0}
                            max={100}
                            step={5}
                            value={chapterCoverage}
                            onChange={(event) => setChapterCoverage(normalizeRatioValue(Number(event.target.value)))}
                            className="flex-1 accent-blue-600"
                          />
                          <input
                            type="number"
                            min={0}
                            max={100}
                            value={chapterCoverage}
                            onChange={(event) => setChapterCoverage(normalizeRatioValue(Number(event.target.value)))}
                            className={`${fieldClass} w-24`}
                          />
                        </div>
                      </div>

                      <div>
                        <label className={labelClass}>难度配比</label>
                        <div className="grid grid-cols-3 gap-3">
                          {Object.keys(defaultDifficultyRatio).map((difficulty) => (
                            <label key={difficulty} className="rounded-lg border border-slate-200 bg-white p-3">
                              <span className="mb-2 block text-sm font-medium text-slate-700">
                                {difficultyLabels[difficulty]}
                              </span>
                              <input
                                type="number"
                                min={0}
                                max={100}
                                value={difficultyRatio[difficulty]}
                                onChange={(event) => updateDifficultyRatio(difficulty, Number(event.target.value))}
                                className={fieldClass}
                              />
                            </label>
                          ))}
                        </div>
                      </div>

                      <div>
                        <label className={labelClass}>题型配比</label>
                        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                          {Object.keys(defaultQuestionTypeRatio).map((questionType) => (
                            <label key={questionType} className="rounded-lg border border-slate-200 bg-white p-3">
                              <span className="mb-2 block text-sm font-medium text-slate-700">
                                {questionTypeLabels[questionType]}
                              </span>
                              <input
                                type="number"
                                min={0}
                                max={100}
                                value={questionTypeRatio[questionType]}
                                onChange={(event) => updateQuestionTypeRatio(questionType, Number(event.target.value))}
                                className={fieldClass}
                              />
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </section>
              )}

              {examMode === 'chapter' && (
                <section>
                  <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className={sectionTitleClass}>练习章节</h3>
                      <p className={sectionHintClass}>
                        当前科目共 {chapters.length} 个章节，已选 {selectedChapterIds.length} 个。
                      </p>
                    </div>
                    {chapters.length > 0 && (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setSelectedChapterIds(chapters.map((chapter) => chapter.id))}
                          className="rounded-lg border border-brand-200 bg-white px-3 py-2 text-xs font-medium text-brand-700 hover:bg-brand-50"
                        >
                          全选
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelectedChapterIds([])}
                          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
                        >
                          清空
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="grid max-h-[360px] grid-cols-1 gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
                    {chapters.map((chapter) => (
                      <label
                        key={chapter.id}
                        className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-3 transition ${
                          selectedChapterIds.includes(chapter.id)
                            ? 'border-brand-300 bg-brand-50 shadow-sm'
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedChapterIds.includes(chapter.id)}
                          onChange={() => toggleChapter(chapter.id)}
                          className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600"
                        />
                        <span>
                          <span className="block text-sm font-medium text-slate-900">
                            {chapter.order}. {chapter.name}
                          </span>
                          {chapter.description && (
                            <span className="mt-1 line-clamp-2 block text-xs leading-5 text-slate-500">
                              {chapter.description}
                            </span>
                          )}
                        </span>
                      </label>
                    ))}
                  </div>
                  {chapters.length === 0 && (
                    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                      当前科目暂无章节数据
                    </div>
                  )}
                </section>
              )}

              {examMode === 'weak_point' && (
                <section>
                  <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className={sectionTitleClass}>薄弱知识点</h3>
                      <p className={sectionHintClass}>
                        {weakPointsLoading
                          ? '正在分析薄弱点...'
                          : `检测到 ${weakPoints.length} 个薄弱知识点，已选 ${selectedWeakPointIds.length} 个。`}
                      </p>
                    </div>
                    {weakPoints.length > 0 && (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setSelectedWeakPointIds(weakPoints.map((p) => p.point_id))}
                          className="rounded-lg border border-brand-200 bg-white px-3 py-2 text-xs font-medium text-brand-700 hover:bg-brand-50"
                        >
                          全选
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelectedWeakPointIds([])}
                          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
                        >
                          清空
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="grid max-h-[360px] grid-cols-1 gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
                    {weakPoints.map((point) => (
                      <label
                        key={point.point_id}
                        className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-3 transition ${
                          selectedWeakPointIds.includes(point.point_id)
                            ? 'border-brand-300 bg-brand-50 shadow-sm'
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedWeakPointIds.includes(point.point_id)}
                          onChange={() =>
                            setSelectedWeakPointIds((current) =>
                              current.includes(point.point_id)
                                ? current.filter((id) => id !== point.point_id)
                                : [...current, point.point_id],
                            )
                          }
                          className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600"
                        />
                        <span className="flex-1">
                          <span className="flex items-center justify-between gap-2">
                            <span className="block text-sm font-medium text-slate-900">
                              {point.name}
                            </span>
                            <span
                              className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                                point.priority === 'high'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-amber-100 text-amber-700'
                              }`}
                            >
                              {point.priority === 'high' ? '重点薄弱' : '需巩固'}
                            </span>
                          </span>
                          <span className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                            <span>掌握度 {Math.round(point.mastery_level * 100)}%</span>
                            {point.wrong_count > 0 && <span>错误 {point.wrong_count} 次</span>}
                          </span>
                          {point.description && (
                            <span className="mt-1 line-clamp-1 block text-xs leading-5 text-slate-400">
                              {point.description}
                            </span>
                          )}
                        </span>
                      </label>
                    ))}
                  </div>
                  {!weakPointsLoading && weakPoints.length === 0 && (
                    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                      暂无薄弱知识点数据，请先进行模拟考试以产生学习数据。
                    </div>
                  )}
                </section>
              )}

              {examMode !== 'wrong_questions' && examMode !== 'weak_point' && (
                <section>
                  <div className="mb-4">
                    <h3 className={sectionTitleClass}>题源策略</h3>
                    <p className={sectionHintClass}>本地题库不足时可启用线上题源补充。</p>
                  </div>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <label className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
                      <input
                        type="checkbox"
                        checked={onlineFallback}
                        onChange={(event) => setOnlineFallback(event.target.checked)}
                        className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600"
                      />
                      <span>
                        <span className="block text-sm font-medium text-slate-800">题库无题时线上生成</span>
                        <span className="mt-1 block text-xs leading-5 text-slate-500">
                          本地没有匹配题时，按课程代码和科目名称搜索题源生成试题。
                        </span>
                      </span>
                    </label>
                    <label className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
                      <input
                        type="checkbox"
                        checked={saveOnlineQuestions}
                        onChange={(event) => setSaveOnlineQuestions(event.target.checked)}
                        className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 disabled:opacity-50"
                        disabled={!onlineFallback}
                      />
                      <span>
                        <span className="block text-sm font-medium text-slate-800">保存线上生成题到题库</span>
                        <span className="mt-1 block text-xs leading-5 text-slate-500">
                          勾选后生成题会正式入库，后续同科目组卷优先复用本地题。
                        </span>
                      </span>
                    </label>
                  </div>
                </section>
              )}
            </div>

            <div className="border-t border-slate-100 bg-slate-50 px-6 py-5">
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-brand-600 py-3 font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? '生成中...' : '生成试卷并开始'}
              </button>
            </div>
          </form>

          <aside className="space-y-6">
            <div className={`${panelClass} p-5`}>
              <h2 className="text-lg font-semibold text-slate-950">当前配置</h2>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-slate-500">科目</span>
                  <span className="text-right font-medium text-slate-900">{selectedSubject?.name || '未选择'}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-slate-500">模式</span>
                  <span className="font-medium text-slate-900">{examModeLabels[examMode].title}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-slate-500">题量</span>
                  <span className="font-medium text-slate-900">{limit} 题</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-slate-500">默认时长</span>
                  <span className="font-medium text-slate-900">{selectedSubject?.exam_duration || 120} 分钟</span>
                </div>
                {examMode === 'chapter' && (
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-500">章节</span>
                    <span className="font-medium text-slate-900">{selectedChapterIds.length} 个</span>
                  </div>
                )}
              </div>
            </div>

            <div className={`${panelClass} p-5`}>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-950">考试历史</h2>
                <span className="text-xs text-slate-400">最近 10 次</span>
              </div>
              <div className="space-y-3">
                {history.map((item) => (
                  <div key={item.session_id} className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-medium text-slate-900">试卷 #{item.exam_id}</div>
                      <div className="text-lg font-bold text-brand-600">{item.score ?? '-'}分</div>
                    </div>
                    <div className="mt-1 flex items-center justify-between gap-3 text-xs text-slate-500">
                      <span>{item.start_time ? new Date(item.start_time).toLocaleString() : '-'}</span>
                      <span>{item.status === 'in_progress' ? '进行中' : item.status === 'completed' ? '已完成' : item.status === 'cancelled' ? '已放弃' : '已超时'}</span>
                    </div>
                    {item.status === 'in_progress' && (
                      <div className="mt-3 grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          onClick={() => void restoreSession(item.session_id)}
                          className="rounded-md border border-brand-300 bg-white px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
                        >
                          继续答题
                        </button>
                        <button
                          type="button"
                          onClick={() => void cancelSession(item.session_id)}
                          className="rounded-md border border-red-200 bg-white px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                        >
                          放弃考试
                        </button>
                      </div>
                    )}
                    {item.status === 'completed' && (
                      <button
                        type="button"
                        onClick={() => void reviewCompletedSession(item.session_id)}
                        className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                      >
                        查看评分解析
                      </button>
                    )}
                  </div>
                ))}
                {historyTotal > 10 && (
                  <Pagination
                    current={historyPage}
                    total={historyTotal}
                    pageSize={10}
                    loading={loading}
                    onChange={(p) => void loadHistory(p)}
                    className="pt-2"
                  />
                )}
                {history.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
                    暂无考试历史
                  </div>
                )}
              </div>
            </div>
          </aside>
        </div>
      )}

      {paper && session && !scoreResult && (
        <div className="space-y-6">
          <div className={`${panelClass} p-6`}>
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">{paper.name || examModeLabels[paper.mode].title}</h2>
                <div className="mt-1 text-sm leading-6 text-slate-500">
                  {subjectNameById.get(paper.subject_id) || `科目 ${paper.subject_id}`} · {paper.question_count}题
                  {paper.requested_question_count && paper.requested_question_count !== paper.question_count
                    ? `（请求 ${paper.requested_question_count}，题库匹配 ${paper.available_question_count ?? paper.question_count}）`
                    : ''}{' '}
                  · 总分{' '}
                  {paper.total_score}
                  {paper.online_generated_count ? ` · 线上生成 ${paper.online_generated_count}题` : ''}
                  {paper.saved_online_question_count ? ` · 已入库 ${paper.saved_online_question_count}题` : ''}
                </div>
                {paper.constraint_report && (
                  <div className="mt-2 text-xs text-slate-500">
                    智能组卷 · 章节覆盖 {paper.constraint_report.chapter_coverage_actual_count}/
                    {paper.constraint_report.chapter_coverage_target_count || paper.constraint_report.covered_chapter_ids.length}
                    {paper.constraint_report.satisfied ? ' · 约束已满足' : ' · 已按题库可用范围放宽'}
                  </div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="rounded-lg bg-brand-50 px-4 py-3">
                  <div className="text-lg font-bold text-brand-700">{answeredCount}/{paper.question_count}</div>
                  <div className="text-xs text-brand-600">已答</div>
                </div>
                <div className="rounded-lg bg-amber-50 px-4 py-3">
                  <div className="text-lg font-bold text-amber-700">{flaggedCount}</div>
                  <div className="text-xs text-amber-600">标记</div>
                </div>
              </div>
            </div>
          </div>

          <div className="sticky top-4 z-10 rounded-lg border border-slate-200 bg-white/95 p-4 shadow-sm backdrop-blur">
            <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="font-medium text-slate-900">答题卡</div>
              <div className="flex flex-wrap gap-3 text-xs text-slate-500">
                <span>白色未答</span>
                <span>蓝色已答</span>
                <span>黄色已标记</span>
                <span className="hidden sm:inline rounded bg-slate-100 px-1.5 py-0.5">快捷键: 1-6选项 · ↑↓切题 · 空格标记</span>
                {paper.constraint_report?.recent_done_excluded_count ? (
                  <span>已避开近 3 年做过题 {paper.constraint_report.recent_done_excluded_count} 道</span>
                ) : null}
              </div>
            </div>
            <div className="grid grid-cols-8 gap-2 sm:grid-cols-10 md:grid-cols-12">
              {paper.questions.map((question, index) => {
                const answered = Boolean(answers[question.id]?.trim())
                const flagged = flaggedQuestions.includes(question.id)
                return (
                  <button
                    key={question.id}
                    type="button"
                    onClick={() => scrollToQuestion(question.id)}
                    className={`h-9 rounded border text-sm font-medium transition ${
                      flagged
                        ? 'border-amber-300 bg-amber-100 text-amber-800'
                        : answered
                          ? 'border-brand-300 bg-brand-100 text-brand-800'
                          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {index + 1}
                  </button>
                )
              })}
            </div>
          </div>

          {paper.questions.map((question, index) => (
            <div key={question.id} id={`question-${question.id}`} className={`${panelClass} scroll-mt-28 p-6`}>
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">第 {index + 1} 题</span>
                <span className="rounded-full bg-brand-100 px-3 py-1 text-sm font-medium text-brand-700">
                  {questionTypeLabels[question.question_type] || question.question_type}
                </span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">{question.score} 分</span>
                <button
                  type="button"
                  onClick={() => toggleQuestionFlag(question.id)}
                  className={`rounded-full px-3 py-1 text-sm font-medium ${
                    flaggedQuestions.includes(question.id)
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {flaggedQuestions.includes(question.id) ? '取消标记' : '标记跳过'}
                </button>
              </div>
              <div className="mb-5 whitespace-pre-wrap text-base leading-8 text-slate-900">{question.content}</div>
              {renderQuestionInput(question)}
            </div>
          ))}

          <div className="sticky bottom-4 rounded-lg border border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur">
            <button
              type="button"
              disabled={loading}
              onClick={() => void submitPaper()}
              className="w-full rounded-lg bg-brand-600 py-3 font-semibold text-white shadow-sm hover:bg-brand-700 disabled:opacity-60"
            >
              {loading ? '交卷中...' : '提交试卷'}
            </button>
          </div>
        </div>
      )}

      {paper && scoreResult && (
        <div className="space-y-6">
          <div className={`${panelClass} p-6`}>
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-2xl font-bold text-slate-950">考试结果</h2>
                <div className="mt-2 text-sm leading-6 text-slate-500">
                  已自动评分 {scoreResult.auto_scored_count || scoreResult.total_count} / {scoreResult.total_count} 题，
                  客观题 {scoreResult.objective_count} 题，主观题 {scoreResult.subjective_count || 0} 题，
                  得分率 {Math.round(scoreResult.accuracy * 100)}%
                </div>
              </div>
              <div className="rounded-lg bg-brand-50 px-6 py-4 text-4xl font-bold text-brand-700">
                {scoreResult.score} / {scoreResult.total_score}
              </div>
            </div>
            <button
              type="button"
              onClick={resetExam}
              className="mt-6 rounded-lg border border-brand-200 bg-white px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
            >
              返回考试配置
            </button>
          </div>

          {scoreResult.question_analysis.map((item, index) => (
            <div key={item.question_id} className={`${panelClass} p-6`}>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="font-semibold text-slate-950">第 {index + 1} 题</span>
                <span className="rounded-full bg-brand-100 px-3 py-1 text-sm text-brand-700">
                  {questionTypeLabels[item.question_type || ''] || item.question_type || '题目'}
                </span>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
                  {item.score} / {item.full_score} 分
                </span>
                {item.is_correct === true && <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm text-emerald-700">正确</span>}
                {item.is_correct === false && <span className="rounded-full bg-red-100 px-3 py-1 text-sm text-red-700">需复习</span>}
              </div>
              <div className="whitespace-pre-wrap text-base leading-8 text-slate-900">{item.content}</div>
              {item.options && item.options.length > 0 && (
                <div className="mt-4 space-y-2">
                  {item.options.map((option, optionIndex) => {
                    const letter = optionLetters[optionIndex]
                    const isCorrect = item.correct_answer.includes(letter)
                    const isUserSelected = item.user_answer.includes(letter)
                    return (
                      <div
                        key={`${item.question_id}-analysis-${letter}`}
                        className={`rounded border px-3 py-2 text-sm ${
                          isCorrect
                            ? 'border-green-200 bg-green-50 text-green-800'
                            : isUserSelected
                              ? 'border-red-200 bg-red-50 text-red-800'
                              : 'border-slate-200 bg-slate-50 text-slate-700'
                        }`}
                      >
                        {letter}. {option}
                      </div>
                    )
                  })}
                </div>
              )}
              <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                <div className="rounded bg-slate-50 p-3">你的答案：{item.user_answer || '-'}</div>
                <div className="rounded bg-slate-50 p-3">参考答案：{item.correct_answer || '-'}</div>
              </div>
              {item.scoring_points && item.scoring_points.length > 0 && (
                <div className="mt-3 rounded bg-amber-50 p-3 text-sm text-amber-900">
                  <div className="mb-2 font-medium">标准评分项</div>
                  <div className="space-y-2">
                    {item.scoring_points.map((point, pointIndex) => (
                      <div key={`${item.question_id}-point-${pointIndex}`}>
                        <div>
                          {pointIndex + 1}. {point.label}：{point.earned_score} / {point.score} 分
                        </div>
                        {point.comment && <div className="text-amber-800">{point.comment}</div>}
                        {point.matched_keywords && point.matched_keywords.length > 0 && (
                          <div className="text-amber-700">命中：{point.matched_keywords.join('、')}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {item.final_explanation && (
                <div className="mt-3 rounded bg-green-50 p-3 text-sm text-green-800">{item.final_explanation}</div>
              )}
              {item.explanation && <div className="mt-3 rounded bg-brand-50 p-3 text-sm text-brand-800">{item.explanation}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ExamPage
