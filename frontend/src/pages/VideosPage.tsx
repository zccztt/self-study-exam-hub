import React, { FormEvent, useEffect, useRef, useState } from 'react'
import { Chapter, subjectApi, Subject } from '../api/subject'
import { videoApi, VideoDetail, VideoSearchResult } from '../api/video'
import { enrollmentApi, EnrollmentListItem } from '../api/enrollment'
import Pagination from '../components/ui/Pagination'

const sourceLabels: Record<string, string> = {
  bilibili: 'B站',
  netease: '网易公开课',
  tencent: '腾讯课堂',
  youtube: 'YouTube',
  custom: '公开视频',
}

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
}

const formatDuration = (seconds?: number) => {
  if (!seconds) return '未知时长'
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  return `${minutes}:${remainSeconds.toString().padStart(2, '0')}`
}

const formatViews = (count: number) => {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  return `${count}`
}

const VideosPage: React.FC = () => {
  const abortRef = useRef<AbortController | null>(null)
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chapterId, setChapterId] = useState('')
  const [source, setSource] = useState('')
  const [keyword, setKeyword] = useState('')
  const [result, setResult] = useState<VideoSearchResult | null>(null)
  const [details, setDetails] = useState<Record<number, VideoDetail>>({})
  const [detailLoadingId, setDetailLoadingId] = useState<number | null>(null)
  const [favoriteStatus, setFavoriteStatus] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [enrolledSubjectIds, setEnrolledSubjectIds] = useState<number[]>([])
  const [enrolledFilter, setEnrolledFilter] = useState(false)

  const pageSize = 12
  const currentPage = result?.page || 1

  const loadVideos = async (page = 1) => {
    abortRef.current?.abort()
    abortRef.current = new AbortController()
    setLoading(true)
    setError('')
    try {
      const data = await videoApi.searchVideos({
        keyword: keyword.trim() || undefined,
        subject_id: subjectId ? Number(subjectId) : undefined,
        chapter_ids: chapterId ? [Number(chapterId)] : undefined,
        source: source || undefined,
        page,
        page_size: pageSize,
      }, abortRef.current.signal)
      setResult(data)
    } catch (err) {
      if (err instanceof Error && (err.name === 'AbortError' || err.message === 'canceled')) return
      setError(err instanceof Error ? err.message : '视频加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const initialize = async () => {
      try {
        const [subjectData, videoData, enrollmentData] = await Promise.all([
          subjectApi.list(),
          videoApi.searchVideos({ page: 1, page_size: pageSize }),
          enrollmentApi.listEnrollments().catch(() => [] as EnrollmentListItem[]),
        ])
        setSubjects(subjectData)
        setResult(videoData)

        // Pre-load enrolled subject IDs for filtering
        if (enrollmentData.length > 0) {
          try {
            const ids = await enrollmentApi.getRemainingSubjects(enrollmentData[0].id)
            setEnrolledSubjectIds(ids)
            if (ids.length > 0) {
              setEnrolledFilter(true)
              setSubjectId(String(ids[0]))
            }
          } catch {
            // ignore
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '初始化视频中心失败')
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
    void loadVideos(1)
  }

  const addFavorite = async (videoId: number) => {
    setFavoriteStatus((current) => ({ ...current, [videoId]: '保存中' }))
    try {
      await videoApi.addToFavorites(videoId)
      setFavoriteStatus((current) => ({ ...current, [videoId]: '已收藏' }))
    } catch (err) {
      setFavoriteStatus((current) => ({
        ...current,
        [videoId]: err instanceof Error ? err.message : '收藏失败',
      }))
    }
  }

  const toggleDetail = async (videoId: number) => {
    if (details[videoId]) {
      const nextDetails = { ...details }
      delete nextDetails[videoId]
      setDetails(nextDetails)
      return
    }

    setDetailLoadingId(videoId)
    setError('')
    try {
      const detail = await videoApi.getVideoDetail(videoId)
      setDetails((current) => ({ ...current, [videoId]: detail }))
    } catch (err) {
      setError(err instanceof Error ? err.message : '视频详情加载失败')
    } finally {
      setDetailLoadingId(null)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="text-sm font-medium text-blue-600">真实资源链接</div>
        <h1 className="mt-1 text-3xl font-bold text-slate-950">资源中心</h1>
        <p className="mt-2 text-sm text-slate-500">优先展示本地真实视频；本地无匹配时线上实时搜索公开视频并保存链接。</p>
      </div>

      <form onSubmit={handleSearch} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
        {enrolledSubjectIds.length > 0 && (
          <div className="mb-3 flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-blue-600 cursor-pointer">
              <input
                type="checkbox"
                checked={enrolledFilter}
                onChange={(e) => setEnrolledFilter(e.target.checked)}
                className="rounded"
              />
              只显示我的报考科目
            </label>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <select
            value={subjectId}
            onChange={(event) => setSubjectId(event.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">全部科目</option>
            {subjects
              .filter((subject) => !enrolledFilter || enrolledSubjectIds.includes(subject.id))
              .map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </select>
          <select
            value={source}
            onChange={(event) => setSource(event.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">全部来源</option>
            {Object.entries(sourceLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
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
          <input
            type="text"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索视频..."
            className="px-4 py-2 border border-gray-300 rounded-lg"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-60"
          >
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>
      </form>

      {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</div>}

      <div className="mb-4 text-sm text-gray-600">
        {result?.online_saved_count ? `线上补充并保存 ${result.online_saved_count} 个` : ''}
      </div>
      {result?.message && <div className="mb-4 rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-700">{result.message}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {(result?.items || []).map((video) => {
          const detail = details[video.id]
          return (
            <div key={video.id} className="bg-white rounded-lg shadow overflow-hidden hover:shadow-lg transition-shadow">
              <div className="aspect-video bg-gray-200 flex items-center justify-center overflow-hidden">
                {video.thumbnail ? (
                  <img src={video.thumbnail} alt={video.title} className="h-full w-full object-cover" />
                ) : (
                  <span className="text-4xl">🎬</span>
                )}
              </div>
              <div className="p-4">
                <h3 className="font-semibold mb-2 line-clamp-2">{video.title}</h3>
                <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600 mb-2">
                  <span>{sourceLabels[video.source] || video.source}</span>
                  <span>{formatDuration(video.duration)}</span>
                  <span>{formatViews(video.view_count)} 次观看</span>
                </div>
                {video.author && <div className="text-sm text-gray-500 mb-2">{video.author}</div>}
                <div className="flex flex-wrap gap-1 mb-3">
                  {video.tags.map((tag) => (
                    <span key={`${video.id}-${tag}`} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                      {tag}
                    </span>
                  ))}
                </div>
                {video.description && <p className="text-sm text-gray-600 line-clamp-3 mb-3">{video.description}</p>}
                <div className="flex gap-2">
                  <a
                    href={video.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm text-center"
                  >
                    打开视频
                  </a>
                  <button
                    type="button"
                    onClick={() => void toggleDetail(video.id)}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 text-sm"
                  >
                    {detail ? '收起' : detailLoadingId === video.id ? '加载中' : '详情'}
                  </button>
                  <button
                    type="button"
                    onClick={() => void addFavorite(video.id)}
                    className="px-4 py-2 border border-blue-500 text-blue-500 rounded hover:bg-blue-50 text-sm"
                  >
                    {favoriteStatus[video.id] || '收藏'}
                  </button>
                </div>

                {detail && (
                  <div className="mt-4 rounded-lg bg-gray-50 p-4">
                    {detail.description && <p className="mb-3 text-sm text-gray-700">{detail.description}</p>}
                    <div className="mb-3 text-sm text-gray-600">
                      关联训练题 {detail.related_questions.length} 道
                    </div>
                    <div className="space-y-2">
                      {detail.related_questions.map((question) => (
                        <div key={question.id} className="rounded border border-gray-200 bg-white p-3 text-sm">
                          <div className="mb-1 flex flex-wrap gap-2">
                            <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                              {questionTypeLabels[question.question_type] || question.question_type}
                            </span>
                            {question.year && (
                              <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">
                                {question.year}年
                              </span>
                            )}
                            <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                              {question.score} 分
                            </span>
                          </div>
                          <div className="line-clamp-3 text-gray-800">{question.content}</div>
                        </div>
                      ))}
                      {detail.related_questions.length === 0 && (
                        <div className="text-sm text-gray-500">暂无关联训练题</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {result && result.items.length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">没有找到匹配视频</div>
      )}

      <Pagination
        current={currentPage}
        total={result?.total || 0}
        pageSize={pageSize}
        loading={loading}
        onChange={(page) => void loadVideos(page)}
        className="mt-8"
      />
    </div>
  )
}

export default VideosPage
