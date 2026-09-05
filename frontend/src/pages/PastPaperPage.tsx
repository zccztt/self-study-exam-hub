import React, { useCallback, useEffect, useRef, useState } from 'react'
import { pastPaperApi, PastPaper, PastPaperDetail, PastPaperSubject, PaperType } from '../api/pastPaper'
import { examApi, ExamSession, ScoreResult } from '../api/exam'
import { Question } from '../api/question'
import { enrollmentApi } from '../api/enrollment'
import { useAuthStore } from '../stores/useAuthStore'
import EnrolledSubjectToggle from '../components/EnrolledSubjectToggle'
import Pagination from '../components/ui/Pagination'

const optionLetters = ['A', 'B', 'C', 'D', 'E', 'F']

const panelClass = 'rounded-lg border border-slate-200 bg-white shadow-sm'
const fieldClass =
  'w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100'
const labelClass = 'mb-2 block text-sm font-medium text-slate-700'

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
}

const PastPaperPage: React.FC = () => {
  // List state
  const [subjects, setSubjects] = useState<PastPaperSubject[]>([])
  const [enrolledCodes, setEnrolledCodes] = useState<Set<string> | null>(null)
  const [onlyEnrolled, setOnlyEnrolled] = useState(false)
  const user = useAuthStore((s) => s.user)
  const [years, setYears] = useState<number[]>([])
  const [papers, setPapers] = useState<PastPaper[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filterSubjectId, setFilterSubjectId] = useState<string>('')
  const [filterYear, setFilterYear] = useState<string>('')
  const [filterPaperType, setFilterPaperType] = useState<PaperType>('')
  const [keyword, setKeyword] = useState('')
  const [searchInput, setSearchInput] = useState('')

  // Detail / exam state
  const [detail, setDetail] = useState<PastPaperDetail | null>(null)
  const [session, setSession] = useState<ExamSession | null>(null)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null)
  const [now, setNow] = useState(Date.now())

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [autoSubmitted, setAutoSubmitted] = useState(false)
  const debounceTimerRef = useRef<Record<number, ReturnType<typeof setTimeout>>>({})

  const remainingSeconds = session
    ? Math.max(0, Math.floor((new Date(session.end_time).getTime() - now) / 1000))
    : 0

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  // Timer
  useEffect(() => {
    if (!session || session.status !== 'in_progress') return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [session])

  // Load enrolled subject codes
  useEffect(() => {
    if (!user) return
    enrollmentApi.listEnrollments().then(async (enrollments) => {
      if (enrollments.length === 0) { setEnrolledCodes(new Set()); return }
      const results = await Promise.all(
        enrollments.map((e) => enrollmentApi.getEnrollmentSubjects(e.id).catch(() => null)),
      )
      const codes = new Set<string>()
      for (const data of results) {
        if (!data) continue
        for (const group of [data.subjects.required, data.subjects.elective, data.subjects.additional]) {
          for (const s of group) codes.add(s.code)
        }
      }
      setEnrolledCodes(codes)
    }).catch(() => setEnrolledCodes(null))
  }, [user])

  // Load filters
  useEffect(() => {
    const init = async () => {
      try {
        const [subjectData, yearData] = await Promise.all([
          pastPaperApi.getSubjects(filterPaperType || undefined),
          pastPaperApi.getYears(undefined, filterPaperType || undefined),
        ])
        setSubjects(subjectData)
        setYears(yearData)
        await loadPapers(1)
      } catch (err) {
        setError(err instanceof Error ? err.message : '初始化失败')
      }
    }
    void init()
  }, [])

  // Load papers list
  const loadPapers = async (p = page, subjectId?: string, year?: string, paperType?: PaperType, kw?: string) => {
    setLoading(true)
    setError('')
    try {
      const params: Record<string, unknown> = { page: p, page_size: 12 }
      const sid = subjectId ?? filterSubjectId
      const yr = year ?? filterYear
      const pt = paperType ?? filterPaperType
      const searchKw = kw ?? keyword
      if (sid) params.subject_id = Number(sid)
      if (yr) params.year = Number(yr)
      if (pt) params.paper_type = pt
      if (searchKw) params.keyword = searchKw
      const data = await pastPaperApi.list(params as any)
      setPapers(data.items)
      setTotal(data.total)
      setPage(data.page)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  // Handle filter changes
  const handleSubjectChange = (value: string) => {
    setFilterSubjectId(value)
    void loadPapers(1, value, filterYear, filterPaperType, keyword)
  }
  const handleYearChange = (value: string) => {
    setFilterYear(value)
    void loadPapers(1, filterSubjectId, value, filterPaperType, keyword)
  }
  const handlePaperTypeChange = (value: PaperType) => {
    setFilterPaperType(value)
    void loadPapers(1, filterSubjectId, filterYear, value, keyword)
  }
  const handleSearch = () => {
    setKeyword(searchInput)
    void loadPapers(1, filterSubjectId, filterYear, filterPaperType, searchInput)
  }
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  // Open paper detail
  const openPaper = async (paperId: number) => {
    setLoading(true)
    setError('')
    try {
      const data = await pastPaperApi.getDetail(paperId)
      setDetail(data)
      setSession(null)
      setAnswers({})
      setScoreResult(null)
      setMessage('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载真题详情失败')
    } finally {
      setLoading(false)
    }
  }

  // Start exam
  const startExam = async () => {
    if (!detail) return
    setLoading(true)
    setError('')
    try {
      const sess = await pastPaperApi.start(detail.id)
      setSession(sess)
      setAnswers({})
      setScoreResult(null)
      setNow(Date.now())
      setMessage('考试已开始，请在限定时间内答题。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '开始考试失败')
    } finally {
      setLoading(false)
    }
  }

  // Submit answer with debounce for text inputs
  const handleAnswerChange = async (questionId: number, answer: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answer }))
    if (session) {
      // Clear previous debounce timer for this question
      if (debounceTimerRef.current[questionId]) {
        clearTimeout(debounceTimerRef.current[questionId])
      }
      debounceTimerRef.current[questionId] = setTimeout(async () => {
        try {
          await examApi.submitAnswer(session.session_id, questionId, answer)
        } catch (err) {
          setError(err instanceof Error ? err.message : '答案保存失败，请重试')
          setTimeout(() => setError(''), 3000)
        }
      }, 800)
    }
  }

  // Immediate submit for choice questions
  const handleChoiceChange = async (questionId: number, answer: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answer }))
    if (session) {
      try {
        await examApi.submitAnswer(session.session_id, questionId, answer)
      } catch (err) {
        setError(err instanceof Error ? err.message : '答案保存失败，请重试')
        setTimeout(() => setError(''), 3000)
      }
    }
  }

  // Submit paper
  const submitPaper = useCallback(async (auto = false) => {
    if (!session) return
    if (autoSubmitted) return
    if (!auto && !window.confirm('确认交卷？交卷后将不能修改答案。')) return
    setAutoSubmitted(true)
    setLoading(true)
    setError('')
    try {
      const result = await examApi.submitPaper(session.session_id)
      setScoreResult(result)
      setSession((prev) => prev ? { ...prev, status: 'completed' } : prev)
      setMessage(auto ? `时间到，已自动交卷。得分：${result.score}/${result.total_score}` : `交卷成功！得分：${result.score}/${result.total_score}`)
    } catch (err) {
      setAutoSubmitted(false)
      setError(err instanceof Error ? err.message : '交卷失败')
    } finally {
      setLoading(false)
    }
  }, [session, autoSubmitted])

  // Auto-submit on timeout
  useEffect(() => {
    if (!session || session.status !== 'in_progress') return
    if (remainingSeconds <= 0 && !autoSubmitted) {
      void submitPaper(true)
    }
  }, [remainingSeconds, session, autoSubmitted, submitPaper])

  // Go back to list
  const goBack = () => {
    setDetail(null)
    setSession(null)
    setScoreResult(null)
    setAnswers({})
    setMessage('')
    setError('')
  }

  // Render question
  const renderQuestion = (question: Question, index: number) => {
    const userAnswer = answers[question.id] || ''
    const isReview = !!scoreResult
    const analysis = scoreResult?.question_analysis?.find((a) => a.question_id === question.id)

    return (
      <div key={question.id} className={`${panelClass} p-5 mb-4`}>
        <div className="flex items-start gap-3 mb-3">
          <span className="flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
            {index + 1}
          </span>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                {questionTypeLabels[question.question_type] || question.question_type}
              </span>
              <span className="text-xs text-slate-400">{question.score}分</span>
            </div>
            <p className="text-sm text-slate-900 leading-relaxed whitespace-pre-wrap">{question.content}</p>
          </div>
        </div>

        {/* Options for choice questions */}
        {(question.question_type === 'single_choice' || question.question_type === 'multiple_choice') && (
          <div className="ml-10 space-y-2">
            {(Array.isArray(question.options) ? question.options : []).map((opt: string, oi: number) => {
              const letter = optionLetters[oi]
              const isSelected = question.question_type === 'multiple_choice'
                ? userAnswer.includes(letter)
                : userAnswer === letter
              const isCorrect = isReview && analysis?.correct_answer?.includes(letter)
              const isWrong = isReview && isSelected && !isCorrect

              return (
                <label
                  key={oi}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition ${
                    isReview
                      ? isCorrect
                        ? 'border-green-300 bg-green-50'
                        : isWrong
                        ? 'border-red-300 bg-red-50'
                        : 'border-slate-200'
                      : isSelected
                      ? 'border-blue-400 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <input
                    type={question.question_type === 'multiple_choice' ? 'checkbox' : 'radio'}
                    name={`q_${question.id}`}
                    disabled={isReview || !session}
                    checked={isSelected}
                    onChange={() => {
                      if (isReview || !session) return
                      if (question.question_type === 'multiple_choice') {
                        const current = userAnswer.split('').filter(Boolean)
                        const next = current.includes(letter)
                          ? current.filter((c) => c !== letter)
                          : [...current, letter].sort()
                        void handleChoiceChange(question.id, next.join(''))
                      } else {
                        void handleChoiceChange(question.id, letter)
                      }
                    }}
                    className="accent-blue-600"
                  />
                  <span className="text-sm">
                    {letter}. {opt}
                  </span>
                </label>
              )
            })}
          </div>
        )}

        {/* Text input for other types */}
        {!['single_choice', 'multiple_choice'].includes(question.question_type) && (
          <div className="ml-10">
            <textarea
              value={userAnswer}
              disabled={isReview || !session}
              onChange={(e) => void handleAnswerChange(question.id, e.target.value)}
              placeholder={session ? '请输入答案...' : '开始考试后可作答'}
              className={`${fieldClass} min-h-[80px] resize-y`}
            />
          </div>
        )}

        {/* Review: show result */}
        {isReview && analysis && (
          <div className="ml-10 mt-3 space-y-2">
            <div className={`text-sm font-medium ${analysis.is_correct ? 'text-green-600' : 'text-red-600'}`}>
              {analysis.is_correct ? '✓ 正确' : '✗ 错误'}
              <span className="ml-2 text-slate-500">得分：{analysis.score}/{analysis.full_score}</span>
            </div>
            <div className="text-xs text-slate-600 bg-slate-50 rounded-lg p-3">
              <div><strong>正确答案：</strong>{analysis.correct_answer}</div>
              {analysis.explanation && <div className="mt-1"><strong>解析：</strong>{analysis.explanation}</div>}
            </div>
          </div>
        )}
      </div>
    )
  }

  // ===== Detail / Exam view =====
  if (detail) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <button onClick={goBack} className="text-sm text-blue-600 hover:text-blue-800 font-medium">
            ← 返回真题列表
          </button>
          {session && session.status === 'in_progress' && (
            <div className="flex items-center gap-4">
              <span className={`text-sm font-mono font-bold ${remainingSeconds < 300 ? 'text-red-600' : 'text-slate-700'}`}>
                剩余 {formatTime(remainingSeconds)}
              </span>
              <button
                onClick={() => submitPaper(false)}
                disabled={loading}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                交卷
              </button>
            </div>
          )}
        </div>

        {/* Paper info */}
        <div className={`${panelClass} p-6`}>
          <h2 className="text-lg font-bold text-slate-900 mb-2">{detail.name}</h2>
          <div className="flex flex-wrap gap-4 text-sm text-slate-600">
            <span>科目：{detail.subject_name}</span>
            <span>总分：{detail.total_score}分</span>
            <span>时长：{detail.duration}分钟</span>
            <span>题量：{detail.question_count}题</span>
            {detail.source && <span>来源：{detail.source}</span>}
          </div>
          {!session && !scoreResult && (
            <button
              onClick={startExam}
              disabled={loading}
              className="mt-4 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              开始答题
            </button>
          )}
        </div>

        {/* Score result banner */}
        {scoreResult && (
          <div className={`${panelClass} p-5 border-green-200 bg-green-50`}>
            <div className="text-lg font-bold text-green-800">
              考试得分：{scoreResult.score} / {scoreResult.total_score}
            </div>
            <div className="text-sm text-green-700 mt-1">
              正确率：{(scoreResult.accuracy * 100).toFixed(1)}% · 答对 {scoreResult.correct_count}/{scoreResult.total_count}
            </div>
          </div>
        )}

        {/* Error / Message */}
        {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        {message && <div className="rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-700">{message}</div>}

        {/* Questions */}
        <div>
          {detail.questions.map((q, i) => renderQuestion(q, i))}
        </div>

        {/* Bottom submit */}
        {session && session.status === 'in_progress' && (
          <div className="flex justify-center pb-8">
            <button
              onClick={() => submitPaper(false)}
              disabled={loading}
              className="rounded-lg bg-blue-600 px-8 py-3 text-base font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              确认交卷
            </button>
          </div>
        )}
      </div>
    )
  }

  // ===== List view =====
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-950">历年真题</h1>
        <p className="text-sm text-slate-500 mt-1">完整的自考历年真题，按科目/年份分类，支持在线答题与自动评分</p>
      </div>

      {/* Filters */}
      <div className={`${panelClass} p-5`}>
        {/* Type tabs */}
        <div className="flex gap-2 mb-4">
          {[
            { value: '' as PaperType, label: '全部' },
            { value: 'real' as PaperType, label: '📋 真题' },
            { value: 'mock' as PaperType, label: '📝 模拟题' },
          ].map((tab) => (
            <button
              key={tab.value}
              onClick={() => handlePaperTypeChange(tab.value)}
              className={`px-4 py-2 text-sm font-medium rounded-full transition ${
                filterPaperType === tab.value
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {/* Search */}
          <div>
            <label className={labelClass}>搜索</label>
            <div className="flex gap-1">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                placeholder="课程代码或名称"
                className={fieldClass}
              />
              <button
                onClick={handleSearch}
                className="flex-shrink-0 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
              >
                搜索
              </button>
            </div>
          </div>
          <div>
            <label className={labelClass}>科目</label>
            {user && enrolledCodes && enrolledCodes.size > 0 && (
              <div className="mb-2">
                <EnrolledSubjectToggle
                  onlyEnrolled={onlyEnrolled}
                  setOnlyEnrolled={setOnlyEnrolled}
                  hasEnrollments={enrolledCodes.size > 0}
                  isLoggedIn={!!user}
                />
              </div>
            )}
            <select
              value={filterSubjectId}
              onChange={(e) => handleSubjectChange(e.target.value)}
              className={fieldClass}
            >
              <option value="">全部科目</option>
              {subjects
                .filter((s) => !onlyEnrolled || !enrolledCodes || enrolledCodes.has(s.code))
                .map((s) => (
                <option key={s.subject_id} value={s.subject_id}>
                  {s.code} {s.name} ({s.paper_count}套)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>年份</label>
            <select
              value={filterYear}
              onChange={(e) => handleYearChange(e.target.value)}
              className={fieldClass}
            >
              <option value="">全部年份</option>
              {years.map((y) => (
                <option key={y} value={y}>{y}年</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <span className="text-sm text-slate-500">共 {total} 套{filterPaperType === 'real' ? '真题' : filterPaperType === 'mock' ? '模拟题' : '试卷'}</span>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {/* Loading */}
      {loading && <div className="text-center text-sm text-slate-500 py-8">加载中...</div>}

      {/* Paper cards */}
      {!loading && papers.length === 0 && (
        <div className="text-center text-sm text-slate-400 py-12">暂无真题数据</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {papers.map((paper) => (
          <div
            key={paper.id}
            onClick={() => openPaper(paper.id)}
            className={`${panelClass} p-5 cursor-pointer hover:border-blue-300 hover:shadow-md transition`}
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="text-sm font-bold text-slate-900 line-clamp-2 flex-1">{paper.name}</h3>
              <span className={`flex-shrink-0 ml-2 px-2 py-0.5 text-xs rounded-full font-medium ${
                paper.paper_type === 'real'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-amber-100 text-amber-700'
              }`}>
                {paper.paper_type === 'real' ? '真题' : '模拟'}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-slate-500">
              <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700">{paper.subject_name}</span>
              <span className="px-2 py-0.5 rounded bg-slate-100">{paper.year}年{paper.month}月</span>
              <span>{paper.total_score}分</span>
              <span>{paper.question_count}题</span>
              <span>{paper.duration}分钟</span>
            </div>
            {paper.province_name && (
              <div className="mt-2 text-xs text-slate-400">{paper.province_name}</div>
            )}
          </div>
        ))}
      </div>

      {/* Pagination */}
      <Pagination
        current={page}
        total={total}
        pageSize={12}
        onChange={(p) => void loadPapers(p)}
        className="pt-4"
      />
    </div>
  )
}

export default PastPaperPage
