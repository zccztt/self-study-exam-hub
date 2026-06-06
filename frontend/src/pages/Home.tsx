import React from 'react'
import { Link } from 'react-router-dom'

const Home: React.FC = () => {
  return (
    <div className="px-4 py-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          自考真题模拟与学习系统
        </h1>
        <p className="text-xl text-gray-600">
          一站式自学考试备考平台：真题模拟 × 题库检索 × 视频资源 × 高频考点 × 智能规划
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
        {/* 模拟考试 */}
        <Link
          to="/exam"
          className="block p-6 bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <div className="text-blue-500 text-4xl mb-4">📝</div>
          <h2 className="text-2xl font-bold mb-2">模拟考试</h2>
          <p className="text-gray-600">
            还原真实考试场景，支持真题卷、随机组卷、章节练习、错题重做
          </p>
          <div className="mt-4 text-blue-500 font-semibold">开始考试 →</div>
        </Link>

        {/* 题库搜索 */}
        <Link
          to="/questions"
          className="block p-6 bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <div className="text-green-500 text-4xl mb-4">🔍</div>
          <h2 className="text-2xl font-bold mb-2">题库搜索</h2>
          <p className="text-gray-600">
            全文检索，多维筛选，支持按年份、题型、难度、章节快速定位题目
          </p>
          <div className="mt-4 text-green-500 font-semibold">搜索题目 →</div>
        </Link>

        {/* 视频中心 */}
        <Link
          to="/videos"
          className="block p-6 bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <div className="text-purple-500 text-4xl mb-4">🎬</div>
          <h2 className="text-2xl font-bold mb-2">视频中心</h2>
          <p className="text-gray-600">
            聚合B站、网易公开课等平台视频资源，与题目、考点智能关联
          </p>
          <div className="mt-4 text-purple-500 font-semibold">观看视频 →</div>
        </Link>

        {/* 考点分析 */}
        <Link
          to="/analysis"
          className="block p-6 bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <div className="text-red-500 text-4xl mb-4">📊</div>
          <h2 className="text-2xl font-bold mb-2">考点分析</h2>
          <p className="text-gray-600">
            高频考点大纲、可视化数据分析、知识点热力图、趋势预测
          </p>
          <div className="mt-4 text-red-500 font-semibold">查看分析 →</div>
        </Link>

        {/* 学习规划 */}
        <Link
          to="/planner"
          className="block p-6 bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <div className="text-yellow-500 text-4xl mb-4">🗓️</div>
          <h2 className="text-2xl font-bold mb-2">学习规划</h2>
          <p className="text-gray-600">
            基于薄弱点识别和遗忘曲线，生成个性化学习计划和每日任务
          </p>
          <div className="mt-4 text-yellow-500 font-semibold">制定计划 →</div>
        </Link>

        <Link
          to="/favorites"
          className="block p-6 bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
        >
          <div className="text-pink-500 text-4xl mb-4">⭐</div>
          <h2 className="text-2xl font-bold mb-2">我的收藏</h2>
          <p className="text-gray-600">
            收藏的题目和视频，支持自定义标签分类管理
          </p>
          <div className="mt-4 text-pink-500 font-semibold">查看收藏 →</div>
        </Link>
      </div>

      {/* 特性介绍 */}
      <div className="mt-16 max-w-4xl mx-auto">
        <h3 className="text-2xl font-bold text-center mb-8">核心特性</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex items-start space-x-3">
            <div className="text-blue-500 text-2xl">✓</div>
            <div>
              <h4 className="font-semibold mb-1">真题模拟考试</h4>
              <p className="text-gray-600 text-sm">
                历年真题、智能组卷、自动评分、错题归档
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <div className="text-green-500 text-2xl">✓</div>
            <div>
              <h4 className="font-semibold mb-1">全文搜索引擎</h4>
              <p className="text-gray-600 text-sm">
                基于Elasticsearch，支持分词和语义匹配
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <div className="text-purple-500 text-2xl">✓</div>
            <div>
              <h4 className="font-semibold mb-1">视频资源聚合</h4>
              <p className="text-gray-600 text-sm">
                多平台视频关联，与题目、考点智能匹配
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <div className="text-red-500 text-2xl">✓</div>
            <div>
              <h4 className="font-semibold mb-1">数据可视化分析</h4>
              <p className="text-gray-600 text-sm">
                高频考点、趋势图、热力图、词云等多维度展示
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
