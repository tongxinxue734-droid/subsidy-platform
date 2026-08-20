<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 工单中心 -->
      <el-tab-pane label="工单中心" name="orders">
        <el-row :gutter="16">
          <el-col :span="6" v-for="k in kpis" :key="k.label">
            <div class="stat-card">
              <div class="stat-label">{{ k.label }}</div>
              <div class="stat-value" :style="{ color: k.color }">{{ k.value }}</div>
              <div class="stat-sub">{{ k.sub }}</div>
            </div>
          </el-col>
        </el-row>

        <div class="panel">
          <div class="panel-title">工单闭环流转</div>
          <div ref="funnelRef" class="chart" style="height:240px"></div>
        </div>

        <div class="panel">
          <el-form :inline="true">
            <el-form-item label="类别">
              <el-select v-model="filter.category" placeholder="全部" clearable style="width:130px">
                <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="filter.status" placeholder="全部" clearable style="width:120px">
                <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
            <el-form-item label="级别">
              <el-select v-model="filter.level" placeholder="全部" clearable style="width:110px">
                <el-option v-for="l in levels" :key="l" :label="l" :value="l" />
              </el-select>
            </el-form-item>
            <el-button type="primary" plain @click="load">刷新</el-button>
            <el-button plain @click="exportOrders">导出工单</el-button>
          </el-form>

          <el-table :data="filtered" border stripe max-height="560" v-loading="loading" empty-text="暂无工单">
            <el-table-column prop="work_no" label="工单号" width="165" />
            <el-table-column prop="category" label="类别" width="95">
              <template #default="{ row }">
                <el-tag :type="{ 稽核: 'danger', 比对: 'warning', 政策找人: 'primary', 诉求: 'info' }[row.category]" size="small">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="105" />
            <el-table-column prop="district" label="区县" width="95" />
            <el-table-column prop="name" label="姓名(脱敏)" width="100" />
            <el-table-column prop="title" label="事项" min-width="180" show-overflow-tooltip />
            <el-table-column prop="level" label="级别" width="75">
              <template #default="{ row }">
                <el-tag :type="{ 红色: 'danger', 橙色: 'warning', 黄色: 'warning' }[row.level]" effect="plain" size="small">{{ row.level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="{ 待处理: 'danger', 整改中: 'warning', 待复核: 'primary', 已销号: 'success' }[row.status]" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status !== '已销号'" link type="primary" @click="advance(row)">{{ nextAction(row.status) }}</el-button>
                <el-button v-if="row.category === '政策找人' && row.status === '待处理'" link type="success" @click="enroll(row)">纳入申领</el-button>
                <span v-if="row.status === '已销号'" style="color:#c0c4cc">已闭环</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 数据比对 -->
      <el-tab-pane label="数据比对" name="compare">
        <div class="panel">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px">
            <div class="panel-title" style="margin:0">跨部门数据比对任务</div>
            <el-button type="primary" @click="runCompare">发起一次比对</el-button>
          </div>
          <el-table :data="tasks" border stripe>
            <el-table-column prop="task_no" label="任务编号" width="160" />
            <el-table-column prop="source" label="比对数据源" width="130">
              <template #default="{ row }">
                <el-tag size="small">{{ row.source }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="district" label="区县" width="110" />
            <el-table-column prop="compared_count" label="比对人数" width="110" />
            <el-table-column prop="hit_count" label="命中人数" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.hit_count > 0" type="danger" size="small">{{ row.hit_count }}</el-tag>
                <span v-else>0</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }"><el-tag type="success" size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="compared_at" label="比对时间" width="120" />
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api'
import { exportCSV } from '../utils/export'
import * as echarts from 'echarts'

const activeTab = ref('orders')
const items = ref([])
const tasks = ref([])
const loading = ref(false)
const funnelRef = ref()
let funnelChart = null
const filter = reactive({ category: '', status: '', level: '' })
const categories = ['稽核', '比对', '政策找人', '诉求']
const statuses = ['待处理', '整改中', '待复核', '已销号']
const levels = ['红色', '橙色', '黄色']

const filtered = computed(() => items.value.filter(r =>
  (!filter.category || r.category === filter.category) &&
  (!filter.status || r.status === filter.status) &&
  (!filter.level || r.level === filter.level)
))

const kpis = computed(() => {
  const cnt = s => items.value.filter(r => r.status === s).length
  return [
    { label: '待处理', value: cnt('待处理'), sub: '需立即处置', color: '#f56c6c' },
    { label: '整改中', value: cnt('整改中'), sub: '处理进行中', color: '#e6a23c' },
    { label: '待复核', value: cnt('待复核'), sub: '等待复核销号', color: '#409eff' },
    { label: '已销号', value: cnt('已销号'), sub: '已闭环', color: '#67c23a' }
  ]
})

function nextAction(status) {
  return { 待处理: '开始处理', 整改中: '提交复核', 待复核: '销号' }[status] || ''
}

async function load() {
  loading.value = true
  try {
    items.value = (await request.get('/workorders')).items
    tasks.value = (await request.get('/compare')).items
    await nextTick()
    renderFunnel()
  } finally {
    loading.value = false
  }
}

function renderFunnel() {
  if (!funnelRef.value) return
  const cnt = s => items.value.filter(r => r.status === s).length
  if (!funnelChart) funnelChart = echarts.init(funnelRef.value)
  funnelChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [{
      type: 'funnel', left: '8%', width: '84%', top: 10, bottom: 10,
      label: { show: true, position: 'inside', formatter: '{b} {c}' },
      data: [
        { name: '待处理', value: cnt('待处理') },
        { name: '整改中', value: cnt('整改中') },
        { name: '待复核', value: cnt('待复核') },
        { name: '已销号', value: cnt('已销号') }
      ],
      color: ['#f56c6c', '#e6a23c', '#409eff', '#67c23a']
    }]
  })
}

async function advance(row) {
  await request.post(`/workorders/${row.id}/advance`)
  ElMessage.success('工单已流转')
  load()
}

async function enroll(row) {
  try {
    await ElMessageBox.confirm(`将 ${row.name}（${row.age_band}）纳入申领，生成申领工单？`, '政策找人', { type: 'success' })
  } catch (e) { return }
  const data = await request.post(`/workorders/${row.id}/enroll`)
  ElMessage.success(`已纳入申领，申领编号 ${data.apply_no}`)
  load()
}

async function runCompare() {
  const data = await request.post('/compare/run')
  ElMessage.success(`比对完成：命中 ${data.hit_count} 人`)
  load()
}

function exportOrders() {
  const rows = filtered.value.map(r => [r.work_no, r.category, r.source, r.district, r.name, r.title, r.level, r.status])
  exportCSV('监管工单.csv', ['工单号', '类别', '来源', '区县', '姓名', '事项', '级别', '状态'], rows)
}

onMounted(load)
onBeforeUnmount(() => { if (funnelChart) funnelChart.dispose() })
</script>
