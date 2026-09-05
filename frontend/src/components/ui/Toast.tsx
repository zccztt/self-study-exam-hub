import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import classNames from 'classnames'

type ToastType = 'success' | 'error' | 'info' | 'warning'

interface Toast {
  id: number
  type: ToastType
  message: string
  duration: number
}

interface ToastContextValue {
  success: (message: string, duration?: number) => void
  error: (message: string, duration?: number) => void
  info: (message: string, duration?: number) => void
  warning: (message: string, duration?: number) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let nextId = 0

const typeStyles: Record<ToastType, { bg: string; icon: string }> = {
  success: { bg: 'border-emerald-200 bg-emerald-50 text-emerald-800', icon: '✓' },
  error: { bg: 'border-red-200 bg-red-50 text-red-800', icon: '✕' },
  info: { bg: 'border-brand-200 bg-brand-50 text-brand-800', icon: 'ℹ' },
  warning: { bg: 'border-amber-200 bg-amber-50 text-amber-800', icon: '⚠' },
}

const ToastItem: React.FC<{ toast: Toast; onRemove: (id: number) => void }> = ({ toast, onRemove }) => {
  const [exiting, setExiting] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    timerRef.current = setTimeout(() => {
      setExiting(true)
      setTimeout(() => onRemove(toast.id), 200)
    }, toast.duration)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [toast.id, toast.duration, onRemove])

  const style = typeStyles[toast.type]

  return (
    <div
      className={classNames(
        'flex items-center gap-2.5 rounded-lg border px-4 py-3 text-sm font-medium shadow-lg backdrop-blur transition-all duration-200',
        style.bg,
        exiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100 animate-slide-up',
      )}
    >
      <span className="text-base leading-none">{style.icon}</span>
      <span className="flex-1">{toast.message}</span>
      <button
        type="button"
        onClick={() => { setExiting(true); setTimeout(() => onRemove(toast.id), 200) }}
        className="ml-2 opacity-60 hover:opacity-100 transition-opacity"
        aria-label="关闭"
      >
        ✕
      </button>
    </div>
  )
}

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((type: ToastType, message: string, duration = 3000) => {
    const id = ++nextId
    setToasts((current) => [...current.slice(-4), { id, type, message, duration }])
  }, [])

  const removeToast = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const contextValue: ToastContextValue = {
    success: useCallback((msg, dur) => addToast('success', msg, dur), [addToast]),
    error: useCallback((msg, dur) => addToast('error', msg, dur), [addToast]),
    info: useCallback((msg, dur) => addToast('info', msg, dur), [addToast]),
    warning: useCallback((msg, dur) => addToast('warning', msg, dur), [addToast]),
  }

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      {/* Toast container — fixed top-right */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2.5 w-80 max-w-[calc(100vw-2rem)] pointer-events-none">
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} onRemove={removeToast} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
