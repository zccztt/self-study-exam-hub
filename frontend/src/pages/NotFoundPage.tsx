import React from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui'

const NotFoundPage: React.FC = () => {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center animate-fade-in">
      <div className="mb-6 text-7xl">📚</div>
      <h1 className="text-3xl font-bold text-slate-950">页面未找到</h1>
      <p className="mt-3 max-w-sm text-sm text-slate-500">
        你访问的页面不存在或已被移动，请返回首页继续备考。
      </p>
      <div className="mt-6">
        <Link to="/">
          <Button size="lg">返回首页</Button>
        </Link>
      </div>
    </div>
  )
}

export default NotFoundPage
