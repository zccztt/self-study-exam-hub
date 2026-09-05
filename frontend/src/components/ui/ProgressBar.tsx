import React from 'react'
import classNames from 'classnames'

interface ProgressBarProps {
  value: number
  max?: number
  size?: 'sm' | 'md' | 'lg'
  color?: 'brand' | 'success' | 'warning' | 'danger'
  showLabel?: boolean
  className?: string
}

const colorStyles: Record<string, string> = {
  brand: 'bg-brand-500',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
}

const sizeStyles: Record<string, string> = {
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-4',
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  size = 'md',
  color = 'brand',
  showLabel = false,
  className,
}) => {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div className={classNames('w-full', className)}>
      {showLabel && (
        <div className="mb-1.5 flex items-center justify-between text-sm">
          <span className="text-slate-600">{Math.round(percentage)}%</span>
        </div>
      )}
      <div className={classNames('w-full overflow-hidden rounded-full bg-slate-100', sizeStyles[size])}>
        <div
          className={classNames(
            'rounded-full transition-all duration-500 ease-out',
            colorStyles[color],
            sizeStyles[size],
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

export default ProgressBar
