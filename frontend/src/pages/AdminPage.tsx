import React, { useCallback, useEffect, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Statistic, Table, Tabs, Tag, Upload, message } from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined, UploadOutlined, UserOutlined, BookOutlined, FileTextOutlined, VideoCameraOutlined, ApartmentOutlined, DashboardOutlined } from '@ant-design/icons'
import {
  adminApi,
  AdminChapter,
  AdminQuestion,
  AdminSubject,
  AdminUser,
  AdminVideo,
  DashboardData,
} from '../api/admin'

const { TabPane } = Tabs

// ─── Dashboard Tab ────────────────────────────────────────────────────────────

const DashboardTab: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null)
  useEffect(() => { adminApi.dashboard().then(setData).catch(() => {}) }, [])
  if (!data) return <div className="py-8 text-center text-slate-500">加载中...</div>
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      <Card><Statistic title="用户" value={data.user_count} prefix={<UserOutlined />} /></Card>
      <Card><Statistic title="科目" value={data.subject_count} prefix={<BookOutlined />} /></Card>
      <Card><Statistic title="题目" value={data.question_count} prefix={<FileTextOutlined />} /></Card>
      <Card><Statistic title="视频" value={data.video_count} prefix={<VideoCameraOutlined />} /></Card>
      <Card><Statistic title="章节" value={data.chapter_count} prefix={<ApartmentOutlined />} /></Card>
      <Card><Statistic title="考试次数" value={data.exam_session_count} prefix={<DashboardOutlined />} /></Card>
    </div>
  )
}

// ─── Users Tab ────────────────────────────────────────────────────────────────

const UsersTab: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AdminUser | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(() => {
    adminApi.listUsers({ page, page_size: 20, keyword: keyword || undefined }).then((r) => {
      setUsers(r.items); setTotal(r.total)
    }).catch(() => {})
  }, [page, keyword])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditing(null); form.resetFields(); setModalOpen(true) }
  const openEdit = (u: AdminUser) => { setEditing(u); form.setFieldsValue(u); setModalOpen(true) }

  const handleSave = async () => {
    const values = await form.validateFields()
    try {
      if (editing) {
        await adminApi.updateUser(editing.id, values)
        message.success('已更新')
      } else {
        await adminApi.createUser(values)
        message.success('已创建')
      }
      setModalOpen(false); load()
    } catch (e: any) { message.error(e.message) }
  }

  const handleDelete = async (id: number) => {
    try { await adminApi.deleteUser(id); message.success('已删除'); load() }
    catch (e: any) { message.error(e.message) }
  }

  return (
    <>
      <div className="mb-4 flex items-center gap-3">
        <Input.Search placeholder="搜索用户名/邮箱" allowClear onSearch={(v) => { setKeyword(v); setPage(1) }} style={{ width: 260 }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建用户</Button>
      </div>
      <Table
        dataSource={users} rowKey="id" size="small"
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '用户名', dataIndex: 'username' },
          { title: '邮箱', dataIndex: 'email' },
          { title: '姓名', dataIndex: 'full_name' },
          { title: '状态', dataIndex: 'is_active', width: 80, render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag color="red">停用</Tag> },
          { title: '管理员', dataIndex: 'is_superuser', width: 80, render: (v: boolean) => v ? <Tag color="blue">是</Tag> : <Tag>否</Tag> },
          {
            title: '操作', width: 120, render: (_: any, r: AdminUser) => (
              <Space size="small">
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
                <Popconfirm title="确定删除此用户？" onConfirm={() => handleDelete(r.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal title={editing ? '编辑用户' : '新建用户'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)} destroyOnClose>
        <Form form={form} layout="vertical">
          {!editing && <Form.Item name="username" label="用户名" rules={[{ required: true }]}><Input /></Form.Item>}
          <Form.Item name="email" label="邮箱" rules={[{ required: !editing }]}><Input /></Form.Item>
          {!editing && <Form.Item name="password" label="密码" rules={[{ required: true, min: 8 }]}><Input.Password /></Form.Item>}
          <Form.Item name="full_name" label="姓名"><Input /></Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked" initialValue={true}>
            <Select options={[{ value: true, label: '启用' }, { value: false, label: '停用' }]} />
          </Form.Item>
          <Form.Item name="is_superuser" label="管理员" initialValue={false}>
            <Select options={[{ value: true, label: '是' }, { value: false, label: '否' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// ─── PLACEHOLDER_SUBJECTS_TAB ─────────────────────────────────────────────────

const SubjectsTab: React.FC = () => {
  const [items, setItems] = useState<AdminSubject[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AdminSubject | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(() => {
    adminApi.listSubjects({ page, page_size: 20, keyword: keyword || undefined }).then((r) => {
      setItems(r.items); setTotal(r.total)
    }).catch(() => {})
  }, [page, keyword])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ category: 'public', exam_duration: 150, total_score: 100 }); setModalOpen(true) }
  const openEdit = (s: AdminSubject) => { setEditing(s); form.setFieldsValue(s); setModalOpen(true) }

  const handleSave = async () => {
    const values = await form.validateFields()
    try {
      if (editing) { await adminApi.updateSubject(editing.id, values); message.success('已更新') }
      else { await adminApi.createSubject(values); message.success('已创建') }
      setModalOpen(false); load()
    } catch (e: any) { message.error(e.message) }
  }

  const handleDelete = async (id: number) => {
    try { await adminApi.deleteSubject(id); message.success('已删除'); load() }
    catch (e: any) { message.error(e.message) }
  }

  return (
    <>
      <div className="mb-4 flex items-center gap-3">
        <Input.Search placeholder="搜索科目名称/代码" allowClear onSearch={(v) => { setKeyword(v); setPage(1) }} style={{ width: 260 }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建科目</Button>
      </div>
      <Table
        dataSource={items} rowKey="id" size="small"
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '代码', dataIndex: 'code', width: 100 },
          { title: '名称', dataIndex: 'name' },
          { title: '分类', dataIndex: 'category', width: 100 },
          { title: '时长(分)', dataIndex: 'exam_duration', width: 90 },
          { title: '总分', dataIndex: 'total_score', width: 70 },
          {
            title: '操作', width: 120, render: (_: any, r: AdminSubject) => (
              <Space size="small">
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
                <Popconfirm title="确定删除此科目？" onConfirm={() => handleDelete(r.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal title={editing ? '编辑科目' : '新建科目'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="code" label="科目代码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="科目名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="category" label="分类"><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="exam_duration" label="考试时长(分钟)"><InputNumber min={30} max={300} /></Form.Item>
          <Form.Item name="total_score" label="总分"><InputNumber min={1} /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// ─── PLACEHOLDER_QUESTIONS_TAB ────────────────────────────────────────────────

const QUESTION_TYPES = [
  { value: 'single_choice', label: '单选题' },
  { value: 'multiple_choice', label: '多选题' },
  { value: 'fill_blank', label: '填空题' },
  { value: 'short_answer', label: '简答题' },
  { value: 'essay', label: '论述题' },
  { value: 'case', label: '案例分析题' },
]

const QuestionsTab: React.FC<{ subjects: AdminSubject[] }> = ({ subjects }) => {
  const [items, setItems] = useState<AdminQuestion[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filterSubject, setFilterSubject] = useState<number | undefined>()
  const [keyword, setKeyword] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AdminQuestion | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(() => {
    adminApi.listQuestions({ page, page_size: 20, subject_id: filterSubject, keyword: keyword || undefined }).then((r) => {
      setItems(r.items); setTotal(r.total)
    }).catch(() => {})
  }, [page, filterSubject, keyword])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ difficulty: 'medium', score: 2 }); setModalOpen(true) }
  const openEdit = (q: AdminQuestion) => { setEditing(q); form.setFieldsValue({ ...q, options: q.options ? JSON.stringify(q.options) : '' }); setModalOpen(true) }

  const handleSave = async () => {
    const values = await form.validateFields()
    const payload = { ...values }
    if (typeof payload.options === 'string' && payload.options.trim()) {
      try { payload.options = JSON.parse(payload.options) } catch { message.error('选项格式不正确（需为 JSON）'); return }
    } else { payload.options = null }
    try {
      if (editing) { await adminApi.updateQuestion(editing.id, payload); message.success('已更新') }
      else { await adminApi.createQuestion(payload); message.success('已创建') }
      setModalOpen(false); load()
    } catch (e: any) { message.error(e.message) }
  }

  const handleDelete = async (id: number) => {
    try { await adminApi.deleteQuestion(id); message.success('已删除'); load() }
    catch (e: any) { message.error(e.message) }
  }

  const handleImport = async (file: File) => {
    try {
      const result = await adminApi.importQuestions(file)
      message.success(`成功导入 ${result.imported} 道题目`)
      if (result.errors.length) message.warning(`有 ${result.errors.length} 条错误`)
      load()
    } catch (e: any) { message.error(e.message) }
    return false
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select placeholder="按科目筛选" allowClear style={{ width: 180 }} onChange={(v) => { setFilterSubject(v); setPage(1) }}
          options={subjects.map((s) => ({ value: s.id, label: s.name }))} />
        <Input.Search placeholder="搜索题目内容" allowClear onSearch={(v) => { setKeyword(v); setPage(1) }} style={{ width: 220 }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建题目</Button>
        <Upload accept=".json,.csv" showUploadList={false} beforeUpload={(f) => { handleImport(f); return false }}>
          <Button icon={<UploadOutlined />}>批量导入</Button>
        </Upload>
      </div>
      <Table
        dataSource={items} rowKey="id" size="small"
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '内容', dataIndex: 'content', ellipsis: true },
          { title: '题型', dataIndex: 'question_type', width: 90, render: (v: string) => QUESTION_TYPES.find((t) => t.value === v)?.label || v },
          { title: '难度', dataIndex: 'difficulty', width: 70 },
          { title: '年份', dataIndex: 'year', width: 70 },
          { title: '分值', dataIndex: 'score', width: 60 },
          {
            title: '操作', width: 120, render: (_: any, r: AdminQuestion) => (
              <Space size="small">
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
                <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal title={editing ? '编辑题目' : '新建题目'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)} destroyOnClose width={640}>
        <Form form={form} layout="vertical">
          <Form.Item name="subject_id" label="科目" rules={[{ required: true }]}>
            <Select options={subjects.map((s) => ({ value: s.id, label: s.name }))} />
          </Form.Item>
          <Form.Item name="content" label="题目内容" rules={[{ required: true }]}><Input.TextArea rows={4} /></Form.Item>
          <Form.Item name="question_type" label="题型" rules={[{ required: true }]}>
            <Select options={QUESTION_TYPES} />
          </Form.Item>
          <Form.Item name="options" label="选项 (JSON数组)" tooltip='例如: ["A.xxx","B.xxx","C.xxx","D.xxx"]'><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="answer" label="答案" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="explanation" label="解析"><Input.TextArea rows={2} /></Form.Item>
          <div className="grid grid-cols-3 gap-3">
            <Form.Item name="year" label="年份"><InputNumber style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="difficulty" label="难度"><Select options={[{ value: 'easy', label: '简单' }, { value: 'medium', label: '中等' }, { value: 'hard', label: '困难' }]} /></Form.Item>
            <Form.Item name="score" label="分值"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          </div>
        </Form>
      </Modal>
    </>
  )
}

// ─── PLACEHOLDER_VIDEOS_TAB ──────────────────────────────────────────────────

const VideosTab: React.FC<{ subjects: AdminSubject[] }> = ({ subjects }) => {
  const [items, setItems] = useState<AdminVideo[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filterSubject, setFilterSubject] = useState<number | undefined>()
  const [keyword, setKeyword] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AdminVideo | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(() => {
    adminApi.listVideos({ page, page_size: 20, subject_id: filterSubject, keyword: keyword || undefined }).then((r) => {
      setItems(r.items); setTotal(r.total)
    }).catch(() => {})
  }, [page, filterSubject, keyword])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ source: 'custom' }); setModalOpen(true) }
  const openEdit = (v: AdminVideo) => { setEditing(v); form.setFieldsValue({ ...v, tags: v.tags?.join(', ') || '' }); setModalOpen(true) }

  const handleSave = async () => {
    const values = await form.validateFields()
    const payload = { ...values }
    if (typeof payload.tags === 'string') { payload.tags = payload.tags.split(',').map((s: string) => s.trim()).filter(Boolean) }
    try {
      if (editing) { await adminApi.updateVideo(editing.id, payload); message.success('已更新') }
      else { await adminApi.createVideo(payload); message.success('已创建') }
      setModalOpen(false); load()
    } catch (e: any) { message.error(e.message) }
  }

  const handleDelete = async (id: number) => {
    try { await adminApi.deleteVideo(id); message.success('已删除'); load() }
    catch (e: any) { message.error(e.message) }
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select placeholder="按科目筛选" allowClear style={{ width: 180 }} onChange={(v) => { setFilterSubject(v); setPage(1) }}
          options={subjects.map((s) => ({ value: s.id, label: s.name }))} />
        <Input.Search placeholder="搜索视频标题" allowClear onSearch={(v) => { setKeyword(v); setPage(1) }} style={{ width: 220 }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建视频</Button>
      </div>
      <Table
        dataSource={items} rowKey="id" size="small"
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '标题', dataIndex: 'title', ellipsis: true },
          { title: '来源', dataIndex: 'source', width: 80 },
          { title: '作者', dataIndex: 'author', width: 100, ellipsis: true },
          { title: '时长(秒)', dataIndex: 'duration', width: 80 },
          {
            title: '操作', width: 120, render: (_: any, r: AdminVideo) => (
              <Space size="small">
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
                <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal title={editing ? '编辑视频' : '新建视频'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)} destroyOnClose width={560}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="url" label="链接" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="source" label="来源">
            <Select options={[{ value: 'bilibili', label: 'B站' }, { value: 'netease', label: '网易' }, { value: 'tencent', label: '腾讯' }, { value: 'youtube', label: 'YouTube' }, { value: 'custom', label: '自定义' }]} />
          </Form.Item>
          <Form.Item name="subject_id" label="科目" rules={[{ required: true }]}>
            <Select options={subjects.map((s) => ({ value: s.id, label: s.name }))} />
          </Form.Item>
          <Form.Item name="author" label="作者"><Input /></Form.Item>
          <Form.Item name="duration" label="时长(秒)"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="tags" label="标签 (逗号分隔)"><Input /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// ─── PLACEHOLDER_CHAPTERS_TAB ─────────────────────────────────────────────────

const ChaptersTab: React.FC<{ subjects: AdminSubject[] }> = ({ subjects }) => {
  const [items, setItems] = useState<AdminChapter[]>([])
  const [filterSubject, setFilterSubject] = useState<number | undefined>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AdminChapter | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(() => {
    adminApi.listChapters(filterSubject).then(setItems).catch(() => {})
  }, [filterSubject])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditing(null); form.resetFields(); if (filterSubject) form.setFieldsValue({ subject_id: filterSubject }); setModalOpen(true) }
  const openEdit = (c: AdminChapter) => { setEditing(c); form.setFieldsValue(c); setModalOpen(true) }

  const handleSave = async () => {
    const values = await form.validateFields()
    try {
      if (editing) { await adminApi.updateChapter(editing.id, values); message.success('已更新') }
      else { await adminApi.createChapter(values); message.success('已创建') }
      setModalOpen(false); load()
    } catch (e: any) { message.error(e.message) }
  }

  const handleDelete = async (id: number) => {
    try { await adminApi.deleteChapter(id); message.success('已删除'); load() }
    catch (e: any) { message.error(e.message) }
  }

  const subjectName = (id: number) => subjects.find((s) => s.id === id)?.name || `#${id}`

  return (
    <>
      <div className="mb-4 flex items-center gap-3">
        <Select placeholder="按科目筛选" allowClear style={{ width: 200 }} onChange={setFilterSubject}
          options={subjects.map((s) => ({ value: s.id, label: s.name }))} />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建章节</Button>
      </div>
      <Table
        dataSource={items} rowKey="id" size="small" pagination={false}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '科目', dataIndex: 'subject_id', width: 140, render: (v: number) => subjectName(v) },
          { title: '章节名称', dataIndex: 'name' },
          { title: '排序', dataIndex: 'order', width: 70 },
          { title: '父章节', dataIndex: 'parent_id', width: 80, render: (v: number | null) => v ?? '-' },
          {
            title: '操作', width: 120, render: (_: any, r: AdminChapter) => (
              <Space size="small">
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
                <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal title={editing ? '编辑章节' : '新建章节'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="subject_id" label="科目" rules={[{ required: true }]}>
            <Select options={subjects.map((s) => ({ value: s.id, label: s.name }))} />
          </Form.Item>
          <Form.Item name="name" label="章节名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="order" label="排序"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="parent_id" label="父章节ID"><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// ─── Main Admin Page ──────────────────────────────────────────────────────────

const AdminPage: React.FC = () => {
  const [subjects, setSubjects] = useState<AdminSubject[]>([])

  useEffect(() => {
    adminApi.listSubjects({ page: 1, page_size: 100 }).then((r) => setSubjects(r.items)).catch(() => {})
  }, [])

  return (
    <div>
      <h1 className="mb-4 text-xl font-bold text-slate-900">系统管理</h1>
      <Tabs defaultActiveKey="dashboard" type="card">
        <TabPane tab={<span><DashboardOutlined /> 概览</span>} key="dashboard"><DashboardTab /></TabPane>
        <TabPane tab={<span><UserOutlined /> 用户管理</span>} key="users"><UsersTab /></TabPane>
        <TabPane tab={<span><BookOutlined /> 科目管理</span>} key="subjects"><SubjectsTab /></TabPane>
        <TabPane tab={<span><FileTextOutlined /> 题库管理</span>} key="questions"><QuestionsTab subjects={subjects} /></TabPane>
        <TabPane tab={<span><VideoCameraOutlined /> 视频管理</span>} key="videos"><VideosTab subjects={subjects} /></TabPane>
        <TabPane tab={<span><ApartmentOutlined /> 章节管理</span>} key="chapters"><ChaptersTab subjects={subjects} /></TabPane>
      </Tabs>
    </div>
  )
}

export default AdminPage
