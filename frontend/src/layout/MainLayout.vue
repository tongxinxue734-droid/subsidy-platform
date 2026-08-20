<template>
  <el-container class="layout">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <div class="logo-icon" v-show="!isCollapse">🏛️</div>
        <div class="logo-text" v-show="!isCollapse">
          <div class="logo-title">西安市高龄补贴</div>
          <div class="logo-sub">监管平台</div>
        </div>
        <el-icon class="logo-collapse" :size="18" @click="toggleCollapse">
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="openeds"
        :collapse="isCollapse"
        router
        background-color="#001529"
        text-color="rgba(255,255,255,0.68)"
        active-text-color="#fff"
        class="menu"
      >
        <template v-for="g in visibleMenus" :key="g.title || g.path">
          <el-sub-menu v-if="g.children" :index="g.title">
            <template #title>
              <el-icon><component :is="g.icon" /></el-icon>
              <span>{{ g.title }}</span>
            </template>
            <el-menu-item v-for="c in g.children" :key="c.path" :index="c.path">
              <el-icon><component :is="c.icon" /></el-icon>
              <span>{{ c.title }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="g.path">
            <el-icon><component :is="g.icon" /></el-icon>
            <span>{{ g.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>西安市高龄补贴监管平台</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
          <el-autocomplete
            v-model="searchText"
            :fetch-suggestions="searchSuggestions"
            :trigger-on-focus="false"
            placeholder="搜索档案号 / 姓名 / 工单号"
            clearable
            @select="onSearchSelect"
            class="search-box"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-autocomplete>
        </div>
        <div class="header-right">
          <el-tooltip content="工单待办" placement="bottom">
            <el-badge :value="todoCount" :hidden="!todoCount" :max="99" class="badge">
              <el-button link @click="router.push('/workorders')"><el-icon :size="18"><Tickets /></el-icon></el-button>
            </el-badge>
          </el-tooltip>
          <el-tooltip content="未读消息" placement="bottom">
            <el-badge :value="unreadCount" :hidden="!unreadCount" :max="99" class="badge">
              <el-button link @click="router.push('/admin')"><el-icon :size="18"><Bell /></el-icon></el-button>
            </el-badge>
          </el-tooltip>
          <el-divider direction="vertical" />
          <el-tag size="small" :type="roleTagType" effect="light">{{ roleName }}</el-tag>
          <span class="user-name">{{ user.name }}</span>
          <span class="user-dept">{{ user.dept_name }}</span>
          <el-button link type="primary" @click="logout">退出登录</el-button>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <AiAssistant />
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../api'
import AiAssistant from '../components/AiAssistant.vue'

const route = useRoute()
const router = useRouter()

const user = JSON.parse(localStorage.getItem('user') || '{}')
const roleName = computed(() => ({ 1: '市级', 2: '区县', 3: '街道' }[user.role_level] || '用户'))
const roleTagType = computed(() => ({ 1: 'danger', 2: 'warning', 3: 'info' }[user.role_level] || 'info'))

const menuGroups = [
  { path: '/workbench', title: '工作台', icon: 'HomeFilled', roles: [1, 2, 3] },
  { path: '/dashboard', title: '监管驾驶舱', icon: 'Odometer', roles: [1, 2, 3] },
  { path: '/bigscreen', title: '数据大屏', icon: 'Monitor', roles: [1] },
  {
    title: '业务经办', icon: 'FolderOpened', roles: [1, 2, 3], children: [
      { path: '/applications', title: '申领审核', icon: 'EditPen' },
      { path: '/elders', title: '受益对象管理', icon: 'User' },
      { path: '/certify', title: '年度复审', icon: 'Calendar' },
      { path: '/payments', title: '发放管理', icon: 'Money' }
    ]
  },
  { path: '/fund', title: '资金监管', icon: 'Coin', roles: [1, 2] },
  {
    title: '监管稽核', icon: 'Aim', roles: [1, 2, 3], children: [
      { path: '/audit', title: '智能稽核', icon: 'Warning' },
      { path: '/risk', title: '风险画像', icon: 'DataLine' },
      { path: '/spotcheck', title: '双随机抽查', icon: 'Refresh' },
      { path: '/workorders', title: '工单督办', icon: 'Tickets' }
    ]
  },
  { path: '/publicity', title: '阳光公示', icon: 'View', roles: [1, 2] },
  { path: '/analysis', title: '统计分析', icon: 'DataAnalysis', roles: [1, 2, 3] },
  {
    title: '政策公开', icon: 'Document', roles: [1, 2, 3], children: [
      { path: '/subsidy', title: '补贴标准与政策', icon: 'Document' },
      { path: '/notices', title: '通知公告', icon: 'Bell' }
    ]
  },
  { path: '/admin', title: '系统管理', icon: 'Setting', roles: [1] }
]

const visibleMenus = computed(() => menuGroups.filter(g => (g.roles || [1, 2, 3]).includes(user.role_level)))

const flatMenus = computed(() => {
  const out = []
  for (const g of visibleMenus.value) {
    if (g.children) out.push(...g.children)
    else out.push(g)
  }
  return out
})

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => {
  const m = flatMenus.value.find(x => x.path === route.path)
  return m ? m.title : ''
})
const openeds = computed(() => visibleMenus.value.filter(g => g.children).map(g => g.title))

const unreadCount = ref(0)
const todoCount = ref(0)

const isCollapse = ref(window.innerWidth < 768)
function toggleCollapse() { isCollapse.value = !isCollapse.value }

const searchText = ref('')
async function searchSuggestions(q, cb) {
  if (!q) { cb([]); return }
  const r = await request.get('/search', { params: { q } })
  const list = []
  r.elders.forEach(e => list.push({ value: `老人 · ${e.name}（${e.archive_no}）`, type: 'elder', id: e.id }))
  r.work_orders.forEach(w => list.push({ value: `工单 · ${w.work_no} ${w.title}`, type: 'workorder', id: w.id }))
  r.applications.forEach(a => list.push({ value: `申领 · ${a.apply_no} ${a.name}`, type: 'application', id: a.id }))
  cb(list)
}
function onSearchSelect(item) {
  searchText.value = ''
  if (item.type === 'elder') router.push(`/elders?open=${item.id}`)
  else if (item.type === 'workorder') router.push('/workorders')
  else router.push('/applications')
}

onMounted(async () => {
  try {
    const msgs = await request.get('/messages')
    unreadCount.value = msgs.items.filter(m => !m.read).length
  } catch (e) { /* 后端未就绪时忽略 */ }
  try {
    const wos = await request.get('/workorders')
    todoCount.value = wos.items.filter(w => w.status === '待处理').length
  } catch (e) { /* 后端未就绪时忽略 */ }
})

function logout() {
  localStorage.clear()
  router.push('/login')
}
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #001529; overflow: hidden; display: flex; flex-direction: column; }
.logo { height: 60px; display: flex; align-items: center; padding: 0 16px; background: #002140; flex-shrink: 0; }
.logo-collapse { cursor: pointer; color: rgba(255,255,255,0.75); margin-left: auto; padding: 6px; flex-shrink: 0; }
.logo-collapse:hover { color: #fff; }
.logo-icon { font-size: 26px; margin-right: 10px; }
.logo-text { color: #fff; }
.logo-title { font-size: 14px; font-weight: 600; }
.logo-sub { font-size: 12px; opacity: 0.75; }
.menu { border-right: none; flex: 1; overflow-y: auto; }
.header {
  background: #fff; display: flex; align-items: center; justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0,21,41,0.08); padding: 0 20px;
}
.collapse-btn { cursor: pointer; color: #606266; flex-shrink: 0; padding: 10px; border-radius: 4px; line-height: 1; }
.collapse-btn:active { background: #f0f2f5; }
.collapse-btn:hover { color: #409eff; }
.header-left { display: flex; align-items: center; gap: 20px; flex: 1; min-width: 0; }
.search-box { width: 280px; }
.header-right { display: flex; align-items: center; gap: 14px; }
.badge { display: inline-flex; }
.user-name { font-weight: 600; }
.user-dept { color: #909399; font-size: 13px; }
.main { background: #f0f2f5; padding: 16px; }
</style>
