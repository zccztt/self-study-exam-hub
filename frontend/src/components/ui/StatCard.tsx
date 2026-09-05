import React from 'react'
import classNames from 'classnames'

interface StatCardProps {
  label: string
  value: string | number
  description?: string
  trend?: 'up' | 'down' | 'stable'
  color?: 'default' | 'brand' | 'success' | 'warning' | 'danger'
  className?: string
}

const colorStyles: Record<string, string> = {
  default: 'border-slate-200 bg-white',
  brand: 'border-brand-100 bg-brand-50',
  success: 'border-emerald-100 bg-emerald-50',
  warning: 'border-amber-100 bg-amber-50',
  danger: 'border-red-100 bg-red-50',
}

const trendIcons: Record<string, { icon: string; color: string }> = {
  up: { icon: '↑', color: 'text-emerald-600' },
  down: { icon: '↓', color: 'text-red-600' },
  stable: { icon: '→', color: 'text-slate-500' },
}

const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  description,
  trend,
  color = 'default',
  className,
}) => {
  return (
    <div
      className={classNames(
        'rounded-xl border p-5 shadow-sm animate-slide-up',
        colorStyles[color],
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-slate-500">{label}</span>
        {trend && (
          <span className={classNames('text-sm font-medium', trendIcons[trend].color)}>
            {trendIcons[trend].icon}
          </span>
        )}
      </div>
      <div className="mt-2 text-2xl font-bold text-slate-950">{value}</div>
      {description && <div className="mt-1 text-sm text-slate-500">{description}</div>}
    </div>
  )
}

export default StatCard
