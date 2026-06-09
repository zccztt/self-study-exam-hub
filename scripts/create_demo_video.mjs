import { mkdir, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { spawn } from 'node:child_process'

const ROOT = resolve(new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'))
const OUT_DIR = join(ROOT, 'docs', 'demo')
const FFMPEG_CANDIDATES = [
  process.env.FFMPEG_PATH,
  'D:\\warzip\\EVCapture\\ffmpeg.exe',
  'C:\\Program Files\\Red Giant\\Trapcode Suite\\Tools\\ffmpeg.exe',
  'ffmpeg',
].filter(Boolean)

const slides = [
  {
    title: '系统概览',
    tag: '首页工作台',
    duration: 7,
    bullets: [
      '面向自学考试备考的一站式学习平台。',
      '核心闭环：题库检索 -> 模拟考试 -> 考点分析 -> 学习规划 -> 错题复盘。',
      '演示库已内置 2026 自考课程、公开资源入口、高频考点和演示账号。',
    ],
    sideTitle: '入口信息',
    sideItems: ['演示账号：demo', '密码：demo123456', '本地前端：http://127.0.0.1:3000'],
  },
  {
    title: '登录与账号模块',
    tag: 'Auth',
    duration: 6,
    bullets: [
      '支持演示账号登录和新用户注册。',
      '登录后保存访问令牌，前端 API 自动携带 Authorization。',
      '演示账号可直接体验组卷、收藏、错题和学习计划流程。',
    ],
    sideTitle: '关键页面',
    sideItems: ['/auth', '演示账号填充', '注册与登录切换'],
  },
  {
    title: '题库搜索模块',
    tag: 'Questions',
    duration: 8,
    bullets: [
      '支持关键词、课程代码、科目、年份、章节、题型、难度等多维筛选。',
      '题目卡片展示来源、频次、题型和科目，并可展开答案解析。',
      '本地题库不足时预留线上补充能力，题源链接可回溯。',
    ],
    sideTitle: '可演示动作',
    sideItems: ['搜索“矛盾”', '筛选 2026 年题库', '查看答案并收藏'],
  },
  {
    title: '模拟考试模块',
    tag: 'Exam',
    duration: 8,
    bullets: [
      '支持年份卷、随机组卷、章节练习、错题重做四种模式。',
      '考试过程中显示剩余时间、答题进度和试题类型。',
      '提交后自动评分，客观题判分，主观题展示参考答案和评分点。',
    ],
    sideTitle: '考试流程',
    sideItems: ['选择科目与模式', '生成试卷并开始', '答题 -> 交卷 -> 分析'],
  },
  {
    title: '考点分析模块',
    tag: 'Analysis',
    duration: 8,
    bullets: [
      '按知识树、高频考点、章节热度和题型分布拆解备考重点。',
      '选中考点后展示命题重点、答题模板、常见易错和学习建议。',
      '趋势和预测数据帮助确定下一阶段复习优先级。',
    ],
    sideTitle: '分析视图',
    sideItems: ['高频考点 Top 20', '章节出题频次', '年度趋势与预测'],
  },
  {
    title: '学习规划模块',
    tag: 'Planner',
    duration: 8,
    bullets: [
      '根据考试日期、每日学习时长和报考科目生成备考计划。',
      '计划包括阶段目标、周目标、每日时间块、里程碑和风险提示。',
      '今日任务支持勾选完成，系统同步更新完成率和弱点分配。',
    ],
    sideTitle: '计划输出',
    sideItems: ['阶段计划', '周目标', '每日任务', '薄弱点识别'],
  },
  {
    title: '资源中心模块',
    tag: 'Videos',
    duration: 7,
    bullets: [
      '聚合公开学习视频，优先展示本地真实链接。',
      '支持按科目、章节、来源和关键词筛选。',
      '视频详情可关联训练题，便于看课后立刻刷题巩固。',
    ],
    sideTitle: '资源能力',
    sideItems: ['B站等公开视频', '视频收藏', '关联训练题'],
  },
  {
    title: '收藏与错题本',
    tag: 'Favorites',
    duration: 7,
    bullets: [
      '统一管理题目收藏、视频收藏和错题记录。',
      '错题本支持关键词、科目和掌握状态筛选。',
      '每道错题保留用户答案、参考答案、解析和关联考点。',
    ],
    sideTitle: '复盘动作',
    sideItems: ['取消收藏', '筛选错题', '标记已掌握'],
  },
  {
    title: '线上部署结论',
    tag: 'Deploy',
    duration: 8,
    bullets: [
      '完整系统不能直接部署到 GitHub Pages，因为 Pages 不能运行 FastAPI 后端和数据库服务。',
      'GitHub Pages 可以部署前端静态站点，但必须配置线上 API 地址。',
      '推荐：前端走 GitHub Pages，后端和 PostgreSQL/Redis/Elasticsearch/MinIO 部署到云服务器或托管平台。',
    ],
    sideTitle: '已补充文件',
    sideItems: ['docs/DEPLOYMENT.md', '.github/workflows/deploy-pages.yml', 'Vite base 与 Router basename'],
  },
]

function findFfmpeg() {
  const found = FFMPEG_CANDIDATES.find((candidate) => candidate === 'ffmpeg' || existsSync(candidate))
  if (!found) {
    throw new Error('未找到 ffmpeg，请设置 FFMPEG_PATH 后重试。')
  }
  return found
}

function assTime(seconds) {
  const whole = Math.floor(seconds)
  const centiseconds = Math.floor((seconds - whole) * 100)
  const h = Math.floor(whole / 3600)
  const m = Math.floor((whole % 3600) / 60)
  const s = whole % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(centiseconds).padStart(2, '0')}`
}

function escapeAss(text) {
  return text.replaceAll('\\', '\\\\').replaceAll('{', '\\{').replaceAll('}', '\\}')
}

function dialogue(start, end, style, text) {
  return `Dialogue: 0,${assTime(start)},${assTime(end)},${style},,0,0,0,,${text}`
}

function makeAss() {
  let cursor = 0
  const events = []
  const total = slides.reduce((sum, slide) => sum + slide.duration, 0)

  for (const [index, slide] of slides.entries()) {
    const start = cursor
    const end = cursor + slide.duration
    const body = slide.bullets.map((item) => `• ${escapeAss(item)}`).join('\\N')
    const side = slide.sideItems.map((item) => `- ${escapeAss(item)}`).join('\\N')

    events.push(dialogue(start, end, 'Header', '{\\pos(64,30)}自考真题模拟与学习系统  |  功能演示'))
    events.push(dialogue(start, end, 'Page', `{\\pos(1130,32)}${index + 1} / ${slides.length}`))
    events.push(dialogue(start, end, 'Tag', `{\\pos(94,122)}${escapeAss(slide.tag)}`))
    events.push(dialogue(start, end, 'Title', `{\\pos(94,174)}${escapeAss(slide.title)}`))
    events.push(dialogue(start, end, 'Body', `{\\pos(94,246)}${body}`))
    events.push(dialogue(start, end, 'SideTitle', `{\\pos(904,178)}${escapeAss(slide.sideTitle)}`))
    events.push(dialogue(start, end, 'SideBody', `{\\pos(904,244)}${side}`))
    events.push(dialogue(start, end, 'Footer', `{\\pos(64,674)}本视频由 scripts/create_demo_video.mjs 生成；完整部署说明见 docs/DEPLOYMENT.md`))
    events.push(dialogue(start, end, 'Progress', `{\\pos(64,646)}${'━'.repeat(Math.max(3, Math.round(((index + 1) / slides.length) * 48)))}`))
    cursor = end
  }

  return {
    total,
    text: `[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Header,Microsoft YaHei,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Page,Microsoft YaHei,22,&H00DBEAFE,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Tag,Microsoft YaHei,22,&H00FFFFFF,&H000000FF,&H003B82F6,&H003B82F6,-1,0,0,0,100,100,0,0,3,12,0,7,0,0,0,1
Style: Title,Microsoft YaHei,46,&H000F172A,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Body,Microsoft YaHei,28,&H00334155,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: SideTitle,Microsoft YaHei,30,&H000F172A,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: SideBody,Microsoft YaHei,24,&H00475569,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Footer,Microsoft YaHei,18,&H0064758B,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Progress,Microsoft YaHei,18,&H003B82F6,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
${events.join('\n')}
`,
  }
}

function run(command, args, options = {}) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, { ...options, stdio: ['ignore', 'pipe', 'pipe'] })
    let stderr = ''
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString()
    })
    child.on('error', reject)
    child.on('close', (code) => {
      if (code === 0) resolveRun()
      else reject(new Error(`${command} exited with ${code}\n${stderr}`))
    })
  })
}

async function writeScriptMarkdown(videoPath) {
  const lines = [
    '# 演示视频脚本',
    '',
    `成片文件：\`${videoPath}\``,
    '',
    '## 镜头顺序',
    '',
  ]
  slides.forEach((slide, index) => {
    lines.push(`${index + 1}. ${slide.title}`)
    lines.push(`   ${slide.bullets.join(' ')}`)
  })
  lines.push('')
  lines.push('## 口播稿')
  lines.push('')
  lines.push('这是一个面向自学考试备考的真题模拟与学习系统。首页展示备考工作台、演示账号和主要功能入口。登录后，用户可以进入题库搜索，按课程、年份、题型、难度和高频标记定位题目，并查看答案解析。模拟考试模块支持年份卷、随机卷、章节练习和错题重做，提交后自动评分并沉淀错题。考点分析模块展示知识树、高频考点、章节热度、题型分布和趋势预测。学习规划模块根据考试日期、每日学习时长和报考科目生成阶段计划、周目标和每日任务。资源中心聚合公开视频并关联训练题，收藏与错题本用于复盘题目、视频和薄弱点。上线时，GitHub Pages 只能部署前端静态页面，完整系统还需要单独部署 FastAPI 后端和数据库等服务。')
  await writeFile(join(OUT_DIR, 'demo-script.md'), lines.join('\n'), 'utf8')
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true })
  const ffmpeg = findFfmpeg()
  const ass = makeAss()
  const assPath = join(OUT_DIR, 'demo-video.ass')
  const output = join(OUT_DIR, 'self-study-exam-hub-demo.mp4')
  await writeFile(assPath, ass.text, 'utf8')

  const filter = [
    'drawbox=x=0:y=0:w=1280:h=720:color=0xf4f7fb:t=fill',
    'drawbox=x=0:y=0:w=1280:h=84:color=0x0f172a:t=fill',
    'drawbox=x=0:y=84:w=1280:h=6:color=0x2563eb:t=fill',
    'drawbox=x=64:y=118:w=792:h=506:color=0xffffff@0.96:t=fill',
    'drawbox=x=64:y=118:w=792:h=506:color=0xd8e1ec:t=2',
    'drawbox=x=884:y=118:w=332:h=506:color=0xeef6ff@0.96:t=fill',
    'drawbox=x=884:y=118:w=332:h=506:color=0xbfdbfe:t=2',
    'drawbox=x=64:y=640:w=1152:h=10:color=0xdbeafe:t=fill',
    'ass=demo-video.ass',
    'format=yuv420p',
  ].join(',')

  await run(ffmpeg, [
    '-y',
    '-f',
    'lavfi',
    '-i',
    `color=c=0xf4f7fb:s=1280x720:r=30:d=${ass.total}`,
    '-vf',
    filter,
    '-c:v',
    'libx264',
    '-preset',
    'veryfast',
    '-crf',
    '20',
    '-t',
    String(ass.total),
    'self-study-exam-hub-demo.mp4',
  ], { cwd: OUT_DIR })

  await writeScriptMarkdown('docs/demo/self-study-exam-hub-demo.mp4')
  console.log(`Demo video: ${output}`)
  console.log(`Script: ${join(OUT_DIR, 'demo-script.md')}`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
