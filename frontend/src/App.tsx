import React, { Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import { ToastProvider } from './components/ui'

const Home = React.lazy(() => import('./pages/Home'))
const ExamPage = React.lazy(() => import('./pages/ExamPage'))
const QuestionsPage = React.lazy(() => import('./pages/QuestionsPage'))
const VideosPage = React.lazy(() => import('./pages/VideosPage'))
const AnalysisPage = React.lazy(() => import('./pages/AnalysisPage'))
const PlannerPage = React.lazy(() => import('./pages/PlannerPage'))
const EnrollmentPage = React.lazy(() => import('./pages/EnrollmentPage'))
const FavoritesPage = React.lazy(() => import('./pages/FavoritesPage'))
const PastPaperPage = React.lazy(() => import('./pages/PastPaperPage'))
const ReplacementMapPage = React.lazy(() => import('./pages/ReplacementMapPage'))
const AuthPage = React.lazy(() => import('./pages/AuthPage'))
const ProfilePage = React.lazy(() => import('./pages/ProfilePage'))
const AdminProvidersPage = React.lazy(() => import('./pages/AdminProvidersPage'))

const App: React.FC = () => {
  return (
    <Router basename={import.meta.env.BASE_URL}>
      <ToastProvider>
      <Layout>
        <ErrorBoundary>
          <Suspense fallback={<div className="rounded-lg bg-blue-50 px-4 py-3 text-blue-700">页面加载中...</div>}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/exam" element={<ExamPage />} />
              <Route path="/past-papers" element={<PastPaperPage />} />
              <Route path="/questions" element={<QuestionsPage />} />
              <Route path="/videos" element={<VideosPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/planner" element={<PlannerPage />} />
              <Route path="/enrollment" element={<EnrollmentPage />} />
              <Route path="/favorites" element={<FavoritesPage />} />
              <Route path="/replacement-map" element={<ReplacementMapPage />} />
              <Route path="/auth" element={<AuthPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/admin/providers" element={<AdminProvidersPage />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </Layout>
      </ToastProvider>
    </Router>
  )
}


export default App
