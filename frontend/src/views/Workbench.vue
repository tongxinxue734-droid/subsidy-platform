<template>
  <div class="page-container">
    <!-- 顶部：问候 + 今日待办总览 -->
    <div class="welcome">
      <div>
        <div class="welcome-title">{{ greeting }}，{{ user.name }}</div>
        <div class="welcome-sub">{{ user.dept_name }} · {{ roleName }}账号</div>
      </div>
      <div class="todo-total">
        <div class="todo-num">{{ totalTodo.toLocaleString() }}</div>
        <div class="todo-label">今日待办</div>
      </div>
      <div class="todo-break">
        <span class="break-item" @click="router.push('/applications')">待审申领 <b>{{ kpi.pending_apps }}</b></span>
        <span class="break-item" @click="router.push('/certify')">待复审 <b>{{ kpi.pending_cert }}</b></span>
        <span class="break-item" @click="router.push('/workorders')">待处理工单 <b>{{ kpi.pending_wo }}</b></span>
        <span class="break-item" @click="router.push('/admin')">未读消息 <b>{{ kpi.unread }}</b></span>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <el-button type="primary" @click="router.push('/applications')">+ 新增申领</el-button>
      <el-button @click="router.push('/spotcheck')">发起抽查</el-button>
      <el-button @click="router.push('/workorders')">工单督办</el-button>
      <el-button @click="router.push('/elders')">查老人档案</el-button>
    </div>

    <!-- 待办中心 -->
    <div class="panel">
      <div class="panel-title">待办中心（按紧急度排序）</div>
      <el-table :data="todoList" border stripe max-height="520" empty-text="暂无待办">
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.type)" size="small" effect="dark">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="事项" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-weight:500">{{ row.title }}</span>
            <span style="color:#909399; font-size:12px; margin-left:8px">{{ row.sub }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(row.link)">去处理 →</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api'

const router = useRouter()
const user = JSON.parse(localStorage.getItem('user') || '{}')
const roleName = computed(() => ({ 1: '市级', 2: '区县', 3: '街道' }[user.role_level] || ''))
const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 12 ? '早上好' : h < 18 ? '下午好' : '晚上好'
})

const kpi = ref({ pending_apps: 0, pending_cert: 0, pending_wo: 0, unread: 0 })
const data = ref(null)

const totalTodo = computed(() => data.value
  ? data.value.kpi.pending_apps + data.value.kpi.pending_cert + data.value.kpi.pending_wo
  : 0)

const order = { '待处理': 0, '认证过期': 1, '待复核': 2, '待认证': 3, '待街道审核': 4, '待区县审批': 5, '整改中': 6 }

const todoList = computed(() => {
  if (!data.value) return []
  const items = []
  data.value.recent_wo.forEach(w => items.push({ type: '工单', title: w.title, sub: w.work_no, status: w.status, link: '/workorders' }))
  data.value.recent_cert.forEach(e => items.push({ type: '复审', title: `${e.name}（${e.certify_status}）`, sub: e.archive_no, status: e.certify_status, link: '/certify' }))
  data.value.recent_apps.forEach(a => items.push({ type: '申领', title: `${a.name} 申领`, sub: a.apply_no, status: a.status, link: '/applications' }))
  items.sort((a, b) => (order[a.status] ?? 99) - (order[b.status] ?? 99))
  return items.slice(0, 12)
})

function typeTag(t) { return { 工单: 'danger', 复审: 'warning', 申领: 'primary' }[t] || 'info' }
function statusTag(s) {
  return { 待处理: 'danger', 认证过期: 'danger', 待复核: 'warning', 待认证: 'warning', 待街道审核: 'primary', 待区县审批: 'primary', 整改中: 'info' }[s] || 'info'
}

onMounted(async () => {
  const d = await request.get('/workbench')
  data.value = d
  kpi.value = d.kpi
})
</script>

<style scoped>
.welcome {
  display: flex; align-items: center; gap: 40px; padding: 22px 24px;
  background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,21,41,0.05);
  border: 1px solid #eef0f4; margin-bottom: 16px; flex-wrap: wrap;
}
.welcome-title { font-size: 20px; font-weight: 700; color: #303133; }
.welcome-sub { font-size: 13px; color: #909399; margin-top: 4px; }

.todo-total { text-align: center; min-width: 120px; }
.todo-num { font-size: 34px; font-weight: 800; color: #409eff; line-height: 1; }
.todo-label { font-size: 12px; color: #909399; margin-top: 4px; }

.todo-break { display: flex; gap: 20px; flex-wrap: wrap; }
.break-item { font-size: 13px; color: #606266; cursor: pointer; }
.break-item b { font-size: 18px; color: #303133; margin-left: 4px; }
.break-item:hover { color: #409eff; }

.quick-actions { display: flex; gap: 12px; margin-bottom: 16px; }

.panel-title { display: flex; align-items: center; }
</style>
