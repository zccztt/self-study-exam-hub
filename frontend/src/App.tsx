import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import ExamPage from './pages/ExamPage'
import QuestionsPage from './pages/QuestionsPage'
import VideosPage from './pages/VideosPage'
import AnalysisPage from './pages/AnalysisPage'
import PlannerPage from './pages/PlannerPage'
import FavoritesPage from './pages/FavoritesPage'
import AuthPage from './pages/AuthPage'

const App: React.FC = () => {
  return (
    <Router basename={import.meta.env.BASE_URL}>
      <Layout>
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
      </Layout>
    </Router>
  )
}

export default App
