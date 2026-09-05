import React from 'react'
import classNames from 'classnames'

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: React.ReactNode
  block?: boolean
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-brand-600 text-white shadow-sm hover:bg-brand-700 active:scale-[0.97] disabled:bg-slate-300 disabled:text-slate-500',
  secondary:
    'bg-slate-900 text-white shadow-sm hover:bg-slate-800 active:scale-[0.97] disabled:bg-slate-300 disabled:text-slate-500',
  outline:
    'border border-slate-200 bg-white text-slate-700 shadow-sm hover:border-brand-300 hover:text-brand-700 active:scale-[0.97] disabled:opacity-50',
  ghost:
    'text-slate-600 hover:bg-slate-100 hover:text-slate-900 active:scale-[0.97] disabled:opacity-50',
  danger:
    'border border-red-200 bg-white text-red-600 shadow-sm hover:bg-red-50 active:scale-[0.97] disabled:opacity-50',
}

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm rounded-lg',
  md: 'px-4 py-2.5 text-sm rounded-lg',
  lg: 'px-5 py-3 text-sm font-semibold rounded-lg',
}

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  block = false,
  className,
  children,
  disabled,
  ...props
}) => {
  return (
    <button
      className={classNames(
        'inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2',
        variantStyles[variant],
        sizeStyles[size],
        block && 'w-full',
        (disabled || loading) && 'cursor-not-allowed',
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {!loading && icon}
      {children}
    </button>
  )
}

export default Button
