import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const titleMap: Record<string, string> = {
  '/': '首页',
  '/exam': '模拟考试',
  '/questions': '题库搜索',
  '/videos': '资源中心',
  '/analysis': '考点分析',
  '/planner': '学习规划',
  '/favorites': '收藏错题',
  '/auth': '登录',
  '/account': '账户设置',
  '/admin': '管理后台',
}

const BASE_TITLE = '自考备考中枢'

export function useDocumentTitle() {
  const { pathname } = useLocation()

  useEffect(() => {
    const pageTitle = titleMap[pathname]
    document.title = pageTitle ? `${pageTitle} - ${BASE_TITLE}` : BASE_TITLE
  }, [pathname])
}
