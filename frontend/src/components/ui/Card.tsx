import React from 'react'
import classNames from 'classnames'

interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
}

interface CardHeaderProps {
  children: React.ReactNode
  className?: string
  action?: React.ReactNode
}

const paddingStyles = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

const Card: React.FC<CardProps> & { Header: React.FC<CardHeaderProps> } = ({
  children,
  className,
  padding = 'md',
  hover = false,
}) => {
  return (
    <div
      className={classNames(
        'rounded-xl border border-slate-200 bg-white shadow-sm animate-fade-in',
        paddingStyles[padding],
        hover && 'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md',
        className,
      )}
    >
      {children}
    </div>
  )
}

const CardHeader: React.FC<CardHeaderProps> = ({ children, className, action }) => {
  return (
    <div className={classNames('flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between', className)}>
      <div>{children}</div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}

Card.Header = CardHeader

export default Card
