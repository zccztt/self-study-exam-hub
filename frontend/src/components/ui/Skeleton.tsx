import React from 'react'
import classNames from 'classnames'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'rect' | 'circle'
  width?: string | number
  height?: string | number
  lines?: number
}

const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'rect',
  width,
  height,
  lines = 1,
}) => {
  const baseClass = 'animate-pulse-soft bg-slate-200 rounded'

  if (variant === 'circle') {
    return (
      <div
        className={classNames(baseClass, 'rounded-full', className)}
        style={{ width: width || 40, height: height || 40 }}
      />
    )
  }

  if (lines > 1) {
    return (
      <div className="space-y-2.5">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={classNames(baseClass, className)}
            style={{
              width: i === lines - 1 ? '75%' : width || '100%',
              height: height || (variant === 'text' ? 14 : 20),
            }}
          />
        ))}
      </div>
    )
  }

  return (
    <div
      className={classNames(baseClass, className)}
      style={{ width: width || '100%', height: height || 20 }}
    />
  )
}

export default Skeleton
