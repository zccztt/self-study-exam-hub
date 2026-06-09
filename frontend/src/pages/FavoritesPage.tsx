import React, { FormEvent, useEffect, useState } from 'react'
import { examApi, WrongQuestionItem } from '../api/exam'
import { questionApi, Question } from '../api/question'
import { sessionStore } from '../api/session'
import { subjectApi, Subject } from '../api/subject'
import { videoApi, VideoItem } from '../api/video'

type FavoriteTab = 'questions' | 'videos' | 'wrong'

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
}

const FavoritesPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<FavoriteTab>('questions')
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [questions, setQuestions] = useState<Question[]>([])
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [wrongQuestions, setWrongQuestions] = useState<WrongQuestionItem[]>([])
  const [wrongTotal, setWrongTotal] = useState(0)
  const [wrongKeyword, setWrongKeyword] = useState('')
  const [wrongSubjectId, setWrongSubjectId] = useState('')
  const [wrongMastered, setWrongMastered] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadFavorites = async () => {
    setLoading(true)
    setError('')
    try {
      const userId = sessionStore.getUserId()
      const [subjectData, questionData, videoData, wrongData] = await Promise.all([
        subjectApi.list(),
        questionApi.getFavorites(userId, 1, 50),
        videoApi.getFavorites(userId, 1, 50),
        examApi.getWrongQuestions({ user_id: userId, page: 1, page_size: 50 }),
      ])
      setSubjects(subjectData)
      setQuestions(questionData.items)
      setVideos(videoData.items)
      setWrongQuestions(wrongData.items)
      setWrongTotal(wrongData.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '收藏数据加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadFavorites()
  }, [])

  const loadWrongQuestions = async (event?: FormEvent) => {
    event?.preventDefault()
    setLoading(true)
    setError('')
    try {
      const userId = sessionStore.getUserId()
      const data = await examApi.getWrongQuestions({
        user_id: userId,
        keyword: wrongKeyword.trim() || undefined,
        subject_id: wrongSubjectId ? Number(wrongSubjectId) : undefined,
        is_mastered: wrongMastered ? wrongMastered === 'true' : undefined,
        page: 1,
        page_size: 50,
      })
      setWrongQuestions(data.items)
      setWrongTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '错题本加载失败')
    } finally {
      setLoading(false)
    }
  }

  const removeQuestion = async (questionId: number) => {
    setError('')
    try {
      await questionApi.removeFromFavorites(questionId, sessionStore.getUserId())
      setQuestions((current) => current.filter((question) => question.id !== questionId))
    } catch (err) {
      setError(err instanceof Error ? err.message : '取消题目收藏失败')
    }
  }

  const removeVideo = async (videoId: number) => {
    setError('')
    try {
      await videoApi.removeFromFavorites(videoId, sessionStore.getUserId())
      setVideos((current) => current.filter((video) => video.id !== videoId))
    } catch (err) {
      setError(err instanceof Error ? err.message : '取消视频收藏失败')
    }
  }

  const setWrongMastery = async (questionId: number, isMastered: boolean) => {
    setError('')
    try {
      const updated = await examApi.updateWrongQuestion(questionId, { is_mastered: isMastered }, sessionStore.getUserId())
      setWrongQuestions((current) =>
        current.map((item) => (item.question_id === questionId ? updated : item)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新错题状态失败')
    }
  }

  const removeWrong = async (questionId: number) => {
    setError('')
    try {
      await examApi.removeWrongQuestion(questionId, sessionStore.getUserId())
      setWrongQuestions((current) => current.filter((item) => item.question_id !== questionId))
      setWrongTotal((current) => Math.max(0, current - 1))
    } catch (err) {
      setError(err instanceof Error ? err.message : '移除错题失败')
    }
  }

  const exportWrongBook = async (format: 'markdown' | 'csv' | 'word') => {
    setError('')
    try {
      const blob = await examApi.exportWrongQuestions(
        {
          user_id: sessionStore.getUserId(),
          keyword: wrongKeyword.trim() || undefined,
          subject_id: wrongSubjectId ? Number(wrongSubjectId) : undefined,
          is_mastered: wrongMastered ? wrongMastered === 'true' : undefined,
          page: 1,
          page_size: 1000,
        },
        format,
      )
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `wrong_questions.${format === 'word' ? 'doc' : format === 'markdown' ? 'md' : 'csv'}`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : '错题导出失败')
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">我的收藏</h1>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}
      {loading && <div className="mb-4 rounded-lg bg-blue-50 px-4 py-3 text-blue-700">收藏加载中...</div>}

      <div className="mb-6 flex rounded-lg border border-gray-200 bg-white p-1">
        <button
          type="button"
          onClick={() => setActiveTab('questions')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium ${
            activeTab === 'questions' ? 'bg-blue-500 text-white' : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          题目收藏 ({questions.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('videos')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium ${
            activeTab === 'videos' ? 'bg-blue-500 text-white' : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          视频收藏 ({videos.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('wrong')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium ${
            activeTab === 'wrong' ? 'bg-blue-500 text-white' : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          错题本 ({wrongTotal})
        </button>
      </div>

      {activeTab === 'questions' && (
        <div className="space-y-4">
          {questions.map((question) => (
            <div key={question.id} className="rounded-lg bg-white p-6 shadow">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="rounded bg-blue-100 px-2 py-1 text-xs text-blue-700">
                  {questionTypeLabels[question.question_type] || question.question_type}
                </span>
                {question.year && (
                  <span className="rounded bg-green-100 px-2 py-1 text-xs text-green-700">
                    {question.year}年{question.month ? `${question.month}月` : ''}
                  </span>
                )}
              </div>
              <div className="whitespace-pre-wrap text-gray-900">{question.content}</div>
              <button
                type="button"
                onClick={() => void removeQuestion(question.id)}
                className="mt-4 rounded border border-red-500 px-4 py-2 text-sm text-red-500 hover:bg-red-50"
              >
                取消收藏
              </button>
            </div>
          ))}
          {questions.length === 0 && !loading && (
            <div className="rounded-lg bg-white p-8 text-center text-gray-500 shadow">暂无题目收藏</div>
          )}
        </div>
      )}

      {activeTab === 'videos' && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {videos.map((video) => (
            <div key={video.id} className="rounded-lg bg-white p-6 shadow">
              <h2 className="font-semibold">{video.title}</h2>
              {video.description && <p className="mt-2 line-clamp-2 text-sm text-gray-600">{video.description}</p>}
              <div className="mt-4 flex gap-2">
                <a
                  href={video.url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded bg-blue-500 px-4 py-2 text-sm text-white hover:bg-blue-600"
                >
                  打开视频
                </a>
                <button
                  type="button"
                  onClick={() => void removeVideo(video.id)}
                  className="rounded border border-red-500 px-4 py-2 text-sm text-red-500 hover:bg-red-50"
                >
                  取消收藏
                </button>
              </div>
            </div>
          ))}
          {videos.length === 0 && !loading && (
            <div className="rounded-lg bg-white p-8 text-center text-gray-500 shadow">暂无视频收藏</div>
          )}
        </div>
      )}

      {activeTab === 'wrong' && (
        <div className="space-y-4">
          <form onSubmit={loadWrongQuestions} className="grid grid-cols-1 gap-3 rounded-lg bg-white p-4 shadow md:grid-cols-4">
            <input
              type="text"
              value={wrongKeyword}
              onChange={(event) => setWrongKeyword(event.target.value)}
              className="rounded border border-gray-300 px-3 py-2"
              placeholder="搜索错题"
            />
            <select
              value={wrongSubjectId}
              onChange={(event) => setWrongSubjectId(event.target.value)}
              className="rounded border border-gray-300 px-3 py-2"
            >
              <option value="">全部科目</option>
              {subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {subject.name}
                </option>
              ))}
            </select>
            <select
              value={wrongMastered}
              onChange={(event) => setWrongMastered(event.target.value)}
              className="rounded border border-gray-300 px-3 py-2"
            >
              <option value="">全部状态</option>
              <option value="false">未掌握</option>
              <option value="true">已掌握</option>
            </select>
            <button
              type="submit"
              disabled={loading}
              className="rounded bg-blue-500 px-4 py-2 text-sm text-white hover:bg-blue-600 disabled:opacity-60"
            >
              {loading ? '筛选中...' : '筛选'}
            </button>
          </form>
          <div className="flex flex-wrap gap-2 rounded-lg bg-white p-4 shadow">
            <button
              type="button"
              onClick={() => void exportWrongBook('markdown')}
              className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              导出 Markdown
            </button>
            <button
              type="button"
              onClick={() => void exportWrongBook('csv')}
              className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              导出 CSV
            </button>
            <button
              type="button"
              onClick={() => void exportWrongBook('word')}
              className="rounded border border-blue-500 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50"
            >
              导出 Word
            </button>
          </div>

          {wrongQuestions.map((item) => (
            <div key={item.id} className="rounded-lg bg-white p-6 shadow">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="rounded bg-blue-100 px-2 py-1 text-xs text-blue-700">
                  {questionTypeLabels[item.question.question_type] || item.question.question_type}
                </span>
                <span className={item.is_mastered ? 'rounded bg-green-100 px-2 py-1 text-xs text-green-700' : 'rounded bg-red-100 px-2 py-1 text-xs text-red-700'}>
                  {item.is_mastered ? '已掌握' : '未掌握'}
                </span>
                <span className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-600">
                  错误 {item.wrong_count} 次
                </span>
                {item.last_wrong_at && (
                  <span className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-600">
                    {new Date(item.last_wrong_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <div className="whitespace-pre-wrap text-gray-900">{item.question.content}</div>
              {item.question.options.length > 0 && (
                <div className="mt-3 space-y-1 text-sm text-gray-600">
                  {item.question.options.map((option, index) => (
                    <div key={`${item.question_id}-${index}`}>{String.fromCharCode(65 + index)}. {option}</div>
                  ))}
                </div>
              )}
              <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                <div className="rounded bg-gray-50 p-3">你的答案：{item.user_answer || '-'}</div>
                <div className="rounded bg-gray-50 p-3">参考答案：{item.question.answer || '-'}</div>
              </div>
              {item.question.explanation && (
                <div className="mt-3 rounded bg-blue-50 p-3 text-sm text-blue-800">{item.question.explanation}</div>
              )}
              {item.knowledge_points.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.knowledge_points.map((point) => (
                    <span key={point.id} className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-700">
                      {point.name}
                    </span>
                  ))}
                </div>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void setWrongMastery(item.question_id, !item.is_mastered)}
                  className="rounded border border-blue-500 px-4 py-2 text-sm text-blue-500 hover:bg-blue-50"
                >
                  {item.is_mastered ? '标记未掌握' : '标记已掌握'}
                </button>
                <button
                  type="button"
                  onClick={() => void removeWrong(item.question_id)}
                  className="rounded border border-red-500 px-4 py-2 text-sm text-red-500 hover:bg-red-50"
                >
                  移除错题
                </button>
              </div>
            </div>
          ))}

          {wrongQuestions.length === 0 && !loading && (
            <div className="rounded-lg bg-white p-8 text-center text-gray-500 shadow">暂无错题记录</div>
          )}
        </div>
      )}
    </div>
  )
}

export default FavoritesPage
