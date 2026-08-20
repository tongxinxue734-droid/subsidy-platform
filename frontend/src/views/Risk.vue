<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :span="4" v-for="k in kpis" :key="k.label">
        <div class="stat-card">
          <div class="stat-label">{{ k.label }}</div>
          <div class="stat-value" :style="{ color: k.color }">{{ k.value }}</div>
          <div class="stat-sub">{{ k.sub }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="8">
        <div class="panel">
          <div class="panel-title">疑点类型分布</div>
          <div ref="typeRef" class="chart" style="height:300px"></div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="panel">
          <div class="panel-title">风险分数段分布</div>
          <div ref="scoreRef" class="chart" style="height:300px"></div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="panel">
          <div class="panel-title">年龄段风险分布</div>
          <div ref="ageRef" class="chart" style="height:300px"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="10">
        <div class="panel">
          <div class="panel-title">区县高风险人数排行</div>
          <div ref="districtRef" class="chart" style="height:360px"></div>
        </div>
      </el-col>
      <el-col :span="14">
        <div class="panel">
          <div class="panel-title">风险评分规则</div>
          <el-table :data="rules" border size="small">
            <el-table-column prop="factor" label="风险因子" width="200" />
            <el-table-column prop="score" label="分值" width="80" />
            <el-table-column prop="desc" label="说明" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <div class="panel">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px">
        <div class="panel-title" style="margin:0">高风险人群清单</div>
        <el-button type="primary" size="small" @click="generateWorkOrders">一键生成稽核工单</el-button>
      </div>
      <el-table :data="highList" border stripe max-height="480">
        <el-table-column prop="archive_no" label="档案号" width="155" />
        <el-table-column prop="name" label="姓名(脱敏)" width="105" />
        <el-table-column prop="district" label="区县" width="95" />
        <el-table-column prop="street" label="街道" width="120" />
        <el-table-column prop="suspect_type" label="疑点" width="105">
          <template #default="{ row }">
            <el-tag v-if="row.suspect_type" :type="{ 疑似冒领: 'danger', 重复领取: 'danger', 认证过期: 'warning', 信息异常: 'info' }[row.suspect_type]" size="small">{{ row.suspect_type }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="certify_status" label="认证" width="90" />
        <el-table-column label="风险分" width="90">
          <template #default="{ row }">
            <el-tag :type="row.score >= 60 ? 'danger' : row.score >= 40 ? 'warning' : 'info'" size="small">{{ row.score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <ElderDetail v-model="detailVisible" :elder-id="detailId" />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import request from '../api'
import ElderDetail from '../components/ElderDetail.vue'
import { CHART } from '../utils/palette'

const kpis = ref([])
const highList = ref([])
const typeRef = ref()
const scoreRef = ref()
const ageRef = ref()
const districtRef = ref()
const detailVisible = ref(false)
const detailId = ref(null)
const rules = [
  { factor: '疑似冒领 / 重复领取', score: '+40', desc: '最高风险，立即停发并逐人核实' },
  { factor: '认证过期', score: '+30', desc: '认证过期，暂停发放' },
  { factor: '信息异常', score: '+20', desc: '身份 / 银行信息校验异常' },
  { factor: '认证状态为待认证', score: '+10', desc: '尚未完成本年度认证' },
  { factor: '发放状态为停发', score: '+10', desc: '当前已停发' }
]
const charts = []
let disposed = false

function safeInit(el) {
  if (disposed || !el) return null
  const c = echarts.init(el)
  charts.push(c)
  return c
}

function openDetail(row) { detailId.value = row.id; detailVisible.value = true }

async function generateWorkOrders() {
  const data = await request.post('/audit/generate')
  ElMessage.success(`已生成 ${data.generated} 件稽核工单`)
}

onMounted(async () => {
  const data = await request.get('/risk')
  if (disposed) return
  kpis.value = [
    { label: '在册老人', value: data.kpi.total.toLocaleString(), sub: '风险评分对象', color: '#409eff' },
    { label: '高风险', value: data.kpi.high.toLocaleString(), sub: '需立即处置', color: '#f56c6c' },
    { label: '中风险', value: data.kpi.mid.toLocaleString(), sub: '需关注', color: '#e6a23c' },
    { label: '低风险', value: data.kpi.low.toLocaleString(), sub: '正常', color: '#67c23a' },
    { label: '高风险占比', value: ((data.kpi.high / data.kpi.total) * 100).toFixed(1) + '%', sub: '占在册老人比例', color: '#f56c6c' },
    { label: '待处置', value: (data.kpi.high - data.kpi.disposed).toLocaleString(), sub: '高风险中未生成工单', color: '#e6a23c' }
  ]
  highList.value = data.high_list

  const type = safeInit(typeRef.value)
  if (type) {
    type.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} 人（{d}%）' },
      series: [{ type: 'pie', radius: ['40%', '65%'], data: data.type_dist, color: CHART.series }]
    })
  }

  const score = safeInit(scoreRef.value)
  if (score) {
    score.setOption({
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: data.score_dist.map(d => d.name) },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: data.score_dist.map(d => d.value), itemStyle: { color: CHART.danger, borderRadius: [4, 4, 0, 0] } }]
    })
  }

  const age = safeInit(ageRef.value)
  if (age) {
    age.setOption({
      grid: { left: 60, right: 20, top: 20, bottom: 30 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: data.age_risk.map(d => d.name), axisLabel: { rotate: 20 } },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: data.age_risk.map(d => d.value), itemStyle: { color: CHART.warning, borderRadius: [4, 4, 0, 0] } }]
    })
  }

  const dist = safeInit(districtRef.value)
  if (dist) {
    const d = data.district_risk
    dist.setOption({
      grid: { left: 100, right: 40, top: 10, bottom: 30 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'value', name: '人' },
      yAxis: { type: 'category', data: d.map(x => x.district).reverse() },
      series: [{ type: 'bar', data: d.map(x => x.high).reverse(), itemStyle: { color: CHART.danger, borderRadius: [0, 4, 4, 0] } }]
    })
  }
})

onBeforeUnmount(() => {
  disposed = true
  charts.forEach(c => c.dispose())
  charts.length = 0
})
</script>
