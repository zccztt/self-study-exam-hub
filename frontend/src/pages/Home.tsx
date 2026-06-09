import React from 'react'
import { Link } from 'react-router-dom'

const modules = [
  {
    to: '/exam',
    title: '模拟考试',
    meta: '限时组卷 · 自动评分 · 错题归档',
    description: '按 2026 备考节奏生成随机卷、章节练习卷和错题重做卷，交卷后同步更新错题本与掌握度。',
    tone: 'bg-blue-50 text-blue-700 border-blue-100',
  },
  {
    to: '/questions',
    title: '题库搜索',
    meta: '2026 题库 · 多维筛选',
    description: '按课程、章节、年份、题型、难度和高频标记检索，题目详情包含答案解析和关联考点。',
    tone: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  },
  {
    to: '/analysis',
    title: '考点分析',
    meta: '知识树 · 高频趋势 · 作答模板',
    description: '查看每个考点的详细说明、易错点、答题层次和复习建议，用数据决定优先级。',
    tone: 'bg-violet-50 text-violet-700 border-violet-100',
  },
  {
    to: '/planner',
    title: '学习规划',
    meta: '阶段计划 · 周目标 · 每日时间块',
    description: '基于考试日期、每日时长、薄弱点和高频考点生成完整计划，并跟踪每日完成度。',
    tone: 'bg-amber-50 text-amber-700 border-amber-100',
  },
  {
    to: '/videos',
    title: '资源中心',
    meta: '真实视频 · 线上补充',
    description: '优先展示本地真实视频；没有匹配资源时线上搜索公开视频页并保存链接，视频详情可关联题目与章节。',
    tone: 'bg-rose-50 text-rose-700 border-rose-100',
  },
  {
    to: '/favorites',
    title: '收藏错题',
    meta: '收藏 · 错题 · 掌握状态',
    description: '集中管理收藏题目、资源和错题记录，支持标记掌握、筛选薄弱题。',
    tone: 'bg-slate-100 text-slate-700 border-slate-200',
  },
]

const officialLinks = [
  { label: '教育部教育考试院', href: 'https://www.neea.edu.cn/' },
  { label: '高等教育自学考试入口', href: 'https://zikao.neea.edu.cn/' },
  { label: 'B站：马克思主义基本原理公开视频', href: 'https://www.bilibili.com/video/BV1hW41167NW' },
  { label: 'B站：中国近现代史纲要公开视频', href: 'https://www.bilibili.com/video/BV1t4411e7Q5' },
]

const Home: React.FC = () => {
  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[1.4fr_0.9fr]">
          <div className="p-6 sm:p-8">
            <div className="mb-4 inline-flex rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">
              2026 自学考试备考工作台
            </div>
            <h1 className="max-w-3xl text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">
              从题库检索、模拟考试到间隔复习，形成完整备考闭环。
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              当前演示库已内置 2026 公共课课程、公开官方入口、B站真实视频资源、高频考点详情和系统学习计划。
              登录后可直接体验题库检索、组卷提交、错题归档、薄弱点识别和复习计划更新。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/planner" className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700">
                生成学习计划
              </Link>
              <Link to="/analysis" className="rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-800 hover:border-blue-300 hover:text-blue-700">
                查看考点详情
              </Link>
              <Link to="/auth" className="rounded-lg border border-slate-300 bg-slate-50 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-white">
                使用演示账号登录
              </Link>
            </div>
          </div>
          <aside className="border-t border-slate-200 bg-slate-950 p-6 text-white lg:border-l lg:border-t-0 sm:p-8">
            <div className="text-sm text-slate-300">默认演示账号</div>
            <div className="mt-3 rounded-lg bg-white/10 p-4">
              <div className="text-sm text-slate-300">用户名</div>
              <div className="text-2xl font-bold">demo</div>
              <div className="mt-3 text-sm text-slate-300">密码</div>
              <div className="text-2xl font-bold">demo123456</div>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg bg-white/10 p-3">
                <div className="text-slate-300">重点课程</div>
                <div className="mt-1 text-xl font-semibold">2 门</div>
              </div>
              <div className="rounded-lg bg-white/10 p-3">
                <div className="text-slate-300">备考年份</div>
                <div className="mt-1 text-xl font-semibold">2026</div>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {[
          ['考试窗口', '2026 年 4 月 / 10 月', '以各省教育考试院公告为准'],
          ['公共课代码', '15044 / 15043', '马原与中国近现代史纲要'],
          ['学习闭环', '题库 → 考试 → 错题 → 规划', '沉淀掌握度与薄弱点'],
          ['数据接入', '导入脚本 + 公开资源', '支持线上补充检索'],
        ].map(([label, value, desc]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-sm text-slate-500">{label}</div>
            <div className="mt-2 text-xl font-bold text-slate-950">{value}</div>
            <div className="mt-1 text-sm text-slate-500">{desc}</div>
          </div>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {modules.map((module) => (
          <Link key={module.to} to={module.to} className={`rounded-xl border bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${module.tone}`}>
            <div className="text-sm font-semibold">{module.meta}</div>
            <h2 className="mt-3 text-xl font-bold text-slate-950">{module.title}</h2>
            <p className="mt-2 min-h-20 text-sm leading-6 text-slate-600">{module.description}</p>
            <div className="mt-4 text-sm font-semibold">进入模块 →</div>
          </Link>
        ))}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-950">真实资源入口</h2>
            <p className="mt-1 text-sm text-slate-500">用于核对政策和查找公开视频资源，链接均为真实站点。</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {officialLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 hover:border-blue-300 hover:text-blue-700"
            >
              {link.label}
            </a>
          ))}
        </div>
      </section>
    </div>
  )
}

export default Home
