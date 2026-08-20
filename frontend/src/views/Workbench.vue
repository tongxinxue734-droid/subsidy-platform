<template>
  <div class="page-container">
    <div class="welcome">
      <div>
        <div class="welcome-title">{{ greeting }}，{{ user.name }}</div>
        <div class="welcome-sub">{{ user.dept_name }} · {{ roleName }}账号</div>
      </div>
      <div class="quick-actions">
        <el-button type="primary" @click="router.push('/applications')">+ 新增申领</el-button>
        <el-button @click="router.push('/spotcheck')">发起抽查</el-button>
        <el-button @click="router.push('/workorders')">工单督办</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :md="6" v-for="k in kpis" :key="k.label">
        <div class="stat-card clickable" @click="k.link && router.push(k.link)">
          <div class="stat-label">{{ k.label }}</div>
          <div class="stat-value" :style="{ color: k.color }">{{ k.value }}</div>
          <div class="stat-sub">{{ k.sub }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">
            待审申领
            <el-button link type="primary" style="margin-left:auto" @click="router.push('/applications')">去处理 →</el-button>
          </div>
          <el-table :data="recentApps" size="small" border>
            <el-table-column prop="apply_no" label="申领编号" width="160" />
            <el-table-column prop="name" label="姓名(脱敏)" width="100" />
            <el-table-column prop="district" label="区县" width="95" />
            <el-table-column prop="status" label="状态" />
          </el-table>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">
            待复审老人
            <el-button link type="primary" style="margin-left:auto" @click="router.push('/certify')">去处理 →</el-button>
          </div>
          <el-table :data="recentCert" size="small" border>
            <el-table-column prop="archive_no" label="档案号" width="150" />
            <el-table-column prop="name" label="姓名(脱敏)" width="100" />
            <el-table-column prop="district" label="区县" width="95" />
            <el-table-column prop="certify_status" label="状态" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">
            待处理工单
            <el-button link type="primary" style="margin-left:auto" @click="router.push('/workorders')">去处理 →</el-button>
          </div>
          <el-table :data="recentWo" size="small" border>
            <el-table-column prop="work_no" label="工单号" width="170" />
            <el-table-column prop="category" label="类别" width="90" />
            <el-table-column prop="title" label="事项" min-width="160" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="90" />
          </el-table>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">
            未读消息
            <el-button link type="primary" style="margin-left:auto" @click="router.push('/admin')">去查看 →</el-button>
          </div>
          <el-table :data="recentMsg" size="small" border>
            <el-table-column prop="category" label="类型" width="90">
              <template #default="{ row }">
                <el-tag :type="{ 预警: 'danger', 待办: 'warning', 通知: 'info', 政策: 'primary' }[row.category]" size="small">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" />
          </el-table>
        </div>
      </el-col>
    </el-row>
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

const kpis = ref([])
const recentApps = ref([])
const recentCert = ref([])
const recentWo = ref([])
const recentMsg = ref([])

onMounted(async () => {
  const d = await request.get('/workbench')
  kpis.value = [
    { label: '待审申领', value: d.kpi.pending_apps, sub: '去申领审核处理', color: '#409eff', link: '/applications' },
    { label: '待复审', value: d.kpi.pending_cert, sub: '认证待处理', color: '#e6a23c', link: '/certify' },
    { label: '待处理工单', value: d.kpi.pending_wo, sub: '监管闭环', color: '#f56c6c', link: '/workorders' },
    { label: '未读消息', value: d.kpi.unread, sub: '消息中心', color: '#909399', link: '/admin' }
  ]
  recentApps.value = d.recent_apps
  recentCert.value = d.recent_cert
  recentWo.value = d.recent_wo
  recentMsg.value = d.recent_msg
})
</script>

<style scoped>
.welcome {
  display: flex; align-items: center; justify-content: space-between; padding: 18px 22px;
  background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,21,41,0.06); margin-bottom: 16px;
}
.welcome-title { font-size: 20px; font-weight: 700; color: #303133; }
.welcome-sub { font-size: 13px; color: #909399; margin-top: 4px; }
.panel-title { display: flex; align-items: center; }
.clickable { cursor: pointer; transition: box-shadow .2s; }
.clickable:hover { box-shadow: 0 4px 14px rgba(64,158,255,0.22); }
</style>
