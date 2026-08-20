<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 资金监管 -->
      <el-tab-pane label="资金监管" name="fund">
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="stat-card">
              <div class="stat-label">累计发放金额</div>
              <div class="stat-value" style="color:#409eff">{{ (totalAmount / 10000).toFixed(2) }} 亿元</div>
              <div class="stat-sub">财政分级负担</div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="stat-card">
              <div class="stat-label">覆盖区县</div>
              <div class="stat-value" style="color:#67c23a">{{ districtFund.length }}</div>
              <div class="stat-sub">行政区划</div>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="12">
            <div class="panel">
              <div class="panel-title">市、区县财政分担比例</div>
              <el-table :data="splitGroups" border stripe size="small">
                <el-table-column prop="分担比例" label="分担比例" width="180" />
                <el-table-column label="覆盖区县">
                  <template #default="{ row }">{{ row.区县.join('、') }}</template>
                </el-table-column>
              </el-table>
              <div class="panel-title" style="margin-top:18px">资金来源（省/市/区县）</div>
              <el-table :data="fundSources" border stripe size="small">
                <el-table-column prop="年龄段" label="年龄段" width="140" />
                <el-table-column prop="省财政负担" label="省财政" />
                <el-table-column prop="市、区县财政负担" label="市、区县财政" />
              </el-table>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="panel">
              <div class="panel-title">各区县资金拨付情况</div>
              <div ref="fundRef" class="chart" style="height:420px"></div>
            </div>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 绩效评价 -->
      <el-tab-pane label="绩效评价" name="performance">
        <el-alert title="预算执行率为演示参考值；及时到账率按区县整改情况动态计算" type="info" show-icon :closable="false" style="margin-bottom:16px" />
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-label">累计发放金额</div>
              <div class="stat-value" style="color:#409eff">{{ (perf.total_amount / 10000).toFixed(2) }} 亿元</div>
              <div class="stat-sub">近 {{ perf.months }} 个月</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-label">月均发放</div>
              <div class="stat-value" style="color:#e6a23c">{{ perf.avg_month }} 万元</div>
              <div class="stat-sub">全市月均</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-label">预算执行率</div>
              <div class="stat-value" style="color:#67c23a">{{ perf.exec_rate }}%</div>
              <div class="stat-sub">执行进度</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-label">及时到账率</div>
              <div class="stat-value" style="color:#f56c6c">{{ perf.on_time_rate }}%</div>
              <div class="stat-sub">按时足额发放</div>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="12">
            <div class="panel">
              <div class="panel-title">全市发放汇总</div>
              <el-table :data="cityStats" border stripe size="small">
                <el-table-column prop="周期" label="周期" width="130" />
                <el-table-column prop="发放金额" label="发放金额" width="110" />
                <el-table-column prop="受益老人" label="受益老人" width="110" />
                <el-table-column prop="70-79 周岁" label="70-79" width="90" />
                <el-table-column prop="80-89 周岁" label="80-89" width="90" />
                <el-table-column prop="90-99 周岁" label="90-99" width="90" />
                <el-table-column prop="百岁及以上" label="百岁+" width="90" />
              </el-table>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="panel">
              <div class="panel-title">资金发放问题整改</div>
              <el-table :data="rectifications" border stripe size="small">
                <el-table-column prop="区县" label="区县" width="90" />
                <el-table-column prop="问题" label="问题" />
                <el-table-column label="状态" width="180">
                  <template #default>
                    <el-tag type="success" size="small">✓ 已整改</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import request from '../api'
import { CHART } from '../utils/palette'

const activeTab = ref('fund')
const totalAmount = ref(0)
const splitGroups = ref([])
const fundSources = ref([])
const districtFund = ref([])
const perf = ref({ total_amount: 0, avg_month: 0, months: 0, exec_rate: 0, on_time_rate: 0 })
const cityStats = ref([])
const rectifications = ref([])
const fundRef = ref()
let chart = null
let disposed = false

onMounted(async () => {
  const data = await request.get('/fund')
  const pdata = await request.get('/performance')
  if (disposed) return
  totalAmount.value = data.total_amount
  splitGroups.value = data.split_groups
  fundSources.value = data.fund_sources
  districtFund.value = data.district_fund
  perf.value = { ...pdata.kpi }
  cityStats.value = pdata.city_stats
  rectifications.value = pdata.rectifications

  if (!fundRef.value) return
  chart = echarts.init(fundRef.value)
  chart.setOption({
    grid: { left: 100, right: 30, top: 10, bottom: 30 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value', name: '万元' },
    yAxis: { type: 'category', data: districtFund.value.map(d => d.district).reverse() },
    series: [{
      type: 'bar', data: districtFund.value.map(d => Math.round(d.amount)).reverse(),
      itemStyle: { color: CHART.warning, borderRadius: [0, 4, 4, 0] }
    }]
  })
})

onBeforeUnmount(() => { disposed = true; if (chart) chart.dispose() })
</script>

<style scoped>
.stat-label { font-size: 13px; color: #909399; }
.stat-value { font-size: 26px; font-weight: 700; margin: 8px 0 4px; }
.stat-sub { font-size: 12px; color: #c0c4cc; }
</style>
