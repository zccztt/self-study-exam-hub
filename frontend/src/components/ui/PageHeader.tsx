import React from 'react'
import classNames from 'classnames'

interface PageHeaderProps {
  tag?: string
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

const PageHeader: React.FC<PageHeaderProps> = ({
  tag,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div
      className={classNames(
        'rounded-xl border border-slate-200 bg-white p-6 shadow-sm animate-fade-in',
        className,
      )}
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          {tag && <div className="mb-1 text-sm font-medium text-brand-600">{tag}</div>}
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">{title}</h1>
          {description && (
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">{description}</p>
          )}
        </div>
        {action && <div className="flex-shrink-0">{action}</div>}
      </div>
    </div>
  )
}

export default PageHeader
