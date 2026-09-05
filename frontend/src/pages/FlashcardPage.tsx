import React, { useEffect, useState } from 'react'
import { flashcardApi, FlashcardItem, FlashcardStats } from '../api/flashcard'
import { subjectApi, Subject } from '../api/subject'

const qualityButtons = [
  { quality: 1, label: '忘了', emoji: '😰', color: 'bg-red-100 text-red-700 hover:bg-red-200 border-red-200' },
  { quality: 3, label: '模糊', emoji: '🤔', color: 'bg-amber-100 text-amber-700 hover:bg-amber-200 border-amber-200' },
  { quality: 4, label: '想起来了', emoji: '😊', color: 'bg-green-100 text-green-700 hover:bg-green-200 border-green-200' },
  { quality: 5, label: '秒答', emoji: '✨', color: 'bg-brand-100 text-brand-700 hover:bg-brand-200 border-brand-200' },
]

const panelClass = 'rounded-lg border border-slate-200 bg-white shadow-sm'

const FlashcardPage: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('')
  const [stats, setStats] = useState<FlashcardStats | null>(null)
  const [dueCards, setDueCards] = useState<FlashcardItem[]>([])
  const [totalDue, setTotalDue] = useState(0)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [reviewing, setReviewing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [generating, setGenerating] = useState(false)

  // Custom card form
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [customFront, setCustomFront] = useState('')
  const [customBack, setCustomBack] = useState('')
  const [customTags, setCustomTags] = useState('')

  const currentCard = dueCards[currentIndex] || null

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      try {
        const subjectData = await subjectApi.list(undefined, true)
        setSubjects(subjectData)
        if (subjectData[0]) setSelectedSubjectId(String(subjectData[0].id))
      } catch (err) {
        setError(err instanceof Error ? err.message : '初始化失败')
      } finally {
        setLoading(false)
      }
    }
    void init()
  }, [])

  useEffect(() => {
    if (!selectedSubjectId) return
    void loadStats()
    void loadDueCards()
  }, [selectedSubjectId])

  const loadStats = async () => {
    try {
      const data = await flashcardApi.getStats(Number(selectedSubjectId) || undefined)
      setStats(data)
    } catch (err) {
      // stats are non-critical
    }
  }

  const loadDueCards = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await flashcardApi.getDueCards(Number(selectedSubjectId) || undefined, 30)
      setDueCards(data.items)
      setTotalDue(data.total_due)
      setCurrentIndex(0)
      setFlipped(false)
      setReviewing(data.items.length > 0)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载卡片失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    if (!selectedSubjectId) {
      setError('请先选择科目')
      return
    }
    setGenerating(true)
    setError('')
    try {
      const result = await flashcardApi.generate(Number(selectedSubjectId))
      setMessage(result.message)
      await loadStats()
      await loadDueCards()
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成闪卡失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleReview = async (quality: number) => {
    if (!currentCard) return
    try {
      await flashcardApi.reviewCard(currentCard.id, quality)
      if (currentIndex < dueCards.length - 1) {
        setCurrentIndex((prev) => prev + 1)
        setFlipped(false)
      } else {
        // All done
        setReviewing(false)
        setMessage('🎉 今日复习完成！')
        await loadStats()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交复习结果失败')
    }
  }

  const handleCreateCustom = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedSubjectId || !customFront.trim() || !customBack.trim()) return
    try {
      await flashcardApi.createCustom(
        Number(selectedSubjectId),
        customFront.trim(),
        customBack.trim(),
        customTags.trim() || undefined,
      )
      setCustomFront('')
      setCustomBack('')
      setCustomTags('')
      setShowCustomForm(false)
      setMessage('自定义卡片已创建')
      await loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建卡片失败')
    }
  }

  const handleSuspend = async () => {
    if (!currentCard) return
    try {
      await flashcardApi.suspendCard(currentCard.id, true)
      // Remove from current deck and move to next
      const newCards = dueCards.filter((_, i) => i !== currentIndex)
      setDueCards(newCards)
      if (currentIndex >= newCards.length && newCards.length > 0) {
        setCurrentIndex(newCards.length - 1)
      }
      setFlipped(false)
      if (newCards.length === 0) {
        setReviewing(false)
        setMessage('所有卡片已完成')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '暂停卡片失败')
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <div className="text-sm font-medium text-brand-600">Flashcards</div>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">知识点闪卡</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          基于艾宾浩斯遗忘曲线的间隔复习系统，帮助你高效记忆自考核心知识点。
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}
      {message && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {message}
          <button onClick={() => setMessage('')} className="ml-2 text-green-900 hover:underline">×</button>
        </div>
      )}

      {/* Header controls */}
      <div className={`${panelClass} mb-6 p-5`}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <select
              value={selectedSubjectId}
              onChange={(e) => setSelectedSubjectId(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            >
              <option value="">全部科目</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerate}
              disabled={generating || !selectedSubjectId}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {generating ? '生成中...' : '生成闪卡'}
            </button>
            <button
              onClick={() => setShowCustomForm(!showCustomForm)}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              自定义卡片
            </button>
            <button
              onClick={() => void loadDueCards()}
              disabled={loading}
              className="rounded-lg border border-brand-200 bg-white px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
            >
              开始复习
            </button>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-slate-50 p-3 text-center">
              <div className="text-2xl font-bold text-slate-900">{stats.total}</div>
              <div className="text-xs text-slate-500">总卡片</div>
            </div>
            <div className="rounded-lg bg-amber-50 p-3 text-center">
              <div className="text-2xl font-bold text-amber-700">{stats.due_today}</div>
              <div className="text-xs text-amber-600">今日到期</div>
            </div>
            <div className="rounded-lg bg-blue-50 p-3 text-center">
              <div className="text-2xl font-bold text-blue-700">{stats.learning}</div>
              <div className="text-xs text-blue-600">学习中</div>
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <div className="text-2xl font-bold text-green-700">{stats.mastered}</div>
              <div className="text-xs text-green-600">已掌握</div>
            </div>
          </div>
        )}
      </div>

      {/* Custom card form */}
      {showCustomForm && (
        <div className={`${panelClass} mb-6 p-5`}>
          <h3 className="mb-4 text-base font-semibold text-slate-950">创建自定义卡片</h3>
          <form onSubmit={handleCreateCustom} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">正面（问题/概念）</label>
              <textarea
                value={customFront}
                onChange={(e) => setCustomFront(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                rows={2}
                placeholder="输入问题或概念..."
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">反面（答案/解释）</label>
              <textarea
                value={customBack}
                onChange={(e) => setCustomBack(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                rows={3}
                placeholder="输入答案或解释..."
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">标签（可选）</label>
              <input
                value={customTags}
                onChange={(e) => setCustomTags(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                placeholder="如：重点,第三章"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                创建卡片
              </button>
              <button
                type="button"
                onClick={() => setShowCustomForm(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Review area */}
      {reviewing && currentCard && (
        <div className="space-y-4">
          {/* Progress bar */}
          <div className="flex items-center gap-3">
            <div className="flex-1 rounded-full bg-slate-100 h-2">
              <div
                className="h-2 rounded-full bg-brand-500 transition-all"
                style={{ width: `${((currentIndex + 1) / dueCards.length) * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium text-slate-600">
              {currentIndex + 1} / {dueCards.length}
            </span>
          </div>

          {/* Card */}
          <div
            className={`${panelClass} cursor-pointer p-8 text-center transition-all min-h-[280px] flex flex-col items-center justify-center`}
            onClick={() => setFlipped(!flipped)}
          >
            {!flipped ? (
              <>
                <div className="mb-4 text-xs font-medium uppercase tracking-wider text-slate-400">
                  正面 · 点击翻转
                </div>
                <div className="text-lg font-medium leading-8 text-slate-900 whitespace-pre-wrap">
                  {currentCard.front}
                </div>
                <div className="mt-6 text-sm text-slate-400">👆 点击查看答案</div>
              </>
            ) : (
              <>
                <div className="mb-4 text-xs font-medium uppercase tracking-wider text-green-600">
                  反面 · 答案
                </div>
                <div className="text-base leading-7 text-slate-800 whitespace-pre-wrap">
                  {currentCard.back}
                </div>
              </>
            )}
          </div>

          {/* Rating buttons - only show when flipped */}
          {flipped && (
            <div className="space-y-3">
              <div className="text-center text-sm font-medium text-slate-600">回忆程度如何？</div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {qualityButtons.map((btn) => (
                  <button
                    key={btn.quality}
                    onClick={() => void handleReview(btn.quality)}
                    className={`rounded-lg border px-4 py-3 text-sm font-medium transition ${btn.color}`}
                  >
                    <span className="text-lg">{btn.emoji}</span>
                    <span className="ml-2">{btn.label}</span>
                  </button>
                ))}
              </div>
              <div className="flex justify-center">
                <button
                  onClick={() => void handleSuspend()}
                  className="text-xs text-slate-400 hover:text-slate-600 hover:underline"
                >
                  暂停此卡片（不再出现）
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* No cards state */}
      {!reviewing && !loading && (
        <div className={`${panelClass} p-8 text-center`}>
          <div className="text-4xl mb-3">📚</div>
          <h3 className="text-lg font-semibold text-slate-900">
            {stats && stats.due_today === 0 && stats.total > 0
              ? '今日复习已完成！'
              : stats && stats.total === 0
                ? '还没有闪卡'
                : '准备好复习了吗？'}
          </h3>
          <p className="mt-2 text-sm text-slate-500">
            {stats && stats.total === 0
              ? '选择一个科目并点击"生成闪卡"来自动创建学习卡片。'
              : stats && stats.due_today === 0
                ? '明天再来继续保持记忆强度吧！'
                : `有 ${totalDue} 张卡片等待复习。`}
          </p>
        </div>
      )}
    </div>
  )
}

export default FlashcardPage
