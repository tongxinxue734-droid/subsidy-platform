<template>
  <div class="page-container" ref="pageRef">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px">
      <div style="font-size:16px; font-weight:600">监管驾驶舱</div>
      <el-button @click="toggleFullscreen">🖥️ 大屏模式</el-button>
    </div>
    <el-alert type="warning" show-icon :closable="false" style="margin-bottom:16px">
      <template #title>
        认证到期提醒：{{ certifyExpired }} 人认证过期，请及时完成年度复审
        <el-button link type="primary" style="margin-left:8px" @click="router.push('/certify')">去复审 →</el-button>
      </template>
    </el-alert>
    <el-row :gutter="16">
      <el-col :span="6" v-for="k in kpis" :key="k.label">
        <div class="kpi-card" :style="{ '--c': k.color }">
          <div class="kpi-icon">{{ k.icon }}</div>
          <div class="kpi-body">
            <div class="kpi-label">{{ k.label }}</div>
            <div class="kpi-value">{{ k.value }}</div>
            <div class="kpi-sub">{{ k.sub }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="6" v-for="a in alertCards" :key="a.label">
        <div class="kpi-card clickable" :style="{ '--c': a.color }" @click="goAudit">
          <div class="kpi-icon">{{ a.icon }}</div>
          <div class="kpi-body">
            <div class="kpi-label">{{ a.label }}</div>
            <div class="kpi-value">{{ a.value }}</div>
            <div class="kpi-sub">{{ a.sub }} · 点击进入稽核</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="16">
        <div class="panel">
          <div class="panel-title">月度发放趋势</div>
          <div ref="trendRef" class="chart" style="height:320px"></div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="panel">
          <div class="panel-title">受益老人年龄结构</div>
          <div ref="ageRef" class="chart" style="height:320px"></div>
        </div>
      </el-col>
    </el-row>

    <div class="panel">
      <div class="panel-title">西安各区县受益老人分布（点击区县下钻街道）</div>
      <div ref="districtRef" class="chart" style="height:420px"></div>
    </div>

    <el-dialog v-model="drillVisible" :title="`${drillName} · 街道受益老人分布`" width="480px">
      <el-table :data="drillItems" border size="small" max-height="400">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="street" label="街道" />
        <el-table-column prop="count" label="受益老人" width="110">
          <template #default="{ row }">{{ row.count.toLocaleString() }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import request from '../api'
import xianGeo from '../assets/xian.json'
import { CHART } from '../utils/palette'

echarts.registerMap('xian', xianGeo)

const AGG = { '高新区': '雁塔区', '经开区': '未央区', '国际港务区': '灞桥区', '西咸新区': '长安区' }

function buildMapData(dist) {
  const m = {}
  for (const d of dist) {
    const k = AGG[d.name] || d.name
    m[k] = (m[k] || 0) + d.value
  }
  return Object.entries(m).map(([name, value]) => ({ name, value }))
}

const router = useRouter()

function goAudit() { router.push('/audit') }

const kpis = ref([])
const alertCards = ref([])
const trendRef = ref()
const ageRef = ref()
const districtRef = ref()
const charts = []
let disposed = false

const certifyExpired = ref(0)
const drillVisible = ref(false)
const drillName = ref('')
const drillItems = ref([])
const pageRef = ref()

function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen()
  else pageRef.value?.requestFullscreen()
}

function safeInit(el) {
  if (disposed || !el) return null
  const c = echarts.init(el)
  charts.push(c)
  return c
}

onMounted(async () => {
  const data = await request.get('/dashboard')
  if (disposed) return

  kpis.value = [
    { label: '累计发放金额', value: `${(data.kpi.total_amount / 10000).toFixed(2)} 亿元`, sub: '2025-01 至今', color: '#409eff', icon: '💰' },
    { label: '本月发放', value: `${data.kpi.latest_amount} 万元`, sub: data.kpi.latest_month, color: '#67c23a', icon: '📅' },
    { label: '受益老人', value: `${data.kpi.total_elders.toLocaleString()} 人`, sub: '70 周岁以上', color: '#e6a23c', icon: '👴' },
    { label: '资格认证率', value: `${data.kpi.cert_rate}%`, sub: '已认证占比', color: '#f56c6c', icon: '✅' }
  ]
  alertCards.value = [
    { label: '红色预警（冒领/重复）', value: data.alerts.red, sub: '紧急', color: '#f56c6c', icon: '🚨' },
    { label: '橙色预警（认证过期）', value: data.alerts.orange, sub: '较重', color: '#e6a23c', icon: '🟠' },
    { label: '黄色预警（信息异常）', value: data.alerts.yellow, sub: '一般', color: '#f7ba2a', icon: '🟡' },
    { label: '疑点合计', value: data.alerts.total, sub: '待稽核', color: '#909399', icon: '⚠️' }
  ]
  certifyExpired.value = data.alerts.orange

  const trend = safeInit(trendRef.value)
  if (trend) {
    trend.setOption({
      grid: { left: 55, right: 20, top: 20, bottom: 50 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: data.trend.map(t => t.month), axisLabel: { rotate: 45, interval: 1, fontSize: 10, color: '#606266' } },
      yAxis: { type: 'value', name: '万元' },
      series: [{ type: 'line', smooth: true, data: data.trend.map(t => t.amount), itemStyle: { color: '#409eff' }, areaStyle: { opacity: 0.15 } }]
    })
  }

  const age = safeInit(ageRef.value)
  if (age) {
    age.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: ['45%', '70%'], data: data.age_structure, label: { formatter: '{b}\n{c} 人' }, color: CHART.ageBands }]
    })
  }

  const district = safeInit(districtRef.value)
  if (district) {
    const mapData = buildMapData(data.district_dist)
    const maxV = mapData.length ? Math.max(...mapData.map(d => d.value)) : 1
    district.setOption({
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>受益老人 ${(p.value || 0).toLocaleString()} 人` },
      visualMap: { min: 0, max: maxV, left: 12, bottom: 12, text: ['高', '低'], calculable: true, inRange: { color: CHART.map } },
      series: [{
        type: 'map', map: 'xian', data: mapData, roam: false,
        label: { show: true, fontSize: 9, color: '#333' },
        itemStyle: { borderColor: '#fff', borderWidth: 1, areaColor: '#eef2f7' },
        emphasis: { label: { show: true, fontWeight: 'bold' }, itemStyle: { areaColor: '#ffd04b' } }
      }]
    })

    district.on('click', async (params) => {
      const name = params.name
      if (!name) return
      const r = await request.get(`/district/${name}/streets`)
      drillName.value = name
      drillItems.value = r.items
      drillVisible.value = true
    })
  }
})

onBeforeUnmount(() => {
  disposed = true
  charts.forEach(c => c.dispose())
  charts.length = 0
})
</script>

<style scoped>
.kpi-card {
  display: flex; align-items: center; gap: 14px; background: #fff;
  border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(0,21,41,0.05);
  border: 1px solid #eef0f4; position: relative; overflow: hidden;
  transition: box-shadow .2s, transform .2s;
}
.kpi-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--c); }
.kpi-card:hover { box-shadow: 0 6px 16px rgba(0,21,41,0.1); transform: translateY(-2px); }
.kpi-icon { font-size: 30px; flex-shrink: 0; }
.kpi-label { font-size: 13px; color: #909399; }
.kpi-value { font-size: 24px; font-weight: 700; color: var(--c); margin: 4px 0 2px; }
.kpi-sub { font-size: 12px; color: #c0c4cc; }
.clickable { cursor: pointer; }
</style>
