import React, { FormEvent, useEffect, useState } from 'react'
import { questionApi, Question, QuestionSearchResult, SearchQuestionsParams } from '../api/question'
import { Chapter, subjectApi, Subject } from '../api/subject'

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
  online_resource: '线上题源',
}

const difficultyLabels: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

const optionLetters = ['A', 'B', 'C', 'D', 'E', 'F']

const QuestionsPage: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [keyword, setKeyword] = useState('')
  const [subjectQuery, setSubjectQuery] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chapterId, setChapterId] = useState('')
  const [year, setYear] = useState('')
  const [questionType, setQuestionType] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [highFrequency, setHighFrequency] = useState(false)
  const [onlineSearch, setOnlineSearch] = useState(true)
  const [result, setResult] = useState<QuestionSearchResult | null>(null)
  const [details, setDetails] = useState<Record<number, Question>>({})
  const [favoriteStatus, setFavoriteStatus] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const pageSize = 10
  const currentPage = result?.page || 1
  const totalPages = Math.max(1, Math.ceil((result?.total || 0) / pageSize))

  const buildParams = (page: number): SearchQuestionsParams => {
    const trimmedSubjectQuery = subjectQuery.trim()
    const isCourseCode = /^\d{3,5}$/.test(trimmedSubjectQuery)
    return {
      keyword: keyword.trim() || undefined,
      subject_id: subjectId ? Number(subjectId) : undefined,
      subject_code: !subjectId && isCourseCode ? trimmedSubjectQuery : undefined,
      subject_query: !subjectId && trimmedSubjectQuery && !isCourseCode ? trimmedSubjectQuery : undefined,
      years: year ? [Number(year)] : undefined,
      question_types: questionType ? [questionType] : undefined,
      difficulty: difficulty || undefined,
      chapter_ids: chapterId ? [Number(chapterId)] : undefined,
      high_frequency: highFrequency || undefined,
      online_search: onlineSearch,
      page,
      page_size: pageSize,
    }
  }

  const loadQuestions = async (page = 1) => {
    setLoading(true)
    setError('')
    try {
      const data = await questionApi.searchQuestions(buildParams(page))
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '题目加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const initialize = async () => {
      try {
        const [subjectData, questionData] = await Promise.all([
          subjectApi.list(),
          questionApi.searchQuestions({ page: 1, page_size: pageSize }),
        ])
        setSubjects(subjectData)
        setResult(questionData)
      } catch (err) {
        setError(err instanceof Error ? err.message : '初始化题库失败')
      }
    }
    void initialize()
  }, [])

  useEffect(() => {
    const loadChapters = async () => {
      setChapterId('')
      if (!subjectId) {
        setChapters([])
        return
      }
      try {
        const detail = await subjectApi.detail(Number(subjectId))
        setChapters(detail.chapters)
      } catch (err) {
        setError(err instanceof Error ? err.message : '章节加载失败')
      }
    }
    void loadChapters()
  }, [subjectId])

  const handleSearch = (event: FormEvent) => {
    event.preventDefault()
    void loadQuestions(1)
  }

  const toggleDetail = async (questionId: number) => {
    if (details[questionId]) {
      const nextDetails = { ...details }
      delete nextDetails[questionId]
      setDetails(nextDetails)
      return
    }

    try {
      const detail = await questionApi.getQuestionDetail(questionId)
      setDetails((current) => ({ ...current, [questionId]: detail }))
    } catch (err) {
      setError(err instanceof Error ? err.message : '题目详情加载失败')
    }
  }

  const addFavorite = async (questionId: number) => {
    setFavoriteStatus((current) => ({ ...current, [questionId]: '保存中' }))
    try {
      await questionApi.addToFavorites(questionId)
      setFavoriteStatus((current) => ({ ...current, [questionId]: '已收藏' }))
    } catch (err) {
      setFavoriteStatus((current) => ({
        ...current,
        [questionId]: err instanceof Error ? err.message : '收藏失败',
      }))
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">题库搜索</h1>

      <form onSubmit={handleSearch} className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <input
            type="text"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="输入关键词搜索题目..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            type="submit"
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-60"
            disabled={loading}
          >
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <input
            type="text"
            value={subjectQuery}
            onChange={(event) => {
              setSubjectQuery(event.target.value)
              if (event.target.value.trim()) setSubjectId('')
            }}
            placeholder="课程代码或科目名称，如 15043 / 近现代史"
            className="px-4 py-2 border border-gray-300 rounded-lg"
          />
          <select
            value={subjectId}
            onChange={(event) => {
              setSubjectId(event.target.value)
              if (event.target.value) setSubjectQuery('')
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">全部科目</option>
            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.code} {subject.name}
              </option>
            ))}
          </select>
          <select
            value={year}
            onChange={(event) => setYear(event.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">全部年份</option>
            {[2026].map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select
            value={chapterId}
            onChange={(event) => setChapterId(event.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
            disabled={!subjectId}
          >
            <option value="">全部章节</option>
            {chapters.map((chapter) => (
              <option key={chapter.id} value={chapter.id}>
                {chapter.name}
              </option>
            ))}
          </select>
          <select
            value={questionType}
            onChange={(event) => setQuestionType(event.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">全部题型</option>
            {Object.entries(questionTypeLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">全部难度</option>
            {Object.entries(difficultyLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg bg-white">
            <input
              type="checkbox"
              checked={highFrequency}
              onChange={(event) => setHighFrequency(event.target.checked)}
            />
            <span className="text-sm">只看高频</span>
          </label>
          <label className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg bg-white">
            <input
              type="checkbox"
              checked={onlineSearch}
              onChange={(event) => setOnlineSearch(event.target.checked)}
            />
            <span className="text-sm">线上实时补充</span>
          </label>
        </div>
      </form>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}

      <div className="mb-4 text-sm text-gray-600">
        共 {result?.total || 0} 条结果，当前第 {currentPage} / {totalPages} 页
        {typeof result?.local_count === 'number' && ` · 本地题库 ${result.local_count} 条`}
        {typeof result?.online_count === 'number' && ` · 线上补充 ${result.online_count} 条`}
      </div>

      <div className="space-y-4">
        {(result?.items || []).map((question) => {
          const detail = details[question.id]
          return (
            <div key={question.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                      {questionTypeLabels[question.question_type] || question.question_type}
                    </span>
                    {question.year && (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                        {question.year}年{question.month ? `${question.month}月` : ''}
                      </span>
                    )}
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded">
                      {difficultyLabels[question.difficulty] || question.difficulty}
                    </span>
                    <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                      频次 {question.frequency}
                    </span>
                    {(question.subject_code || question.subject_name) && (
                      <span className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs rounded">
                        {question.subject_code ? `${question.subject_code} ` : ''}
                        {question.subject_name || ''}
                      </span>
                    )}
                    {question.is_online && (
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                        实时搜索
                      </span>
                    )}
                  </div>
                  <p className="text-gray-900 mb-4 whitespace-pre-wrap">{question.content}</p>
                  {question.options.length > 0 && (
                    <div className="text-sm text-gray-600 space-y-1">
                      {question.options.map((option, index) => (
                        <div key={`${question.id}-${optionLetters[index]}`}>
                          {optionLetters[index]}. {option}
                        </div>
                      ))}
                    </div>
                  )}

                  {detail && (
                    <div className="mt-4 rounded-lg bg-gray-50 p-4 text-sm">
                      <div className="font-medium text-gray-900">答案：{detail.answer}</div>
                      {detail.explanation && (
                        <div className="mt-2 text-gray-700 whitespace-pre-wrap">{detail.explanation}</div>
                      )}
                    </div>
                  )}
                  {question.source && (
                    <div className="mt-4 text-sm text-gray-500">
                      来源：{question.source}
                      {question.source_url && (
                        <>
                          {' · '}
                          <a
                            href={question.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            打开题源
                          </a>
                        </>
                      )}
                    </div>
                  )}
                </div>
                <div className="flex flex-row gap-2 lg:ml-4 lg:flex-col">
                  {question.is_online ? (
                    question.source_url && (
                      <a
                        href={question.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="px-4 py-2 border border-blue-500 text-blue-500 rounded hover:bg-blue-50 text-sm"
                      >
                        打开链接
                      </a>
                    )
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => void toggleDetail(question.id)}
                        className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 text-sm"
                      >
                        {detail ? '收起答案' : '查看答案'}
                      </button>
                      <button
                        type="button"
                        onClick={() => void addFavorite(question.id)}
                        className="px-4 py-2 border border-blue-500 text-blue-500 rounded hover:bg-blue-50 text-sm"
                      >
                        {favoriteStatus[question.id] || '收藏'}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {result && result.items.length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">没有找到匹配题目</div>
      )}

      <div className="mt-8 flex justify-center gap-2">
        <button
          type="button"
          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={currentPage <= 1 || loading}
          onClick={() => void loadQuestions(currentPage - 1)}
        >
          上一页
        </button>
        <button className="px-4 py-2 bg-blue-500 text-white rounded" type="button">
          {currentPage}
        </button>
        <button
          type="button"
          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={currentPage >= totalPages || loading}
          onClick={() => void loadQuestions(currentPage + 1)}
        >
          下一页
        </button>
      </div>
    </div>
  )
}

export default QuestionsPage
