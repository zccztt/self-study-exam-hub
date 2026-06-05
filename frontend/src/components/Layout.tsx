import React from 'react'
import { Link } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center">
                <h1 className="text-xl font-bold text-gray-900">
                  自考真题学习系统
                </h1>
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Link to="/exam" className="text-gray-700 hover:text-gray-900">
                模拟考试
              </Link>
              <Link to="/questions" className="text-gray-700 hover:text-gray-900">
                题库搜索
              </Link>
              <Link to="/videos" className="text-gray-700 hover:text-gray-900">
                视频中心
              </Link>
              <Link to="/analysis" className="text-gray-700 hover:text-gray-900">
                考点分析
              </Link>
              <Link to="/planner" className="text-gray-700 hover:text-gray-900">
                学习规划
              </Link>
            </div>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-auto">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-500 text-sm">
            © 2024 自考真题模拟与学习系统. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}

export default Layout
