import React from 'react'
import classNames from 'classnames'

interface PaginationProps {
  current: number
  total: number
  pageSize: number
  loading?: boolean
  onChange: (page: number) => void
  className?: string
}

/**
 * 生成页码列表：始终显示首页、末页、当前页及其前后各 1 页，
 * 中间用 -1 表示省略号。
 */
function buildPageNumbers(current: number, totalPages: number): number[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }

  const pages = new Set<number>()
  pages.add(1)
  pages.add(totalPages)
  for (let i = current - 1; i <= current + 1; i++) {
    if (i >= 1 && i <= totalPages) pages.add(i)
  }

  const sorted = [...pages].sort((a, b) => a - b)
  const result: number[] = []
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
      result.push(-1) // 省略号占位
    }
    result.push(sorted[i])
  }
  return result
}

const btnBase =
  'min-w-[36px] rounded-lg px-3 py-2 text-sm font-medium shadow-sm transition select-none'
const btnNormal =
  'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40'
const btnActive = 'bg-blue-600 text-white border border-blue-600'
const btnEllipsis =
  'min-w-[36px] px-2 py-2 text-sm text-slate-400 cursor-default select-none'

const Pagination: React.FC<PaginationProps> = ({
  current,
  total,
  pageSize,
  loading = false,
  onChange,
  className,
}) => {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  if (totalPages <= 1 && total <= pageSize) return null

  const pageNumbers = buildPageNumbers(current, totalPages)

  const start = Math.min((current - 1) * pageSize + 1, total)
  const end = Math.min(current * pageSize, total)

  return (
    <div
      className={classNames(
        'flex flex-col items-center gap-3 sm:flex-row sm:justify-between',
        className,
      )}
    >
      {/* 左侧：总量信息 */}
      <div className="text-sm text-slate-500">
        共 <span className="font-medium text-slate-700">{total}</span> 条，
        第 {start}-{end} 条 · {current}/{totalPages} 页
      </div>

      {/* 右侧：页码 */}
      <div className="flex items-center gap-1">
        {/* 上一页 */}
        <button
          type="button"
          disabled={current <= 1 || loading}
          onClick={() => onChange(current - 1)}
          className={classNames(btnBase, btnNormal)}
          aria-label="上一页"
        >
          ‹
        </button>

        {/* 页码按钮 */}
        {pageNumbers.map((page, idx) =>
          page === -1 ? (
            <span key={`ellipsis-${idx}`} className={btnEllipsis}>
              ···
            </span>
          ) : (
            <button
              key={page}
              type="button"
              disabled={loading}
              onClick={() => page !== current && onChange(page)}
              className={classNames(
                btnBase,
                page === current ? btnActive : btnNormal,
              )}
            >
              {page}
            </button>
          ),
        )}

        {/* 下一页 */}
        <button
          type="button"
          disabled={current >= totalPages || loading}
          onClick={() => onChange(current + 1)}
          className={classNames(btnBase, btnNormal)}
          aria-label="下一页"
        >
          ›
        </button>
      </div>
    </div>
  )
}

export default Pagination
