import React, { FormEvent, useEffect, useState } from 'react'
import { examApi, WrongQuestionItem } from '../api/exam'
import { questionApi, Question } from '../api/question'
import { sessionStore } from '../api/session'
import { videoApi, VideoItem } from '../api/video'
import EnrolledSubjectToggle from '../components/EnrolledSubjectToggle'
import { Badge, Button, Card, EmptyState, PageHeader, Pagination, Select, useToast } from '../components/ui'
import { useEnrolledSubjectFilter } from '../hooks/useEnrolledSubjectFilter'

type FavoriteTab = 'questions' | 'videos' | 'wrong'

const questionTypeLabels: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
  case: '案例题',
}

const tabConfig: { key: FavoriteTab; label: string; icon: string }[] = [
  { key: 'questions', label: '题目收藏', icon: '📝' },
  { key: 'videos', label: '视频收藏', icon: '🎬' },
  { key: 'wrong', label: '错题本', icon: '❌' },
]

const FavoritesPage: React.FC = () => {
  const toast = useToast()
  const [activeTab, setActiveTab] = useState<FavoriteTab>('questions')
  const { subjects, onlyEnrolled, setOnlyEnrolled, hasEnrollments, isLoggedIn } = useEnrolledSubjectFilter()
  const [questions, setQuestions] = useState<Question[]>([])
  const [questionTotal, setQuestionTotal] = useState(0)
  const [questionPage, setQuestionPage] = useState(1)
  const [questionDetails, setQuestionDetails] = useState<Record<number, Question>>({})
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [videoTotal, setVideoTotal] = useState(0)
  const [videoPage, setVideoPage] = useState(1)
  const [wrongQuestions, setWrongQuestions] = useState<WrongQuestionItem[]>([])
  const [wrongTotal, setWrongTotal] = useState(0)
  const [wrongPage, setWrongPage] = useState(1)
  const [wrongKeyword, setWrongKeyword] = useState('')
  const [wrongSubjectId, setWrongSubjectId] = useState('')
  const [wrongMastered, setWrongMastered] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [wrongDrafts, setWrongDrafts] = useState<Record<number, { note: string; tags: string }>>({})
  const [questionDrafts, setQuestionDrafts] = useState<Record<number, { note: string; tags: string }>>({})
  const pageSize = 20

  const loadFavorites = async () => {
    setLoading(true)
    setError('')
    try {
      const userId = sessionStore.getUserId()
      const [questionData, videoData, wrongData] = await Promise.all([
        questionApi.getFavorites(userId, 1, pageSize),
        videoApi.getFavorites(userId, 1, pageSize),
        examApi.getWrongQuestions({ user_id: userId, page: 1, page_size: pageSize }),
      ])
      setQuestions(questionData.items)
      setQuestionTotal(questionData.total)
      setQuestionDrafts(
        Object.fromEntries(
          questionData.items.map((item) => [
            item.id,
            { note: item.favorite_note || '', tags: (item.favorite_tags || []).join(', ') },
          ]),
        ),
      )
      setVideos(videoData.items)
      setVideoTotal(videoData.total)
      setWrongQuestions(wrongData.items)
      setWrongTotal(wrongData.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '收藏数据加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadFavorites() }, [])

  const loadQuestionFavorites = async (page: number) => {
    setLoading(true)
    setError('')
    try {
      const data = await questionApi.getFavorites(sessionStore.getUserId(), page, pageSize)
      setQuestions(data.items)
      setQuestionTotal(data.total)
      setQuestionPage(page)
    } catch (err) {
      setError(err instanceof Error ? err.message : '题目收藏加载失败')
    } finally {
      setLoading(false)
    }
  }

  const loadVideoFavorites = async (page: number) => {
    setLoading(true)
    setError('')
    try {
      const data = await videoApi.getFavorites(sessionStore.getUserId(), page, pageSize)
      setVideos(data.items)
      setVideoTotal(data.total)
      setVideoPage(page)
    } catch (err) {
      setError(err instanceof Error ? err.message : '视频收藏加载失败')
    } finally {
      setLoading(false)
    }
  }

  const loadWrongQuestions = async (event?: FormEvent, page = 1) => {
    event?.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await examApi.getWrongQuestions({
        user_id: sessionStore.getUserId(),
        keyword: wrongKeyword.trim() || undefined,
        subject_id: wrongSubjectId ? Number(wrongSubjectId) : undefined,
        is_mastered: wrongMastered ? wrongMastered === 'true' : undefined,
        page,
        page_size: pageSize,
      })
      setWrongQuestions(data.items)
      setWrongTotal(data.total)
      setWrongPage(page)
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
      setQuestions((current) => current.filter((q) => q.id !== questionId))
      setQuestionDrafts((current) => { const next = { ...current }; delete next[questionId]; return next })
      setQuestionTotal((current) => Math.max(0, current - 1))
    } catch (err) {
      setError(err instanceof Error ? err.message : '取消题目收藏失败')
    }
  }

  const toggleQuestionDetail = async (questionId: number) => {
    if (questionDetails[questionId]) {
      setQuestionDetails((current) => { const next = { ...current }; delete next[questionId]; return next })
      return
    }
    try {
      const detail = await questionApi.getQuestionDetail(questionId)
      setQuestionDetails((current) => ({ ...current, [questionId]: detail }))
    } catch (err) {
      setError(err instanceof Error ? err.message : '题目解析加载失败')
    }
  }

  const saveQuestionFavorite = async (question: Question) => {
    setError('')
    try {
      const draft = questionDrafts[question.id] || { note: question.favorite_note || '', tags: (question.favorite_tags || []).join(', ') }
      await questionApi.addToFavorites(
        question.id,
        draft.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean),
      )
      setQuestions((current) => current.map((item) =>
        item.id === question.id ? { ...item, favorite_note: draft.note.trim(), favorite_tags: draft.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean) } : item,
      ))
      toast.success('题目收藏已保存')
    } catch (err) {
      setError(err instanceof Error ? err.message : '题目收藏保存失败')
    }
  }

  const removeVideo = async (videoId: number) => {
    setError('')
    try {
      await videoApi.removeFromFavorites(videoId, sessionStore.getUserId())
      setVideos((current) => current.filter((v) => v.id !== videoId))
      setVideoTotal((current) => Math.max(0, current - 1))
    } catch (err) {
      setError(err instanceof Error ? err.message : '取消视频收藏失败')
    }
  }

  const setWrongMastery = async (questionId: number, isMastered: boolean) => {
    setError('')
    try {
      const updated = await examApi.updateWrongQuestion(questionId, { is_mastered: isMastered }, sessionStore.getUserId())
      setWrongQuestions((current) => current.map((item) => (item.question_id === questionId ? updated : item)))
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新错题状态失败')
    }
  }

  const saveWrongNotes = async (item: WrongQuestionItem) => {
    setError(''); setMessage('')
    const draft = wrongDrafts[item.question_id] || { note: item.note || '', tags: (item.tags || []).join(', ') }
    try {
      const updated = await examApi.updateWrongQuestion(
        item.question_id,
        { note: draft.note.trim(), tags: draft.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean) },
        sessionStore.getUserId(),
      )
      setWrongQuestions((current) => current.map((c) => (c.question_id === item.question_id ? updated : c)))
      toast.success('错题笔记已保存')
    } catch (err) {
      setError(err instanceof Error ? err.message : '错题笔记保存失败')
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
        { user_id: sessionStore.getUserId(), keyword: wrongKeyword.trim() || undefined, subject_id: wrongSubjectId ? Number(wrongSubjectId) : undefined, is_mastered: wrongMastered ? wrongMastered === 'true' : undefined, page: 1, page_size: 1000 },
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
    <div className="space-y-6">
      <PageHeader
        tag="收藏 · 错题 · 掌握状态"
        title="我的收藏"
        description="集中管理收藏题目、资源和错题记录，支持标记掌握、筛选薄弱题。"
      />

      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 animate-fade-in">{error}</div>}
      {message && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 animate-fade-in">{message}</div>}

      {/* Tab bar */}
      <div className="flex rounded-xl border border-slate-200 bg-white p-1.5 shadow-sm">
        {tabConfig.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-150 ${
              activeTab === tab.key
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            <span className="mr-1.5">{tab.icon}</span>
            {tab.label} ({tab.key === 'questions' ? questionTotal : tab.key === 'videos' ? videoTotal : wrongTotal})
          </button>
        ))}
      </div>

      {/* Questions Tab */}
      {activeTab === 'questions' && (
        <div className="space-y-4">
          {questions.map((question) => (
            <Card key={question.id}>
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <Badge variant="primary">{questionTypeLabels[question.question_type] || question.question_type}</Badge>
                {question.year && <Badge variant="success">{question.year}年{question.month ? `${question.month}月` : ''}</Badge>}
              </div>
              <div className="whitespace-pre-wrap text-slate-900 leading-7">{question.content}</div>
              {question.favorite_tags && question.favorite_tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {question.favorite_tags.map((tag) => <Badge key={`${question.id}-${tag}`} variant="warning" pill>{tag}</Badge>)}
                </div>
              )}
              {question.favorite_note && (
                <div className="mt-3 rounded-lg bg-slate-50 border border-slate-200 px-4 py-2.5 text-sm text-slate-700">备注：{question.favorite_note}</div>
              )}
              <div className="mt-4 grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">收藏备注</label>
                  <textarea
                    value={questionDrafts[question.id]?.note ?? question.favorite_note ?? ''}
                    onChange={(e) => setQuestionDrafts((c) => ({ ...c, [question.id]: { note: e.target.value, tags: c[question.id]?.tags ?? (question.favorite_tags || []).join(', ') } }))}
                    rows={3}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                    placeholder="记录收藏理由、复习提醒或知识点"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">收藏标签</label>
                  <input
                    value={questionDrafts[question.id]?.tags ?? (question.favorite_tags || []).join(', ')}
                    onChange={(e) => setQuestionDrafts((c) => ({ ...c, [question.id]: { note: c[question.id]?.note ?? question.favorite_note ?? '', tags: e.target.value } }))}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                    placeholder="例如：高频, 易错, 重点"
                  />
                  <Button variant="secondary" size="sm" className="mt-3" onClick={() => void saveQuestionFavorite(question)}>保存收藏</Button>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => void toggleQuestionDetail(question.id)}>
                  {questionDetails[question.id] ? '收起解析' : '查看解析'}
                </Button>
                <Button variant="danger" size="sm" onClick={() => void removeQuestion(question.id)}>取消收藏</Button>
              </div>
              {questionDetails[question.id] && (
                <div className="mt-4 space-y-2 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm animate-scale-in">
                  <div><span className="font-semibold">参考答案：</span>{questionDetails[question.id].answer || '-'}</div>
                  <div className="leading-6 text-emerald-900">{questionDetails[question.id].explanation || '暂无解析'}</div>
                </div>
              )}
            </Card>
          ))}
          {questions.length === 0 && !loading && <EmptyState icon="📝" title="暂无题目收藏" description="在题库搜索中收藏感兴趣的题目" />}
          <Pagination current={questionPage} total={questionTotal} pageSize={pageSize} loading={loading} onChange={(p) => void loadQuestionFavorites(p)} />
        </div>
      )}

      {/* Videos Tab */}
      {activeTab === 'videos' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            {videos.map((video) => (
              <Card key={video.id}>
                <h2 className="font-semibold text-slate-900">{video.title}</h2>
                {video.description && <p className="mt-2 line-clamp-2 text-sm text-slate-600 leading-6">{video.description}</p>}
                {video.favorite_note && (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">备注：{video.favorite_note}</div>
                )}
                <div className="mt-4 flex gap-2">
                  <Button size="sm" onClick={() => window.open(video.url, '_blank')}>打开视频</Button>
                  <Button variant="danger" size="sm" onClick={() => void removeVideo(video.id)}>取消收藏</Button>
                </div>
              </Card>
            ))}
          </div>
          {videos.length === 0 && !loading && <EmptyState icon="🎬" title="暂无视频收藏" description="在资源中心收藏感兴趣的视频" />}
          <Pagination current={videoPage} total={videoTotal} pageSize={pageSize} loading={loading} onChange={(p) => void loadVideoFavorites(p)} />
        </div>
      )}

      {/* Wrong Questions Tab */}
      {activeTab === 'wrong' && (
        <div className="space-y-4">
          <Card>
            <form onSubmit={loadWrongQuestions} className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <input
                type="text"
                value={wrongKeyword}
                onChange={(e) => setWrongKeyword(e.target.value)}
                className="rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none placeholder:text-slate-400 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                placeholder="搜索错题"
              />
              <EnrolledSubjectToggle
                onlyEnrolled={onlyEnrolled}
                setOnlyEnrolled={setOnlyEnrolled}
                hasEnrollments={hasEnrollments}
                isLoggedIn={isLoggedIn}
              />
              <Select value={wrongSubjectId} onChange={(e) => setWrongSubjectId(e.target.value)}>
                <option value="">全部科目</option>
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
              <Select value={wrongMastered} onChange={(e) => setWrongMastered(e.target.value)}>
                <option value="">全部状态</option>
                <option value="false">未掌握</option>
                <option value="true">已掌握</option>
              </Select>
              <Button type="submit" loading={loading}>筛选</Button>
            </form>
          </Card>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => void exportWrongBook('markdown')}>导出 Markdown</Button>
            <Button variant="outline" size="sm" onClick={() => void exportWrongBook('csv')}>导出 CSV</Button>
            <Button variant="outline" size="sm" onClick={() => void exportWrongBook('word')}>导出 Word</Button>
          </div>

          {wrongQuestions.map((item) => (
            <Card key={item.id}>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge variant="primary">{questionTypeLabels[item.question.question_type] || item.question.question_type}</Badge>
                <Badge variant={item.is_mastered ? 'success' : 'danger'}>{item.is_mastered ? '已掌握' : '未掌握'}</Badge>
                <Badge>错误 {item.wrong_count} 次</Badge>
                {item.last_wrong_at && <Badge>{new Date(item.last_wrong_at).toLocaleDateString()}</Badge>}
              </div>
              <div className="whitespace-pre-wrap text-slate-900 leading-7">{item.question.content}</div>
              {item.question.options.length > 0 && (
                <div className="mt-3 space-y-1.5 text-sm text-slate-600">
                  {item.question.options.map((option, index) => (
                    <div key={`${item.question_id}-${index}`} className="rounded-md bg-slate-50 px-3 py-2">
                      {String.fromCharCode(65 + index)}. {option}
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">你的答案：{item.user_answer || '-'}</div>
                <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">参考答案：{item.question.answer || '-'}</div>
              </div>
              {item.question.explanation && (
                <div className="mt-3 rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm text-brand-800 leading-6">{item.question.explanation}</div>
              )}
              {item.knowledge_points.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.knowledge_points.map((point) => <Badge key={point.id} pill>{point.name}</Badge>)}
                </div>
              )}
              <div className="mt-4 grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">复习笔记</label>
                  <textarea
                    value={wrongDrafts[item.question_id]?.note ?? item.note ?? ''}
                    onChange={(e) => setWrongDrafts((c) => ({ ...c, [item.question_id]: { note: e.target.value, tags: c[item.question_id]?.tags ?? (item.tags || []).join(', ') } }))}
                    rows={3}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                    placeholder="记录错误原因、解题方法或复习重点"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">标签</label>
                  <input
                    value={wrongDrafts[item.question_id]?.tags ?? (item.tags || []).join(', ')}
                    onChange={(e) => setWrongDrafts((c) => ({ ...c, [item.question_id]: { note: c[item.question_id]?.note ?? item.note ?? '', tags: e.target.value } }))}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                    placeholder="例如：概念混淆, 重点复习"
                  />
                  <Button variant="secondary" size="sm" className="mt-3" onClick={() => void saveWrongNotes(item)}>保存笔记</Button>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => void setWrongMastery(item.question_id, !item.is_mastered)}>
                  {item.is_mastered ? '标记未掌握' : '标记已掌握'}
                </Button>
                <Button variant="danger" size="sm" onClick={() => void removeWrong(item.question_id)}>移除错题</Button>
              </div>
            </Card>
          ))}

          {wrongQuestions.length === 0 && !loading && <EmptyState icon="✅" title="暂无错题记录" description="完成模拟考试后错题会自动归集到这里" />}
          <Pagination current={wrongPage} total={wrongTotal} pageSize={pageSize} loading={loading} onChange={(p) => void loadWrongQuestions(undefined, p)} />
        </div>
      )}
    </div>
  )
}

export default FavoritesPage
