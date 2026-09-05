import React, { useEffect, useState, useCallback } from 'react'
import {
  adminProviderApi,
  AIProvider,
  AIProviderCreate,
  SearchProvider,
  SearchProviderCreate,
  TestResult,
  BatchTestResult,
} from '../api/adminProvider'
import { useAuthStore } from '../stores/useAuthStore'
import { Badge, Button, Card, EmptyState, PageHeader, useToast } from '../components/ui'

type Tab = 'ai' | 'search'

// ------------------------------------------------------------------
// AI Provider Form — with multi-model selection
// ------------------------------------------------------------------

const emptyAI: AIProviderCreate & { is_active?: boolean } = { name: '', base_url: '', model: '', api_key: '', timeout: 30, weight: 1, roles: [], priority: 0, description: '' }

const AI_ROLE_OPTIONS = ['analysis', 'grading', 'judge', 'review', 'generate']

/** Parse model string to array (handles comma-separated or JSON array) */
function parseModels(model: string): string[] {
  if (!model) return []
  const s = model.trim()
  if (s.startsWith('[')) {
    try {
      const arr = JSON.parse(s)
      if (Array.isArray(arr)) return arr.map(String).filter(Boolean)
    } catch { /* fall through */ }
  }
  return s.split(',').map((m) => m.trim()).filter(Boolean)
}

/** Serialize model array back to comma-separated string */
function serializeModels(models: string[]): string {
  return models.join(',')
}

const AIProviderForm: React.FC<{
  initial?: AIProvider | null
  onSave: () => void
  onCancel: () => void
}> = ({ initial, onSave, onCancel }) => {
  const toast = useToast()
  const [form, setForm] = useState<AIProviderCreate & { is_active?: boolean }>(initial ? {
    name: initial.name,
    base_url: initial.base_url,
    model: initial.model,
    api_key: '',
    timeout: initial.timeout,
    weight: initial.weight,
    roles: initial.roles || [],
    priority: initial.priority,
    description: initial.description || '',
    is_active: initial.is_active,
  } : { ...emptyAI })
  const [saving, setSaving] = useState(false)

  // Model selection state
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [selectedModels, setSelectedModels] = useState<string[]>(parseModels(initial?.model || ''))
  const [fetchingModels, setFetchingModels] = useState(false)
  const [modelSearchFilter, setModelSearchFilter] = useState('')
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [customModelInput, setCustomModelInput] = useState('')

  // Sync selectedModels → form.model
  useEffect(() => {
    setForm((f) => ({ ...f, model: serializeModels(selectedModels) }))
  }, [selectedModels])

  const handleFetchModels = useCallback(async () => {
    if (!form.base_url && !initial) { toast.error('请先填写 Base URL'); return }
    setFetchingModels(true)
    try {
      let models: string[]
      if (initial && !form.api_key) {
        // 编辑模式且未填新 key —> 用已存储的凭据
        models = await adminProviderApi.fetchModels(form.base_url || initial.base_url, '', initial.id)
      } else if (form.api_key && form.base_url) {
        models = await adminProviderApi.fetchModels(form.base_url, form.api_key)
      } else {
        toast.error('请先填写 Base URL 和 API Key')
        return
      }
      setAvailableModels(models)
      setShowModelDropdown(true)
      if (models.length === 0) {
        toast.info('该服务商返回的模型列表为空')
      } else {
        toast.success(`获取到 ${models.length} 个模型`)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '获取模型列表失败')
    } finally {
      setFetchingModels(false)
    }
  }, [form.base_url, form.api_key, initial, toast])

  const toggleModel = (model: string) => {
    setSelectedModels((prev) =>
      prev.includes(model) ? prev.filter((m) => m !== model) : [...prev, model]
    )
  }

  const selectAllModels = () => {
    const filtered = filteredModels()
    const allSelected = filtered.every((m) => selectedModels.includes(m))
    if (allSelected) {
      setSelectedModels((prev) => prev.filter((m) => !filtered.includes(m)))
    } else {
      setSelectedModels((prev) => [...new Set([...prev, ...filtered])])
    }
  }

  const filteredModels = () => {
    if (!modelSearchFilter) return availableModels
    const q = modelSearchFilter.toLowerCase()
    return availableModels.filter((m) => m.toLowerCase().includes(q))
  }

  const addCustomModel = () => {
    const name = customModelInput.trim()
    if (!name) return
    if (!selectedModels.includes(name)) {
      setSelectedModels((prev) => [...prev, name])
    }
    setCustomModelInput('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedModels.length === 0) {
      toast.error('请选择至少一个模型')
      return
    }
    setSaving(true)
    try {
      if (initial) {
        const payload: Record<string, any> = { ...form }
        if (!payload.api_key) delete payload.api_key // don't send empty key on update
        await adminProviderApi.updateAI(initial.id, payload)
        toast.success('AI 服务商已更新')
      } else {
        await adminProviderApi.createAI(form as AIProviderCreate)
        toast.success('AI 服务商已创建')
      }
      onSave()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const set = (key: string, value: any) => setForm((f) => ({ ...f, [key]: value }))

  return (
    <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
      {/* Hidden dummy fields to trick browser autofill */}
      <input type="text" name="_af_trap1" style={{ display: 'none' }} tabIndex={-1} />
      <input type="password" name="_af_trap2" style={{ display: 'none' }} tabIndex={-1} />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Field label="名称" required value={form.name} onChange={(v) => set('name', v)} placeholder="如 openai-main" autoComplete="off" />
        <div />  {/* spacer */}
        <Field label="Base URL" required value={form.base_url} onChange={(v) => set('base_url', v)} placeholder="https://api.openai.com/v1" className="md:col-span-2" autoComplete="off" />
        <Field label={initial ? 'API Key（留空不修改）' : 'API Key'} required={!initial} value={form.api_key} onChange={(v) => set('api_key', v)} placeholder={initial ? initial.api_key_preview : '请输入 API Key'} type="text" autoComplete="new-password" maskAsPassword />
        <div /> {/* spacer */}
      </div>

      {/* Model selection area */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-slate-700">
          模型（可选）
        </label>

        {/* Selected models display box */}
        <div className="min-h-[68px] rounded-lg border border-slate-200 bg-white p-2.5">
          {selectedModels.length > 0 ? (
            <>
              <div className="flex flex-wrap gap-2">
                {selectedModels.map((m) => (
                  <span key={m} className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-sm text-slate-700">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-brand-500 flex-shrink-0" />
                    {m}
                    <button type="button" onClick={() => toggleModel(m)} className="ml-0.5 text-slate-400 hover:text-slate-700 transition">
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div className="mt-2 flex items-center gap-1 text-xs text-slate-400">
                <span>{selectedModels.length} 个模型</span>
                {availableModels.length > 0 && (
                  <button type="button" onClick={() => setShowModelDropdown(!showModelDropdown)} className="ml-1 text-slate-400 hover:text-slate-600">
                    {showModelDropdown ? '▲' : '▼'}
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="flex h-10 items-center text-sm text-slate-400">暂未选择模型</div>
          )}
        </div>

        {/* Dropdown: available models from upstream */}
        {showModelDropdown && availableModels.length > 0 && (
          <div className="rounded-lg border border-slate-200 bg-white shadow-md">
            <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2">
              <input
                type="text"
                value={modelSearchFilter}
                onChange={(e) => setModelSearchFilter(e.target.value)}
                placeholder="搜索模型..."
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
              />
              <button type="button" onClick={selectAllModels} className="text-xs font-medium text-brand-600 hover:text-brand-700 whitespace-nowrap">
                {filteredModels().every((m) => selectedModels.includes(m)) ? '取消全选' : '全选'}
              </button>
            </div>
            <div className="max-h-48 overflow-y-auto p-2">
              {filteredModels().map((model) => {
                const checked = selectedModels.includes(model)
                return (
                  <button
                    key={model}
                    type="button"
                    onClick={() => toggleModel(model)}
                    className={`flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-left text-sm transition ${
                      checked ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <span className={`inline-flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border text-xs ${
                      checked ? 'border-brand-500 bg-brand-500 text-white' : 'border-slate-300'
                    }`}>
                      {checked ? '✓' : ''}
                    </span>
                    {model}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Action buttons row */}
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="outline" size="sm" onClick={handleFetchModels} loading={fetchingModels}>
            ⇅ 同步上游支持的模型
          </Button>
          {selectedModels.length > 0 && (
            <button
              type="button"
              onClick={() => { setSelectedModels([]); setAvailableModels([]) }}
              className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50 transition"
            >
              清除所有模型
            </button>
          )}
        </div>

        {/* Custom model name input */}
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-slate-700">自定义模型名称</label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={customModelInput}
              onChange={(e) => setCustomModelInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCustomModel() } }}
              placeholder="输入自定义模型名称"
              autoComplete="off"
              className="flex-1 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
            />
            <button
              type="button"
              onClick={addCustomModel}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 transition"
            >
              填入
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="grid grid-cols-3 gap-3 md:col-span-2">
          <Field label="超时(秒)" value={String(form.timeout || 30)} onChange={(v) => set('timeout', Number(v))} type="number" />
          <Field label="权重" value={String(form.weight || 1)} onChange={(v) => set('weight', Number(v))} type="number" />
          <Field label="优先级（越大越高）" value={String(form.priority || 0)} onChange={(v) => set('priority', Number(v))} type="number" />
        </div>
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700">角色</label>
        <div className="flex flex-wrap gap-2">
          {AI_ROLE_OPTIONS.map((role) => {
            const checked = (form.roles || []).includes(role)
            return (
              <button
                key={role}
                type="button"
                onClick={() => set('roles', checked ? (form.roles || []).filter((r) => r !== role) : [...(form.roles || []), role])}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition ${checked ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-slate-200 bg-white text-slate-500 hover:border-slate-300'}`}
              >
                {role}
              </button>
            )
          })}
        </div>
      </div>
      <Field label="描述" value={form.description || ''} onChange={(v) => set('description', v)} placeholder="可选备注" />
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_active ?? true} onChange={(e) => set('is_active', e.target.checked)} className="rounded" />
          启用
        </label>
      )}
      <div className="flex gap-2 pt-2">
        <Button type="submit" loading={saving}>{initial ? '保存修改' : '新增服务商'}</Button>
        <Button variant="outline" type="button" onClick={onCancel}>取消</Button>
      </div>
    </form>
  )
}

// ------------------------------------------------------------------
// Search Provider Form
// ------------------------------------------------------------------

const emptySearch: SearchProviderCreate = { name: '', provider_type: 'tavily', base_url: '', api_key: '', timeout: 30, weight: 1, priority: 0, description: '' }

const SearchProviderForm: React.FC<{
  initial?: SearchProvider | null
  onSave: () => void
  onCancel: () => void
}> = ({ initial, onSave, onCancel }) => {
  const toast = useToast()
  const [form, setForm] = useState<SearchProviderCreate & { is_active?: boolean }>(initial ? {
    name: initial.name,
    provider_type: initial.provider_type,
    base_url: initial.base_url,
    api_key: '',
    timeout: initial.timeout,
    weight: initial.weight,
    priority: initial.priority,
    description: initial.description || '',
    is_active: initial.is_active,
  } : { ...emptySearch })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (initial) {
        const payload: Record<string, any> = { ...form }
        if (!payload.api_key) delete payload.api_key
        await adminProviderApi.updateSearch(initial.id, payload)
        toast.success('搜索服务商已更新')
      } else {
        await adminProviderApi.createSearch(form as SearchProviderCreate)
        toast.success('搜索服务商已创建')
      }
      onSave()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const set = (key: string, value: any) => setForm((f) => ({ ...f, [key]: value }))

  return (
    <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
      {/* Hidden dummy fields to trick browser autofill */}
      <input type="text" name="_af_trap_s1" style={{ display: 'none' }} tabIndex={-1} />
      <input type="password" name="_af_trap_s2" style={{ display: 'none' }} tabIndex={-1} />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Field label="名称" required value={form.name} onChange={(v) => set('name', v)} placeholder="如 tavily-main" autoComplete="off" />
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-slate-700">类型 <span className="text-red-500">*</span></label>
          <select
            value={form.provider_type}
            onChange={(e) => set('provider_type', e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
          >
            <option value="tavily">Tavily</option>
            <option value="search_api">Search API (SearXNG等)</option>
            <option value="custom">自定义</option>
          </select>
        </div>
        <Field label="Base URL" required value={form.base_url} onChange={(v) => set('base_url', v)} placeholder="https://api.tavily.com" className="md:col-span-2" autoComplete="off" />
        <Field label={initial ? 'API Key（留空不修改）' : 'API Key'} required={!initial} value={form.api_key} onChange={(v) => set('api_key', v)} placeholder={initial ? initial.api_key_preview : '请输入 API Key'} type="text" autoComplete="new-password" maskAsPassword />
        <div className="grid grid-cols-3 gap-3">
          <Field label="超时(秒)" value={String(form.timeout || 30)} onChange={(v) => set('timeout', Number(v))} type="number" />
          <Field label="权重" value={String(form.weight || 1)} onChange={(v) => set('weight', Number(v))} type="number" />
          <Field label="优先级（越大越高）" value={String(form.priority || 0)} onChange={(v) => set('priority', Number(v))} type="number" />
        </div>
      </div>
      <Field label="描述" value={form.description || ''} onChange={(v) => set('description', v)} placeholder="可选备注" />
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_active ?? true} onChange={(e) => set('is_active', e.target.checked)} className="rounded" />
          启用
        </label>
      )}
      <div className="flex gap-2 pt-2">
        <Button type="submit" loading={saving}>{initial ? '保存修改' : '新增服务商'}</Button>
        <Button variant="outline" type="button" onClick={onCancel}>取消</Button>
      </div>
    </form>
  )
}

// ------------------------------------------------------------------
// Shared field component
// ------------------------------------------------------------------

const Field: React.FC<{
  label: string
  value: string
  onChange: (v: string) => void
  required?: boolean
  type?: string
  placeholder?: string
  className?: string
  autoComplete?: string
  maskAsPassword?: boolean
}> = ({ label, value, onChange, required, type = 'text', placeholder, className, autoComplete, maskAsPassword }) => {
  // Use a random name to prevent browser autofill
  const [randName] = useState(() => `_naf_${Math.random().toString(36).slice(2, 8)}`)
  return (
    <div className={`space-y-1.5 ${className || ''}`}>
      <label className="block text-sm font-medium text-slate-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        name={randName}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        autoComplete={autoComplete || 'off'}
        data-lpignore="true"
        data-1p-ignore="true"
        data-form-type="other"
        className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
        {...(maskAsPassword ? { style: { WebkitTextSecurity: 'disc' } as React.CSSProperties } : {})}
      />
    </div>
  )
}

// ------------------------------------------------------------------
// Provider Card (shared for both types)
// ------------------------------------------------------------------

const ProviderCard: React.FC<{
  name: string
  type?: string
  model?: string
  baseUrl: string
  keyPreview: string
  isActive: boolean
  priority: number
  weight: number
  timeout: number
  description: string | null
  roles?: string[] | null
  lastTestAt: string | null
  lastTestOk: boolean | null
  testing: boolean
  onTest: (customPrompt?: string, model?: string) => void
  onTestBatch: (models: string[], prompt?: string) => void
  onEdit: () => void
  onDelete: () => void
}> = ({ name, type, model, baseUrl, keyPreview, isActive, priority, weight, timeout, description, roles, lastTestAt, lastTestOk, testing, onTest, onTestBatch, onEdit, onDelete }) => {
  const [showTestPanel, setShowTestPanel] = useState(false)
  const [testPrompt, setTestPrompt] = useState('')
  const [testSelectedModels, setTestSelectedModels] = useState<string[]>([])
  const modelList = model ? parseModels(model) : []
  const modelCount = modelList.length

  const toggleTestModel = (m: string) => {
    setTestSelectedModels((prev) => prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m])
  }

  const handleRunTest = () => {
    if (testSelectedModels.length === 0) {
      // No model selected, run default test
      onTest(testPrompt || undefined)
    } else if (testSelectedModels.length === 1) {
      // Single model
      onTest(testPrompt || undefined, testSelectedModels[0])
    } else {
      // Batch test
      onTestBatch(testSelectedModels, testPrompt || undefined)
    }
    setShowTestPanel(false)
    setTestPrompt('')
    setTestSelectedModels([])
  }

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <h3 className="font-semibold text-slate-900 truncate">{name}</h3>
            <Badge variant={isActive ? 'success' : 'danger'}>{isActive ? '启用' : '停用'}</Badge>
            {type && <Badge variant="primary">{type}</Badge>}
            {modelCount > 0 && <Badge>{modelCount} 个模型</Badge>}
          </div>
          <div className="space-y-1 text-xs text-slate-500">
            <div className="truncate">URL: <span className="text-slate-700">{baseUrl}</span></div>
            <div>Key: <span className="font-mono text-slate-700">{keyPreview}</span></div>
            <div className="flex flex-wrap gap-3">
              <span>优先级 {priority}</span>
              <span>权重 {weight}</span>
              <span>超时 {timeout}s</span>
            </div>
            {roles && roles.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {roles.map((r) => <Badge key={r} variant="warning" pill>{r}</Badge>)}
              </div>
            )}
            {description && <div className="text-slate-600 pt-1">{description}</div>}
            {lastTestAt && (
              <div className="flex items-center gap-1.5 pt-1">
                <span className={`inline-block h-2 w-2 rounded-full ${lastTestOk ? 'bg-emerald-500' : 'bg-red-500'}`} />
                上次测试: {new Date(lastTestAt).toLocaleString()} — {lastTestOk ? '成功' : '失败'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Test panel */}
      {showTestPanel && (
        <div className="mt-3 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          {/* Model selection for test */}
          {modelList.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-600">选择测试模型（不选则使用默认第一个）</span>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setTestSelectedModels([...modelList])} className="text-xs text-brand-600 hover:text-brand-700">全选</button>
                  <button type="button" onClick={() => setTestSelectedModels([])} className="text-xs text-slate-500 hover:text-slate-700">清空</button>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {modelList.map((m) => {
                  const checked = testSelectedModels.includes(m)
                  return (
                    <button
                      key={m}
                      type="button"
                      onClick={() => toggleTestModel(m)}
                      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition ${
                        checked
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      <span className={`inline-flex h-3.5 w-3.5 flex-shrink-0 items-center justify-center rounded border text-[10px] ${
                        checked ? 'border-brand-500 bg-brand-500 text-white' : 'border-slate-300'
                      }`}>
                        {checked ? '✓' : ''}
                      </span>
                      {m}
                    </button>
                  )
                })}
              </div>
              {testSelectedModels.length > 1 && (
                <div className="text-xs text-slate-400">已选 {testSelectedModels.length} 个模型，将并发测试</div>
              )}
            </div>
          )}
          {/* Custom prompt */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              placeholder="自定义测试内容（留空使用默认）"
              className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
            />
            <Button size="sm" onClick={handleRunTest} loading={testing}>
              {testSelectedModels.length > 1 ? '批量测试' : '测试'}
            </Button>
            <Button variant="outline" size="sm" onClick={() => { setShowTestPanel(false); setTestSelectedModels([]) }}>取消</Button>
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={() => setShowTestPanel(!showTestPanel)} loading={testing}>测试连通</Button>
        <Button variant="secondary" size="sm" onClick={onEdit}>编辑</Button>
        <Button variant="danger" size="sm" onClick={onDelete}>删除</Button>
      </div>
    </Card>
  )
}

// ------------------------------------------------------------------
// Main Page
// ------------------------------------------------------------------

const AdminProvidersPage: React.FC = () => {
  const toast = useToast()
  const user = useAuthStore((s) => s.user)
  const [tab, setTab] = useState<Tab>('ai')

  // AI state
  const [aiList, setAiList] = useState<AIProvider[]>([])
  const [aiEditing, setAiEditing] = useState<AIProvider | null | 'new'>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiTesting, setAiTesting] = useState<number | null>(null)

  // Search state
  const [searchList, setSearchList] = useState<SearchProvider[]>([])
  const [searchEditing, setSearchEditing] = useState<SearchProvider | null | 'new'>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchTesting, setSearchTesting] = useState<number | null>(null)

  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [batchResults, setBatchResults] = useState<BatchTestResult[]>([])

  const loadAI = async () => {
    setAiLoading(true)
    try {
      setAiList(await adminProviderApi.listAI(true))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'AI 服务商列表加载失败')
    } finally {
      setAiLoading(false)
    }
  }

  const loadSearch = async () => {
    setSearchLoading(true)
    try {
      setSearchList(await adminProviderApi.listSearch(true))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '搜索服务商列表加载失败')
    } finally {
      setSearchLoading(false)
    }
  }

  useEffect(() => {
    if (user?.is_superuser) {
      void loadAI()
      void loadSearch()
    }
  }, [user])

  const handleTestAI = async (id: number, customPrompt?: string, model?: string) => {
    setAiTesting(id)
    setTestResult(null)
    setBatchResults([])
    try {
      const result = await adminProviderApi.testAI(id, customPrompt, model)
      setTestResult(result)
      if (result.success) {
        toast.success(`测试成功 (${result.latency_ms}ms)${result.model ? ` [${result.model}]` : ''}`)
      } else {
        toast.error(`测试失败: ${result.error || 'Unknown'}`)
      }
      void loadAI()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '测试请求失败')
    } finally {
      setAiTesting(null)
    }
  }

  const handleTestAIBatch = async (id: number, models: string[], prompt?: string) => {
    setAiTesting(id)
    setTestResult(null)
    setBatchResults([])
    try {
      const results = await adminProviderApi.testAIBatch(id, models, prompt)
      setBatchResults(results)
      const ok = results.filter((r) => r.success).length
      const fail = results.length - ok
      if (fail === 0) {
        toast.success(`全部 ${ok} 个模型测试通过`)
      } else {
        toast.info(`${ok} 个通过, ${fail} 个失败`)
      }
      void loadAI()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '批量测试请求失败')
    } finally {
      setAiTesting(null)
    }
  }

  const handleTestSearch = async (id: number, customPrompt?: string) => {
    setSearchTesting(id)
    setTestResult(null)
    try {
      const result = await adminProviderApi.testSearch(id, customPrompt)
      setTestResult(result)
      if (result.success) {
        toast.success(`测试成功 (${result.latency_ms}ms)`)
      } else {
        toast.error(`测试失败: ${result.error || 'Unknown'}`)
      }
      void loadSearch()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '测试请求失败')
    } finally {
      setSearchTesting(null)
    }
  }

  const handleDeleteAI = async (id: number, name: string) => {
    if (!confirm(`确定删除 AI 服务商「${name}」？`)) return
    try {
      await adminProviderApi.deleteAI(id)
      toast.success('已删除')
      void loadAI()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleDeleteSearch = async (id: number, name: string) => {
    if (!confirm(`确定删除搜索服务商「${name}」？`)) return
    try {
      await adminProviderApi.deleteSearch(id)
      toast.success('已删除')
      void loadSearch()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleReloadAI = async () => {
    try {
      const data = await adminProviderApi.reloadAI()
      toast.success(`已重载 ${data.loaded} 个 AI 服务商到内存池`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '重载失败')
    }
  }

  const handleReloadSearch = async () => {
    try {
      const data = await adminProviderApi.reloadSearch()
      toast.success(`已重载: Tavily ${data.tavily_count} 个, Search API ${data.search_api ? '✓' : '✕'}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '重载失败')
    }
  }

  // Guard: not admin
  if (!user?.is_superuser) {
    return (
      <div className="space-y-6">
        <PageHeader tag="管理" title="配置中心" description="仅管理员可访问此页面" />
        <EmptyState icon="🔒" title="无权限" description="请使用管理员账号登录后访问" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        tag="管理 · 服务商配置"
        title="配置中心"
        description="管理 AI 和搜索服务商，API Key 加密存储。修改后点击「重载到内存」即可生效，无需重启。"
      />

      {/* Tab */}
      <div className="flex rounded-xl border border-slate-200 bg-white p-1.5 shadow-sm">
        {([['ai', '🤖 AI 服务商', aiList.length], ['search', '🔍 搜索服务商', searchList.length]] as const).map(([key, label, count]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-150 ${
              tab === key ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            {label} ({count})
          </button>
        ))}
      </div>

      {/* Test result banner */}
      {testResult && (
        <div className={`rounded-lg border px-4 py-3 text-sm animate-fade-in ${
          testResult.success ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'
        }`}>
          {testResult.success
            ? `✓ 连通测试成功${testResult.model ? ` [${testResult.model}]` : ''} — 延迟 ${testResult.latency_ms}ms${testResult.reply ? `，回复: ${testResult.reply}` : ''}${testResult.status_code ? `, HTTP ${testResult.status_code}` : ''}`
            : `✕ 连通测试失败${testResult.model ? ` [${testResult.model}]` : ''} — ${testResult.error || '未知错误'}${testResult.latency_ms ? ` (${testResult.latency_ms}ms)` : ''}`
          }
          <button type="button" onClick={() => setTestResult(null)} className="ml-3 opacity-60 hover:opacity-100">关闭</button>
        </div>
      )}

      {/* Batch test results */}
      {batchResults.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm animate-fade-in">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
            <span className="text-sm font-medium text-slate-700">
              批量测试结果 — <span className="text-emerald-600">{batchResults.filter((r) => r.success).length} 通过</span>
              {batchResults.some((r) => !r.success) && (
                <span className="text-red-500"> / {batchResults.filter((r) => !r.success).length} 失败</span>
              )}
            </span>
            <button type="button" onClick={() => setBatchResults([])} className="text-xs text-slate-400 hover:text-slate-600">关闭</button>
          </div>
          <div className="divide-y divide-slate-50">
            {batchResults.map((r) => (
              <div key={r.model} className="flex items-center gap-3 px-4 py-2 text-sm">
                <span className={`inline-block h-2 w-2 flex-shrink-0 rounded-full ${r.success ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <span className="font-mono text-xs text-slate-700 min-w-[180px]">{r.model}</span>
                <span className="text-xs text-slate-500">{r.latency_ms}ms</span>
                {r.success
                  ? <span className="text-xs text-emerald-600 truncate">{r.reply || 'ok'}</span>
                  : <span className="text-xs text-red-500 truncate">{r.error}</span>
                }
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Tab */}
      {tab === 'ai' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={() => setAiEditing('new')}>＋ 新增 AI 服务商</Button>
            <Button variant="outline" onClick={() => void handleReloadAI()}>🔄 重载到内存</Button>
          </div>

          {aiEditing && (
            <Card>
              <h3 className="mb-4 font-semibold text-slate-900">{aiEditing === 'new' ? '新增 AI 服务商' : `编辑: ${aiEditing.name}`}</h3>
              <AIProviderForm
                initial={aiEditing === 'new' ? null : aiEditing}
                onSave={() => { setAiEditing(null); void loadAI() }}
                onCancel={() => setAiEditing(null)}
              />
            </Card>
          )}

          {aiLoading && <div className="text-sm text-slate-500">加载中...</div>}
          {!aiLoading && aiList.length === 0 && <EmptyState icon="🤖" title="暂无 AI 服务商" description="点击上方按钮新增" />}

          {aiList.map((p) => (
            <ProviderCard
              key={p.id}
              name={p.name}
              model={p.model}
              baseUrl={p.base_url}
              keyPreview={p.api_key_preview}
              isActive={p.is_active}
              priority={p.priority}
              weight={p.weight}
              timeout={p.timeout}
              description={p.description}
              roles={p.roles}
              lastTestAt={p.last_test_at}
              lastTestOk={p.last_test_ok}
              testing={aiTesting === p.id}
              onTest={(customPrompt) => void handleTestAI(p.id, customPrompt)}
              onTestBatch={(models, prompt) => void handleTestAIBatch(p.id, models, prompt)}
              onEdit={() => setAiEditing(p)}
              onDelete={() => void handleDeleteAI(p.id, p.name)}
            />
          ))}
        </div>
      )}

      {/* Search Tab */}
      {tab === 'search' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={() => setSearchEditing('new')}>＋ 新增搜索服务商</Button>
            <Button variant="outline" onClick={() => void handleReloadSearch()}>🔄 重载到内存</Button>
          </div>

          {searchEditing && (
            <Card>
              <h3 className="mb-4 font-semibold text-slate-900">{searchEditing === 'new' ? '新增搜索服务商' : `编辑: ${searchEditing.name}`}</h3>
              <SearchProviderForm
                initial={searchEditing === 'new' ? null : searchEditing}
                onSave={() => { setSearchEditing(null); void loadSearch() }}
                onCancel={() => setSearchEditing(null)}
              />
            </Card>
          )}

          {searchLoading && <div className="text-sm text-slate-500">加载中...</div>}
          {!searchLoading && searchList.length === 0 && <EmptyState icon="🔍" title="暂无搜索服务商" description="点击上方按钮新增" />}

          {searchList.map((p) => (
            <ProviderCard
              key={p.id}
              name={p.name}
              type={p.provider_type}
              baseUrl={p.base_url}
              keyPreview={p.api_key_preview}
              isActive={p.is_active}
              priority={p.priority}
              weight={p.weight}
              timeout={p.timeout}
              description={p.description}
              lastTestAt={p.last_test_at}
              lastTestOk={p.last_test_ok}
              testing={searchTesting === p.id}
              onTest={(customPrompt) => void handleTestSearch(p.id, customPrompt)}
              onTestBatch={() => {}}
              onEdit={() => setSearchEditing(p)}
              onDelete={() => void handleDeleteSearch(p.id, p.name)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default AdminProvidersPage
