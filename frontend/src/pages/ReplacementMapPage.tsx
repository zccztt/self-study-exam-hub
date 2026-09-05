import React, { useEffect, useState, useMemo } from 'react'
import { enrollmentApi, ReplacementMapItem } from '../api/enrollment'

type GroupKey = 'public' | 'cs' | 'law' | 'special'

const GROUP_META: Record<GroupKey, { label: string; emoji: string; desc: string }> = {
  public: {
    label: '公共政治课替代',
    emoji: '📚',
    desc: '全专业通用，2025年起旧代码停用，已通过旧课程可直接替代新课程。',
  },
  cs: {
    label: '计算机科学与技术 (080901)',
    emoji: '💻',
    desc: '专业课课程替代，适用于计算机科学与技术专升本新计划。',
  },
  law: {
    label: '法律事务 (专科)',
    emoji: '⚖️',
    desc: '适用于法律事务专科新计划的专业课替代。',
  },
  special: {
    label: '特殊多对一替代',
    emoji: '🔀',
    desc: '原多门课程任一通过即可顶替新计划课程。',
  },
}

const PUBLIC_NEW_CODES = new Set(['15041', '15042', '15043', '15044'])
const CS_NEW_CODES = new Set([
  '13000', '00023', '02324', '13013', '13014', '13003', '13004',
  '13015', '13180', '14263', '13009', '13005', '13017', '14349',
])
const LAW_NEW_CODES = new Set(['14005', '07790', '00264'])
const SPECIAL_NEW_CODES = new Set(['05680'])

function classifyItem(item: ReplacementMapItem): GroupKey {
  if (PUBLIC_NEW_CODES.has(item.new_code)) return 'public'
  if (CS_NEW_CODES.has(item.new_code)) return 'cs'
  if (LAW_NEW_CODES.has(item.new_code)) return 'law'
  if (SPECIAL_NEW_CODES.has(item.new_code)) return 'special'
  return 'public'
}

const ReplacementMapPage: React.FC = () => {
  const [items, setItems] = useState<ReplacementMapItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    enrollmentApi
      .getReplacementMap()
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!search.trim()) return items
    const q = search.trim().toLowerCase()
    return items.filter(
      (it) =>
        it.new_code.includes(q) ||
        it.new_name.toLowerCase().includes(q) ||
        it.old_code.toLowerCase().includes(q) ||
        it.old_name.toLowerCase().includes(q) ||
        it.note.toLowerCase().includes(q),
    )
  }, [items, search])

  const grouped = useMemo(() => {
    const groups: Record<GroupKey, ReplacementMapItem[]> = { public: [], cs: [], law: [], special: [] }
    for (const item of filtered) {
      groups[classifyItem(item)].push(item)
    }
    return groups
  }, [filtered])

  const groupOrder: GroupKey[] = ['public', 'cs', 'law', 'special']

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900">
          🔄 新旧课程替代对照表
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          自2025年起，全国自学考试课程代码全面调整。已通过旧课程的考生，成绩可直接替代对应新课程，无需重新考试。
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索课程代码或名称..."
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 pl-10 text-sm shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
        />
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
      </div>

      {loading ? (
        <div className="py-16 text-center text-slate-400">加载中...</div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center">
          <p className="text-slate-500">未找到匹配的替代记录</p>
        </div>
      ) : (
        groupOrder.map((key) => {
          const groupItems = grouped[key]
          if (groupItems.length === 0) return null
          const meta = GROUP_META[key]
          return (
            <div key={key} className="rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-5 py-4">
                <h3 className="flex items-center gap-2 text-base font-semibold text-slate-800">
                  <span>{meta.emoji}</span> {meta.label}
                  <span className="text-xs font-normal text-slate-400">({groupItems.length}对)</span>
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">{meta.desc}</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/50 text-left text-slate-500">
                      <th className="px-5 py-2.5 font-medium">新代码</th>
                      <th className="px-5 py-2.5 font-medium">新课程名称</th>
                      <th className="px-5 py-2.5 font-medium">←</th>
                      <th className="px-5 py-2.5 font-medium">原代码</th>
                      <th className="px-5 py-2.5 font-medium">原课程名称</th>
                      <th className="px-5 py-2.5 font-medium">说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupItems.map((item) => (
                      <tr
                        key={item.new_code + item.old_code}
                        className="border-b border-slate-50 transition hover:bg-blue-50/40"
                      >
                        <td className="whitespace-nowrap px-5 py-3 font-mono font-semibold text-blue-700">
                          {item.new_code}
                        </td>
                        <td className="px-5 py-3 text-slate-800">
                          {item.new_name}
                        </td>
                        <td className="px-5 py-3 text-center text-slate-300">←</td>
                        <td className="whitespace-nowrap px-5 py-3 font-mono text-slate-400 line-through">
                          {item.old_code}
                        </td>
                        <td className="px-5 py-3 text-slate-500">{item.old_name}</td>
                        <td className="max-w-xs px-5 py-3 text-xs leading-5 text-amber-700">
                          {item.note}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })
      )}

      {/* Tips */}
      <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-5">
        <p className="text-sm font-medium text-amber-800">ℹ️ 重要提示</p>
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-amber-700">
          <li>如您已通过原课程代码的考试，请在「我的报考」中将新课程直接标记为“已过”。</li>
          <li>河北省自2026年起按新专业计划执行，之前已通过的旧代码课程成绩继续有效。</li>
          <li>新增课程（如 15040 习近平新时代中国特色社会主义思想概论）无旧代码对应，需单独报考。</li>
          <li>各省具体替代细则可能略有差异，请以当地考试院公告为准。</li>
        </ul>
      </div>
    </div>
  )
}

export default ReplacementMapPage
