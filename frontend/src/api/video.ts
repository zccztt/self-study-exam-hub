import apiClient, { unwrap } from './client'
import { sessionStore } from './session'

export interface VideoItem {
  id: number
  title: string
  url: string
  source: string
  duration?: number
  author?: string
  view_count: number
  subject_id: number
  chapter_id?: number
  thumbnail?: string
  description?: string
  tags: string[]
  favorite_note?: string
}

export interface RelatedVideoQuestion {
  id: number
  content: string
  question_type: string
  year?: number
  score: number
}

export interface VideoDetail extends VideoItem {
  related_questions: RelatedVideoQuestion[]
}

export interface VideoSearchResult {
  total: number
  page: number
  page_size: number
  online_saved_count?: number
  online_searched?: boolean
  message?: string | null
  items: VideoItem[]
}

export interface SearchVideosParams {
  keyword?: string
  subject_id?: number
  chapter_ids?: number[]
  source?: string
  page?: number
  page_size?: number
}

const serializeParams = (params: SearchVideosParams) => ({
  ...params,
  chapter_ids: params.chapter_ids?.join(','),
})

export const videoApi = {
  searchVideos: (params: SearchVideosParams, signal?: AbortSignal) =>
    unwrap<VideoSearchResult>(apiClient.get('/videos', { params: serializeParams(params), signal })),
  getVideoDetail: (videoId: number) => unwrap<VideoDetail>(apiClient.get(`/videos/${videoId}`)),
  addFavorite: (videoId: number, note?: string, userId = sessionStore.getUserId()) =>
    unwrap<{ success: boolean }>(
      apiClient.post('/videos/favorites', {
        user_id: userId,
        video_id: videoId,
        note,
      }),
    ),
  removeFavorite: (videoId: number, userId = sessionStore.getUserId()) =>
    unwrap<{ success: boolean }>(apiClient.delete(`/videos/favorites/${userId}/${videoId}`)),
  getFavorites: (userId = sessionStore.getUserId(), page = 1, pageSize = 20) =>
    unwrap<VideoSearchResult>(
      apiClient.get(`/videos/favorites/${userId}`, {
        params: { page, page_size: pageSize },
      }),
    ),
  // Aliases for backward compat
  addToFavorites: (videoId: number, note?: string, userId = sessionStore.getUserId()) =>
    unwrap<{ success: boolean }>(
      apiClient.post('/videos/favorites', { user_id: userId, video_id: videoId, note }),
    ),
  removeFromFavorites: (videoId: number, userId = sessionStore.getUserId()) =>
    unwrap<{ success: boolean }>(apiClient.delete(`/videos/favorites/${userId}/${videoId}`)),
}
