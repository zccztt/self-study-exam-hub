import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'

// 页面组件（TODO: 实现具体页面）
const HomePage = () => <div>首页 - 功能导航</div>
const ExamPage = () => <div>模拟考试模块</div>
const QuestionBankPage = () => <div>题库搜索模块</div>
const VideoPage = () => <div>视频中心模块</div>
const AnalysisPage = () => <div>考点分析模块</div>
const PlannerPage = () => <div>学习规划模块</div>

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/exam" element={<ExamPage />} />
          <Route path="/questions" element={<QuestionBankPage />} />
          <Route path="/videos" element={<VideoPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/planner" element={<PlannerPage />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
