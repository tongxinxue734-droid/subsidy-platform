<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :span="6" v-for="k in kpis" :key="k.label">
        <div class="stat-card">
          <div class="stat-label">{{ k.label }}</div>
          <div class="stat-value" :style="{ color: k.color }">{{ k.value }}</div>
          <div class="stat-sub">{{ k.sub }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="8">
        <div class="panel" style="display:flex; flex-direction:column; align-items:center">
          <div class="panel-title" style="align-self:flex-start">年度认证进度</div>
          <el-progress type="dashboard" :percentage="certRate" :color="certRate >= 90 ? '#67c23a' : certRate >= 80 ? '#e6a23c' : '#f56c6c'" />
          <div style="color:#909399; font-size:13px; margin-top:6px">已完成年度资格认证 · 每年一次</div>
        </div>
      </el-col>
      <el-col :span="16">
        <div class="panel">
          <div class="panel-title">最近认证记录</div>
          <el-table :data="recentRecords" border stripe size="small" max-height="220">
            <el-table-column prop="name" label="姓名(脱敏)" width="110" />
            <el-table-column prop="date" label="认证日期" width="130" />
            <el-table-column prop="method" label="认证方式" />
            <el-table-column prop="result" label="结果" width="90">
              <template #default="{ row }"><el-tag type="success" size="small">{{ row.result }}</el-tag></template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="14">
        <div class="panel">
          <div class="panel-title">各区县复审率</div>
          <div ref="distRef" class="chart" style="height:320px"></div>
        </div>
      </el-col>
      <el-col :span="10">
        <div class="panel">
          <div class="panel-title">认证方式分布</div>
          <div ref="methodRef" class="chart" style="height:320px"></div>
        </div>
      </el-col>
    </el-row>

    <div class="panel">
      <div class="panel-title">待复审清单（认证过期 / 待认证）</div>
      <el-table :data="todoList" border stripe max-height="460">
        <el-table-column prop="archive_no" label="档案号" width="150" />
        <el-table-column prop="name" label="姓名(脱敏)" width="110" />
        <el-table-column prop="district" label="区县" width="100" />
        <el-table-column prop="street" label="街道" width="130" />
        <el-table-column prop="age_band" label="年龄段" width="130" />
        <el-table-column prop="certify_status" label="认证状态" width="105">
          <template #default="{ row }">
            <el-tag :type="row.certify_status === '认证过期' ? 'danger' : 'warning'" size="small">{{ row.certify_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_certify" label="上次认证" width="110">
          <template #default="{ row }">{{ row.last_certify || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" @click="certifyOne(row)">完成复审</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import request from '../api'
import { CHART } from '../utils/palette'

const kpis = ref([])
const todoList = ref([])
const recentRecords = ref([])
const certRate = ref(0)
const distRef = ref()
const methodRef = ref()
const charts = []
let disposed = false

function safeInit(el) {
  if (disposed || !el) return null
  const c = echarts.init(el)
  charts.push(c)
  return c
}

function certifyOne(row) {
  request.post(`/elders/${row.id}/certify`).then(() => {
    ElMessage.success('复审完成')
    load()
  })
}

async function load() {
  const data = await request.get('/certify/overview')
  kpis.value = [
    { label: '受益老人', value: data.kpi.total.toLocaleString(), sub: '在册总数', color: '#409eff' },
    { label: '已认证', value: data.kpi.certified.toLocaleString(), sub: '认证通过', color: '#67c23a' },
    { label: '待认证', value: data.kpi.pending.toLocaleString(), sub: '需完成复审', color: '#e6a23c' },
    { label: '认证过期', value: data.kpi.expired.toLocaleString(), sub: '已暂停发放', color: '#f56c6c' }
  ]
  todoList.value = [...data.expired_list, ...data.pending_list]
  recentRecords.value = data.recent_records
  certRate.value = data.kpi.rate

  const dist = safeInit(distRef.value)
  if (dist) {
    dist.setOption({
      grid: { left: 90, right: 30, top: 10, bottom: 30 },
      tooltip: { trigger: 'axis', formatter: p => `${p[0].name}<br/>复审率 ${p[0].value}%` },
      xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      yAxis: { type: 'category', data: data.districts.map(d => d.district).reverse() },
      series: [{ type: 'bar', data: data.districts.map(d => d.rate).reverse(), itemStyle: { color: CHART.primary, borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'right', formatter: '{c}%' } }]
    })
  }

  const method = safeInit(methodRef.value)
  if (method) {
    method.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: ['45%', '70%'], data: data.methods, label: { formatter: '{b}\n{c}' }, color: CHART.series }]
    })
  }
}

onMounted(load)

onBeforeUnmount(() => {
  disposed = true
  charts.forEach(c => c.dispose())
  charts.length = 0
})
</script>
