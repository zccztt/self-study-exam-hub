import { create } from 'zustand'
import { questionApi } from '../api/question'
import { videoApi } from '../api/video'
import { sessionStore } from '../api/session'

interface FavoritesState {
  questionIds: Set<number>
  videoIds: Set<number>
  loaded: boolean
  loading: boolean

  // Actions
  loadFavorites: () => Promise<void>
  toggleQuestionFavorite: (questionId: number, tags?: string[]) => Promise<boolean>
  toggleVideoFavorite: (videoId: number) => Promise<boolean>
  isQuestionFavorited: (questionId: number) => boolean
  isVideoFavorited: (videoId: number) => boolean
  reset: () => void
}

export const useFavoritesStore = create<FavoritesState>((set, get) => ({
  questionIds: new Set(),
  videoIds: new Set(),
  loaded: false,
  loading: false,

  loadFavorites: async () => {
    const userId = sessionStore.getUserId(0)
    if (!userId || get().loading) return

    set({ loading: true })
    try {
      const [qFavs, vFavs] = await Promise.all([
        questionApi.getFavorites(userId, 1, 200).catch(() => ({ items: [] as { id: number }[] })),
        videoApi.getFavorites(userId, 1, 200).catch(() => ({ items: [] as { id: number }[] })),
      ])
      set({
        questionIds: new Set(qFavs.items.map((item: { id: number }) => item.id)),
        videoIds: new Set(vFavs.items.map((item: { id: number }) => item.id)),
        loaded: true,
      })
    } catch {
      // Silently fail - favorites are non-critical
    } finally {
      set({ loading: false })
    }
  },

  toggleQuestionFavorite: async (questionId: number, tags?: string[]) => {
    const { questionIds } = get()
    const isFav = questionIds.has(questionId)

    try {
      if (isFav) {
        await questionApi.removeFromFavorites(questionId)
        const next = new Set(questionIds)
        next.delete(questionId)
        set({ questionIds: next })
        return false
      } else {
        await questionApi.addToFavorites(questionId, tags)
        const next = new Set(questionIds)
        next.add(questionId)
        set({ questionIds: next })
        return true
      }
    } catch {
      return isFav // Return original state on error
    }
  },

  toggleVideoFavorite: async (videoId: number) => {
    const { videoIds } = get()
    const isFav = videoIds.has(videoId)

    try {
      if (isFav) {
        await videoApi.removeFavorite(videoId)
        const next = new Set(videoIds)
        next.delete(videoId)
        set({ videoIds: next })
        return false
      } else {
        await videoApi.addFavorite(videoId)
        const next = new Set(videoIds)
        next.add(videoId)
        set({ videoIds: next })
        return true
      }
    } catch {
      return isFav
    }
  },

  isQuestionFavorited: (questionId: number) => get().questionIds.has(questionId),
  isVideoFavorited: (videoId: number) => get().videoIds.has(videoId),

  reset: () => set({ questionIds: new Set(), videoIds: new Set(), loaded: false }),
}))
