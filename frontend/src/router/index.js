import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { title: '登录' } },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/workbench',
    children: [
      { path: 'workbench', component: () => import('../views/Workbench.vue'), meta: { title: '工作台' } },
      { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '监管驾驶舱' } },
      { path: 'subsidy', component: () => import('../views/Subsidy.vue'), meta: { title: '补贴标准与政策' } },
      { path: 'applications', component: () => import('../views/Applications.vue'), meta: { title: '申领审核' } },
      { path: 'elders', component: () => import('../views/Elders.vue'), meta: { title: '受益对象管理' } },
      { path: 'certify', component: () => import('../views/Certify.vue'), meta: { title: '年度复审' } },
      { path: 'payments', component: () => import('../views/Payments.vue'), meta: { title: '发放管理' } },
      { path: 'fund', component: () => import('../views/Fund.vue'), meta: { title: '资金监管' } },
      { path: 'audit', component: () => import('../views/Audit.vue'), meta: { title: '智能稽核' } },
      { path: 'spotcheck', component: () => import('../views/SpotCheck.vue'), meta: { title: '双随机抽查' } },
      { path: 'workorders', component: () => import('../views/WorkOrders.vue'), meta: { title: '工单督办' } },
      { path: 'analysis', component: () => import('../views/Analysis.vue'), meta: { title: '统计分析' } },
      { path: 'publicity', component: () => import('../views/Publicity.vue'), meta: { title: '阳光公示' } },
      { path: 'notices', component: () => import('../views/Notices.vue'), meta: { title: '通知公告' } },
      { path: 'admin', component: () => import('../views/Admin.vue'), meta: { title: '系统管理' } }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/workbench' }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
