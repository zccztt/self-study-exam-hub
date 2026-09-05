import React from 'react'
import classNames from 'classnames'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'sm' | 'md'
  pill?: boolean
  className?: string
}

const variantStyles: Record<string, string> = {
  default: 'bg-slate-100 text-slate-700',
  primary: 'bg-brand-100 text-brand-700',
  success: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  danger: 'bg-red-100 text-red-700',
  info: 'bg-violet-100 text-violet-700',
}

const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  pill = false,
  className,
}) => {
  return (
    <span
      className={classNames(
        'inline-flex items-center font-medium',
        variantStyles[variant],
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        pill ? 'rounded-full' : 'rounded',
        className,
      )}
    >
      {children}
    </span>
  )
}

export default Badge
