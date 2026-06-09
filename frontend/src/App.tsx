import React, { Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'

const Home = React.lazy(() => import('./pages/Home'))
const ExamPage = React.lazy(() => import('./pages/ExamPage'))
const QuestionsPage = React.lazy(() => import('./pages/QuestionsPage'))
const VideosPage = React.lazy(() => import('./pages/VideosPage'))
const AnalysisPage = React.lazy(() => import('./pages/AnalysisPage'))
const PlannerPage = React.lazy(() => import('./pages/PlannerPage'))
const FavoritesPage = React.lazy(() => import('./pages/FavoritesPage'))
const AuthPage = React.lazy(() => import('./pages/AuthPage'))

const App: React.FC = () => {
  return (
    <Router basename={import.meta.env.BASE_URL}>
      <Layout>
        <Suspense fallback={<div className="rounded-lg bg-blue-50 px-4 py-3 text-blue-700">页面加载中...</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/exam" element={<ExamPage />} />
            <Route path="/questions" element={<QuestionsPage />} />
            <Route path="/videos" element={<VideosPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/planner" element={<PlannerPage />} />
            <Route path="/favorites" element={<FavoritesPage />} />
            <Route path="/auth" element={<AuthPage />} />
          </Routes>
        </Suspense>
      </Layout>
    </Router>
  )
}


export default App
