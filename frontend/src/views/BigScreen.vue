<template>
  <div class="bigscreen">
    <div class="bs-mobile-tip">📱 数据大屏请在电脑或横屏模式下查看</div>
    <div class="bs-header">
      <div class="bs-title">🏛️ 西安市高龄补贴监管平台 · 数据大屏</div>
      <div class="bs-time">{{ now }}</div>
      <el-button link class="bs-back" @click="router.push('/workbench')">← 返回工作台</el-button>
    </div>

    <div class="bs-kpis">
      <div class="bs-kpi" v-for="k in kpis" :key="k.label">
        <div class="bs-kpi-icon">{{ k.icon }}</div>
        <div>
          <div class="bs-kpi-label">{{ k.label }}</div>
          <div class="bs-kpi-value" :style="{ color: k.color }">{{ k.value }}</div>
        </div>
      </div>
    </div>

    <div class="bs-alerts">
      <div class="bs-alert" v-for="a in alerts" :key="a.label">
        <div class="bs-alert-value" :style="{ color: a.color }">{{ a.value }}</div>
        <div class="bs-alert-label">{{ a.label }}</div>
      </div>
    </div>

    <div class="bs-grid">
      <div class="bs-card bs-map">
        <div class="bs-panel-title">西安区县受益老人分布</div>
        <div ref="mapRef" class="bs-chart"></div>
      </div>
      <div class="bs-card">
        <div class="bs-panel-title">月度发放趋势</div>
        <div ref="trendRef" class="bs-chart"></div>
      </div>
      <div class="bs-card">
        <div class="bs-panel-title">年龄结构</div>
        <div ref="ageRef" class="bs-chart"></div>
      </div>
      <div class="bs-card">
        <div class="bs-panel-title">资格认证率</div>
        <div ref="gaugeRef" class="bs-chart"></div>
      </div>
      <div class="bs-card">
        <div class="bs-panel-title">监管健康度</div>
        <div ref="radarRef" class="bs-chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import request from '../api'
import xianGeo from '../assets/xian.json'

echarts.registerMap('xian', xianGeo)
const router = useRouter()

const AGG = { '高新区': '雁塔区', '经开区': '未央区', '国际港务区': '灞桥区', '西咸新区': '长安区' }
const now = ref('')
const kpis = ref([])
const alerts = ref([])
const mapRef = ref()
const trendRef = ref()
const ageRef = ref()
const gaugeRef = ref()
const radarRef = ref()
const charts = []
const chartCache = new Map()
let disposed = false
let timer = null
let dataTimer = null

function buildMapData(dist) {
  const m = {}
  for (const d of dist) { const k = AGG[d.name] || d.name; m[k] = (m[k] || 0) + d.value }
  return Object.entries(m).map(([name, value]) => ({ name, value }))
}

function getChart(el) {
  if (disposed || !el) return null
  if (!chartCache.has(el)) {
    chartCache.set(el, echarts.init(el))
    charts.push(chartCache.get(el))
  }
  return chartCache.get(el)
}

function resizeAll() {
  charts.forEach(c => c.resize())
}

function tickTime() {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  now.value = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

async function load() {
  const data = await request.get('/dashboard')
  if (disposed) return
  await nextTick()
  kpis.value = [
    { label: '累计发放金额', value: `${(data.kpi.total_amount / 10000).toFixed(2)} 亿元`, color: '#4fd1ff', icon: '💰' },
    { label: '本月发放', value: `${data.kpi.latest_amount} 万元`, color: '#67e0a3', icon: '📅' },
    { label: '受益老人', value: `${data.kpi.total_elders.toLocaleString()} 人`, color: '#ffd166', icon: '👴' },
    { label: '资格认证率', value: `${data.kpi.cert_rate}%`, color: '#ff7a7a', icon: '✅' }
  ]
  alerts.value = [
    { label: '红色预警 · 冒领/重复', value: data.alerts.red, color: '#ff5b5b' },
    { label: '橙色预警 · 认证过期', value: data.alerts.orange, color: '#ffb020' },
    { label: '黄色预警 · 信息异常', value: data.alerts.yellow, color: '#f7d44c' },
    { label: '疑点合计', value: data.alerts.total, color: '#9aa8c7' }
  ]

  const map = getChart(mapRef.value)
  if (map) {
    const mapData = buildMapData(data.district_dist)
    const maxV = mapData.length ? Math.max(...mapData.map(d => d.value)) : 1
    map.setOption({
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>${(p.value || 0).toLocaleString()} 人` },
      visualMap: { min: 0, max: maxV, left: 8, bottom: 8, text: ['高', '低'], calculable: true, inRange: { color: ['#14324f', '#1e6fbf', '#3fd1ff'] }, textStyle: { color: '#c8d4e8' } },
      series: [{
        type: 'map', map: 'xian', data: mapData, roam: false,
        label: { show: true, fontSize: 9, color: '#cfe0ff' },
        itemStyle: { borderColor: '#0a1a3a', borderWidth: 1, areaColor: '#173a63' },
        emphasis: { label: { show: true, color: '#fff' }, itemStyle: { areaColor: '#ffd166' } }
      }]
    })
  }

  const trend = getChart(trendRef.value)
  if (trend) {
    trend.setOption({
      grid: { left: 52, right: 20, top: 24, bottom: 40 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: data.trend.map(t => t.month), axisLabel: { color: '#9aa8c7', fontSize: 9, interval: 1, rotate: 45 }, axisLine: { lineStyle: { color: '#2c4a74' } } },
      yAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#9aa8c7' }, axisLabel: { color: '#9aa8c7' }, splitLine: { lineStyle: { color: '#1c3560' } } },
      series: [{ type: 'line', smooth: true, data: data.trend.map(t => t.amount), itemStyle: { color: '#4fd1ff' }, areaStyle: { color: 'rgba(79,209,255,0.18)' } }]
    })
  }

  const age = getChart(ageRef.value)
  if (age) {
    age.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} 人（{d}%）' },
      legend: { bottom: 0, textStyle: { color: '#9aa8c7' } },
      series: [{ type: 'pie', radius: ['42%', '66%'], data: data.age_structure, label: { color: '#cfe0ff', formatter: '{b}\n{d}%' }, color: ['#4fd1ff', '#67e0a3', '#ffd166', '#ff7a7a'] }]
    })
  }

  const gauge = getChart(gaugeRef.value)
  if (gauge) {
    gauge.setOption({
      series: [{
        type: 'gauge', radius: '92%', center: ['50%', '56%'],
        progress: { show: true, width: 14, itemStyle: { color: '#4fd1ff' } },
        axisLine: { lineStyle: { width: 14, color: [[1, '#1c3560']] } },
        axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
        pointer: { show: false },
        detail: { valueAnimation: true, fontSize: 30, color: '#4fd1ff', formatter: '{value}%', offsetCenter: [0, 0] },
        data: [{ value: data.kpi.cert_rate }]
      }]
    })
  }

  const radar = getChart(radarRef.value)
  if (radar) {
    radar.setOption({
      radar: {
        indicator: ['认证率', '覆盖率', '发放及时率', '风险控制', '工单销号率'].map(n => ({ name: n, max: 100 })),
        radius: '66%',
        axisName: { color: '#9aa8c7', fontSize: 10 },
        splitLine: { lineStyle: { color: '#1c3560' } },
        splitArea: { areaStyle: { color: ['rgba(79,209,255,0.03)', 'rgba(79,209,255,0.06)'] } }
      },
      series: [{
        type: 'radar',
        data: [{
          value: [data.kpi.cert_rate, 100, 98.5,
                  100 - (data.alerts.total / data.kpi.total_elders * 100), 70],
          name: '健康度', areaStyle: { color: 'rgba(79,209,255,0.3)' },
          lineStyle: { color: '#4fd1ff' }, itemStyle: { color: '#4fd1ff' }
        }]
      }]
    })
  }

  resizeAll()
  setTimeout(resizeAll, 300)
}

onMounted(() => {
  tickTime()
  timer = setInterval(tickTime, 1000)
  load()
  dataTimer = setInterval(load, 30000)
  window.addEventListener('resize', resizeAll)
})

onBeforeUnmount(() => {
  disposed = true
  if (timer) clearInterval(timer)
  if (dataTimer) clearInterval(dataTimer)
  window.removeEventListener('resize', resizeAll)
  charts.forEach(c => c.dispose())
  charts.length = 0
})
</script>

<style scoped>
.bs-mobile-tip {
  display: none; position: fixed; inset: 0; z-index: 999;
  background: #050f22; color: #4fd1ff; font-size: 16px;
  align-items: center; justify-content: center; text-align: center; padding: 20px;
}
@media (max-width: 768px) {
  .bs-mobile-tip { display: flex; }
}
.bigscreen {
  height: 100vh; display: flex; flex-direction: column; overflow: hidden;
  background: radial-gradient(circle at 50% 0%, #0e2a55 0%, #081833 55%, #050f22 100%);
  color: #fff; padding: 0 16px;
}
.bs-header {
  flex-shrink: 0; display: flex; align-items: center; justify-content: space-between;
  padding: 14px 4px; border-bottom: 1px solid rgba(79,209,255,0.2);
}
.bs-title { font-size: 20px; font-weight: 700; letter-spacing: 2px; text-shadow: 0 0 12px rgba(79,209,255,0.5); }
.bs-time { font-size: 15px; color: #4fd1ff; font-variant-numeric: tabular-nums; }
.bs-back { color: #cfe0ff; }

.bs-kpis { flex-shrink: 0; display: flex; gap: 12px; margin: 14px 0; }
.bs-kpi {
  flex: 1; display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  background: rgba(13,35,72,0.7); border: 1px solid rgba(79,209,255,0.18); border-radius: 10px;
}
.bs-kpi-icon { font-size: 26px; }
.bs-kpi-label { font-size: 12px; color: #9aa8c7; }
.bs-kpi-value { font-size: 22px; font-weight: 700; line-height: 1.2; }

.bs-alerts { flex-shrink: 0; display: flex; gap: 12px; margin-bottom: 14px; }
.bs-alert {
  flex: 1; display: flex; align-items: center; justify-content: space-between; padding: 10px 16px;
  background: rgba(13,35,72,0.7); border: 1px solid rgba(79,209,255,0.18); border-radius: 10px;
}
.bs-alert-value { font-size: 24px; font-weight: 700; }
.bs-alert-label { font-size: 12px; color: #9aa8c7; }

.bs-grid {
  flex: 1; min-height: 0; display: grid;
  grid-template-columns: 1.5fr 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 12px;
}
.bs-card {
  display: flex; flex-direction: column; min-height: 0;
  background: rgba(13,35,72,0.7); border: 1px solid rgba(79,209,255,0.18);
  border-radius: 10px; padding: 12px 14px;
}
.bs-map { grid-row: span 2; }
.bs-panel-title { flex-shrink: 0; font-size: 13px; color: #cfe0ff; font-weight: 600; margin-bottom: 8px; }
.bs-chart { flex: 1; min-height: 0; width: 100%; }
</style>
