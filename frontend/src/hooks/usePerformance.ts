import { useEffect, useRef } from 'react'

/**
 * Debounce a callback. Returns a stable function reference
 * that delays invocation until `delay` ms after the last call.
 */
export function useDebounce<T extends (...args: unknown[]) => void>(
  callback: T,
  delay: number,
): T {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const callbackRef = useRef(callback)

  useEffect(() => {
    callbackRef.current = callback
  }, [callback])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const debounced = ((...args: unknown[]) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      callbackRef.current(...args)
    }, delay)
  }) as T

  return debounced
}

/**
 * Creates an AbortController that auto-aborts on unmount or deps change.
 * Use this for API calls that should cancel when the component re-renders.
 */
export function useAbortController(deps: unknown[] = []): () => AbortController {
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => {
      controllerRef.current?.abort()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return () => {
    controllerRef.current?.abort()
    controllerRef.current = new AbortController()
    return controllerRef.current
  }
}

/**
 * IntersectionObserver hook for lazy-loading sections.
 */
export function useInView(
  callback: () => void,
  options?: IntersectionObserverInit,
): React.RefObject<HTMLDivElement> {
  const ref = useRef<HTMLDivElement>(null)
  const calledRef = useRef(false)

  useEffect(() => {
    if (!ref.current || calledRef.current) return
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !calledRef.current) {
        calledRef.current = true
        callback()
        observer.disconnect()
      }
    }, { threshold: 0.1, ...options })
    observer.observe(ref.current)
    return () => observer.disconnect()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callback])

  return ref
}
