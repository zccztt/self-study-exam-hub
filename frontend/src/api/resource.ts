import apiClient from './client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ResourceSummary {
  id: number
  filename: string
  media_type: string        // pdf / image / video / doc
  storage_type: string      // minio / external_link
  external_url: string | null
  download_url: string | null
  file_size: number | null
  ocr_status: string
  sort_order?: number
}

export interface ResourceDetail extends ResourceSummary {
  content_type: string | null
  has_content_text: boolean
  created_at: string | null
}

export interface ResourceContent {
  id: number
  ocr_status: string
  content_text: string | null
}

// ---------------------------------------------------------------------------
// 上传文件
// ---------------------------------------------------------------------------

export async function uploadResource(file: File): Promise<ResourceSummary> {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await apiClient.post('/resources/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000, // 大文件上传可能较慢
  })
  return resp.data
}

// ---------------------------------------------------------------------------
// 创建外部链接
// ---------------------------------------------------------------------------

export interface LinkCreateParams {
  url: string
  title?: string
  media_type?: string
}

export async function createLinkResource(params: LinkCreateParams): Promise<ResourceSummary> {
  const resp = await apiClient.post('/resources/link', params)
  return resp.data
}

// ---------------------------------------------------------------------------
// 查看 / 删除
// ---------------------------------------------------------------------------

export async function getResource(resourceId: number): Promise<ResourceDetail> {
  const resp = await apiClient.get(`/resources/${resourceId}`)
  return resp.data
}

export async function getResourceContent(resourceId: number): Promise<ResourceContent> {
  const resp = await apiClient.get(`/resources/${resourceId}/content`)
  return resp.data
}

export async function deleteResource(resourceId: number): Promise<void> {
  await apiClient.delete(`/resources/${resourceId}`)
}

// ---------------------------------------------------------------------------
// 挂载 / 取消挂载 — 题目
// ---------------------------------------------------------------------------

export async function attachToQuestion(
  resourceId: number,
  questionId: number,
  sortOrder = 0,
): Promise<void> {
  await apiClient.post(
    `/resources/${resourceId}/attach/question/${questionId}`,
    null,
    { params: { sort_order: sortOrder } },
  )
}

export async function detachFromQuestion(
  resourceId: number,
  questionId: number,
): Promise<void> {
  await apiClient.delete(`/resources/${resourceId}/attach/question/${questionId}`)
}

// ---------------------------------------------------------------------------
// 挂载 / 取消挂载 — 真题卷源
// ---------------------------------------------------------------------------

export async function attachToPaperSource(
  resourceId: number,
  paperSourceId: number,
  sortOrder = 0,
): Promise<void> {
  await apiClient.post(
    `/resources/${resourceId}/attach/paper-source/${paperSourceId}`,
    null,
    { params: { sort_order: sortOrder } },
  )
}

export async function detachFromPaperSource(
  resourceId: number,
  paperSourceId: number,
): Promise<void> {
  await apiClient.delete(`/resources/${resourceId}/attach/paper-source/${paperSourceId}`)
}

// ---------------------------------------------------------------------------
// 列出某实体的资源
// ---------------------------------------------------------------------------

export async function listQuestionResources(questionId: number): Promise<ResourceSummary[]> {
  const resp = await apiClient.get(`/resources/by-question/${questionId}`)
  return resp.data
}

export async function listPaperSourceResources(paperSourceId: number): Promise<ResourceSummary[]> {
  const resp = await apiClient.get(`/resources/by-paper-source/${paperSourceId}`)
  return resp.data
}
