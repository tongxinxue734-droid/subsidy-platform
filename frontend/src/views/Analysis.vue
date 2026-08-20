<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">各区县受益老人分布</div>
          <div ref="districtRef" class="chart" style="height:340px"></div>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">年龄段 × 区县交叉分析</div>
          <div ref="crossRef" class="chart" style="height:340px"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">年龄结构</div>
          <div ref="ageRef" class="chart" style="height:300px"></div>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">性别结构</div>
          <div ref="genderRef" class="chart" style="height:300px"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :xs="24" :md="8">
        <div class="panel">
          <div class="panel-title">申领渠道分布</div>
          <div ref="channelRef" class="chart" style="height:300px"></div>
        </div>
      </el-col>
      <el-col :xs="24" :md="16">
        <div class="panel">
          <div class="panel-title">未来 5 年高龄人口与资金需求预测</div>
          <div ref="projectRef" class="chart" style="height:300px"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import request from '../api'
import { CHART } from '../utils/palette'

const districtRef = ref()
const crossRef = ref()
const ageRef = ref()
const genderRef = ref()
const channelRef = ref()
const projectRef = ref()
const charts = []
let disposed = false

function safeInit(el) {
  if (disposed || !el) return null
  const c = echarts.init(el)
  charts.push(c)
  return c
}

onMounted(async () => {
  const data = await request.get('/analysis')
  if (disposed) return

  const district = safeInit(districtRef.value)
  if (district) {
    district.setOption({
      grid: { left: 90, right: 20, top: 10, bottom: 30 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: data.district_dist.map(d => d.name).reverse() },
      series: [{ type: 'bar', data: data.district_dist.map(d => d.value).reverse(), itemStyle: { color: CHART.primary, borderRadius: [0, 4, 4, 0] } }]
    })
  }

  const districts = data.district_dist.map(d => d.name)
  const ageBands = [...new Set(data.cross.map(c => c.age_band))]
  const crossSeries = ageBands.map((band, i) => ({
    name: band, type: 'bar', stack: 'total',
    data: districts.map(d => {
      const row = data.cross.find(c => c.district === d && c.age_band === band)
      return row ? row.count : 0
    }),
    itemStyle: { color: CHART.ageBands[i] }
  }))
  const cross = safeInit(crossRef.value)
  if (cross) {
    cross.setOption({
      grid: { left: 60, right: 20, top: 40, bottom: 60 },
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      xAxis: { type: 'category', data: districts, axisLabel: { rotate: 45 } },
      yAxis: { type: 'value' },
      series: crossSeries
    })
  }

  const age = safeInit(ageRef.value)
  if (age) {
    age.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: ['40%', '65%'], data: data.age_structure, color: CHART.ageBands }]
    })
  }

  const gender = safeInit(genderRef.value)
  if (gender) {
    gender.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: '65%', data: data.gender_structure, color: [CHART.primary, CHART.danger], label: { formatter: '{b}: {c}' } }]
    })
  }

  const channel = safeInit(channelRef.value)
  if (channel) {
    channel.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} 人（{d}%）' },
      series: [{ type: 'pie', radius: ['40%', '65%'], data: data.channel_dist, color: CHART.series }]
    })
  }

  const project = safeInit(projectRef.value)
  if (project) {
    project.setOption({
      grid: { left: 60, right: 60, top: 40, bottom: 30 },
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      xAxis: { type: 'category', data: data.projection.map(p => p.year) },
      yAxis: [
        { type: 'value', name: '人数' },
        { type: 'value', name: '万元/月' }
      ],
      series: [
        { name: '高龄人口', type: 'bar', data: data.projection.map(p => p.people), itemStyle: { color: CHART.primary, borderRadius: [4, 4, 0, 0] } },
        { name: '月资金需求(万元)', type: 'line', yAxisIndex: 1, smooth: true, data: data.projection.map(p => p.fund), itemStyle: { color: CHART.warning } }
      ]
    })
  }
})

onBeforeUnmount(() => {
  disposed = true
  charts.forEach(c => c.dispose())
  charts.length = 0
})
</script>
