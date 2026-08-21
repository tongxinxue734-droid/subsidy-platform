<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <div class="stat-card">
          <div class="stat-label">累计发放金额</div>
          <div class="stat-value" style="color:#409eff">{{ (totalAmount / 10000).toFixed(2) }} 亿元</div>
          <div class="stat-sub">台账范围内</div>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="stat-card">
          <div class="stat-label">累计受益人次</div>
          <div class="stat-value" style="color:#67c23a">{{ totalCount.toLocaleString() }}</div>
          <div class="stat-sub">台账范围内</div>
        </div>
      </el-col>
    </el-row>

    <div class="panel" style="margin-top:16px">
      <div class="panel-title">月度发放金额趋势</div>
      <div ref="trendRef" class="chart" style="height:300px"></div>
    </div>

    <div class="panel">
      <div style="display:flex; justify-content:space-between; align-items:center">
        <div class="panel-title" style="margin:0">发放记录明细</div>
        <el-button size="small" plain @click="exportItems">导出明细</el-button>
      </div>
      <el-form :inline="true">
        <el-form-item label="区县" v-if="isCity">
          <el-select v-model="filter.district" placeholder="全部" clearable style="width:140px" @change="load">
            <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="月份">
          <el-select v-model="filter.month" placeholder="全部" clearable style="width:130px" @change="load">
            <el-option v-for="m in months" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-table :data="items" border stripe v-loading="loading">
        <el-table-column prop="district" label="区县" />
        <el-table-column prop="month" label="发放月份" />
        <el-table-column prop="amount" label="发放金额(万元)" />
        <el-table-column prop="count" label="受益人数" />
      </el-table>
    </div>

    <div class="panel">
      <div class="panel-title">发放异常人员（停发 / 待认证，需复核补发）</div>
      <el-table :data="abnormal" border stripe max-height="400">
        <el-table-column prop="archive_no" label="档案号" width="160" />
        <el-table-column prop="name" label="姓名(脱敏)" width="110" />
        <el-table-column prop="district" label="区县" width="100" />
        <el-table-column prop="age_band" label="年龄段" width="120" />
        <el-table-column prop="standard" label="标准" width="90" />
        <el-table-column prop="status" label="发放状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === '停发' ? 'danger' : 'warning'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="certify_status" label="认证状态" width="100" />
        <el-table-column label="处理建议" min-width="150">
          <template #default="{ row }">
            <span style="color:#e6a23c">{{ row.certify_status === '认证过期' ? '完成复审后自动补发' : '完成复审后恢复发放' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import request from '../api'
import { exportCSV } from '../utils/export'
import { CHART } from '../utils/palette'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const isCity = computed(() => user.role_level === 1)

const districts = ref([])
const months = ref([])
const items = ref([])
const abnormal = ref([])
const totalAmount = ref(0)
const totalCount = ref(0)
const loading = ref(false)
const filter = reactive({ district: '', month: '' })
const trendRef = ref()
let chart = null
let disposed = false

async function load() {
  loading.value = true
  try {
    const data = await request.get('/payments', { params: filter })
    items.value = data.items
    abnormal.value = data.abnormal
    totalAmount.value = data.total_amount
    totalCount.value = data.total_count
    renderTrend(data.trend)
  } finally {
    loading.value = false
  }
}

function renderTrend(trend) {
  if (disposed || !trendRef.value) return
  if (chart) chart.dispose()
  chart = echarts.init(trendRef.value)
  chart.setOption({
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: trend.map(t => t.month) },
    yAxis: { type: 'value', name: '万元' },
    series: [{ type: 'line', smooth: true, data: trend.map(t => t.amount), itemStyle: { color: CHART.primary }, areaStyle: { opacity: 0.15 } }]
  })
}

function exportItems() {
  const rows = items.value.map(r => [r.district, r.month, r.amount, r.count])
  exportCSV('发放明细.csv', ['区县', '发放月份', '金额(万元)', '受益人数'], rows)
}

onMounted(async () => {
  const s = await request.get('/standards')
  districts.value = s.districts
  const p = await request.get('/payments', { params: { month: '' } })
  months.value = [...new Set(p.items.map(i => i.month))].sort()
  load()
})

onBeforeUnmount(() => { disposed = true; if (chart) chart.dispose() })
</script>

<style scoped>
.stat-label { font-size: 13px; color: #909399; }
.stat-value { font-size: 26px; font-weight: 700; margin: 8px 0 4px; }
.stat-sub { font-size: 12px; color: #c0c4cc; }
</style>
