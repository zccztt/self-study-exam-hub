import React, { useEffect, useState } from 'react'
import { userProviderApi, UserProviderConfig, UserProviderCreate, EffectiveConfig } from '../api/userProvider'
import { Badge, Button, Card, EmptyState, useToast } from './ui'

type ConfigTab = 'ai' | 'search'

const UserProvidersSection: React.FC = () => {
  const toast = useToast()
  const [tab, setTab] = useState<ConfigTab>('ai')
  const [configs, setConfigs] = useState<UserProviderConfig[]>([])
  const [effective, setEffective] = useState<EffectiveConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<UserProviderConfig | null | 'new'>(null)

  const load = async () => {
    setLoading(true)
    try {
      const [list, eff] = await Promise.all([
        userProviderApi.list(),
        userProviderApi.effective(),
      ])
      setConfigs(list)
      setEffective(eff)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`确定删除「${name}」？`)) return
    try {
      await userProviderApi.delete(id)
      toast.success('已删除')
      void load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  const filtered = configs.filter((c) => c.config_type === tab)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">🔑 服务商配置</h2>
      </div>

      {/* Effective status */}
      {effective && (
        <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
          <div className="font-medium mb-1">当前生效配置</div>
          <div className="flex flex-wrap gap-4">
            <span>
              AI: <Badge variant={effective.ai.source === 'user' ? 'success' : 'primary'}>{effective.ai.source === 'user' ? '个人配置' : effective.ai.source === 'admin' ? '管理员配置' : '未配置'}</Badge>
              {effective.ai.count > 0 && <span className="ml-1 text-xs">({effective.ai.count} 个)</span>}
            </span>
            <span>
              搜索: <Badge variant={effective.search.source === 'user' ? 'success' : 'primary'}>{effective.search.source === 'user' ? '个人配置' : effective.search.source === 'admin' ? '管理员配置' : '未配置'}</Badge>
            </span>
          </div>
          <div className="mt-1.5 text-xs text-brand-600">
            💡 默认使用管理员全局配置。添加个人配置后，将优先使用您自己的服务商。
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
        {([
          ['ai', '🤖 AI 服务商'],
          ['search', '🔍 搜索服务商'],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => { setTab(key); setEditing(null) }}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition ${
              tab === key ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            {label} ({configs.filter(c => c.config_type === key).length})
          </button>
        ))}
      </div>

      <Button size="sm" onClick={() => setEditing('new')}>＋ 添加{tab === 'ai' ? 'AI' : '搜索'}服务商</Button>

      {/* Form */}
      {editing && (
        <Card>
          <h3 className="mb-3 font-semibold text-slate-900">
            {editing === 'new' ? `新增${tab === 'ai' ? 'AI' : '搜索'}服务商` : `编辑: ${editing.name}`}
          </h3>
          <ConfigForm
            tab={tab}
            initial={editing === 'new' ? null : editing}
            onSave={() => { setEditing(null); void load() }}
            onCancel={() => setEditing(null)}
          />
        </Card>
      )}

      {/* List */}
      {loading && <div className="text-sm text-slate-500">加载中...</div>}
      {!loading && filtered.length === 0 && !editing && (
        <EmptyState
          icon={tab === 'ai' ? '🤖' : '🔍'}
          title={`暂无个人${tab === 'ai' ? 'AI' : '搜索'}配置`}
          description="将使用管理员全局配置"
        />
      )}

      {filtered.map((c) => (
        <Card key={c.id}>
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-1.5">
                <span className="font-semibold text-slate-900">{c.name}</span>
                <Badge variant={c.is_active ? 'success' : 'danger'}>{c.is_active ? '启用' : '停用'}</Badge>
                {c.model && <Badge>{c.model}</Badge>}
                {c.provider_type && <Badge variant="primary">{c.provider_type}</Badge>}
              </div>
              <div className="text-xs text-slate-500 space-y-0.5">
                <div className="truncate">URL: <span className="text-slate-700">{c.base_url}</span></div>
                <div>Key: <span className="font-mono text-slate-700">{c.api_key_preview}</span></div>
                {c.description && <div className="text-slate-600">{c.description}</div>}
              </div>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setEditing(c)}>编辑</Button>
            <Button variant="danger" size="sm" onClick={() => void handleDelete(c.id, c.name)}>删除</Button>
          </div>
        </Card>
      ))}
    </div>
  )
}

// ------------------------------------------------------------------
// Inline form
// ------------------------------------------------------------------

const ConfigForm: React.FC<{
  tab: ConfigTab
  initial: UserProviderConfig | null
  onSave: () => void
  onCancel: () => void
}> = ({ tab, initial, onSave, onCancel }) => {
  const toast = useToast()
  const [form, setForm] = useState({
    name: initial?.name || '',
    base_url: initial?.base_url || '',
    api_key: '',
    model: initial?.model || '',
    provider_type: initial?.provider_type || (tab === 'search' ? 'tavily' : ''),
    timeout: initial?.timeout || 30,
    description: initial?.description || '',
    is_active: initial?.is_active ?? true,
  })
  const [saving, setSaving] = useState(false)

  const set = (key: string, value: any) => setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (initial) {
        const payload: Record<string, any> = { ...form }
        if (!payload.api_key) delete payload.api_key
        await userProviderApi.update(initial.id, payload)
        toast.success('配置已更新')
      } else {
        await userProviderApi.create({
          config_type: tab,
          name: form.name,
          base_url: form.base_url,
          api_key: form.api_key,
          model: tab === 'ai' ? form.model : undefined,
          provider_type: tab === 'search' ? form.provider_type : undefined,
          timeout: form.timeout,
          description: form.description || undefined,
        } as UserProviderCreate)
        toast.success('配置已创建')
      }
      onSave()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const inputClass = 'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100'
  const noAutoFill = { autoComplete: 'off', 'data-lpignore': 'true', 'data-1p-ignore': 'true', 'data-form-type': 'other' } as const

  return (
    <form onSubmit={handleSubmit} className="space-y-3" autoComplete="off">
      {/* Hidden dummy fields to trick browser autofill */}
      <input type="text" name="_prevent_af1" style={{ display: 'none' }} tabIndex={-1} />
      <input type="password" name="_prevent_af2" style={{ display: 'none' }} tabIndex={-1} />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="space-y-1">
          <label className="block text-sm font-medium text-slate-700">名称 <span className="text-red-500">*</span></label>
          <input className={inputClass} {...noAutoFill} name="_naf_name" value={form.name} onChange={(e) => set('name', e.target.value)} required placeholder="如 my-openai" />
        </div>
        {tab === 'ai' && (
          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-700">模型 <span className="text-red-500">*</span></label>
            <input className={inputClass} {...noAutoFill} name="_naf_model" value={form.model} onChange={(e) => set('model', e.target.value)} required placeholder="如 gpt-4o" />
          </div>
        )}
        {tab === 'search' && (
          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-700">类型 <span className="text-red-500">*</span></label>
            <select className={inputClass} value={form.provider_type} onChange={(e) => set('provider_type', e.target.value)}>
              <option value="tavily">Tavily</option>
              <option value="search_api">Search API (SearXNG等)</option>
              <option value="custom">自定义</option>
            </select>
          </div>
        )}
        <div className="space-y-1 md:col-span-2">
          <label className="block text-sm font-medium text-slate-700">Base URL <span className="text-red-500">*</span></label>
          <input className={inputClass} {...noAutoFill} name="_naf_url" value={form.base_url} onChange={(e) => set('base_url', e.target.value)} required placeholder="https://api.openai.com/v1" />
        </div>
        <div className="space-y-1">
          <label className="block text-sm font-medium text-slate-700">{initial ? 'API Key（留空不修改）' : 'API Key'} {!initial && <span className="text-red-500">*</span>}</label>
          <input className={inputClass} type="text" {...noAutoFill} autoComplete="new-password" name="_naf_key" value={form.api_key} onChange={(e) => set('api_key', e.target.value)} required={!initial} placeholder={initial ? initial.api_key_preview : '请输入 API Key'} style={{ WebkitTextSecurity: 'disc' } as React.CSSProperties} />
        </div>
        <div className="space-y-1">
          <label className="block text-sm font-medium text-slate-700">超时(秒)</label>
          <input className={inputClass} {...noAutoFill} name="_naf_timeout" type="number" value={form.timeout} onChange={(e) => set('timeout', Number(e.target.value))} min={3} max={300} />
        </div>
      </div>
      <div className="space-y-1">
        <label className="block text-sm font-medium text-slate-700">描述</label>
        <input className={inputClass} {...noAutoFill} name="_naf_desc" value={form.description} onChange={(e) => set('description', e.target.value)} placeholder="可选备注" />
      </div>
      {initial && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_active} onChange={(e) => set('is_active', e.target.checked)} className="rounded" />
          启用
        </label>
      )}
      <div className="flex gap-2">
        <Button type="submit" size="sm" loading={saving}>{initial ? '保存修改' : '新增配置'}</Button>
        <Button variant="outline" size="sm" type="button" onClick={onCancel}>取消</Button>
      </div>
    </form>
  )
}

export default UserProvidersSection
