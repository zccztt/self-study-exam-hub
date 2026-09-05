import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { sessionStore } from '../api/session'

interface ProtectedRouteProps {
  children: React.ReactElement
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const location = useLocation()

  if (!sessionStore.getToken()) {
    const next = `${location.pathname}${location.search}`
    return <Navigate to={`/auth?next=${encodeURIComponent(next)}`} replace />
  }

  return children
}

export default ProtectedRoute
